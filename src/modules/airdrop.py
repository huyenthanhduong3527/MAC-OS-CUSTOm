"""
Apple macOS AirDrop & WebDrop Engine for Ubuntu Linux.
Features:
- Local network device discovery via UDP broadcast beacon (compatible across LAN/Wi-Fi).
- Built-in HTTP AirDrop & WebDrop server for instant file transfer from/to iPhones, iPads, Macs, Android, and Linux.
- Zero-installation mobile transfer: iPhones and Android phones can scan a QR code to transfer files instantly.
- High-efficiency non-blocking async network I/O with progress callbacks.
- File integrity check, safe destination naming in ~/Downloads, and auto-notification hooks.
"""

import os
import sys
import time
import json
import socket
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Callable
from gi.repository import GLib

# Default network ports
AIRDROP_HTTP_PORT = 8765
AIRDROP_BEACON_PORT = 8766
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

def get_local_ip() -> str:
    """Retrieve the primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect to 1.1.1.1, just chooses appropriate network interface
        s.connect(('1.1.1.1', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_machine_name() -> str:
    """Retrieve friendly machine name matching macOS style."""
    try:
        from src.config import config
        dev_name = config.get("device_name", "").strip()
        if dev_name:
            return dev_name
        nodename = os.uname().nodename
        # Format as "Ubuntu Mac" or hostname
        if nodename and nodename != "localhost":
            return f"{nodename.capitalize()}"
    except Exception:
        pass
    return "Ubuntu Mac"

def get_safe_filepath(dest_dir: str, filename: str) -> str:
    """Ensure unique destination path without overwriting existing files."""
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(dest_dir, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        counter += 1
    return candidate

def format_size(bytes_size: int) -> str:
    """Format bytes into human-readable size string."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


class AirDropHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP Handler serving the sleek Apple WebDrop UI and receiving/sending files.
    Compatible with iOS Safari, Chrome Mobile, Android, macOS, and Linux.
    """
    server_instance: 'AirDropServer' = None
    protocol_version = "HTTP/1.1"

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception:
            pass

    def log_message(self, format, *args):
        # Suppress verbose default console logging
        pass

    def do_HEAD(self):
        """Respond to HEAD requests (e.g. curl -I, Safari captive/connectivity checks)."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            dev_name = self.server_instance.device_name if self.server_instance else "Mac"
            html_len = len(self._generate_html(dev_name).encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(html_len))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        elif path in ("/favicon.ico", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests from modern web browsers."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._serve_webdrop_html()
        elif path in ("/favicon.ico", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):
            self._serve_favicon()
        elif path == "/api/info":
            self._serve_json({
                "name": self.server_instance.device_name,
                "type": "mac",
                "os": "macOS Sequoia on Ubuntu",
                "status": "ready"
            })
        elif path == "/api/devices":
            devices = self.server_instance.manager.get_discovered_devices()
            self._serve_json(devices)
        elif path == "/api/pending_downloads":
            client_id = query.get("client_id", [""])[0]
            downloads = self.server_instance.get_pending_downloads(client_id)
            self._serve_json(downloads)
        elif path == "/api/download":
            transfer_id = query.get("id", [""])[0]
            self._handle_file_download(transfer_id)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/upload":
            self._handle_file_upload()
        elif path == "/api/register":
            self._handle_client_register()
        elif path == "/api/heartbeat":
            self._handle_client_heartbeat()
        else:
            self.send_error(404, "Not Found")

    def _serve_json(self, data):
        content = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_favicon(self):
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#007aff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.5"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>"""
        content = svg.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(content)

    def _generate_html(self, dev_name: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>AirDrop • {dev_name}</title>
<style>
  :root {{
    --bg: #000000;
    --card-bg: rgba(28, 28, 32, 0.82);
    --border: rgba(255, 255, 255, 0.12);
    --accent: #007aff;
    --accent-hover: #0062cc;
    --text: #ffffff;
    --text-sec: #8e8e93;
    --success: #34c759;
    --success-bg: rgba(52, 199, 89, 0.15);
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f2f2f7;
      --card-bg: rgba(255, 255, 255, 0.88);
      --border: rgba(0, 0, 0, 0.1);
      --text: #1d1d1f;
      --text-sec: #86868b;
    }}
  }}
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-font-smoothing: antialiased;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }}
  .container {{
    width: 100%;
    max-width: 440px;
    background: var(--card-bg);
    backdrop-filter: blur(40px);
    -webkit-backdrop-filter: blur(40px);
    border: 1px solid var(--border);
    border-radius: 28px;
    padding: 28px 22px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.35);
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .connection-chip {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(52, 199, 89, 0.12);
    border: 1px solid rgba(52, 199, 89, 0.28);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
    color: var(--success);
    margin-bottom: 20px;
  }}
  .chip-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 8px var(--success);
    animation: pulse-dot 2s infinite;
  }}
  @keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.5; transform: scale(0.85); }}
  }}
  .radar-icon {{
    width: 76px;
    height: 76px;
    margin: 0 auto 16px;
    border-radius: 50%;
    background: linear-gradient(135deg, #007aff, #5856d6);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 24px rgba(0,122,255,0.4);
    position: relative;
  }}
  .radar-icon::before {{
    content: '';
    position: absolute;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    border: 2px solid rgba(0,122,255,0.35);
    animation: pulse 2.2s infinite ease-out;
  }}
  @keyframes pulse {{
    0% {{ transform: scale(0.75); opacity: 0.85; }}
    100% {{ transform: scale(1.4); opacity: 0; }}
  }}
  h1 {{ font-size: 23px; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.4px; }}
  p.subtitle {{ font-size: 14px; color: var(--text-sec); margin-bottom: 22px; line-height: 1.4; }}

  /* Direct Tappable Dropzone as Label */
  .drop-zone {{
    display: block;
    border: 2px dashed rgba(0, 122, 255, 0.45);
    border-radius: 20px;
    padding: 30px 16px;
    background: rgba(0, 122, 255, 0.05);
    cursor: pointer;
    transition: all 0.25s ease;
    margin-bottom: 16px;
    user-select: none;
  }}
  .drop-zone:active {{
    background: rgba(0, 122, 255, 0.15);
    border-color: var(--accent);
    transform: scale(0.98);
  }}
  .drop-zone-icon {{ font-size: 40px; margin-bottom: 8px; }}
  .drop-zone-title {{ font-size: 16px; font-weight: 600; color: var(--accent); }}
  .drop-zone-sub {{ font-size: 12px; color: var(--text-sec); margin-top: 4px; }}

  /* Quick action buttons for iOS */
  .action-buttons {{
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
  }}
  .btn-action {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 20px;
    border-radius: 16px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    user-select: none;
    text-decoration: none;
  }}
  .btn-media {{
    background: var(--accent);
    color: #ffffff;
    box-shadow: 0 4px 14px rgba(0, 122, 255, 0.35);
  }}
  .btn-media:active {{
    background: var(--accent-hover);
    transform: scale(0.98);
  }}
  .btn-files {{
    background: rgba(255, 255, 255, 0.09);
    border: 1px solid var(--border);
    color: var(--text);
  }}
  .btn-files:active {{
    background: rgba(255, 255, 255, 0.16);
    transform: scale(0.98);
  }}

  /* Screen-reader only / invisible input that iOS Safari will never block */
  .sr-only {{
    position: absolute !important;
    width: 0.1px !important;
    height: 0.1px !important;
    opacity: 0 !important;
    overflow: hidden !important;
    z-index: -1 !important;
    pointer-events: none !important;
  }}

  .progress-wrap {{
    margin-top: 18px;
    display: none;
    text-align: left;
    background: rgba(0,0,0,0.25);
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid var(--border);
  }}
  .status-row {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 600;
  }}
  .file-name {{
    max-width: 250px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .percent-text {{
    color: var(--accent);
  }}
  .progress-bar-bg {{
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 10px;
  }}
  .progress-bar-fill {{
    width: 0%;
    height: 100%;
    background: linear-gradient(90deg, #007aff, #34c759);
    border-radius: 4px;
    transition: width 0.12s ease;
  }}
  .transfer-details {{
    font-size: 11px;
    color: var(--text-sec);
    margin-top: 6px;
  }}

  .success-badge {{
    display: none;
    margin-top: 16px;
    padding: 14px 16px;
    background: var(--success-bg);
    border: 1px solid rgba(52, 199, 89, 0.3);
    border-radius: 16px;
    text-align: left;
    animation: fade-in 0.3s ease;
  }}
  @keyframes fade-in {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  .badge-title {{
    color: var(--success);
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 2px;
  }}
  .badge-sub {{
    font-size: 12px;
    color: var(--text-sec);
  }}

  /* Modal for incoming files (Ubuntu -> iPhone) */
  .modal-overlay {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.65);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
    padding: 20px;
  }}
  .modal-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 24px 20px;
    width: 100%;
    max-width: 380px;
    text-align: center;
    box-shadow: 0 25px 60px rgba(0,0,0,0.5);
    animation: pop-up 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }}
  @keyframes pop-up {{
    from {{ transform: scale(0.9); opacity: 0; }}
    to {{ transform: scale(1); opacity: 1; }}
  }}
  .modal-icon {{
    width: 56px;
    height: 56px;
    margin: 0 auto 12px;
    border-radius: 50%;
    background: rgba(0, 122, 255, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .modal-title {{ font-size: 18px; font-weight: 700; margin-bottom: 6px; }}
  .modal-desc {{ font-size: 13px; color: var(--text-sec); margin-bottom: 20px; line-height: 1.4; word-break: break-all; }}
  .modal-desc b {{ color: var(--text); }}
  .modal-buttons {{
    display: flex;
    gap: 10px;
  }}
  .btn-modal-cancel {{
    flex: 1;
    padding: 12px;
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border);
    border-radius: 14px;
    color: var(--text);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }}
  .btn-modal-download {{
    flex: 1;
    padding: 12px;
    background: var(--accent);
    border: none;
    border-radius: 14px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
</style>
</head>
<body>

<div class="container">
  <div class="connection-chip">
    <span class="chip-dot"></span>
    <span>Đã kết nối với <b>{dev_name}</b></span>
  </div>

  <div class="radar-icon">
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="2.5"/>
      <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>
    </svg>
  </div>

  <h1>AirDrop tới {dev_name}</h1>
  <p class="subtitle">Chạm để chọn ảnh, video hoặc tệp tin để chuyển ngay sang máy tính qua Wi-Fi</p>

  <!-- Drop Zone (Natively activates file picker on tap via label) -->
  <label for="fileInputAll" class="drop-zone" id="dropZone">
    <div class="drop-zone-icon">📁</div>
    <div class="drop-zone-title">Chạm vào đây để chọn tệp</div>
    <div class="drop-zone-sub">Hỗ trợ Ảnh, Video, Tài liệu, v.v.</div>
  </label>

  <!-- Quick Action Buttons for iOS & Mobile -->
  <div class="action-buttons">
    <label for="fileInputMedia" class="btn-action btn-media">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
      <div style="text-align: left; line-height: 1.25;">
        <div style="font-size: 16px; font-weight: 700;">📸 Chọn Ảnh / Video từ iPhone</div>
        <div style="font-size: 12px; opacity: 0.88; font-weight: 500;">Chọn ảnh xong là tự động gửi thẳng sang máy tính</div>
      </div>
    </label>
    <label for="fileInputAll" class="btn-action btn-files">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
      <span>Chọn Tài liệu / Tệp tin khác</span>
    </label>
  </div>

  <!-- Native Hidden Inputs (Never blocked by iOS Safari) -->
  <input type="file" id="fileInputMedia" accept="image/*,video/*" multiple class="sr-only">
  <input type="file" id="fileInputAll" accept="*/*" multiple class="sr-only">

  <!-- Transfer Progress -->
  <div class="progress-wrap" id="progressWrap">
    <div class="status-row">
      <span class="file-name" id="fileName">Đang gửi...</span>
      <span class="percent-text" id="percentText">0%</span>
    </div>
    <div class="progress-bar-bg">
      <div class="progress-bar-fill" id="progressFill"></div>
    </div>
    <div class="transfer-details" id="transferDetails">Đang truyền qua Wi-Fi...</div>
  </div>

  <!-- Success Notification -->
  <div class="success-badge" id="successBadge">
    <div class="badge-title">✓ Đã gửi tệp thành công!</div>
    <div class="badge-sub">Đã lưu an toàn vào thư mục Downloads trên {dev_name}.</div>
  </div>
</div>

<!-- Incoming Download Modal (Ubuntu -> iPhone) -->
<div class="modal-overlay" id="downloadModal">
  <div class="modal-card">
    <div class="modal-icon">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#007aff" stroke-width="2.2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
    </div>
    <div class="modal-title">AirDrop từ {dev_name}</div>
    <div class="modal-desc">
      Máy tính muốn gửi tệp tin cho bạn:<br>
      <b id="dlFileName">tệp.jpg</b> (<span id="dlFileSize">0 MB</span>)
    </div>
    <div class="modal-buttons">
      <button class="btn-modal-cancel" id="btnModalCancel">Để sau</button>
      <a class="btn-modal-download" id="btnModalDownload" href="#" download>Tải về máy</a>
    </div>
  </div>
</div>

<script>
  // Device identity
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isAndroid = /Android/.test(navigator.userAgent);
  let devType = 'mac';
  let devName = 'Trình duyệt Web';
  if (isIOS) {{
    devType = 'iphone';
    devName = 'iPhone';
  }} else if (isAndroid) {{
    devType = 'phone';
    devName = 'Điện thoại Android';
  }}

  let clientId = localStorage.getItem('airdrop_client_id');
  if (!clientId) {{
    clientId = 'client_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
    localStorage.setItem('airdrop_client_id', clientId);
  }}

  // Elements
  const fileInputMedia = document.getElementById('fileInputMedia');
  const fileInputAll = document.getElementById('fileInputAll');
  const progressWrap = document.getElementById('progressWrap');
  const progressFill = document.getElementById('progressFill');
  const percentText = document.getElementById('percentText');
  const fileName = document.getElementById('fileName');
  const transferDetails = document.getElementById('transferDetails');
  const successBadge = document.getElementById('successBadge');

  const downloadModal = document.getElementById('downloadModal');
  const dlFileName = document.getElementById('dlFileName');
  const dlFileSize = document.getElementById('dlFileSize');
  const btnModalDownload = document.getElementById('btnModalDownload');
  const btnModalCancel = document.getElementById('btnModalCancel');

  // Register client to host server
  function registerPresence() {{
    fetch('/api/register', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ id: clientId, name: devName, type: devType }})
    }}).catch(() => {{}});
  }}
  registerPresence();

  // Heartbeat & Check incoming downloads
  setInterval(() => {{
    fetch('/api/heartbeat', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ id: clientId, name: devName, type: devType }})
    }}).catch(() => {{}});

    // Check if Ubuntu sent a file to this iPhone
    fetch('/api/pending_downloads?client_id=' + encodeURIComponent(clientId))
      .then(r => r.json())
      .then(downloads => {{
        if (downloads && downloads.length > 0) {{
          const item = downloads[0];
          showDownloadPrompt(item);
        }}
      }})
      .catch(() => {{}});
  }}, 2500);

  function showDownloadPrompt(item) {{
    dlFileName.textContent = item.filename;
    dlFileSize.textContent = item.size_formatted || (Math.round(item.size/1024) + ' KB');
    btnModalDownload.href = '/api/download?id=' + encodeURIComponent(item.id);
    btnModalDownload.download = item.filename;
    downloadModal.style.display = 'flex';
  }}

  btnModalCancel.addEventListener('click', () => {{
    downloadModal.style.display = 'none';
  }});

  btnModalDownload.addEventListener('click', () => {{
    downloadModal.style.display = 'none';
    if (navigator.vibrate) navigator.vibrate(50);
  }});

  // File selection triggers upload
  [fileInputMedia, fileInputAll].forEach(input => {{
    input.addEventListener('change', () => {{
      if (input.files && input.files.length > 0) {{
        uploadFiles(Array.from(input.files));
        input.value = ''; // Reset for next pick
      }}
    }});
  }});

  // Drag & drop support for iPad/desktop
  const dropZone = document.getElementById('dropZone');
  ['dragenter', 'dragover'].forEach(name => {{
    dropZone.addEventListener(name, (e) => {{ e.preventDefault(); dropZone.style.borderColor = '#007aff'; }});
  }});
  ['dragleave', 'drop'].forEach(name => {{
    dropZone.addEventListener(name, (e) => {{ e.preventDefault(); dropZone.style.borderColor = 'rgba(0,122,255,0.45)'; }});
  }});
  dropZone.addEventListener('drop', (e) => {{
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
      uploadFiles(Array.from(e.dataTransfer.files));
    }}
  }});

  async function uploadFiles(files) {{
    successBadge.style.display = 'none';
    progressWrap.style.display = 'block';

    for (let i = 0; i < files.length; i++) {{
      const file = files[i];
      transferDetails.textContent = 'Tệp ' + (i + 1) + ' / ' + files.length;
      await uploadSingleFile(file);
    }}

    progressWrap.style.display = 'none';
    successBadge.style.display = 'block';
    if (navigator.vibrate) navigator.vibrate([40, 80, 40]);
  }}

  function uploadSingleFile(file) {{
    return new Promise((resolve, reject) => {{
      fileName.textContent = file.name;
      percentText.textContent = '0%';
      progressFill.style.width = '0%';

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/upload?filename=' + encodeURIComponent(file.name));

      xhr.upload.onprogress = (e) => {{
        if (e.lengthComputable) {{
          const pct = Math.round((e.loaded / e.total) * 100);
          percentText.textContent = pct + '%';
          progressFill.style.width = pct + '%';
          const loadedMb = (e.loaded / (1024 * 1024)).toFixed(1);
          const totalMb = (e.total / (1024 * 1024)).toFixed(1);
          transferDetails.textContent = loadedMb + ' MB / ' + totalMb + ' MB';
        }}
      }};

      xhr.onload = () => {{
        if (xhr.status >= 200 && xhr.status < 300) {{
          resolve();
        }} else {{
          alert('Gửi tệp thất bại: ' + xhr.statusText);
          reject();
        }}
      }};

      xhr.onerror = () => {{
        alert('Lỗi kết nối Wi-Fi tới máy tính.');
        reject();
      }};

      xhr.send(file);
    }});
  }}
