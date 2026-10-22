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
from PIL import Image, ImageEnhance
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
                if os.path.isfile(f_path):
                    try:
                        if (now - os.path.getmtime(f_path) > 7200):
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
                background-color: #0d001a;
                background-image: linear-gradient(135deg, rgba(13,0,26,0.85) 0%, rgba(26,0,51,0.85) 50%, rgba(13,0,26,0.85) 100%), url('/static/bg.jpg');
                background-size: cover; background-position: center; background-attachment: fixed;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
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
            input[type="text"], input[type="number"], select {{
                width: 100%; padding: 14px; background: rgba(22, 0, 44, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px;
                color: #ffffff; font-size: 14px; outline: none; margin-bottom: 18px;
            }}
            label {{ display: block; text-align: left; color: #a78bfa; font-size: 13px; margin-bottom: 5px; font-weight: 600; }}
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
        
        <!-- Script to handle processing loader on the execution pages -->
        <div id="processingOverlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(13,0,26,0.92); backdrop-filter:blur(12px); z-index:9999; flex-direction:column; align-items:center; justify-content:center;">
            <div style="width:65px; height:65px; border:4px solid rgba(168,85,247,0.2); border-top:4px solid #a855f7; border-radius:50%; animation:spin 1s linear infinite; margin-bottom:20px;"></div>
            <h2 style="color:#fff; font-size:24px; font-weight:700; margin-bottom:8px;">Processing Media...</h2>
            <p style="color:#a78bfa; font-size:15px;">Please wait, applying your enhancements securely.</p>
        </div>
        <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>
        <script>
            function showLoader() {{ document.getElementById('processingOverlay').style.display = 'flex'; }}
        </script>
    </body>
    </html>
    """

@app.route('/')
def home():
    cleanup_old_files()
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], secure_filename(filename))

@app.route('/upload', methods=['POST'])
def upload_file():
    tool_type = request.form.get('tool_type', 'converter')
    
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
        # Send straight to the Video Studio Editor without asking for action!
        return redirect(url_for('process_video_studio', filename=filename))

    return redirect('/')

@app.route('/execute/convert-direct/<filename>', methods=['GET', 'POST'])
def execute_convert_direct(filename):
    filename = secure_filename(filename)
    sub_type = request.args.get('sub_type', 'img_to_png')
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(input_path):
        return render_glass_page("Error", "<h3 style='color:#ef4444;'>File not found.</h3><a href='/' class='back-link'>← Back</a>")

    base_name, ext = os.path.splitext(filename)
    
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
                    img.save(output_path, target_format.upper())
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
    filename = secure_filename(filename)
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
        <form action="/execute/pdf-edit/{filename}" method="POST" onsubmit="showLoader()">
            <div style="max-height:360px; overflow-y:auto; margin-bottom:15px;">{slots_html}</div>
            <button type="submit" class="btn-primary">Save Edited PDF</button>
        </form>
        <a href="/" class="back-link">← Return to Homepage</a>
    """
    return render_glass_page("PDF Studio", content)

@app.route('/execute/pdf-edit/<filename>', methods=['POST'])
def execute_pdf_edit(filename):
    filename = secure_filename(filename)
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
    filename = secure_filename(filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_filename = f"{os.path.splitext(filename)[0]}_compressed.pdf"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            try:
                page.compress_content_streams()
            except:
                pass
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
    filename = secure_filename(filename)
    content = f"""
        <h2 style="font-size:22px; margin-bottom:10px;">Interactive Image Studio</h2>
        <p style="color:#a78bfa; margin-bottom:15px; font-size:13px;">Enhance <strong>{filename}</strong></p>
        
        <!-- LIVE IMAGE PREVIEW -->
        <div style="margin-bottom: 20px; background: rgba(0,0,0,0.4); padding: 10px; border-radius: 12px;">
            <img src="/uploads/{filename}" style="max-width: 100%; max-height: 280px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); object-fit: contain;">
        </div>

        <form action="/execute/image/{filename}" method="POST" onsubmit="showLoader()">
            <label>Width (px - Optional, auto-scales height):</label>
            <input type="number" name="width" placeholder="Leave empty for original">
            
            <label>Height (px - Optional, auto-scales width):</label>
            <input type="number" name="height" placeholder="Leave empty for original">
            
            <label>Brightness Factor (1.0 is Normal):</label>
            <input type="range" name="brightness" min="0.5" max="2.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px;">
            
            <label>Contrast Factor (1.0 is Normal):</label>
            <input type="range" name="contrast" min="0.5" max="2.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px;">
            
            <button type="submit" class="btn-primary">Save Enhanced Image</button>
        </form>
        <a href="/" class="back-link">← Return to Homepage</a>
    """
    return render_glass_page("Image Studio", content)

@app.route('/execute/image/<filename>', methods=['POST'])
def execute_image_studio(filename):
    filename = secure_filename(filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_filename = f"{os.path.splitext(filename)[0]}_enhanced{os.path.splitext(filename)[1]}"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        w = request.form.get('width', '').strip()
        h = request.form.get('height', '').strip()
        b = float(request.form.get('brightness', 1.0))
        c = float(request.form.get('contrast', 1.0))

        with Image.open(input_path) as img:
            # Bulletproof aspect-ratio resizing
            if w.isdigit() or h.isdigit():
                orig_w, orig_h = img.size
                if w.isdigit() and h.isdigit():
                    new_w, new_h = int(w), int(h)
                elif w.isdigit():
                    new_w = int(w)
                    new_h = int(orig_h * (new_w / orig_w))
                else:
                    new_h = int(h)
                    new_w = int(orig_w * (new_h / orig_h))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
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
    filename = secure_filename(filename)
    ext = os.path.splitext(filename)[1].lower()
    is_audio = ext in ['.mp3', '.wav', '.m4a', '.ogg', '.aac']
    
    # Auto-render correct preview player based on file type
    if is_audio:
        media_player = f'<audio controls style="width: 100%; margin-bottom: 20px; border-radius: 8px;"><source src="/uploads/{filename}"></audio>'
        options_html = """
            <label>Audio Volume Level (1.0 is Normal):</label>
            <input type="range" name="volume" min="0.0" max="3.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px;">
            <label>Target Format / Output:</label>
            <select name="format">
                <option value="mp3">MP3 Audio (.mp3)</option>
            </select>
        """
    else:
        media_player = f'<video controls style="max-width: 100%; max-height: 280px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); margin-bottom: 20px;"><source src="/uploads/{filename}"></video>'
        options_html = """
            <label>Resize Width (px - Optional, auto-scales height):</label>
            <input type="number" name="width" placeholder="Leave empty for original">
            
            <label>Resize Height (px - Optional, auto-scales width):</label>
            <input type="number" name="height" placeholder="Leave empty for original">
            
            <label>Video Compression Level:</label>
            <select name="compression">
                <option value="none">Original Quality (No Compression)</option>
                <option value="medium">Medium Compression (Balanced Bitrate)</option>
                <option value="high">High Compression (Smaller File Size)</option>
            </select>

            <label>Audio Volume Level (1.0 is Normal):</label>
            <input type="range" name="volume" min="0.0" max="3.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px;">
            
            <label>Target Format / Output:</label>
            <select name="format">
                <option value="mp4">MP4 Video (.mp4)</option>
                <option value="webm">WebM Video (.webm)</option>
                <option value="mp3">Extract Audio Only (.mp3)</option>
                <option value="gif">Animated GIF (.gif)</option>
            </select>
        """

    content = f"""
        <h2 style="font-size:22px; margin-bottom:10px;">Interactive Media Studio</h2>
        <p style="color:#a78bfa; margin-bottom:15px; font-size:13px;">Enhance <strong>{filename}</strong></p>
        
        <!-- LIVE MEDIA PREVIEW -->
        <div style="background: rgba(0,0,0,0.4); padding: 10px; border-radius: 12px; margin-bottom: 20px;">
            {media_player}
        </div>

        <form action="/execute/video/{filename}" method="POST" onsubmit="showLoader()">
            {options_html}
            <button type="submit" class="btn-primary" style="margin-top:15px;">Process Media File</button>
        </form>
        <a href="/" class="back-link">← Return to Homepage</a>
    """
    return render_glass_page("Media Studio", content)

@app.route('/execute/video/<filename>', methods=['POST'])
def execute_video_studio(filename):
    filename = secure_filename(filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    target_format = request.form.get('format', 'mp4')
    output_filename = f"{os.path.splitext(filename)[0]}_processed.{target_format}"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    ext = os.path.splitext(filename)[1].lower()
    is_audio = ext in ['.mp3', '.wav', '.m4a', '.ogg', '.aac']

    try:
        import moviepy.editor as mpy
        
        if is_audio:
            clip = mpy.AudioFileClip(input_path)
        else:
            clip = mpy.VideoFileClip(input_path)

        # Apply Audio Volume safely
        vol = float(request.form.get('volume', 1.0))
        if vol != 1.0:
            import moviepy.audio.fx.all as afx
            if is_audio:
                clip = clip.fx(afx.volumex, vol)
            elif clip.audio:
                clip.audio = clip.audio.fx(afx.volumex, vol)
        
        # Apply Video Resizing and Compression safely
        bitrate = None
        if not is_audio:
            w = request.form.get('width', '').strip()
            h = request.form.get('height', '').strip()
            compression = request.form.get('compression', 'none')

            # Aspect Ratio Safe Resizing
            if w.isdigit() or h.isdigit():
                orig_w, orig_h = clip.size
                if w.isdigit() and h.isdigit():
                    new_w, new_h = int(w), int(h)
                elif w.isdigit():
                    new_w = int(w)
                    new_h = int(orig_h * (new_w / orig_w))
                else:
                    new_h = int(h)
                    new_w = int(orig_w * (new_h / orig_h))
                
                # Make divisible by 2 for standard video codecs
                new_w = new_w - (new_w % 2)
                new_h = new_h - (new_h % 2)
                clip = clip.resize(newsize=(new_w, new_h))

            # Set Target Bitrate
            if compression == 'medium':
                bitrate = '2000k'
            elif compression == 'high':
                bitrate = '1000k'
        
        # Export processed file
        if target_format in ['mp4', 'webm']:
            if is_audio:
                raise Exception("Cannot convert a pure audio file into a video format.")
            clip.write_videofile(
                output_path, 
                codec='libx264' if target_format=='mp4' else 'libvpx', 
                audio_codec='aac', 
                bitrate=bitrate,
                logger=None
            )
        elif target_format == 'mp3':
            if is_audio:
                clip.write_audiofile(output_path, logger=None)
            else:
                if clip.audio is None:
                    raise Exception("Video has no audio track to extract.")
                clip.audio.write_audiofile(output_path, logger=None)
        elif target_format == 'gif':
            if is_audio:
                raise Exception("Cannot convert an audio file into an animated GIF.")
            clip.to_gif(output_path, fps=10, logger=None) # Locked to 10 FPS to save server memory
            
        clip.close()
    except Exception as e:
        return render_glass_page("Error", f"<h3 style='color:#ef4444;'>Media Error: {str(e)}</h3><a href='/' class='back-link'>← Back</a>")

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
