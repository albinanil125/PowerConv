import os
import io
import time
import pandas as pd
from werkzeug.utils import secure_filename

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from PIL import Image, ImageEnhance, ImageFilter
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)
app.secret_key = "powerconv_bulletproof_master_key_2026"

UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
STATIC_FOLDER = 'static'

for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER, STATIC_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 256MB max limit

def cleanup_old_files():
    """Automatically deletes files older than 2 hours to prevent disk bloat."""
    for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER]:
        if os.path.exists(folder):
            now = time.time()
            for f in os.listdir(folder):
                f_path = os.path.join(folder, f)
                if os.path.isfile(f_path) and (now - os.path.getmtime(f_path) > 7200):
                    try:
                        os.remove(f_path)
                    except:
                        pass

def render_glass_page(title, body_content):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PowerConv - {title}</title>
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%239333ea'/><text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-size='60' fill='%23ffffff'>⚡</text></svg>">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; }}
            body {{
                min-height: 100vh;
                background: #0d001a url('/static/bg.jpg') center/cover no-repeat fixed, 
                            linear-gradient(135deg, #0d001a 0%, #1a0033 50%, #0d001a 100%);
                background-blend-mode: overlay;
                display: flex; align-items: center; justify-content: center;
                color: #ffffff; padding: 20px;
            }}
            .glass-card {{
                background: rgba(22, 0, 44, 0.92);
                backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 28px; padding: 40px;
                max-width: 860px; width: 100%;
                box-shadow: 0 35px 70px rgba(0, 0, 0, 0.85);
                text-align: center;
            }}
            .brand-logo {{
                display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 15px;
            }}
            .logo-icon {{
                width: 44px; height: 44px; background: linear-gradient(135deg, #9333ea, #ec4899);
                border-radius: 12px; display: flex; align-items: center; justify-content: center;
                font-size: 22px; font-weight: 800; color: #fff;
            }}
            .brand-logo h1 {{ font-size: 28px; font-weight: 800; color: #fff; }}
            .brand-logo span {{
                background: linear-gradient(135deg, #a855f7, #ec4899);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            }}
            .btn-primary {{
                width: 100%; background: linear-gradient(135deg, #9333ea, #c084fc);
                color: white; border: none; padding: 15px 30px; border-radius: 14px;
                font-size: 16px; font-weight: 700; cursor: pointer; text-decoration: none;
                display: inline-block; box-shadow: 0 10px 25px rgba(147, 51, 234, 0.4);
                transition: all 0.3s ease;
            }}
            .btn-primary:hover {{ transform: translateY(-2px); background: linear-gradient(135deg, #a855f7, #e879f9); }}
            .btn-success {{
                background: linear-gradient(135deg, #059669, #34d399);
                box-shadow: 0 10px 25px rgba(5, 150, 105, 0.4);
            }}
            .back-link {{ color: #c084fc; text-decoration: none; font-size: 14px; margin-top: 20px; display: inline-block; font-weight: 600; }}
            .back-link:hover {{ text-decoration: underline; color: #fff; }}
        </style>
    </head>
    <body>
        <div class="glass-card">
            <div class="brand-logo">
                <div class="logo-icon">⚡</div>
                <h1>Power<span>Conv</span></h1>
            </div>
            {body_content}
        </div>
    </body>
    </html>
    """

@app.route('/')
def home():
    cleanup_old_files()
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    tool_type = request.form.get('tool_type', 'converter')
    
    # Handle PDF Merge (Multiple Files)
    if tool_type == 'pdf' and request.form.get('pdf_action') == 'merge':
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            return redirect('/')
        
        try:
            writer = PdfWriter()
            saved_count = 0
            for f in files:
                if f and f.filename:
                    filename = secure_filename(f.filename)
                    f_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    f.save(f_path)
                    reader = PdfReader(f_path)
                    for page in reader.pages:
                        writer.add_page(page)
                    saved_count += 1
            
            output_filename = f"merged_{int(time.time())}.pdf"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            
            return render_glass_page("Success", f"""
                <div style="font-size: 54px; margin-bottom: 12px;">✨</div>
                <h2 style="color: #34d399; margin-bottom: 10px;">PDFs Merged Successfully!</h2>
                <p style="color: #a78bfa; font-size: 14px; margin-bottom: 25px;">Successfully merged {saved_count} documents.</p>
                <a href="/download/{output_filename}" class="btn-primary btn-success">Download Merged PDF</a><br><br>
                <a href="/" class="back-link">← Return to Homepage</a>
            """)
        except Exception as e:
            return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Merge Error: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

    # Standard Single File Upload
    if 'file' not in request.files:
        return redirect('/')
    file = request.files['file']
    if file.filename == '':
        return redirect('/')
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    if tool_type == 'converter':
        sub_type = request.form.get('conv_sub_type', 'img_to_png')
        return redirect(url_for('execute_convert_direct', filename=filename, sub_type=sub_type))
    
    elif tool_type == 'pdf':
        action = request.form.get('pdf_action', 'edit')
        if action == 'compress':
            return redirect(url_for('execute_pdf_compress', filename=filename))
        return redirect(url_for('process_pdf_edit', filename=filename))
    
    elif tool_type == 'image':
        return redirect(url_for('process_image_studio', filename=filename))
    
    elif tool_type == 'video':
        action = request.form.get('video_action', 'compress')
        return redirect(url_for('process_video_studio', filename=filename, action=action))

    return redirect('/')

@app.route('/execute/convert-direct/<filename>', methods=['GET', 'POST'])
def execute_convert_direct(filename):
    sub_type = request.args.get('sub_type', 'img_to_png')
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(input_path):
        return redirect('/')

    base_name, ext = os.path.splitext(filename)
    
    # Map box selection to target format
    target_format = 'png'
    if sub_type == 'img_to_jpg': target_format = 'jpeg'
    elif sub_type == 'img_to_webp': target_format = 'webp'
    elif sub_type == 'img_to_pdf': target_format = 'pdf'
    elif sub_type == 'sheet_to_csv': target_format = 'csv'
    elif sub_type == 'sheet_to_xlsx': target_format = 'xlsx'
    elif sub_type == 'sheet_to_json': target_format = 'json'
    elif sub_type in ['pdf_to_txt', 'doc_to_txt']: target_format = 'txt'

    output_filename = f"{base_name}_converted.{target_format if target_format != 'jpeg' else 'jpg'}"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        if ext.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
            with Image.open(input_path) as img:
                if target_format == 'pdf':
                    img.convert('RGB').save(output_path, "PDF")
                else:
                    img.save(output_path, target_format.upper() if target_format != 'jpeg' else 'JPEG')
        elif ext.lower() in ['.xlsx', '.xls', '.csv']:
            df = pd.read_csv(input_path) if ext.lower() == '.csv' else pd.read_excel(input_path)
            if target_format == 'csv': df.to_csv(output_path, index=False)
            elif target_format == 'xlsx': df.to_excel(output_path, index=False)
            elif target_format == 'json': df.to_json(output_path, orient='records', indent=4)
        elif ext.lower() == '.pdf' and target_format == 'txt':
            reader = PdfReader(input_path)
            text = "\n".join([p.extract_text() or "" for p in reader.pages])
            with open(output_path, 'w', encoding='utf-8') as f: f.write(text)
        elif ext.lower() == '.docx' and target_format == 'txt':
            import docx
            doc = docx.Document(input_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            with open(output_path, 'w', encoding='utf-8') as f: f.write(text)
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Conversion Failed: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

    return render_glass_page("Success", f"""
        <div style="font-size: 54px; margin-bottom: 12px;">✨</div>
        <h2 style="color: #34d399; margin-bottom: 10px;">Conversion Complete!</h2>
        <p style="color: #a78bfa; font-size: 14px; margin-bottom: 20px;">Converted <strong>{filename}</strong> successfully.</p>
        <a href="/download/{output_filename}" class="btn-primary btn-success">Download Converted File</a><br><br>
        <a href="/" class="back-link">← Return to Homepage</a>
    """)

@app.route('/process/pdf-edit/<filename>')
def process_pdf_edit(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Invalid PDF File</h3><a href='/' class='back-link'>← Back</a>")
    
    slots_html = ""
    for i in range(total_pages):
        thumb_html = '<div style="width:90px; height:120px; background:#000; border-radius:6px; display:flex; align-items:center; justify-content:center; color:#666; font-size:11px;">Page</div>'
        if FITZ_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                pix = doc[i].get_pixmap(dpi=100)
                thumb_filename = f"thumb_{os.path.splitext(filename)[0]}_p{i}.png"
                pix.save(os.path.join(app.config['STATIC_FOLDER'], thumb_filename))
                thumb_html = f'<img src="/static/{thumb_filename}" style="width:90px; height:120px; object-fit:contain; background:#000; border-radius:6px;">'
            except: pass

        slots_html += f"""
            <div style="background:rgba(13,0,26,0.7); border:1px solid rgba(168,85,247,0.3); border-radius:12px; padding:12px; margin-bottom:10px; display:flex; align-items:center; gap:15px;">
                {thumb_html}
                <div style="flex:1; text-align:left;">
                    <span style="background:#9333ea; color:white; padding:4px 10px; border-radius:15px; font-weight:700; font-size:12px;">Page {i+1}</span>
                    <input type="hidden" name="page_indices" value="{i}">
                    <label style="font-size:11px; margin-top:8px;">Rotate:</label>
                    <select name="page_rot_{i}" style="padding:6px; font-size:11px; margin:0;">
                        <option value="0">0°</option><option value="90">90° CW</option><option value="180">180°</option><option value="270">270° CW</option>
                    </select>
                </div>
            </div>
        """

    content = f"""
        <h2 style="font-size:22px; margin-bottom:8px;">Visual PDF Studio</h2>
        <p style="color:#a78bfa; margin-bottom:15px; font-size:13px;">Manage pages for <strong>{filename}</strong></p>
        <form action="/execute/pdf-edit/{filename}" method="POST">
            <div style="max-height:360px; overflow-y:auto; margin-bottom:15px;">{slots_html}</div>
            <button type="submit" class="btn-primary">Save Edited PDF</button>
        </form>
        <a href="/" class="back-link">← Return to Homepage</a>
    """
    return render_glass_page("PDF Studio", content)

@app.route('/execute/pdf-edit/<filename>', methods=['POST'])
def execute_pdf_edit(filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_filename = f"{os.path.splitext(filename)[0]}_edited.pdf"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        page_indices = request.form.getlist('page_indices')
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for p_idx_str in page_indices:
            idx = int(p_idx_str)
            page = reader.pages[idx]
            rot = int(request.form.get(f'page_rot_{idx}', 0))
            if rot != 0: page.rotate(rot)
            writer.add_page(page)

        with open(output_path, "wb") as f: writer.write(f)
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>PDF Edit Error: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

    return render_glass_page("Success", f"""
        <h2 style="color: #34d399; margin-bottom: 10px;">PDF Edited Successfully!</h2>
        <a href="/download/{output_filename}" class="btn-primary btn-success">Download PDF</a><br><br>
        <a href="/" class="back-link">← Return to Homepage</a>
    """)

@app.route('/execute/pdf-compress/<filename>')
def execute_pdf_compress(filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_filename = f"{os.path.splitext(filename)[0]}_compressed.pdf"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        writer.add_metadata({})
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Compression Error: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

    return render_glass_page("Success", f"""
        <h2 style="color: #34d399; margin-bottom: 10px;">PDF Compressed Successfully!</h2>
        <a href="/download/{output_filename}" class="btn-primary btn-success">Download Compressed PDF</a><br><br>
        <a href="/" class="back-link">← Return to Homepage</a>
    """)

@app.route('/process/image/<filename>')
def process_image_studio(filename):
    content = f"""
        <h2 style="font-size:22px; margin-bottom:10px;">Interactive Image Studio</h2>
        <p style="color:#a78bfa; margin-bottom:15px; font-size:13px;">Enhance <strong>{filename}</strong></p>
        <form action="/execute/image/{filename}" method="POST">
            <label>Width (px - Optional):</label><input type="number" name="width" placeholder="Leave empty for original">
            <label>Height (px - Optional):</label><input type="number" name="height" placeholder="Leave empty for original">
            <label>Brightness Factor (1.0 is Normal):</label><input type="range" name="brightness" min="0.5" max="2.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px;">
            <label>Contrast Factor (1.0 is Normal):</label><input type="range" name="contrast" min="0.5" max="2.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px;">
            <button type="submit" class="btn-primary">Save Enhanced Image</button>
        </form>
        <a href="/" class="back-link">← Return to Homepage</a>
    """
    return render_glass_page("Image Studio", content)

@app.route('/execute/image/<filename>', methods=['POST'])
def execute_image_studio(filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_filename = f"{os.path.splitext(filename)[0]}_enhanced{os.path.splitext(filename)[1]}"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        w = request.form.get('width', '').strip()
        h = request.form.get('height', '').strip()
        b = float(request.form.get('brightness', 1.0))
        c = float(request.form.get('contrast', 1.0))

        with Image.open(input_path) as img:
            if w.isdigit() and h.isdigit():
                img = img.resize((int(w), int(h)), Image.Resampling.LANCZOS)
            if b != 1.0: img = ImageEnhance.Brightness(img).enhance(b)
            if c != 1.0: img = ImageEnhance.Contrast(img).enhance(c)
            img.save(output_path)
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Image Processing Error: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

    return render_glass_page("Success", f"""
        <h2 style="color: #34d399; margin-bottom: 10px;">Image Enhanced Successfully!</h2>
        <a href="/download/{output_filename}" class="btn-primary btn-success">Download Image</a><br><br>
        <a href="/" class="back-link">← Return to Homepage</a>
    """)

@app.route('/process/video/<filename>')
def process_video_studio(filename):
    action = request.args.get('action', 'compress')
    content = f"""
        <h2 style="font-size:22px; margin-bottom:10px;">Video & Audio Studio</h2>
        <p style="color:#a78bfa; margin-bottom:15px; font-size:13px;">Action Selected: <strong>{action.upper()}</strong> on {filename}</p>
        <form action="/execute/video/{filename}" method="POST">
            <input type="hidden" name="action" value="{action}">
            <label>Target Format / Output:</label>
            <select name="format">
                <option value="mp4">MP4 Video (.mp4)</option>
                <option value="webm">WebM Video (.webm)</option>
                <option value="mp3">Extract Audio Only (.mp3)</option>
                <option value="gif">Animated GIF (.gif)</option>
            </select>
            <button type="submit" class="btn-primary" style="margin-top:15px;">Process Media File</button>
        </form>
        <a href="/" class="back-link">← Return to Homepage</a>
    """
    return render_glass_page("Video Studio", content)

@app.route('/execute/video/<filename>', methods=['POST'])
def execute_video_studio(filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    action = request.form.get('action', 'compress')
    target_format = request.form.get('format', 'mp4')
    output_filename = f"{os.path.splitext(filename)[0]}_processed.{target_format}"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(input_path)
        
        if action == 'resize':
            clip = clip.resize(height=720)
        elif action == 'compress':
            if clip.h > 720:
                clip = clip.resize(height=720)
        
        if target_format in ['mp4', 'webm']:
            clip.write_videofile(
                output_path, 
                codec='libx264' if target_format=='mp4' else 'libvpx', 
                audio_codec='aac', 
                bitrate="1000k" if action == 'compress' else None,
                logger=None
            )
        elif target_format == 'mp3':
            clip.audio.write_audiofile(output_path, logger=None)
        elif target_format == 'gif':
            clip.to_gif(output_path, fps=15, logger=None)
            
        clip.close()
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Video Processing Error: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

    return render_glass_page("Success", f"""
        <h2 style="color: #34d399; margin-bottom: 10px;">Media Processed Successfully!</h2>
        <a href="/download/{output_filename}" class="btn-primary btn-success">Download Media File</a><br><br>
        <a href="/" class="back-link">← Return to Homepage</a>
    """)

@app.route('/download/<filename>')
def download_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(app.config['CONVERTED_FOLDER'], safe_name, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
