"""
Continuity Camera & Remote Phone Camera Server for macOS Photo Booth.
Features:
- Lightweight HTTP micro-server running on local Wi-Fi/LAN (port 8768).
- Zero-app installation: iPhones and Android phones can scan a QR code to instantly use their phone camera.
- High-resolution photo capture directly from phone's native camera or live HTML5 viewfinder.
- Real-time live frame streaming to desktop Photo Booth viewfinder.
- Instant photo upload to ~/Pictures/Photo Booth with screen flash & shutter sound triggers.
"""

import os
import sys
import time
import json
import socket
import threading
import asyncio
import websockets
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable

from gi.repository import GLib

PHOTOBOOTH_PORT = 8768
PHOTOBOOTH_WS_PORT = 8769
PHOTOS_DIR = os.path.expanduser("~/Pictures/Photo Booth")
os.makedirs(PHOTOS_DIR, exist_ok=True)

def get_local_ip() -> str:
    """Retrieve the primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
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
        if nodename and nodename != "localhost":
            return f"{nodename.capitalize()}"
    except Exception:
        pass
    return "Ubuntu Mac"


HTML_MOBILE_APP = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Photo Booth Live Camera</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
            -webkit-user-select: none;
            -webkit-touch-callout: none;
        }
        body {
            background-color: #000000;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
            height: 100vh;
            height: 100dvh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        /* Top Navigation Bar */
        .top-bar {
            height: 56px;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(18, 18, 20, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            z-index: 10;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        }
        .app-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 15px;
            font-weight: 600;
            letter-spacing: -0.2px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #ff3b30;
            box-shadow: 0 0 8px #ff3b30;
            animation: pulse 1.5s infinite;
        }
        .status-dot.active {
            background-color: #30d158;
            box-shadow: 0 0 10px #30d158;
        }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.9); }
            100% { opacity: 1; transform: scale(1); }
        }
        .live-badge {
            background: rgba(48, 209, 88, 0.2);
            border: 1px solid #30d158;
            color: #30d158;
            border-radius: 14px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .live-badge .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: #30d158;
            animation: pulse 1s infinite;
        }

        /* Camera Viewfinder Area */
        .viewfinder-container {
            flex: 1;
            position: relative;
            background-color: #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .flash-overlay {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #ffffff;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.08s ease-out;
            z-index: 50;
        }
        .flash-overlay.flashing {
            opacity: 1;
        }

        /* Permission / Fallback Container */
        .fallback-container {
            display: none;
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #0d0d0f;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
            text-align: center;
            gap: 18px;
            z-index: 20;
        }
        .fallback-icon {
            font-size: 64px;
        }
        .fallback-title {
            font-size: 20px;
            font-weight: 700;
        }
        .fallback-sub {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
            max-width: 300px;
            line-height: 1.5;
        }
        .enable-cam-btn {
            background: #007aff;
            color: #ffffff;
            font-size: 16px;
            font-weight: 600;
            padding: 14px 32px;
            border-radius: 26px;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0, 122, 255, 0.5);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Toast notification */
        .toast {
            position: absolute;
            top: 20px;
            background: rgba(28, 28, 30, 0.94);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ffffff;
            padding: 10px 22px;
            border-radius: 22px;
            font-size: 14px;
            font-weight: 600;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
            opacity: 0;
            transform: translateY(-10px);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
            z-index: 100;
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        /* Bottom Shutter & Controls Bar */
        .bottom-bar {
            height: 120px;
            padding-bottom: env(safe-area-inset-bottom, 16px);
            background: rgba(18, 18, 20, 0.88);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            display: flex;
            align-items: center;
            justify-content: space-around;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            z-index: 10;
        }
        .btn-side {
            width: 50px;
            height: 50px;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .btn-side:active {
            transform: scale(0.92);
            background: rgba(255, 255, 255, 0.3);
        }

        /* Iconic Apple Camera Shutter Button */
        .shutter-outer {
            width: 78px;
            height: 78px;
            border-radius: 39px;
            border: 4px solid #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.1s ease-out;
        }
        .shutter-inner {
            width: 64px;
            height: 64px;
            border-radius: 32px;
            background-color: #ffffff;
            transition: all 0.12s ease-out;
        }
        .shutter-outer:active .shutter-inner {
            transform: scale(0.85);
            background-color: #e5e5ea;
        }

        /* Hidden inputs */
        input[type="file"] {
            display: none;
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="app-title">
            <div id="statusDot" class="status-dot"></div>
            <span>Photo Booth • {machine_name}</span>
        </div>
        <div id="liveBadge" class="live-badge">
            <div class="dot"></div>
            <span id="liveText">LIVE 0 FPS</span>
        </div>
    </div>

    <div class="viewfinder-container">
        <video id="videoElement" autoplay playsinline muted></video>
        <div id="flashOverlay" class="flash-overlay"></div>
        <div id="toast" class="toast">Đã chụp và lưu vào Photo Booth! 📸</div>

        <!-- If permission needed or camera blocked -->
        <div id="fallbackContainer" class="fallback-container">
            <div class="fallback-icon">📷</div>
            <div class="fallback-title">Cho phép truy cập Camera</div>
            <div class="fallback-sub">Nhấn nút bên dưới để bật Camera trực tiếp truyền hình ảnh tức thì tới Photo Booth trên máy tính.</div>
            <button class="enable-cam-btn" onclick="requestCameraAccess()">
                <span>📹</span> Bật Camera Trực Tiếp
            </button>
        </div>
    </div>

    <div class="bottom-bar">
        <!-- Pick from Photo Album -->
        <button class="btn-side" onclick="openPhotoPicker()" title="Album ảnh">
            🖼️
        </button>

        <!-- Shutter Button -->
        <div class="shutter-outer" onclick="takePhoto()">
            <div class="shutter-inner"></div>
        </div>

        <!-- Switch Camera (Front/Back) -->
        <button class="btn-side" onclick="switchCamera()" title="Đổi camera trước/sau">
            🔄
        </button>
    </div>

    <!-- Hidden file input for photo picker -->
    <input type="file" id="photoPickerInput" accept="image/*" onchange="handleFileSelected(this)">

    <!-- Offscreen canvas for frame capture & streaming -->
    <canvas id="streamCanvas" style="display:none;"></canvas>

    <script>
        let currentFacingMode = "environment"; // "environment" (rear) or "user" (front)
        let currentStream = null;
        let isStreamingActive = true;
        let isSendingFrame = false;
        let frameCount = 0;
        let lastFpsUpdate = performance.now();

        const video = document.getElementById("videoElement");
        const flash = document.getElementById("flashOverlay");
        const toast = document.getElementById("toast");
        const streamCanvas = document.getElementById("streamCanvas");
        const sCtx = streamCanvas.getContext("2d", { alpha: false });
        const fallbackContainer = document.getElementById("fallbackContainer");
        const statusDot = document.getElementById("statusDot");
        const liveText = document.getElementById("liveText");

        // Notify server immediately on load
        fetch("/api/ping", { method: "POST" }).catch(() => {});

        async function initCamera() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                showFallback();
                return;
            }

            if (currentStream) {
                currentStream.getTracks().forEach(t => t.stop());
                currentStream = null;
            }

            const constraintsList = [
                { video: { facingMode: { ideal: currentFacingMode }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
                { video: { facingMode: currentFacingMode }, audio: false },
                { video: true, audio: false }
            ];

            let stream = null;
            for (const constraints of constraintsList) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                    if (stream) break;
                } catch (e) {
                    // Try next constraint
                }
            }

            if (!stream) {
                showFallback();
                return;
            }

            currentStream = stream;
            video.srcObject = stream;
            fallbackContainer.style.display = "none";
            video.style.display = "block";
            statusDot.classList.add("active");

            try {
                await video.play();
            } catch (e) {}

            // Start continuous frame stream loop
            isStreamingActive = true;
            startStreamingLoop();
        }

        function requestCameraAccess() {
            initCamera();
        }

        function showFallback() {
            video.style.display = "none";
            fallbackContainer.style.display = "flex";
            statusDot.classList.remove("active");
            liveText.innerText = "OFFLINE";
        }

        function switchCamera() {
            currentFacingMode = currentFacingMode === "environment" ? "user" : "environment";
            initCamera();
        }

        function openPhotoPicker() {
            document.getElementById("photoPickerInput").click();
        }

        function triggerFlash() {
            flash.classList.add("flashing");
            if (navigator.vibrate) {
                navigator.vibrate(40);
            }
            setTimeout(() => {
                flash.classList.remove("flashing");
            }, 120);
        }

        function showToast(msg) {
            toast.innerText = msg;
            toast.classList.add("show");
            setTimeout(() => {
                toast.classList.remove("show");
            }, 2500);
        }

        /* High-Speed WebSocket Connection for 60 FPS Streaming */
        let ws = null;
        function connectWebSocket() {
            const proto = location.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = `${proto}//${location.hostname}:8769`;
            try {
                ws = new WebSocket(wsUrl);
                ws.binaryType = "blob";
                ws.onopen = () => {
                    console.log("WebSocket connected for 60 FPS streaming");
                };
                ws.onclose = () => {
                    setTimeout(connectWebSocket, 1500);
                };
                ws.onerror = () => {
                    try { ws.close(); } catch(e) {}
                };
            } catch (e) {
                console.warn("WS connect error:", e);
            }
        }
        connectWebSocket();

        /* Continuous Ultra-Low Latency Live Frame Streamer */
        function startStreamingLoop() {
            let lastSendTime = 0;
            const targetInterval = 20; // Target 50-60 FPS

            async function frameTick() {
                if (!isStreamingActive) return;

                const now = performance.now();
                // Measure FPS
                frameCount++;
                if (now - lastFpsUpdate >= 1000) {
                    const fps = Math.round((frameCount * 1000) / (now - lastFpsUpdate));
                    liveText.innerText = `LIVE ${fps} FPS`;
                    frameCount = 0;
                    lastFpsUpdate = now;
                }

                if (!isSendingFrame && (now - lastSendTime >= targetInterval)) {
                    if (video.videoWidth > 0 && video.style.display !== "none") {
                        isSendingFrame = true;
                        lastSendTime = now;
                        try {
                            const vw = video.videoWidth;
                            const vh = video.videoHeight;
                            const maxDim = 800;
                            let targetW = vw;
                            let targetH = vh;
                            if (vw > maxDim || vh > maxDim) {
                                if (vw >= vh) {
                                    targetW = maxDim;
                                    targetH = Math.round((vh / vw) * maxDim);
                                } else {
                                    targetH = maxDim;
                                    targetW = Math.round((vw / vh) * maxDim);
                                }
                            }

                            if (streamCanvas.width !== targetW || streamCanvas.height !== targetH) {
                                streamCanvas.width = targetW;
                                streamCanvas.height = targetH;
                            }

                            if (currentFacingMode === "user") {
                                sCtx.save();
                                sCtx.translate(targetW, 0);
                                sCtx.scale(-1, 1);
                                sCtx.drawImage(video, 0, 0, targetW, targetH);
                                sCtx.restore();
                            } else {
                                sCtx.drawImage(video, 0, 0, targetW, targetH);
                            }

                            if (ws && ws.readyState === WebSocket.OPEN) {
                                if (ws.bufferedAmount < 150000) {
                                    streamCanvas.toBlob((blob) => {
                                        if (blob && ws && ws.readyState === WebSocket.OPEN) {
                                            ws.send(blob);
                                        }
                                        isSendingFrame = false;
                                    }, "image/jpeg", 0.65);
                                } else {
                                    isSendingFrame = false;
                                }
                            } else {
                                streamCanvas.toBlob(async (blob) => {
                                    if (blob) {
                                        try {
                                            await fetch("/api/stream_frame", {
                                                method: "POST",
                                                headers: { "Content-Type": "image/jpeg" },
                                                body: blob
                                            });
                                        } catch (e) {}
                                    }
                                    isSendingFrame = false;
                                }, "image/jpeg", 0.65);
                            }
                        } catch (err) {
                            isSendingFrame = false;
                        }
                    }
                }

                requestAnimationFrame(frameTick);
            }

            requestAnimationFrame(frameTick);
        }

        /* High Resolution Photo Capture */
        async function takePhoto() {
            if (video.videoWidth > 0) {
                triggerFlash();
                const snapCanvas = document.createElement("canvas");
                snapCanvas.width = video.videoWidth;
                snapCanvas.height = video.videoHeight;
                const ctx = snapCanvas.getContext("2d");

                if (currentFacingMode === "user") {
                    ctx.translate(snapCanvas.width, 0);
                    ctx.scale(-1, 1);
                }
                ctx.drawImage(video, 0, 0, snapCanvas.width, snapCanvas.height);

                snapCanvas.toBlob(async (blob) => {
                    if (blob) {
                        await uploadPhoto(blob);
                    }
                }, "image/jpeg", 0.95);
            } else {
                openPhotoPicker();
            }
        }

        function handleFileSelected(input) {
            if (input.files && input.files[0]) {
                triggerFlash();
                const file = input.files[0];
                uploadPhoto(file);
                input.value = "";
            }
        }

        async function uploadPhoto(blob) {
            showToast("Đang chuyển ảnh tới Photo Booth...");
            const formData = new FormData();
            formData.append("photo", blob, "phone_capture.jpg");

            try {
                const res = await fetch("/api/upload_photo", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                if (data.status === "ok") {
                    showToast("Đã lưu ảnh vào Photo Booth! 📸");
                } else {
                    showToast("Lỗi: " + (data.error || "Gửi thất bại"));
                }
            } catch (err) {
                showToast("Lỗi kết nối tới máy tính!");
            }
        }

        // Initialize camera on page load
        window.addEventListener("DOMContentLoaded", initCamera);
    </script>
</body>
</html>
"""


