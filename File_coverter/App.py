import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

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
        return redirect(url_for('convert_page', filename=file.filename))

@app.route('/convert/<filename>')
def convert_page(filename):
    ext = os.path.splitext(filename)[1].lower()
    
    # Dynamically choose options based on file type
    options_html = ""
    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
        options_html = """
            <option value="png">PNG (.png)</option>
            <option value="jpeg">JPG (.jpg)</option>
            <option value="webp">WEBP (.webp)</option>
            <option value="bmp">BMP (.bmp)</option>
        """
    elif ext in ['.xlsx', '.xls', '.csv']:
        options_html = """
            <option value="csv">CSV (.csv)</option>
            <option value="xlsx">Excel Workbook (.xlsx)</option>
            <option value="json">JSON (.json)</option>
        """
    else:
        options_html = "<option value='' disabled selected>No direct conversion supported yet</option>"

    # Uses style.css for consistent futuristic purple design
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PowerConv - Choose Format</title>
        <link rel="stylesheet" href="{url_for('static', filename='style.css')}">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Power<span class="bio-comp">Conv</span></h1>
            </div>
            <h2>Select Format</h2>
            <p style="color: #a78bfa; margin-bottom: 20px; font-size: 14px;">File: <strong style="color: #fff;">{filename}</strong></p>
            
            <form action="/process/{filename}" method="POST">
                <select name="format">
                    {options_html}
                </select>
                <button type="submit" class="btn-process" style="padding: 12px; font-weight: 600; border-radius: 8px;">Convert File Now</button>
            </form>
            <br>
            <a href="/" style="color: #c084fc; text-decoration: none; font-size: 14px;">← Choose another file</a>
        </div>
    </body>
    </html>
    """

@app.route('/process/<filename>', methods=['POST'])
def process_conversion(filename):
    target_format = request.form.get('format')
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    base_name = os.path.splitext(filename)[0]
    output_filename = f"{base_name}_converted.{target_format}"
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
    
    ext = os.path.splitext(filename)[1].lower()

    try:
        # Image Conversion
        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
            with Image.open(input_path) as img:
                if target_format == 'jpeg' and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.save(output_path, target_format.upper())

        # Spreadsheet/Data Conversion
        elif ext in ['.xlsx', '.xls', '.csv']:
            df = pd.read_csv(input_path) if ext == '.csv' else pd.read_excel(input_path)
            if target_format == 'csv':
                df.to_csv(output_path, index=False)
            elif target_format == 'xlsx':
                df.to_excel(output_path, index=False)
            elif target_format == 'json':
                df.to_json(output_path, orient='records', indent=4)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PowerConv - Success</title>
            <link rel="stylesheet" href="{url_for('static', filename='style.css')}">
        </head>
        <body>
            <div class="container">
                <div style="font-size: 48px; margin-bottom: 10px;">✨</div>
                <h2 style="color: #34d399; margin-bottom: 10px;">Ready!</h2>
                <p style="color: #a78bfa; font-size: 14px; margin-bottom: 25px;">Your file has been converted to <strong>.{target_format}</strong>.</p>
                <a href="/download/{output_filename}" class="btn-process" style="display: inline-block; text-decoration: none; padding: 14px; border-radius: 8px; background: linear-gradient(135deg, #059669, #34d399);">Download Converted File</a>
                <br><br>
                <a href="/" style="color: #c084fc; text-decoration: none; font-size: 14px;">← Convert another file</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"Conversion Error: {str(e)}"

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
