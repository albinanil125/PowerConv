import os
import io
import json
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)
app.secret_key = "powerconv_master_secret_key_2026"

UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
STATIC_FOLDER = 'static'

for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER, STATIC_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64 MB limit

def render_glass_page(title, body_content):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PowerConv - {title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="/static/style.css">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; }}
            body {{
                min-height: 100vh;
                background: #0d001a url('/static/bg.jpg') center/cover no-repeat fixed;
                background-blend-mode: overlay;
                display: flex; align-items: center; justify-content: center;
                color: #ffffff; padding: 20px; overflow-x: hidden;
            }}
            .glass-card {{
                background: rgba(22, 0, 44, 0.8);
                backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 24px; padding: 40px;
                max-width: 620px; width: 100%;
                box-shadow: 0 30px 60px rgba(0, 0, 0, 0.6);
                text-align: center;
            }}
            .brand-logo {{
                display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 20px;
            }}
            .brand-logo h1 {{ font-size: 28px; font-weight: 800; color: #fff; }}
            .brand-logo span {{
                background: linear-gradient(135deg, #a855f7, #ec4899);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            }}
            .btn-primary {{
                width: 100%; background: linear-gradient(135deg, #9333ea, #c084fc);
                color: white; border: none; padding: 14px 28px; border-radius: 12px;
                font-size: 16px; font-weight: 600; cursor: pointer; text-decoration: none;
                display: inline-block; box-shadow: 0 10px 25px rgba(147, 51, 234, 0.4);
                transition: all 0.3s ease;
            }}
            .btn-primary:hover {{ transform: translateY(-2px); background: linear-gradient(135deg, #a855f7, #e879f9); }}
            .btn-success {{
                background: linear-gradient(135deg, #059669, #34d399);
                box-shadow: 0 10px 25px rgba(5, 150, 105, 0.4);
            }}
            .btn-success:hover {{ background: linear-gradient(135deg, #10b981, #6ee7b7); }}
            .back-link {{ color: #c084fc; text-decoration: none; font-size: 14px; margin-top: 20px; display: inline-block; }}
            .back-link:hover {{ text-decoration: underline; }}
            input[type="text"], input[type="number"], select, input[type="file"] {{
                width: 100%; padding: 12px; background: rgba(13, 0, 26, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px;
                color: #ffffff; font-size: 14px; outline: none; margin-bottom: 15px;
            }}
            select option {{ background: #160b26; color: #fff; }}
            label {{ display: block; text-align: left; color: #a78bfa; font-size: 13px; margin-bottom: 6px; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="glass-card">
            <div class="brand-logo">
                <img src="/static/logo.svg" alt="PowerConv Logo" style="width: 40px; height: 40px; object-fit: contain;" onerror="this.style.display='none'">
                <h1>Power<span>Conv</span></h1>
            </div>
            {body_content}
        </div>
    </body>
    </html>
    """

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect('/')
    file = request.files['file']
    if file.filename == '':
        return redirect('/')
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        tool_type = request.form.get('tool_type', 'convert')
        return redirect(url_for('process_page', filename=file.filename, tool=tool_type))

@app.route('/process-page/<filename>')
def process_page(filename):
    ext = os.path.splitext(filename)[1].lower()
    tool = request.args.get('tool', 'convert')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    controls_html = ""

    # TOOL 1: FILE CONVERTER
    if tool == 'convert':
        options = ""
        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff']:
            options = """
                <option value="png">PNG (.png)</option>
                <option value="jpeg">JPG (.jpg)</option>
                <option value="webp">WEBP (.webp)</option>
                <option value="bmp">BMP (.bmp)</option>
                <option value="pdf">PDF Document (.pdf)</option>
            """
        elif ext in ['.xlsx', '.xls', '.csv']:
            options = """
                <option value="csv">CSV (.csv)</option>
                <option value="xlsx">Excel Workbook (.xlsx)</option>
                <option value="json">JSON Dataset (.json)</option>
            """
        else:
            options = '<option value="pdf">PDF Document (.pdf)</option>'

        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">File Converter Studio</h2>
            <p style="color:#a78bfa; margin-bottom:20px; font-size:14px;">Active File: <strong style="color:#fff;">{filename}</strong></p>
            
            <form action="/execute/convert/{filename}" method="POST">
                <label>Select Target Format:</label>
                <select name="format">{options}</select>
                <button type="submit" class="btn-primary" style="margin-top:10px;">Convert File Now</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>
        """

    # TOOL 2: VISUAL PDF STUDIO (Rearrange, Rotate & Interleave)
    elif tool == 'pdf_edit':
        total_pages = 1
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
        except Exception:
            pass

        page_slots_html = ""
        for i in range(total_pages):
            page_slots_html += f"""
                <div style="background:rgba(13,0,26,0.6); border:1px solid rgba(168,85,247,0.3); border-radius:10px; padding:12px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:#9333ea; color:white; width:26px; height:26px; display:flex; align-items:center; justify-content:center; border-radius:50%; font-weight:700; font-size:12px;">{i+1}</span>
                        <span style="font-size:13px; color:#f3e8ff;">Page {i+1} Slot</span>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <input type="hidden" name="original_indices" value="{i}">
                        <label style="font-size:11px; margin:0; color:#a78bfa;">Rotate:</label>
                        <select name="page_rot_{i}" style="padding:4px; font-size:11px; margin:0; width:95px;">
                            <option value="0">0°</option>
                            <option value="90">90° CW</option>
                            <option value="180">180°</option>
                            <option value="270">270° CCW</option>
                        </select>
                    </div>
                </div>
            """

        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">Visual PDF Studio</h2>
            <p style="color:#a78bfa; margin-bottom:15px; font-size:14px;">PDF Loaded: <strong style="color:#fff;">{filename}</strong> ({total_pages} Pages)</p>

            <form action="/execute/pdf_edit/{filename}" method="POST" enctype="multipart/form-data">
                <label>Rearrange Page Sequence (Comma Separated):</label>
                <input type="text" name="page_order" value="{','.join(str(i+1) for i in range(total_pages))}">

                <label style="margin-top:15px;">Document Page Rotations:</label>
                <div style="max-height:210px; overflow-y:auto; padding-right:5px; margin-bottom:15px; text-align:left;">
                    {page_slots_html}
                </div>

                <div style="background:rgba(168,85,247,0.1); border:1px dashed rgba(168,85,247,0.4); padding:12px; border-radius:10px; margin-bottom:15px; text-align:left;">
                    <label style="color:#e879f9; margin-bottom:4px; font-size:12px;">➕ Interleave / Insert Extra PDF/Image Between Pages:</label>
                    <input type="file" name="interleaved_file" style="font-size:11px; padding:6px; margin:0;">
                </div>

                <button type="submit" class="btn-primary">Compile & Save PDF</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>
        """

    # TOOL 3: REAL-TIME IMAGE STUDIO (Sliders & Canvas Preview)
    elif tool == 'image_enhance':
        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">Interactive Image Studio</h2>
            <p style="color:#a78bfa; margin-bottom:12px; font-size:13px;">Real-Time Browser Preview</p>

            <div style="margin-bottom:15px; background:#000; border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,0.1); max-height:210px; display:flex; align-items:center; justify-content:center;">
                <canvas id="previewCanvas" style="max-width:100%; max-height:200px; object-fit:contain;"></canvas>
            </div>

            <form action="/execute/image_enhance/{filename}" method="POST">
                <div style="display:flex; gap:10px; margin-bottom:10px;">
                    <div style="flex:1;"><label style="font-size:11px;">Width (px):</label><input type="number" name="width" placeholder="Original"></div>
                    <div style="flex:1;"><label style="font-size:11px;">Height (px):</label><input type="number" name="height" placeholder="Original"></div>
                </div>

                <label style="font-size:12px; margin-bottom:2px;">Brightness: <span id="valBright" style="color:#fff;">1.0</span></label>
                <input type="range" name="brightness" id="rangeBright" min="0.1" max="3.0" step="0.1" value="1.0" style="width:100%; margin-bottom:10px; accent-color:#a855f7;" oninput="updateLivePreview()">

                <label style="font-size:12px; margin-bottom:2px;">Contrast: <span id="valContrast" style="color:#fff;">1.0</span></label>
                <input type="range" name="contrast" id="rangeContrast" min="0.1" max="3.0" step="0.1" value="1.0" style="width:100%; margin-bottom:10px; accent-color:#a855f7;" oninput="updateLivePreview()">

                <label style="font-size:12px; margin-bottom:2px;">Sharpness: <span id="valSharp" style="color:#fff;">1.0</span></label>
                <input type="range" name="sharpness" id="rangeSharp" min="0.0" max="5.0" step="0.1" value="1.0" style="width:100%; margin-bottom:15px; accent-color:#a855f7;" oninput="updateLivePreview()">

                <button type="submit" class="btn-primary">Save & Export Enhanced Image</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>

            <script>
                const canvas = document.getElementById('previewCanvas');
                const ctx = canvas.getContext('2d');
                const img = new Image();
                img.src = "/uploads/{filename}";

                img.onload = function() {{
                    canvas.width = img.width;
                    canvas.height = img.height;
                    drawCanvas();
                }};

                function drawCanvas() {{
                    const b = document.getElementById('rangeBright').value;
                    const c = document.getElementById('rangeContrast').value;
                    ctx.filter = `brightness(${b}) contrast(${c})`;
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);

                    document.getElementById('valBright').innerText = b;
                    document.getElementById('valContrast').innerText = c;
                    document.getElementById('valSharp').innerText = document.getElementById('rangeSharp').value;
                }}

                function updateLivePreview() {{
                    drawCanvas();
                }}
            </script>
        """

    return render_glass_page("Studio", controls_html)

@app.route('/execute/<tool>/<filename>', methods=['POST'])
def execute_action(tool, filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    base_name, ext = os.path.splitext(filename)
    
    try:
        if tool == 'convert':
            target_format = request.form.get('format', 'png').lower()
            output_filename = f"{base_name}_converted.{target_format}"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            if ext.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
                with Image.open(input_path) as img:
                    if target_format in ['jpeg', 'jpg'] and img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    if target_format == 'pdf':
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img.save(output_path, "PDF")
                    else:
                        img.save(output_path, target_format.upper())
            elif ext.lower() in ['.xlsx', '.xls', '.csv']:
                df = pd.read_csv(input_path) if ext.lower() == '.csv' else pd.read_excel(input_path)
                if target_format == 'csv':
                    df.to_csv(output_path, index=False)
                elif target_format == 'xlsx':
                    df.to_excel(output_path, index=False)
                elif target_format == 'json':
                    df.to_json(output_path, orient='records', indent=4)

        elif tool == 'pdf_edit':
            output_filename = f"{base_name}_edited.pdf"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            page_order = request.form.get('page_order', '')
            reader = PdfReader(input_path)
            writer = PdfWriter()

            pages_indices = [int(p.strip()) - 1 for p in page_order.split(',') if p.strip().isdigit()]
            
            for idx in pages_indices:
                if 0 <= idx < len(reader.pages):
                    page = reader.pages[idx]
                    rot_val = int(request.form.get(f'page_rot_{idx}', 0))
                    if rot_val != 0:
                        page.rotate(rot_val)
                    writer.add_page(page)

            # Check if user interleaved an extra file
            if 'interleaved_file' in request.files:
                extra_file = request.files['interleaved_file']
                if extra_file and extra_file.filename != '':
                    extra_path = os.path.join(app.config['UPLOAD_FOLDER'], extra_file.filename)
                    extra_file.save(extra_path)
                    if extra_file.filename.lower().endswith('.pdf'):
                        extra_reader = PdfReader(extra_path)
                        for ep in extra_reader.pages:
                            writer.add_page(ep)
                    else:
                        # Append image as page if image
                        with Image.open(extra_path) as im:
                            im_rgb = im.convert('RGB')
                            pdf_bytes = io.BytesIO()
                            im_rgb.save(pdf_bytes, format="PDF")
                            pdf_bytes.seek(0)
                            im_reader = PdfReader(pdf_bytes)
                            writer.add_page(im_reader.pages[0])

            with open(output_path, "wb") as f_out:
                writer.write(f_out)

        elif tool == 'image_enhance':
            output_filename = f"{base_name}_enhanced{ext}"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            width = request.form.get('width')
            height = request.form.get('height')
            brightness = float(request.form.get('brightness', 1.0))
            contrast = float(request.form.get('contrast', 1.0))
            sharpness = float(request.form.get('sharpness', 1.0))

            with Image.open(input_path) as img:
                if width or height:
                    new_w = int(width) if width else img.width
                    new_h = int(height) if height else img.height
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                if brightness != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(brightness)
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)
                if sharpness != 1.0:
                    img = ImageEnhance.Sharpness(img).enhance(sharpness)

                img.save(output_path)

        success_content = f"""
            <div style="font-size: 52px; margin-bottom: 10px;">✨</div>
            <h2 style="color: #34d399; margin-bottom: 10px;">Processing Complete!</h2>
            <p style="color: #a78bfa; font-size: 14px; margin-bottom: 30px;">Your file <strong>{output_filename}</strong> is ready.</p>
            <a href="/download/{output_filename}" class="btn-primary btn-success">Download Converted File</a>
            <br><br><br>
            <a href="/" class="back-link">← Process another file</a>
        """
        return render_glass_page("Success", success_content)

    except Exception as e:
        error_content = f"""
            <div style="font-size: 48px; margin-bottom: 10px;">⚠️</div>
            <h2 style="color: #ef4444; margin-bottom: 10px;">Processing Failed</h2>
            <p style="color: #a78bfa; font-size: 14px; margin-bottom: 25px;">{str(e)}</p>
            <a href="/" class="btn-primary">Return to Homepage</a>
        """
        return render_glass_page("Error", error_content)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