SSL_CERT_PATH = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth/ssl/cert.pem"
SSL_KEY_PATH = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth/ssl/key.pem"

class PhoneCameraHandler(BaseHTTPRequestHandler):
    server_instance: 'PhoneCameraServer' = None
    protocol_version = "HTTP/1.1"

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception:
            pass

    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            machine = get_machine_name()
            html = HTML_MOBILE_APP.replace("{machine_name}", machine)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/status":
            resp = {
                "status": "ok",
                "machine": get_machine_name(),
                "connected": self.server_instance.is_phone_connected if self.server_instance else False
            }
            body = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/ping":
            if self.server_instance:
                self.server_instance.notify_phone_connected()
            resp = {"status": "ok", "machine": get_machine_name()}
            body = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/stream_frame":
            content_length = int(self.headers.get("Content-Length", 0))
            frame_bytes = self.rfile.read(content_length) if content_length > 0 else b""
            if self.server_instance and frame_bytes:
                self.server_instance.notify_frame_received(frame_bytes)
            resp = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(resp)

        elif path == "/api/upload_photo":
            content_length = int(self.headers.get("Content-Length", 0))
            content_type = self.headers.get("Content-Type", "")

            raw_data = self.rfile.read(content_length) if content_length > 0 else b""
            saved_path = self._extract_and_save_photo(raw_data, content_type)

            if saved_path:
                if self.server_instance:
                    self.server_instance.notify_photo_received(saved_path)
                resp = {"status": "ok", "filename": os.path.basename(saved_path), "path": saved_path}
            else:
                resp = {"status": "error", "error": "Không thể xử lý tệp ảnh"}

            body = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def _extract_and_save_photo(self, data: bytes, content_type: str) -> Optional[str]:
        """Extracts JPEG/PNG bytes and writes to ~/Pictures/Photo Booth."""
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Photo_Phone_{ts}.jpg"
        out_path = os.path.join(PHOTOS_DIR, filename)

        if "multipart/form-data" in content_type:
            # Parse multipart boundary
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[len("boundary="):].strip('"').encode("ascii")
                    break

            if boundary:
                # Find start of file data after header \r\n\r\n
                delimiter = b"--" + boundary
                sections = data.split(delimiter)
                for sec in sections:
                    if b"filename=" in sec:
                        idx = sec.find(b"\r\n\r\n")
                        if idx != -1:
                            file_content = sec[idx + 4:].rstrip(b"\r\n")
                            with open(out_path, "wb") as f:
                                f.write(file_content)
                            return out_path
        else:
            # Raw image stream
            if len(data) > 0:
                with open(out_path, "wb") as f:
                    f.write(data)
                return out_path

        return None


