import os
import io
import json
import pandas as pd

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

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
app.config['STATIC_FOLDER'] = STATIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 256 MB limit for videos/large files

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
                background: rgba(22, 0, 44, 0.9);
                backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 24px; padding: 35px;
                max-width: 820px; width: 100%;
                box-shadow: 0 30px 60px rgba(0, 0, 0, 0.8);
                text-align: center;
            }}
            .brand-logo {{
                display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 15px;
            }}
            .logo-icon {{
                width: 40px; height: 40px; background: linear-gradient(135deg, #9333ea, #ec4899);
                border-radius: 10px; display: flex; align-items: center; justify-content: center;
                font-size: 20px; font-weight: 800; color: #fff;
            }}
            .brand-logo h1 {{ font-size: 26px; font-weight: 800; color: #fff; }}
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
            .back-link {{ color: #c084fc; text-decoration: none; font-size: 14px; margin-top: 20px; display: inline-block; }}
            .back-link:hover {{ text-decoration: underline; }}
            input[type="text"], input[type="number"], select, input[type="file"] {{
                width: 100%; padding: 12px; background: rgba(13, 0, 26, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px;
                color: #ffffff; font-size: 14px; outline: none; margin-bottom: 12px;
            }}
            select option {{ background: #160b26; color: #fff; }}
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

    if tool == 'convert':
        options = ""
        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
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
        elif ext == '.pdf':
            options = '<option value="txt">Extracted Text Document (.txt)</option>'
        else:
            options = '<option value="pdf">PDF Document (.pdf)</option>'

        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">File Converter Studio</h2>
            <p style="color:#a78bfa; margin-bottom:20px; font-size:14px;">Active File: <strong style="color:#fff;">{filename}</strong></p>
            
            <form action="/execute/convert/{filename}" method="POST" onsubmit="showLoader()">
                <label>Select Target Format:</label>
                <select name="format">{options}</select>
                <button type="submit" class="btn-primary" style="margin-top:10px;">Convert File Now</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>
        """

    elif tool == 'video_convert':
        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">Video & Audio Studio</h2>
            <p style="color:#a78bfa; margin-bottom:20px; font-size:14px;">Active Media: <strong style="color:#fff;">{filename}</strong></p>
            
            <form action="/execute/video_convert/{filename}" method="POST" onsubmit="showLoader()">
                <label>Select Target Format / Codec:</label>
                <select name="format">
                    <option value="mp4">MP4 Video (.mp4)</option>
                    <option value="webm">WebM Video (.webm)</option>
                    <option value="mp3">MP3 Audio Extract (.mp3)</option>
                    <option value="wav">WAV Audio Extract (.wav)</option>
                    <option value="gif">Animated GIF (.gif)</option>
                </select>
                <button type="submit" class="btn-primary" style="margin-top:10px;">Convert Media Now</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>
        """

    elif tool == 'doc_convert':
        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">Word Document Studio</h2>
            <p style="color:#a78bfa; margin-bottom:20px; font-size:14px;">Active Document: <strong style="color:#fff;">{filename}</strong></p>
            
            <form action="/execute/doc_convert/{filename}" method="POST" onsubmit="showLoader()">
                <label>Select Target Format:</label>
                <select name="format">
                    <option value="txt">Plain Text (.txt)</option>
                </select>
                <button type="submit" class="btn-primary" style="margin-top:10px;">Convert Document Now</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>
        """

    elif tool == 'pdf_edit':
        if ext != '.pdf':
            return render_glass_page("Error", """
                <div style="font-size: 48px; margin-bottom: 10px;">⚠️</div>
                <h2 style="color: #ef4444; margin-bottom: 10px;">Incompatible File Type</h2>
                <p style="color: #a78bfa; font-size: 14px; margin-bottom: 25px;">The Visual PDF Studio requires a PDF document file.</p>
                <a href="/" class="btn-primary">Return to Homepage</a>
            """)

        page_slots_html = ""
        total_pages = 1
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            base_name = os.path.splitext(filename)[0]

            for i in range(total_pages):
                thumb_html = '<div style="width:110px; height:150px; background:#000; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#666; font-size:12px;">No Preview</div>'
                if FITZ_AVAILABLE:
                    try:
                        doc = fitz.open(file_path)
                        page = doc[i]
                        pix = page.get_pixmap(dpi=150)
                        thumb_filename = f"thumb_{base_name}_p{i}.png"
                        thumb_path = os.path.join(app.config['STATIC_FOLDER'], thumb_filename)
                        pix.save(thumb_path)
                        thumb_html = f'<img id="thumb_img_{i}" src="/static/{thumb_filename}" style="width:110px; height:150px; object-fit:contain; background:#000; border-radius:8px; border:1px solid rgba(255,255,255,0.2); transition: transform 0.3s ease;">'
                    except Exception:
                        pass

                plus_divider = f"""
                    <div style="display:flex; align-items:center; justify-content:center; margin:8px 0; position:relative;">
                        <div style="flex:1; height:1px; background:rgba(168,85,247,0.3);"></div>
                        <label title="Insert file here" style="background:#9333ea; color:#fff; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:16px; font-weight:700; margin:0 10px; box-shadow:0 0 10px rgba(147,51,234,0.6); transition:transform 0.2s;">
                            +
                            <input type="file" name="insert_at_{i}" style="display:none;" onchange="updateInsertLabel(this, {i})">
                        </label>
                        <div style="flex:1; height:1px; background:rgba(168,85,247,0.3);"></div>
                    </div>
                    <div id="insert_status_{i}" style="font-size:11px; color:#34d399; text-align:center; margin-bottom:5px;"></div>
                """ if i > 0 else ""

                page_slots_html += f"""
                    {plus_divider}
                    <div class="page-card" draggable="true" ondragstart="drag(event)" ondragover="allowDrop(event)" ondrop="drop(event)" data-index="{i}" style="background:rgba(13,0,26,0.75); border:1px solid rgba(168,85,247,0.4); border-radius:16px; padding:16px; margin-bottom:12px; display:flex; align-items:center; gap:20px; cursor:grab;">
                        <div style="cursor:grab; color:#a78bfa; font-size:20px;">☰</div>
                        {thumb_html}
                        <div style="flex:1; text-align:left;">
                            <span style="background:#9333ea; color:white; padding:6px 14px; border-radius:20px; font-weight:700; font-size:13px; display:inline-block; margin-bottom:10px;">Page {i+1}</span>
                            <input type="hidden" name="page_indices" value="{i}">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <label style="font-size:12px; margin:0; color:#a78bfa;">Instant Rotation:</label>
                                <select name="page_rot_{i}" id="rot_{i}" style="padding:8px; font-size:12px; margin:0; width:140px;" onchange="rotatePreview({i}, this.value)">
                                    <option value="0">0° (Normal)</option>
                                    <option value="90">90° Clockwise</option>
                                    <option value="180">180° Upside Down</option>
                                    <option value="270">270° Counter-CW</option>
                                </select>
                            </div>
                        </div>
                    </div>
                """
        except Exception as e:
            page_slots_html = f"<p style='color:#ef4444;'>Error loading PDF pages: {str(e)}</p>"

        controls_html = f"""
            <h2 style="font-size:24px; margin-bottom:8px;">Visual PDF Studio</h2>
            <p style="color:#a78bfa; margin-bottom:15px; font-size:14px;">Loaded: <strong style="color:#fff;">{filename}</strong> ({total_pages} Pages). Drag cards to reorder or click <strong>+</strong> to insert files anywhere.</p>

            <form action="/execute/pdf_edit/{filename}" method="POST" enctype="multipart/form-data" onsubmit="showLoader()">
                <div id="sortablePages" style="max-height:380px; overflow-y:auto; padding-right:8px; margin-bottom:20px;">
                    {page_slots_html}
                </div>

                <button type="submit" class="btn-primary">Compile & Save Final PDF</button>
            </form>
            <a href="/" class="back-link">← Choose another file</a>

            <script>
                function rotatePreview(idx, angle) {{
                    const img = document.getElementById('thumb_img_' + idx);
                    if (img) {{
                        img.style.transform = 'rotate(' + angle + 'deg)';
                    }}
                }}

                function updateInsertLabel(input, idx) {{
                    const status = document.getElementById('insert_status_' + idx);
                    if (input.files && input.files[0]) {{
                        status.innerText = "File attached for insertion: " + input.files[0].name;
                    }}
                }}

                let draggedSrcEl = null;
                function drag(e) {{
                    draggedSrcEl = e.currentTarget;
                    e.dataTransfer.effectAllowed = 'move';
                }}
                function allowDrop(e) {{
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                }}
                function drop(e) {{
                    e.preventDefault();
                    let target = e.target.closest('.page-card');
                    if (target && draggedSrcEl !== target) {{
                        let allCards = [...document.querySelectorAll('#sortablePages .page-card')];
                        let srcPos = allCards.indexOf(draggedSrcEl);
                        let targetPos = allCards.indexOf(target);
                        if (srcPos < targetPos) {{
                            target.parentNode.insertBefore(draggedSrcEl, target.nextSibling);
                        }} else {{
                            target.parentNode.insertBefore(draggedSrcEl, target);
                        }}
                    }}
                }}
            </script>
        """

    elif tool == 'image_enhance':
        if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
            return render_glass_page("Error", """
                <div style="font-size: 48px; margin-bottom: 10px;">⚠️</div>
                <h2 style="color: #ef4444; margin-bottom: 10px;">Incompatible File Type</h2>
                <p style="color: #a78bfa; font-size: 14px; margin-bottom: 25px;">The Interactive Image Studio requires an image file.</p>
                <a href="/" class="btn-primary">Return to Homepage</a>
            """)

        controls_html = f"""
            <h2 style="font-size:22px; margin-bottom:10px;">Interactive Image Studio</h2>
            <p style="color:#a78bfa; margin-bottom:12px; font-size:13px;">Real-Time Browser Preview</p>

            <div style="margin-bottom:15px; background:#000; border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,0.1); max-height:210px; display:flex; align-items:center; justify-content:center;">
                <canvas id="previewCanvas" style="max-width:100%; max-height:200px; object-fit:contain;"></canvas>
            </div>

            <form action="/execute/image_enhance/{filename}" method="POST" onsubmit="showLoader()">
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
                    ctx.filter = "brightness(" + b + ") contrast(" + c + ")";
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

    loader_script = """
        <div id="processingOverlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(13,0,26,0.9); backdrop-filter:blur(10px); z-index:9999; flex-direction:column; align-items:center; justify-content:center;">
            <div style="width:60px; height:60px; border:4px solid rgba(168,85,247,0.2); border-top:4px solid #a855f7; border-radius:50%; animation:spin 1s linear infinite; margin-bottom:20px;"></div>
            <h2 style="color:#fff; font-size:22px; font-weight:700; margin-bottom:8px;">PowerConv Engine Processing...</h2>
            <p style="color:#a78bfa; font-size:14px;">Optimizing and compiling your file securely.</p>
        </div>
        <style>
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        </style>
        <script>
            function showLoader() {{
                document.getElementById('processingOverlay').style.display = 'flex';
            }}
        </script>
    """

    return render_glass_page("Studio", controls_html + loader_script)

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
                    if getattr(img, "is_animated", False):
                        img.seek(0)
                    if target_format in ['jpeg', 'jpg'] and img.mode in ('RGBA', 'P', 'LA'):
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            bg.paste(img, mask=img.split()[3])
                        else:
                            bg.paste(img.convert('RGB'))
                        img = bg
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
            elif ext.lower() == '.pdf':
                if target_format == 'txt':
                    reader = PdfReader(input_path)
                    extracted_text = ""
                    for page in reader.pages:
                        extracted_text += (page.extract_text() or "") + "\n"
                    with open(output_path, 'w', encoding='utf-8') as f_txt:
                        f_txt.write(extracted_text)

        elif tool == 'video_convert':
            from moviepy.editor import VideoFileClip
            target_format = request.form.get('format', 'mp4').lower()
            output_filename = f"{base_name}_converted.{target_format}"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            clip = VideoFileClip(input_path)
            if target_format in ['mp4', 'webm']:
                clip.write_videofile(output_path, codec='libx264' if target_format == 'mp4' else 'libvpx', audio_codec='aac', logger=None)
            elif target_format in ['mp3', 'wav']:
                clip.audio.write_audiofile(output_path, logger=None)
            elif target_format == 'gif':
                clip.to_gif(output_path, fps=15, logger=None)
            clip.close()

        elif tool == 'doc_convert':
            from docx import Document
            target_format = request.form.get('format', 'txt').lower()
            output_filename = f"{base_name}_converted.{target_format}"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            if ext.lower() == '.docx':
                doc = Document(input_path)
                full_text = "\n".join([para.text for para in doc.paragraphs])
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(full_text)

        elif tool == 'pdf_edit':
            output_filename = f"{base_name}_edited.pdf"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            page_indices = request.form.getlist('page_indices')
            reader = PdfReader(input_path)
            writer = PdfWriter()

            for i, p_idx_str in enumerate(page_indices):
                idx = int(p_idx_str)
                if 0 <= idx < len(reader.pages):
                    page = reader.pages[idx]
                    rot_val = int(request.form.get(f'page_rot_{idx}', 0))
                    if rot_val != 0:
                        page.rotate(rot_val)
                    writer.add_page(page)

                insert_key = f'insert_at_{idx}'
                if insert_key in request.files:
                    extra_file = request.files[insert_key]
                    if extra_file and extra_file.filename != '':
                        extra_path = os.path.join(app.config['UPLOAD_FOLDER'], extra_file.filename)
                        extra_file.save(extra_path)
                        if extra_file.filename.lower().endswith('.pdf'):
                            extra_reader = PdfReader(extra_path)
                            for ep in extra_reader.pages:
                                writer.add_page(ep)
                        else:
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

            width_str = request.form.get('width', '').strip()
            height_str = request.form.get('height', '').strip()
            brightness = float(request.form.get('brightness', 1.0))
            contrast = float(request.form.get('contrast', 1.0))
            sharpness = float(request.form.get('sharpness', 1.0))

            with Image.open(input_path) as img:
                if getattr(img, "is_animated", False):
                    img.seek(0)

                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode == 'LA':
                    bg = Image.new('L', img.size, 255)
                    bg.paste(img, mask=img.split()[1])
                    img = bg.convert('RGB')
                elif img.mode == 'P':
                    img = img.convert('RGB')
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')

                new_w = int(width_str) if width_str.isdigit() and int(width_str) > 0 else img.width
                new_h = int(height_str) if height_str.isdigit() and int(height_str) > 0 else img.height

                if new_w != img.width or new_h != img.height:
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                if brightness != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(brightness)
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)
                if sharpness != 1.0:
                    img = ImageEnhance.Sharpness(img).enhance(sharpness)

                save_ext = ext.lower().replace('.', '')
                if save_ext in ['jpg', 'jpeg']:
                    img.save(output_path, 'JPEG', quality=95)
                elif save_ext == 'png':
                    img.save(output_path, 'PNG')
                elif save_ext == 'webp':
                    img.save(output_path, 'WEBP')
                elif save_ext == 'bmp':
                    img.save(output_path, 'BMP')
                else:
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
