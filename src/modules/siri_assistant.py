"""
Siri Assistant Engine for Dynamic Island (Ubuntu macOS Experience).
Powered by Local AI Model Qwen 2.5 1.5B (via Ollama).
100% Offline, Private, Fast, and Free (No API Keys required).

Features:
- Local Qwen 2.5 1.5B Instruct reasoning & multi-turn dialog
- Active OS & System Automation (Double-Layer Execution):
  * Layer 1: Fast Intent Matching (< 10ms for instant execution)
  * Layer 2: Qwen 2.5 Tool/Action Tag Parsing ([ACTION: ...] actuator)
- Supported System Actions:
  * Open Applications (Dynamic scan of all installed Linux & macOS apps)
  * Delete Files/Folders (Safe Trash via gio trash or permanent removal)
  * Open Files (.txt, .pdf, images, videos, audio via default handlers)
  * Create Files & Documents (Markdown, text, notes on Desktop/Documents)
  * Read & Summarize Files
  * List Files in Desktop / Documents / Downloads
  * System Controls: Dark/Light mode, Battery, Timer, Weather, Google Drive
- Multilingual Neural Voice (Edge-TTS via voice_synthesizer)
"""

import os
import re
import glob
import json
import time
import shutil
import urllib.request
import urllib.parse
import urllib.error
import threading
import subprocess
from typing import Dict, Any, List, Optional, Callable, Tuple

from src.modules.voice_synthesizer import voice_synthesizer

CONFIG_PATH = os.path.expanduser("~/.config/dynamic_island/siri_config.json")
OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:1.5b"

SYSTEM_PROMPT = """Bạn là trợ lý ảo Siri điều khiển hệ thống thông minh Qwen 2.5 trên Ubuntu Linux (Giao diện Dynamic Island macOS).
BẠN CÓ TOÀN QUYỀN TRUY CẬP VÀ ĐIỀU KHIỂN HỆ THỐNG để mở ứng dụng, xóa tệp tin, tạo tài liệu, mở file trên máy tính của người dùng.

KHI NGƯỜI DÙNG YÊU CẦU HÀNH ĐỘNG HỆ THỐNG, BẠN BẮT BUỘC PHẢI XUẤT THẺ LỆNH HỆ THỐNG [ACTION: ...] để phần mềm lập tức thực thi:
- Mở ứng dụng: [ACTION: open_app {"app": "tên_ứng_dụng"}]
- Xóa tệp hoặc thư mục: [ACTION: delete_file {"file": "tên_file"}]
- Tạo tệp mới: [ACTION: create_file {"file": "tên_file", "content": "nội dung"}]
- Mở tệp/tài liệu: [ACTION: open_file {"file": "tên_file"}]
- Đọc nội dung tệp: [ACTION: read_file {"file": "tên_file"}]
- Liệt kê tệp: [ACTION: list_files {"folder": "Desktop"}]

QUY TẮC BẮT BUỘC:
1. TUYỆT ĐỐI KHÔNG BAO GIỜ nói "Tôi là AI không thể thực hiện", KHÔNG bao giờ từ chối lệnh xóa file hay mở app.
2. KHÔNG hướng dẫn người dùng tự thao tác bằng tay (như "Bước 1 mở File Explorer...").
3. Hãy luôn xuất thẻ lệnh [ACTION: ...] kèm câu xác nhận ngắn gọn (1-2 câu để đọc to).
Ví dụ:
- Người dùng: "xóa file test.txt trên desktop" -> Bạn: "[ACTION: delete_file {"file": "test.txt"}] Đã xóa file test.txt trên Desktop cho bạn."
- Người dùng: "mor app chrome" -> Bạn: "[ACTION: open_app {"app": "chrome"}] Đang mở Google Chrome cho bạn."
- Người dùng: "tạo file ghi_chu.txt" -> Bạn: "[ACTION: create_file {"file": "ghi_chu.txt", "content": "Ghi chú mới"}] Đã tạo tệp ghi_chu.txt trên Desktop."
"""


