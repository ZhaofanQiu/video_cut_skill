#!/usr/bin/env python3
"""Simple file upload server for testing."""

import http.server
import socketserver
import os
import uuid
from pathlib import Path

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Video Upload - Video Cut Skill Test</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .upload-form {
            border: 2px dashed #ccc;
            padding: 40px;
            text-align: center;
            border-radius: 8px;
            transition: border-color 0.3s;
        }
        .upload-form:hover {
            border-color: #007bff;
        }
        input[type="file"] {
            margin: 20px 0;
            padding: 10px;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #0056b3;
        }
        .file-list {
            margin-top: 30px;
        }
        .file-item {
            padding: 10px;
            background: #f8f9fa;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .success {
            color: #28a745;
            font-weight: bold;
        }
        .info {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Video Cut Skill - 文件上传</h1>
        <p class="subtitle">上传视频文件进行功能测试</p>
        
        <div class="info">
            <strong>支持的格式：</strong>MP4, MOV, AVI, MKV 等<br>
            <strong>文件大小：</strong>建议不超过 500MB<br>
            <strong>上传后：</strong>AI 助手将自动检测到文件并进行测试
        </div>
        
        <form class="upload-form" method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept="video/*" required>
            <br>
            <button type="submit">📤 上传视频</button>
        </form>
        
        <div class="file-list">
            <h3>已上传文件</h3>
            {file_list}
        </div>
    </div>
</body>
</html>
"""

class UploadHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - show upload form."""
        # List uploaded files
        files = []
        if UPLOAD_DIR.exists():
            for f in sorted(UPLOAD_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    files.append(f"""
                        <div class="file-item">
                            <span>{f.name} ({size_mb:.2f} MB)</span>
                            <span class="success">✓ 已就绪</span>
                        </div>
                    """)
        
        file_list_html = "\n".join(files) if files else "<p>暂无上传文件</p>"
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_FORM.format(file_list=file_list_html).encode())
    
    def do_POST(self):
        """Handle POST requests - file upload."""
        import cgi
        
        # Parse form data
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'}
        )
        
        if 'file' in form:
            file_item = form['file']
            if file_item.filename:
                # Generate unique filename
                ext = Path(file_item.filename).suffix
                filename = f"{uuid.uuid4().hex[:8]}{ext}"
                filepath = UPLOAD_DIR / filename
                
                # Save file
                with open(filepath, 'wb') as f:
                    f.write(file_item.file.read())
                
                # Redirect back to form with success
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
                return
        
        # Error
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b"Upload failed")
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def start_server(port=8080):
    """Start the upload server."""
    with socketserver.TCPServer(("", port), UploadHandler) as httpd:
        print(f"🚀 Upload server started at http://localhost:{port}")
        print(f"📁 Upload directory: {UPLOAD_DIR}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")


if __name__ == "__main__":
    start_server()