class PhoneCameraServer:
    """Manages the Continuity Camera server daemon with HTTPS support."""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = PhoneCameraServer()
        return cls._instance

    def __init__(self, port: int = PHOTOBOOTH_PORT):
        self.port = port
        self.ws_port = PHOTOBOOTH_WS_PORT
        self.server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_phone_connected = False
        self.is_https = False
        self.last_ping_time = 0

        # Callbacks
        self.on_photo_received_cb: Optional[Callable[[str], None]] = None
        self.on_frame_received_cb: Optional[Callable[[bytes], None]] = None
        self.on_phone_connected_cb: Optional[Callable[[], None]] = None

    def start(self):
        """Starts HTTPS/HTTP and WebSocket servers in background threads."""
        if self.server:
            return

        handler_cls = PhoneCameraHandler
        handler_cls.server_instance = self

        try:
            self.server = ThreadingHTTPServer(('0.0.0.0', self.port), handler_cls)
            if os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH):
                try:
                    import ssl
                    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    ctx.load_cert_chain(certfile=SSL_CERT_PATH, keyfile=SSL_KEY_PATH)
                    self.server.socket = ctx.wrap_socket(self.server.socket, server_side=True)
                    self.is_https = True
                except Exception as e:
                    print(f"[PhoneCamera] SSL wrapping failed, falling back to HTTP: {e}")
                    self.is_https = False
            else:
                self.is_https = False

            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()
            scheme = "https" if self.is_https else "http"
            print(f"[PhoneCamera] Continuity Camera Server running on {scheme}://{get_local_ip()}:{self.port}")

            # Start High-Performance WebSocket Server for 60 FPS live feed
            self._ws_thread = threading.Thread(target=self._run_ws_server, daemon=True)
            self._ws_thread.start()
        except Exception as e:
            print(f"[PhoneCamera] Failed to start server on port {self.port}: {e}")
            self.server = None

    def _run_ws_server(self):
        """Runs an ultra-low-latency WebSocket server using asyncio."""
        self._ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._ws_loop)

        async def ws_handler(websocket):
            self.notify_phone_connected()
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        self.notify_frame_received(message)
                    elif isinstance(message, str) and message == "ping":
                        await websocket.send("pong")
            except Exception:
                pass

        ssl_ctx = None
        if os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH):
            try:
                import ssl
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_ctx.load_cert_chain(certfile=SSL_CERT_PATH, keyfile=SSL_KEY_PATH)
            except Exception:
                ssl_ctx = None

        async def main():
            try:
                async with websockets.serve(ws_handler, '0.0.0.0', self.ws_port, ssl=ssl_ctx, max_size=10*1024*1024):
                    print(f"[PhoneCamera] WebSocket High-FPS Server running on port {self.ws_port}")
                    await asyncio.Future()
            except Exception as e:
                print(f"[PhoneCamera] WebSocket serve failed on port {self.ws_port}: {e}")

        try:
            self._ws_loop.run_until_complete(main())
        except Exception:
            pass

    def stop(self):
        """Gracefully shuts down server."""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
            self._thread = None
        if self._ws_loop and self._ws_loop.is_running():
            try:
                self._ws_loop.call_soon_threadsafe(self._ws_loop.stop)
            except Exception:
                pass
            self._ws_loop = None
            self._ws_thread = None
        print("[PhoneCamera] Continuity Camera Server stopped.")

    def get_url(self) -> str:
        scheme = "https" if getattr(self, "is_https", False) else "http"
        return f"{scheme}://{get_local_ip()}:{self.port}"

    def notify_phone_connected(self):
        self.is_phone_connected = True
        self.last_ping_time = time.time()
        if self.on_phone_connected_cb:
            GLib.idle_add(self.on_phone_connected_cb)

    def notify_photo_received(self, filepath: str):
        if self.on_photo_received_cb:
            GLib.idle_add(self.on_photo_received_cb, filepath)

    def notify_frame_received(self, jpeg_bytes: bytes):
        self.is_phone_connected = True
        if self.on_frame_received_cb:
            try:
                self.on_frame_received_cb(jpeg_bytes)
            except Exception:
                pass