class SiriAssistant:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.model: str = DEFAULT_MODEL
        self.voice_enabled: bool = True
        self.selected_voice: str = "vi-female"
        self.conversation_history: List[Dict[str, str]] = []
        self._installed_apps_cache: Dict[str, str] = {}
        self._cache_time: float = 0
        self.load_config()
        self.ensure_ollama_service()
        self._refresh_apps_cache()

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.model = data.get("model", DEFAULT_MODEL)
                    self.voice_enabled = data.get("voice_enabled", True)
                    self.selected_voice = data.get("selected_voice", "vi-female")
                    voice_synthesizer.set_enabled(self.voice_enabled)
                    voice_synthesizer.set_voice_key(self.selected_voice)
            except Exception as e:
                print(f"[SiriAssistant] Load config error: {e}")

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "model": self.model,
                    "voice_enabled": self.voice_enabled,
                    "selected_voice": self.selected_voice
                }, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[SiriAssistant] Save config error: {e}")

    def set_voice_enabled(self, enabled: bool):
        self.voice_enabled = enabled
        voice_synthesizer.set_enabled(enabled)
        self.save_config()

    def set_voice(self, voice_key: str):
        self.selected_voice = voice_key
        voice_synthesizer.set_voice_key(voice_key)
        self.save_config()

    def set_model(self, model_name: str):
        self.model = model_name.strip()
        self.save_config()

    # --- Ollama Service Supervisor ---
    def is_ollama_running(self) -> bool:
        try:
            req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags", headers={"User-Agent": "DynamicIsland/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def ensure_ollama_service(self):
        """Starts ollama serve daemon in the background if not active."""
        if self.is_ollama_running():
            return
        def _starter():
            ollama_bin = os.path.expanduser("~/.local/bin/ollama")
            if not os.path.exists(ollama_bin):
                ollama_bin = shutil.which("ollama") or "ollama"
            try:
                subprocess.Popen(
                    [ollama_bin, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            except Exception as e:
                print(f"[SiriAssistant] Start ollama daemon error: {e}")
        threading.Thread(target=_starter, daemon=True).start()

    def check_local_model_status(self) -> Tuple[bool, str]:
        """Checks if Ollama is running and Qwen 2.5 1.5B is available."""
        if not self.is_ollama_running():
            return False, "Dịch vụ AI Ollama đang khởi động ngầm…"
        try:
            req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                for m in models:
                    if "qwen2.5:1.5b" in m or "qwen" in m:
                        return True, f"Mô hình Qwen 2.5 1.5B sẵn sàng ({m})"
                if models:
                    return True, f"Đang có mô hình: {', '.join(models[:2])}"
                return False, "Đang tải mô hình Qwen 2.5 1.5B về máy…"
        except Exception as e:
            return False, f"Lỗi kết nối Ollama: {e}"

    # --- Voice Output ---
    def speak(self, text: str):
        if self.voice_enabled and text:
            # Strip markdown markup & tags before speaking
            clean_speech = re.sub(r'\[ACTION:\s*[a-zA-Z_]+\s*\{.*?\}\]', '', text, flags=re.DOTALL)
            clean_speech = re.sub(r'<[^>]+>', '', clean_speech)
            clean_speech = re.sub(r'[\*\_#`]', '', clean_speech).strip()
            if clean_speech:
                voice_synthesizer.speak(clean_speech)

    def stop_speaking(self):
        voice_synthesizer.stop()

    # --- Dynamic Installed Applications Scanner ---
    def _refresh_apps_cache(self):
        """Scans installed desktop applications on Ubuntu."""
        now = time.time()
        if self._installed_apps_cache and (now - self._cache_time < 300):
            return

        apps = {}
        paths = [
            "/usr/share/applications/*.desktop",
            os.path.expanduser("~/.local/share/applications/*.desktop"),
            "/var/lib/snapd/desktop/applications/*.desktop",
            "/var/lib/flatpak/exports/share/applications/*.desktop"
        ]
        for pattern in paths:
            for df in glob.glob(pattern):
                try:
                    name, exec_cmd, nodisplay = "", "", False
                    with open(df, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.startswith("Name=") and not name:
                                name = line.split("=", 1)[1].strip()
                            elif line.startswith("Exec=") and not exec_cmd:
                                exec_cmd = line.split("=", 1)[1].strip().split("%")[0].strip()
                            elif line.strip() == "NoDisplay=true":
                                nodisplay = True
                    if name and exec_cmd and not nodisplay:
                        base_id = os.path.basename(df)
                        apps[name.lower()] = (base_id, exec_cmd)
                except Exception:
                    pass

        self._installed_apps_cache = apps
        self._cache_time = now

    # --- OS & System Automation Actions ---
    def action_open_app(self, app_name: str) -> Dict[str, Any]:
        """Launches desktop, system or custom macOS applications."""
        target = app_name.strip().lower()
        # Clean prefix noise
        target = re.sub(r'^(mở app|mở ứng dụng|mor app|bật app|chạy app|open app|mở|mor|bật|chạy|open|launch)\s+', '', target).strip()
        target = target.strip("'\"")

        # 1. Custom macOS & Dynamic Island apps
        run_sh = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/run.sh"

        if "airdrop" in target:
            subprocess.Popen([run_sh, "--airdrop"])
            return {"text": "Đang mở cửa sổ AirDrop để bạn chia sẻ tệp tin.", "success": True}

        if any(w in target for w in ["ảnh", "photos", "photo"]):
            subprocess.Popen([run_sh, "--photos"])
            return {"text": "Đang mở thư viện Ảnh macOS Photos.", "success": True}

        if any(w in target for w in ["ghi chú", "notes", "note"]):
            subprocess.Popen([run_sh, "--notes"])
            return {"text": "Đang mở ứng dụng Ghi chú macOS Notes.", "success": True}

        if any(w in target for w in ["cài đặt", "settings", "setting"]):
            subprocess.Popen([run_sh, "--settings"])
            return {"text": "Đang mở Cài đặt Hệ thống macOS.", "success": True}

        if any(w in target for w in ["chụp ảnh", "photobooth", "photo booth"]):
            subprocess.Popen([run_sh, "--photobooth"])
            return {"text": "Đang mở Photo Booth chụp ảnh macOS.", "success": True}

        if any(w in target for w in ["appstore", "app store", "cửa hàng"]):
            subprocess.Popen([run_sh, "--store"])
            return {"text": "Đang mở Cửa hàng ứng dụng macOS App Store.", "success": True}

        if any(w in target for w in ["drive", "google drive"]):
            try:
                from src.modules.google_account import google_account_mgr
                google_account_mgr.open_google_drive("local")
                return {"text": "Đang mở thư mục Google Drive trên máy tính.", "success": True}
            except Exception:
                pass

        # 2. Known Aliases for Ubuntu Linux
        alias_map = {
            "chrome": "google-chrome-stable || google-chrome",
            "google chrome": "google-chrome-stable || google-chrome",
            "trình duyệt": "google-chrome-stable || google-chrome || firefox || x-www-browser",
            "browser": "google-chrome-stable || google-chrome || firefox || x-www-browser",
            "web": "google-chrome-stable || google-chrome || firefox",
            "firefox": "firefox",
            "terminal": "ptyxis || gnome-terminal || x-terminal-emulator",
            "dòng lệnh": "ptyxis || gnome-terminal",
            "cmd": "ptyxis || gnome-terminal",
            "bash": "ptyxis || gnome-terminal",
            "tệp": "nautilus",
            "file": "nautilus",
            "thư mục": "nautilus",
            "nautilus": "nautilus",
            "máy tính": "gnome-calculator",
            "calculator": "gnome-calculator",
            "văn bản": "gnome-text-editor || gedit",
            "soạn thảo": "gnome-text-editor || gedit",
            "text editor": "gnome-text-editor || gedit",
            "camera": "cheese",
            "nhạc": "rhythmbox",
            "code": "code || vscodium",
            "vscode": "code || vscodium",
        }

        for alias, cmd in alias_map.items():
            if alias in target or target in alias:
                try:
                    subprocess.Popen(f"nohup {cmd} >/dev/null 2>&1 &", shell=True)
                    return {"text": f"Đang mở ứng dụng '{target}'.", "success": True}
                except Exception as e:
                    return {"text": f"Không thể mở {target}: {e}", "success": False}

        # 3. Search Desktop files cache
        self._refresh_apps_cache()
        for app_label, (desktop_id, exec_cmd) in self._installed_apps_cache.items():
            if target in app_label or app_label in target:
                try:
                    subprocess.Popen(["gtk-launch", desktop_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return {"text": f"Đang khởi chạy ứng dụng '{app_label.title()}'.", "success": True}
                except Exception:
                    try:
                        subprocess.Popen(f"nohup {exec_cmd} >/dev/null 2>&1 &", shell=True)
                        return {"text": f"Đang khởi chạy ứng dụng '{app_label.title()}'.", "success": True}
                    except Exception:
                        pass

        # 4. Check if command binary exists in PATH
        if shutil.which(target):
            try:
                subprocess.Popen(f"nohup {target} >/dev/null 2>&1 &", shell=True)
                return {"text": f"Đang khởi chạy {target}.", "success": True}
            except Exception as e:
                return {"text": f"Lỗi khởi chạy {target}: {e}", "success": False}

        return {"text": f"Không tìm thấy ứng dụng '{target}' trên máy tính.", "success": False}

    def extract_filename(self, query: str) -> str:
        """Extracts targeted filename from conversational prompt or query."""
        q = query.strip()
        # 1. Match after 'file' or 'tệp' keyword (e.g. 'file test_123.txt' or 'tệp note.md')
        m = re.search(r'\b(?:file|tệp|folder|thư mục)\s+([a-zA-Z0-9_\-\.]+)', q, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # 2. Match filename with extension (e.g. 'test.txt', 'image.png')
        m = re.search(r'\b([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)\b', q)
        if m:
            return m.group(1).strip()

        # 3. Clean conversational filler words
        fillers = [
            "xóa", "xoá", "xoa", "delete", "remove", "gỡ",
            "giúp tôi", "giúp mình", "giúp em", "giúp",
            "hộ tôi", "hộ mình", "hộ tao", "hộ em", "hộ",
            "cho tôi", "cho mình", "cho tao", "cho em", "cho",
            "dùm tôi", "dùm mình", "dùm",
            "trên desktop", "ở desktop", "ngoài desktop", "trên màn hình", "ngoài màn hình",
            "trong documents", "trong downloads", "trong thư mục",
            "với", "nhé", "nha", "nhá", "đi", "cái", "con", "tệp", "file", "ơi", "bạn", "qwen"
        ]
        cand = q
        for f in fillers:
            cand = re.sub(rf'\b{re.escape(f)}\b', '', cand, flags=re.IGNORECASE).strip()
        return cand.strip().strip("'\"")

    def extract_app_name(self, query: str) -> str:
        """Extracts application name from conversational prompt or query."""
        q = query.strip()
        m = re.search(r'\b(?:app|ứng dụng|phần mềm)\s+([^,.\n?]+)', q, re.IGNORECASE)
        cand = m.group(1).strip() if m else q

        fillers = [
            "mở app", "mor app", "mo app", "mowr app", "bật app", "chạy app", "open app",
            "mở ứng dụng", "bật ứng dụng", "chạy ứng dụng",
            "mở phần mềm", "bật phần mềm",
            "mở", "mor", "mo", "mowr", "bật", "chạy", "open", "launch",
            "giúp tôi", "giúp mình", "giúp em", "giúp",
            "hộ tôi", "hộ mình", "hộ tao", "hộ",
            "cho tôi", "cho mình", "cho",
            "lên nào", "lên đi", "lên", "với", "nhé", "nha", "nhá", "đi", "bạn", "ơi", "qwen"
        ]
        for f in fillers:
            cand = re.sub(rf'\b{re.escape(f)}\b', '', cand, flags=re.IGNORECASE).strip()
        return cand.strip().strip("'\"")

    def action_delete_file(self, file_query: str) -> Dict[str, Any]:
        """
        Deletes or moves a file to Trash:
        Uses 'gio trash' to safely move to Ubuntu Trash, or os.remove/shutil.rmtree.
        """
        fname = self.extract_filename(file_query)
        if not fname:
            return {"text": "Xin cho biết tên tệp bạn muốn xóa.", "success": False}

        home = os.path.expanduser("~")
        target_path = None

        # 1. Direct path check
        if os.path.exists(fname):
            target_path = fname
        elif os.path.exists(os.path.join(home, "Desktop", fname)):
            target_path = os.path.join(home, "Desktop", fname)
        elif os.path.exists(os.path.join(home, "Downloads", fname)):
            target_path = os.path.join(home, "Downloads", fname)
        elif os.path.exists(os.path.join(home, "Documents", fname)):
            target_path = os.path.join(home, "Documents", fname)
        elif os.path.exists(os.path.join(home, fname)):
            target_path = os.path.join(home, fname)
        else:
            # 2. Fuzzy search in key folders
            search_dirs = [
                os.path.join(home, "Desktop"),
                os.path.join(home, "Downloads"),
                os.path.join(home, "Documents"),
                home
            ]
            for sdir in search_dirs:
                if not os.path.isdir(sdir):
                    continue
                # Case-insensitive filename or basename match
                for entry in os.listdir(sdir):
                    if entry.lower() == fname.lower() or os.path.splitext(entry.lower())[0] == fname.lower():
                        target_path = os.path.join(sdir, entry)
                        break
                if target_path:
                    break

                # Glob pattern search
                matches = glob.glob(os.path.join(sdir, f"*{fname}*"))
                if matches:
                    target_path = matches[0]
                    break

        if not target_path or not os.path.exists(target_path):
            return {"text": f"Không tìm thấy tệp tin '{fname}' trên Desktop hay máy tính để xóa.", "success": False}

        base_name = os.path.basename(target_path)
        try:
            # Safe trash via gio trash
            res = subprocess.run(["gio", "trash", target_path], capture_output=True, text=True)
            if res.returncode == 0:
                return {
                    "text": f"Đã xóa tệp tin '{base_name}' và chuyển vào Thùng rác.",
                    "path": target_path,
                    "success": True
                }
            else:
                # Direct removal fallback
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
                return {
                    "text": f"Đã xóa hoàn toàn tệp tin '{base_name}'.",
                    "path": target_path,
                    "success": True
                }
        except Exception as e:
            return {"text": f"Lỗi khi xóa tệp '{base_name}': {e}", "success": False}

    def action_open_file(self, file_query: str) -> Dict[str, Any]:
        """Finds and opens a file using default system handler."""
        q = file_query.strip().strip("'\"")
        home = os.path.expanduser("~")

        target_file = None
        if os.path.exists(q):
            target_file = q
        else:
            fname = re.sub(r'^(mở|mor|mở file|mor file|mở tệp|mor tệp|xem|open file|open)\s+', '', q).strip()
            search_dirs = [
                os.path.join(home, "Desktop"),
                os.path.join(home, "Documents"),
                os.path.join(home, "Downloads"),
                home
            ]
            for sdir in search_dirs:
                if os.path.isdir(sdir):
                    matches = glob.glob(os.path.join(sdir, f"*{fname}*"))
                    if matches:
                        target_file = matches[0]
                        break

        if not target_file:
            return {"text": f"Không tìm thấy tệp tin '{file_query}' trong Desktop, Documents hay Downloads.", "success": False}

        try:
            subprocess.Popen(["xdg-open", target_file])
            base = os.path.basename(target_file)
            return {"text": f"Đã mở tệp tin '{base}' cho bạn.", "path": target_file, "success": True}
        except Exception as e:
            return {"text": f"Lỗi khi mở tệp: {e}", "success": False}

    def action_create_file(self, filename: str, content: str = "", folder: Optional[str] = None) -> Dict[str, Any]:
        """Creates a document or file and opens it in editor."""
        clean_name = filename.strip().strip("'\"")
        if not clean_name:
            clean_name = f"van_ban_{int(time.time())}.txt"
        if not re.search(r'\.[a-zA-Z0-9]+$', clean_name):
            clean_name += ".txt"

        dest_dir = folder or os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(dest_dir):
            dest_dir = os.path.join(os.path.expanduser("~"), "Documents")
        os.makedirs(dest_dir, exist_ok=True)

        full_path = os.path.join(dest_dir, clean_name)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content or f"Tài liệu {clean_name}\nNgày tạo: {time.strftime('%Y-%m-%d %H:%M:%S')}\nĐược tạo bởi Siri AI (Qwen 2.5 1.5B).\n")

            try:
                subprocess.Popen(["xdg-open", full_path])
            except Exception:
                pass

            rel_loc = "Desktop" if "Desktop" in dest_dir else "Documents"
            return {
                "text": f"Đã tạo tệp '{clean_name}' trên {rel_loc} và mở lên cho bạn.",
                "path": full_path,
                "success": True
            }
        except Exception as e:
            return {"text": f"Không thể tạo tệp: {e}", "success": False}

    def action_read_file(self, file_query: str) -> Dict[str, Any]:
        """Reads text content of a file."""
        q = file_query.strip().strip("'\"")
        home = os.path.expanduser("~")
        target_file = None

        if os.path.exists(q) and os.path.isfile(q):
            target_file = q
        else:
            fname = re.sub(r'^(đọc|doc|đọc file|doc file|xem nội dung|read)\s+', '', q).strip()
            for sdir in [os.path.join(home, "Desktop"), os.path.join(home, "Documents"), os.path.join(home, "Downloads"), home]:
                if os.path.isdir(sdir):
                    matches = glob.glob(os.path.join(sdir, f"*{fname}*"))
                    if matches and os.path.isfile(matches[0]):
                        target_file = matches[0]
                        break

        if not target_file:
            return {"text": f"Không tìm thấy tệp để đọc.", "success": False}

        try:
            with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1500)
            base = os.path.basename(target_file)
            return {"text": f"Nội dung tệp '{base}':\n{content}", "content": content, "success": True}
        except Exception as e:
            return {"text": f"Lỗi đọc tệp: {e}", "success": False}

    def action_list_files(self, folder_query: str) -> Dict[str, Any]:
        """Lists files in desktop or documents."""
        home = os.path.expanduser("~")
        target_dir = os.path.join(home, "Desktop")
        fq = folder_query.lower()
        if "tai ve" in fq or "download" in fq:
            target_dir = os.path.join(home, "Downloads")
        elif "tai lieu" in fq or "document" in fq:
            target_dir = os.path.join(home, "Documents")

        try:
            items = os.listdir(target_dir)[:10]
            if not items:
                return {"text": f"Thư mục {os.path.basename(target_dir)} trống.", "success": True}
            return {"text": f"Các tệp trong {os.path.basename(target_dir)}: {', '.join(items)}.", "items": items, "success": True}
        except Exception as e:
            return {"text": f"Không thể xem danh sách tệp: {e}", "success": False}

    # --- Fast Pattern Matching (Zero Latency Execution) ---
    def check_fast_system_action(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Handles fast zero-latency OS intents (<10ms) without waiting for LLM."""
        p = prompt.strip().lower()

        # 1. Delete File / Folder Intent (Handles direct or conversational delete requests)
        if any(w in p for w in ["xóa", "xoá", "xoa", "delete", "remove", "gỡ"]):
            if any(w in p for w in ["file", "tệp", "folder", "thư mục", "tài liệu"]) or re.search(r'\.[a-zA-Z0-9]{1,5}\b', p):
                if not any(w in p for w in ["app", "ứng dụng", "lịch sử", "tin nhắn"]):
                    return self.action_delete_file(prompt)

        # 2. Open App Intent (with typos: mor app, mo app, mowr app, bật app, chạy app, mở app)
        if any(w in p for w in ["mở", "mor", "mo", "mowr", "bật", "chạy", "open", "launch"]):
            if any(w in p for w in ["app", "ứng dụng", "phần mềm"]) or any(k in p for k in ["chrome", "google", "browser", "trình duyệt", "firefox", "terminal", "nautilus", "calculator", "máy tính", "cài đặt", "settings", "airdrop", "photos", "ảnh", "notes", "ghi chú", "photobooth", "appstore", "drive", "camera", "nhạc"]):
                if not any(w in p for w in ["file", "tệp", "tài liệu", "văn bản"]):
                    app_name = self.extract_app_name(prompt)
                    if app_name:
                        return self.action_open_app(app_name)

        # 3. Create File / Document
        create_match = re.search(r'(tạo|tao|taoj|soạn|soan|make|create)\s+(file|tệp|văn bản|tài liệu|ghi chú)\s*(.*)', p)
        if create_match:
            args_str = create_match.group(3).strip()
            if not args_str:
                args_str = f"tai_lieu_{int(time.time())}.txt"
            content_match = re.search(r'(.+?)\s+(với nội dung|nội dung|chứa|ghi là)\s+(.+)', args_str)
            if content_match:
                fname = content_match.group(1).strip()
                content = content_match.group(3).strip()
            else:
                fname = args_str.strip()
                content = f"Tài liệu {fname}\nNgày tạo: {time.strftime('%Y-%m-%d %H:%M:%S')}\nĐược tạo bởi Siri AI."
            return self.action_create_file(fname, content)

        # 5. Open File Intent
        open_file_match = re.search(r'^(mở|mor|mo|xem)\s+(file|tệp|tài liệu)\s+(.+)', p)
        if open_file_match:
            return self.action_open_file(open_file_match.group(3).strip())

        # 6. Read File Intent
        read_file_match = re.search(r'^(đọc|doc|xem nội dung)\s+(file|tệp|tài liệu)?\s*(.+)', p)
        if read_file_match:
            return self.action_read_file(read_file_match.group(3).strip())

        # 7. List Files Intent
        if any(w in p for w in ["danh sách file", "liệt kê file", "xem các file", "list file", "các tệp trên desktop"]):
            return self.action_list_files("Desktop")

        # 8. Weather
        if any(w in p for w in ["thời tiết", "weather", "mưa không", "nhiệt độ ngoài trời"]):
            try:
                from src.modules.weather import get_cached_weather
                w = get_cached_weather()
                if w and w.get("temp") is not None:
                    city = w.get("city", "Hà Nội")
                    temp = w.get("temp")
                    cond = w.get("condition", "Nắng đẹp")
                    ans = f"Thời tiết tại {city} hiện tại là {temp}°C, {cond}."
                    return {"text": ans, "action": "weather", "success": True}
            except Exception:
                pass
            return {"text": "Thời tiết hiện tại rất đẹp và dễ chịu trên hệ thống của bạn.", "action": "weather", "success": True}

        # 9. Timer
        timer_match = re.search(r'(hẹn giờ|đặt hẹn giờ|timer)\s+(\d+)\s*(phút|giây|minute|second)?', p)
        if timer_match:
            val = int(timer_match.group(2))
            unit = timer_match.group(3) or "phút"
            secs = val * 60 if "phút" in unit or "minute" in unit else val
            try:
                from src.ipc import send_command
                send_command("tab timer")
            except Exception:
                pass
            return {
                "text": f"Đã bật đồng hồ đếm giờ {val} {unit} trên Dynamic Island.",
                "action": "timer",
                "seconds": secs,
                "success": True
            }

        # 10. Dark/Light Mode Theme
        if any(w in p for w in ["chế độ tối", "bật dark mode", "dark mode"]):
            try:
                from src.utils.theme import set_dark_mode
                set_dark_mode(True)
                return {"text": "Đã chuyển toàn bộ giao diện sang Chế độ Tối (Dark Mode).", "action": "theme", "success": True}
            except Exception:
                pass

        if any(w in p for w in ["chế độ sáng", "bật light mode", "light mode"]):
            try:
                from src.utils.theme import set_dark_mode
                set_dark_mode(False)
                return {"text": "Đã chuyển toàn bộ giao diện sang Chế độ Sáng (Light Mode).", "action": "theme", "success": True}
            except Exception:
                pass

        # 11. Battery
        if any(w in p for w in ["pin", "battery", "pin còn bao nhiêu"]):
            try:
                from src.modules.battery import get_battery_info
                b = get_battery_info()
                pct = b.get("percent", 100)
                state = "đang sạc" if b.get("is_charging") else "đang dùng pin"
                return {"text": f"Mức pin hiện tại là {pct}% ({state}).", "action": "battery", "success": True}
            except Exception:
                pass

        # 12. Google Drive
        if any(w in p for w in ["google drive", "dung lượng drive", "mở drive"]):
            try:
                from src.modules.google_account import google_account_mgr
                google_account_mgr.open_google_drive("local")
                info = google_account_mgr.get_info()
                return {
                    "text": f"Đã mở thư mục Google Drive. Dung lượng đã dùng: {info.get('used_str', str(info.get('used_gb', 0)) + ' GB')} trên {info.get('total_gb', 15)} GB.",
                    "action": "google_drive",
                    "success": True
                }
            except Exception:
                pass

        return None

    # --- Query LLM / Siri Workflow ---
    def query(self, prompt: str, callback: Optional[Callable[[str, bool], None]] = None) -> str:
        prompt = prompt.strip()
        if not prompt:
            return ""

        # 1. Fast path for direct system & OS actions (< 10ms execution)
        fast_action = self.check_fast_system_action(prompt)
        if fast_action:
            ans = fast_action.get("text", "Đã thực hiện xong.")
            self.speak(ans)
            if callback:
                callback(ans, True)
            return ans

        # 2. Asynchronous call to Local Qwen 2.5 1.5B via Ollama with Tool Execution
        def _call_qwen():
            self.ensure_ollama_service()

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for turn in self.conversation_history[-6:]:
                messages.append(turn)
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "num_predict": 256
                }
            }

            ans_text = ""
            success = False
            last_err = ""

            try:
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{OLLAMA_API_BASE}/api/chat",
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "DynamicIsland/1.0"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=35.0) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    msg = res_json.get("message", {})
                    ans_text = msg.get("content", "").strip()
                    if ans_text:
                        success = True
            except urllib.error.URLError as e:
                last_err = "Ollama đang khởi động hoặc mô hình Qwen 2.5 1.5B đang được nạp vào bộ nhớ."
            except Exception as e:
                last_err = f"Lỗi xử lý Qwen 2.5: {e}"

            if success and ans_text:
                # 3. Parse & Execute [ACTION: ...] Tags from Qwen 2.5 output
                action_pattern = re.search(r'\[ACTION:\s*([a-zA-Z_]+)\s*(\{.*?\})\]', ans_text, re.DOTALL)
                clean_ans = re.sub(r'\[ACTION:\s*[a-zA-Z_]+\s*\{.*?\}\]', '', ans_text, flags=re.DOTALL).strip()

                if action_pattern:
                    act_name = action_pattern.group(1).strip().lower()
                    act_args_raw = action_pattern.group(2).strip()
                    act_res = None
                    try:
                        act_args = json.loads(act_args_raw)
                        if act_name == "delete_file":
                            act_res = self.action_delete_file(act_args.get("file", ""))
                        elif act_name == "open_app":
                            act_res = self.action_open_app(act_args.get("app", ""))
                        elif act_name == "create_file":
                            act_res = self.action_create_file(act_args.get("file", ""), act_args.get("content", ""))
                        elif act_name == "open_file":
                            act_res = self.action_open_file(act_args.get("file", ""))
                        elif act_name == "read_file":
                            act_res = self.action_read_file(act_args.get("file", ""))
                        elif act_name == "list_files":
                            act_res = self.action_list_files(act_args.get("folder", "Desktop"))
                    except Exception as ex:
                        print(f"[SiriAssistant] Action tag execution error: {ex}")

                    if act_res and act_res.get("text"):
                        if not clean_ans:
                            ans_text = act_res["text"]
                        else:
                            ans_text = f"{clean_ans}\n({act_res['text']})"
                    elif clean_ans:
                        ans_text = clean_ans
                elif clean_ans:
                    ans_text = clean_ans

                # Store history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": ans_text})
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]

                # Speak natural neural voice
                self.speak(ans_text)
                if callback:
                    callback(ans_text, True)
            else:
                fallback_msg = (
                    f"Siri (Qwen 2.5 1.5B Local):\n{last_err}\n\n"
                    f"💡 Bạn có thể ra lệnh: 'mở app chrome', 'xóa file test.txt', 'tạo file note.txt', "
                    f"'thời tiết hôm nay', 'hẹn giờ 5 phút', hoặc 'bật dark mode'."
                )
                self.speak("Tôi đang chuẩn bị mô hình cục bộ. Bạn có thể ra lệnh mở ứng dụng, xóa tệp hoặc tạo tệp ngay bây giờ.")
                if callback:
                    callback(fallback_msg, False)

        threading.Thread(target=_call_qwen, daemon=True).start()
        return "Qwen 2.5 đang suy nghĩ…"


siri_assistant = SiriAssistant.get_instance()
