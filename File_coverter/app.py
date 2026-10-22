import os
import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from PIL import Image, ImageEnhance
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)
app.secret_key = "powerconv_secret_key"

UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

COMMON_STYLES = """
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/style.css">
"""

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        tool_type = request.form.get('tool_type', 'convert')
        return redirect(url_for('process_page', filename=file.filename, tool=tool_type))

@app.route('/process-page/<filename>')
def process_page(filename):
    ext = os.path.splitext(filename)[1].lower()
    tool = request.args.get('tool', 'convert')

    # Build Tool-Specific Controls
    controls_html = ""

    if tool == 'convert':
        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
            options = """
                <option value="png">PNG (.png)</option>
                <option value="jpeg">JPG (.jpg)</option>
                <option value="webp">WEBP (.webp)</option>
                <option value="bmp">BMP (.bmp)</option>
            """
        elif ext in ['.xlsx', '.xls', '.csv']:
            options = """
                <option value="csv">CSV (.csv)</option>
                <option value="xlsx">Excel Workbook (.xlsx)</option>
                <option value="json">JSON (.json)</option>
            """
        elif ext in ['.txt']:
            options = """
                <option value="pdf">PDF Document (.pdf)</option>
            """
        else:
            options = "<option value='' disabled>No direct conversion formats available</option>"

        controls_html = f"""
            <label style="color:#a78bfa; font-size:14px; display:block; margin-bottom:8px;">Target Format:</label>
            <select name="format" style="width:100%; padding:12px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff; margin-bottom:20px;">
                {options}
            </select>
        """

    elif tool == 'pdf_edit':
        if ext != '.pdf':
            return f"<h3>Error: Selected file is not a PDF!</h3><a href='/'>Go back</a>"
        reader = PdfReader(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        total_pages = len(reader.pages)

        controls_html = f"""
            <p style="color:#a78bfa; font-size:14px; margin-bottom:15px;">Total Pages Detected: <strong>{total_pages}</strong></p>
            <label style="color:#a78bfa; font-size:13px; display:block; text-align:left;">Rearrange Page Order (e.g., 3,1,2):</label>
            <input type="text" name="page_order" placeholder="1,2,3..." value="{','.join(str(i+1) for i in range(total_pages))}" style="width:100%; padding:10px; margin-bottom:15px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">
            
            <label style="color:#a78bfa; font-size:13px; display:block; text-align:left;">Rotate All Pages (Degrees):</label>
            <select name="rotation" style="width:100%; padding:10px; margin-bottom:20px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">
                <option value="0">0° (No Rotation)</option>
                <option value="90">90° Clockwise</option>
                <option value="180">180° Flip</option>
                <option value="270">270° Counter-Clockwise</option>
            </select>
        """

    elif tool == 'image_enhance':
        if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
            return f"<h3>Error: Selected file is not a supported image!</h3><a href='/'>Go back</a>"
        
        controls_html = """
            <div style="text-align:left; font-size:13px; color:#a78bfa;">
                <label>Resize Width (px, leave blank for original):</label>
                <input type="number" name="width" placeholder="e.g. 1920" style="width:100%; padding:8px; margin-bottom:12px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">
                
                <label>Resize Height (px, leave blank for original):</label>
                <input type="number" name="height" placeholder="e.g. 1080" style="width:100%; padding:8px; margin-bottom:12px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">

                <label>Brightness Multiplier (1.0 = Default, 1.5 = Brighter):</label>
                <input type="number" step="0.1" name="brightness" value="1.0" style="width:100%; padding:8px; margin-bottom:12px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">

                <label>Contrast Multiplier (1.0 = Default, 1.3 = Higher):</label>
                <input type="number" step="0.1" name="contrast" value="1.0" style="width:100%; padding:8px; margin-bottom:12px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">

                <label>Sharpness Multiplier (1.0 = Default, 2.0 = Sharp):</label>
                <input type="number" step="0.1" name="sharpness" value="1.0" style="width:100%; padding:8px; margin-bottom:20px; background:rgba(13,0,26,0.6); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff;">
            </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>PowerConv - Processing Studio</title>{COMMON_STYLES}</head>
    <body>
        <div class="container">
            <div class="header"><h1>Power<span class="bio-comp">Conv</span></h1></div>
            <h2>Tool Studio</h2>
            <p style="color:#a78bfa; margin-bottom:20px; font-size:14px;">Active File: <strong style="color:#fff;">{filename}</strong></p>

            <form action="/execute/{tool}/{filename}" method="POST">
                {controls_html}
                <button type="submit" class="btn-process" style="padding:14px; font-weight:600; border-radius:8px; width:100%;">Process File Now</button>
            </form>
            <br>
            <a href="/" style="color:#c084fc; text-decoration:none; font-size:14px;">← Choose another file / tool</a>
        </div>
    </body>
    </html>
    """

@app.route('/execute/<tool>/<filename>', methods=['POST'])
def execute_action(tool, filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    base_name, ext = os.path.splitext(filename)
    
    try:
        # 1. FILE CONVERTER
        if tool == 'convert':
            target_format = request.form.get('format')
            output_filename = f"{base_name}_converted.{target_format}"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            if ext.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
                with Image.open(input_path) as img:
                    if target_format == 'jpeg' and img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.save(output_path, target_format.upper())

            elif ext.lower() in ['.xlsx', '.xls', '.csv']:
                df = pd.read_csv(input_path) if ext.lower() == '.csv' else pd.read_excel(input_path)
                if target_format == 'csv':
                    df.to_csv(output_path, index=False)
                elif target_format == 'xlsx':
                    df.to_excel(output_path, index=False)
                elif target_format == 'json':
                    df.to_json(output_path, orient='records', indent=4)

        # 2. PDF REARRANGER & EDIT
        elif tool == 'pdf_edit':
            output_filename = f"{base_name}_edited.pdf"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            page_order = request.form.get('page_order', '')
            rotation = int(request.form.get('rotation', 0))

            reader = PdfReader(input_path)
            writer = PdfWriter()

            # Parse user page order
            pages_indices = [int(p.strip()) - 1 for p in page_order.split(',') if p.strip().isdigit()]
            
            for idx in pages_indices:
                if 0 <= idx < len(reader.pages):
                    page = reader.pages[idx]
                    if rotation != 0:
                        page.rotate(rotation)
                    writer.add_page(page)

            with open(output_path, "wb") as f_out:
                writer.write(f_out)

        # 3. IMAGE ENHANCER & RESIZER
        elif tool == 'image_enhance':
            output_filename = f"{base_name}_enhanced{ext}"
            output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

            width = request.form.get('width')
            height = request.form.get('height')
            brightness = float(request.form.get('brightness', 1.0))
            contrast = float(request.form.get('contrast', 1.0))
            sharpness = float(request.form.get('sharpness', 1.0))

            with Image.open(input_path) as img:
                # Resize
                if width or height:
                    new_w = int(width) if width else img.width
                    new_h = int(height) if height else img.height
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Enhancements
                if brightness != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(brightness)
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)
                if sharpness != 1.0:
                    img = ImageEnhance.Sharpness(img).enhance(sharpness)

                img.save(output_path)

        # Render Download Box Page
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>PowerConv - Ready</title>{COMMON_STYLES}</head>
        <body>
            <div class="container">
                <div style="font-size:48px; margin-bottom:10px;">✨</div>
                <h2 style="color:#34d399; margin-bottom:10px;">Processing Complete!</h2>
                <p style="color:#a78bfa; font-size:14px; margin-bottom:25px;">Your file <strong>{output_filename}</strong> is ready.</p>
                <a href="/download/{output_filename}" class="btn-process" style="display:inline-block; text-decoration:none; padding:14px 28px; border-radius:8px; background:linear-gradient(135deg, #059669, #34d399);">Download Converted File</a>
                <br><br><br>
                <a href="/" style="color:#c084fc; text-decoration:none; font-size:14px;">← Process another file</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h3>Processing Error: {str(e)}</h3><a href='/'>Go Back</a>"

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