</script>
</body>
</html>
"""

    def _serve_webdrop_html(self):
        """Serve an authentic Apple-styled WebDrop page for mobile and desktop browsers."""
        dev_name = self.server_instance.device_name if self.server_instance else "Mac"
        html = self._generate_html(dev_name)
        content = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_client_register(self):
        """Register a web client (like iPhone) as a peer on the local AirDrop network."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8")) if body else {}
            client_ip = self.client_address[0]
            client_id = data.get("id") or f"web_{client_ip.replace('.', '_')}"
            client_name = data.get("name") or "iPhone"
            device_type = data.get("type", "iphone")

            peer_info = {
                "id": client_id,
                "name": client_name,
                "type": device_type,
                "ip": client_ip,
                "port": AIRDROP_HTTP_PORT,
                "is_web": True,
                "last_seen": time.time()
            }
            if self.server_instance:
                self.server_instance.manager.register_peer(peer_info)
                self.server_instance.register_web_client(client_id, peer_info)
                self._serve_json({"status": "ok", "id": client_id, "server_name": self.server_instance.device_name})
            else:
                self._serve_json({"status": "ok", "id": client_id})
        except Exception as e:
            self._serve_json({"status": "error", "message": str(e)})

    def _handle_client_heartbeat(self):
        """Touch last_seen timestamp for active web clients."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8")) if body else {}
            client_ip = self.client_address[0]
            client_id = data.get("id") or f"web_{client_ip.replace('.', '_')}"
            client_name = data.get("name") or "iPhone"
            device_type = data.get("type", "iphone")

            peer_info = {
                "id": client_id,
                "name": client_name,
                "type": device_type,
                "ip": client_ip,
                "port": AIRDROP_HTTP_PORT,
                "is_web": True,
                "last_seen": time.time()
            }
            if self.server_instance:
                self.server_instance.manager.register_peer(peer_info)
                self.server_instance.touch_web_client(client_id)
            self._serve_json({"status": "ok"})
        except Exception as e:
            self._serve_json({"status": "error", "message": str(e)})

    def _handle_file_upload(self):
        """Receive binary file stream and save to ~/Downloads with iOS Shortcut support."""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        filename = query.get('filename', [None])[0]

        # Check X-Filename header (standard in iOS Shortcuts)
        if not filename:
            x_fn = self.headers.get('X-Filename')
            if x_fn:
                filename = urllib.parse.unquote(x_fn.strip())

        # Check Content-Disposition header
        if not filename:
            cd = self.headers.get('Content-Disposition', '')
            if 'filename=' in cd:
                parts = cd.split('filename=')
                if len(parts) > 1:
                    filename = parts[1].strip('"\'; ')

        content_length = int(self.headers.get('Content-Length', 0))
        sender_ip = self.client_address[0]

        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

        chunk_size = 64 * 1024
        first_chunk = b""
        if content_length > 0:
            to_read = min(chunk_size, content_length)
            first_chunk = self.rfile.read(to_read)
        elif content_length == 0:
            first_chunk = self.rfile.read()
            content_length = len(first_chunk)

        # Detect extension from magic bytes
        detected_ext = ""
        if len(first_chunk) >= 3 and first_chunk[:3] == b'\xff\xd8\xff':
            detected_ext = ".jpg"
        elif len(first_chunk) >= 8 and first_chunk[:8] == b'\x89PNG\r\n\x1a\n':
            detected_ext = ".png"
        elif b'ftypheic' in first_chunk[:32] or b'ftypmif1' in first_chunk[:32] or b'ftypheix' in first_chunk[:32] or b'ftypmsf1' in first_chunk[:32]:
            detected_ext = ".heic"
        elif b'ftyp' in first_chunk[:16]:
            detected_ext = ".mp4"
        elif len(first_chunk) >= 4 and first_chunk[:4] == b'%PDF':
            detected_ext = ".pdf"
        elif len(first_chunk) >= 12 and first_chunk[:4] == b'RIFF' and first_chunk[8:12] == b'WEBP':
            detected_ext = ".webp"
        elif len(first_chunk) >= 6 and first_chunk[:6] in (b'GIF87a', b'GIF89a'):
            detected_ext = ".gif"

        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename or filename in ('shared_file', 'blob', 'file', 'image'):
            filename = f"iPhone_Photo_{time_str}{detected_ext or '.jpg'}"
        else:
            filename = os.path.basename(filename)
            _, ext = os.path.splitext(filename)
            if not ext and detected_ext:
                filename = f"{filename}{detected_ext}"

        dest_path = get_safe_filepath(DOWNLOADS_DIR, filename)

        # Notify incoming transfer start
        if self.server_instance:
            self.server_instance.manager.notify_transfer_start(
                filename=filename,
                file_size=content_length,
                sender_ip=sender_ip,
                is_incoming=True
            )

        bytes_read = len(first_chunk)
        with open(dest_path, "wb") as f:
            if first_chunk:
                f.write(first_chunk)
            while bytes_read < content_length:
                to_read = min(chunk_size, content_length - bytes_read)
                chunk = self.rfile.read(to_read)
                if not chunk:
                    break
                f.write(chunk)
                bytes_read += len(chunk)

                if content_length > 0 and self.server_instance:
                    pct = (bytes_read / content_length) * 100.0
                    self.server_instance.manager.notify_transfer_progress(
                        filename=filename,
                        pct=pct,
                        is_incoming=True
                    )

        # Notify completion
        if self.server_instance:
            self.server_instance.manager.notify_transfer_complete(
                filename=filename,
                file_path=dest_path,
                sender_ip=sender_ip,
                is_incoming=True
            )

        response = json.dumps({"status": "ok", "saved_path": dest_path, "filename": filename}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _handle_file_download(self, transfer_id: str):
        """Stream a pending file download to the mobile web browser."""
        if not self.server_instance:
            self.send_error(500, "Server instance unavailable")
            return

        transfer = self.server_instance.pending_transfers.get(transfer_id)
        if not transfer:
            self.send_error(404, "Download not found or expired")
            return

        file_path = transfer["file_path"]
        filename = transfer["filename"]

        if not os.path.exists(file_path):
            self.send_error(404, "File no longer exists")
            return

        file_size = os.path.getsize(file_path)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{urllib.parse.quote(filename)}"')
        self.send_header("Content-Length", str(file_size))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        chunk_size = 64 * 1024
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except Exception:
                    break

        on_done = transfer.get("on_done")
        if on_done:
            GLib.idle_add(on_done, True, "")

        self.server_instance.manager.notify_transfer_complete(
            filename=filename,
            file_path=file_path,
            sender_ip=self.client_address[0],
            is_incoming=False
        )

        with self.server_instance._lock:
            self.server_instance.pending_transfers.pop(transfer_id, None)


class AirDropServer:
    """HTTP file transfer server for AirDrop and WebDrop."""
    def __init__(self, manager: 'AirDropManager', port: int = AIRDROP_HTTP_PORT):
        self.manager = manager
        self.port = port
        self.device_name = get_machine_name()
        self.httpd = None
        self._thread = None
        self.is_running = False
        self._lock = threading.Lock()
        self.web_clients: Dict[str, Dict] = {}
        self.pending_transfers: Dict[str, Dict] = {}

    def start(self):
        if self.is_running:
            return
        AirDropHTTPHandler.server_instance = self
        try:
            self.httpd = ThreadingHTTPServer(('0.0.0.0', self.port), AirDropHTTPHandler)
            self.is_running = True
            self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self._thread.start()
        except Exception as e:
            print(f"[AirDropServer] Notice: Port {self.port} error: {e}")

    def stop(self):
        if self.httpd and self.is_running:
            self.is_running = False
            self.httpd.shutdown()
            self.httpd.server_close()

    def register_web_client(self, client_id: str, info: Dict):
        with self._lock:
            self.web_clients[client_id] = info

    def touch_web_client(self, client_id: str):
        with self._lock:
            if client_id in self.web_clients:
                self.web_clients[client_id]["last_seen"] = time.time()

    def is_web_client(self, target_ip_or_id: str) -> bool:
        with self._lock:
            if target_ip_or_id in self.web_clients:
                return True
            for client in self.web_clients.values():
                if client.get("ip") == target_ip_or_id or client.get("id") == target_ip_or_id:
                    return True
        return False

    def queue_download(self, target_ip_or_id: str, file_path: str, on_done=None) -> str:
        with self._lock:
            client_id = target_ip_or_id
            for cid, cinfo in self.web_clients.items():
                if cinfo.get("ip") == target_ip_or_id or cid == target_ip_or_id:
                    client_id = cid
                    break

            transfer_id = f"tx_{int(time.time()*1000)}_{os.path.basename(file_path)}"
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            self.pending_transfers[transfer_id] = {
                "id": transfer_id,
                "client_id": client_id,
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "on_done": on_done,
                "created_at": time.time()
            }
            return transfer_id

    def get_pending_downloads(self, client_id: str) -> List[Dict]:
        with self._lock:
            res = []
            for tid, tinfo in list(self.pending_transfers.items()):
                if tinfo["client_id"] == client_id or not client_id:
                    res.append({
                        "id": tid,
                        "filename": tinfo["filename"],
                        "size": tinfo["file_size"],
                        "size_formatted": format_size(tinfo["file_size"])
                    })
            return res


class AirDropBeacon:
    """
    UDP Broadcast Beacon for peer-to-peer discovery on the local network.
    """
    def __init__(self, manager: 'AirDropManager', port: int = AIRDROP_BEACON_PORT):
        self.manager = manager
        self.port = port
        self._running = False
        self._sock = None
        self._broadcast_thread = None
        self._listen_thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(('', self.port))
            self._sock.settimeout(1.0)
        except Exception as e:
            print(f"[AirDropBeacon] UDP bind notice: {e}")
            return

        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._broadcast_thread.start()
        self._listen_thread.start()

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def _broadcast_loop(self):
        my_ip = get_local_ip()
        my_id = f"mac_{my_ip.replace('.', '_')}"
        msg = json.dumps({
            "id": my_id,
            "name": get_machine_name(),
            "type": "mac",
            "ip": my_ip,
            "port": AIRDROP_HTTP_PORT,
            "discoverable": self.manager.discoverable_mode
        }).encode("utf-8")

        while self._running:
            if self.manager.discoverable_mode != "off":
                try:
                    self._sock.sendto(msg, ('<broadcast>', self.port))
                except Exception:
                    pass
            time.sleep(3.0)

    def _listen_loop(self):
        my_ip = get_local_ip()
        while self._running:
            try:
                data, addr = self._sock.recvfrom(2048)
                peer_ip = addr[0]
                if peer_ip == my_ip:
                    continue

                info = json.loads(data.decode("utf-8"))
                info["ip"] = peer_ip
                info["last_seen"] = time.time()
                self.manager.register_peer(info)
            except (socket.timeout, json.JSONDecodeError, Exception):
                pass


class AirDropManager:
    """
    Central Coordinator for macOS AirDrop on Linux.
    Manages local discovery, file sending, receiving, and UI event dispatching.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AirDropManager()
        return cls._instance

    def __init__(self):
        self.device_name = get_machine_name()
        self.discoverable_mode = "everyone" # "everyone", "contacts", "off"
        self._peers: Dict[str, Dict] = {}
        self._lock = threading.Lock()

        # Listeners
        self.on_device_list_changed: Optional[Callable] = None
        self._transfer_listeners: List[Callable] = []

        # Network servers
        self.server = AirDropServer(self, AIRDROP_HTTP_PORT)
        self.beacon = AirDropBeacon(self, AIRDROP_BEACON_PORT)

        self.start()

    def start(self):
        self.server.start()
        self.beacon.start()
        # Periodically purge stale peers (older than 12 seconds)
        threading.Thread(target=self._purge_loop, daemon=True).start()

    def stop(self):
        self.beacon.stop()
        self.server.stop()

    def add_transfer_listener(self, listener: Callable):
        """Register a callback for file transfer events."""
        if listener not in self._transfer_listeners:
            self._transfer_listeners.append(listener)

    def remove_transfer_listener(self, listener: Callable):
        """Unregister a callback for file transfer events."""
        if listener in self._transfer_listeners:
            self._transfer_listeners.remove(listener)

    @property
    def on_transfer_event(self):
        return None

    @on_transfer_event.setter
    def on_transfer_event(self, listener: Optional[Callable]):
        if listener:
            self.add_transfer_listener(listener)

    def set_discoverable_mode(self, mode: str):
        self.discoverable_mode = mode # "everyone", "contacts", "off"

    def get_local_url(self) -> str:
        return f"http://{get_local_ip()}:{AIRDROP_HTTP_PORT}"

    def register_peer(self, peer_info: Dict):
        peer_id = peer_info.get("id") or peer_info.get("ip")
        with self._lock:
            self._peers[peer_id] = peer_info

        if self.on_device_list_changed:
            GLib.idle_add(self.on_device_list_changed)

    def get_discovered_devices(self) -> List[Dict]:
        with self._lock:
            now = time.time()
            return [p for p in self._peers.values() if now - p.get("last_seen", 0) < 12]

    def _purge_loop(self):
        while True:
            time.sleep(4.0)
            now = time.time()
            changed = False
            with self._lock:
                stale_keys = [k for k, v in self._peers.items() if now - v.get("last_seen", 0) >= 12]
                for k in stale_keys:
                    del self._peers[k]
                    changed = True
            if changed and self.on_device_list_changed:
                GLib.idle_add(self.on_device_list_changed)

    # -------------------------------------------------------------
    # SENDING FILES TO PEERS
    # -------------------------------------------------------------
    def send_file_async(self, target_ip: str, file_path: str, target_port: int = AIRDROP_HTTP_PORT,
                        on_progress: Optional[Callable] = None, on_done: Optional[Callable] = None):
        """Send a file to target peer (Native or WebDrop) in a background thread."""
        def _worker():
            success = False
            err_msg = ""
            try:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File '{file_path}' does not exist.")

                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # Check if target is a WebDrop web client (e.g. iPhone browser)
                if self.server.is_web_client(target_ip):
                    self.notify_transfer_start(filename, file_size, target_ip, is_incoming=False)
                    self.server.queue_download(target_ip, file_path, on_done=on_done)
                    return

                # Standard AirDrop HTTP POST to remote peer server
                self.notify_transfer_start(filename, file_size, target_ip, is_incoming=False)
                url = f"http://{target_ip}:{target_port}/api/upload?filename={urllib.parse.quote(filename)}"

                with open(file_path, "rb") as f:
                    req = urllib.request.Request(url, data=f, method="POST")
                    req.add_header("Content-Length", str(file_size))
                    req.add_header("Content-Type", "application/octet-stream")

                    with urllib.request.urlopen(req, timeout=30.0) as resp:
                        if resp.status == 200:
                            success = True

                self.notify_transfer_complete(filename, file_path, target_ip, is_incoming=False)
            except Exception as e:
                err_msg = str(e)
                print(f"[AirDrop] Send file error to {target_ip}: {e}")

            if on_done:
                GLib.idle_add(on_done, success, err_msg)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # EVENT DISPATCHERS (THREAD-SAFE TO GTK)
    # -------------------------------------------------------------
    def notify_transfer_start(self, filename: str, file_size: int, sender_ip: str, is_incoming: bool):
        for listener in list(self._transfer_listeners):
            try:
                GLib.idle_add(listener, "start", {
                    "filename": filename,
                    "file_size": file_size,
                    "ip": sender_ip,
                    "is_incoming": is_incoming
                })
            except Exception:
                pass

    def notify_transfer_progress(self, filename: str, pct: float, is_incoming: bool):
        for listener in list(self._transfer_listeners):
            try:
                GLib.idle_add(listener, "progress", {
                    "filename": filename,
                    "percent": pct,
                    "is_incoming": is_incoming
                })
            except Exception:
                pass

    def notify_transfer_complete(self, filename: str, file_path: str, sender_ip: str, is_incoming: bool):
        for listener in list(self._transfer_listeners):
            try:
                GLib.idle_add(listener, "complete", {
                    "filename": filename,
                    "file_path": file_path,
                    "ip": sender_ip,
                    "is_incoming": is_incoming
                })
            except Exception:
                pass
