"""
macOS Photos Library & Scanning Engine for Ubuntu Linux.
High-performance background image discovery, EXIF extraction,
smooth caching, and desktop integration.
"""

import os
import sys
import time
import json
import hashlib
import threading
import queue
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Callable, Set

try:
    from PIL import Image, ExifTags
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GLib, Gio, GdkPixbuf

import re

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".bmp", ".tiff", ".tif", ".heic", ".heif",
    ".raw", ".cr2", ".nef", ".arw", ".dng"
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi",
    ".m4v", ".flv", ".wmv", ".3gp", ".mts"
}

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

IGNORED_DIR_NAMES = {
    ".git", ".cache", ".local", ".var", ".venv", "venv", "env",
    "node_modules", "__pycache__", ".cargo", ".rustup", ".npm",
    ".vscode", ".gemini", ".idea", "site-packages", ".mozilla",
    ".thunderbird", ".steam", "Trash", ".Trash", "lost+found",
    "resources", "extensions", "out", "dist", "build", "target",
    "vendor", "bin", "lib", "lib64", "include", "share", "locale",
    "locales", "theme-symbols", "theme-defaults", "fileicons",
    "plugins", "packages", "assets", "static", "tmp", ".system_generated"
}

APP_MARKER_FILES = (
    "package.json", "Cargo.toml", "go.mod", "pom.xml",
    "requirements.txt", "CMakeLists.txt", "Makefile", "app.asar",
    "install.sh", ".gitignore"
)


def is_app_or_system_directory(parent_dir: str, dir_name: str) -> bool:
    """Return True if the directory is an app package, dependency, or source code repo."""
    d_lower = dir_name.lower()
    if dir_name.startswith(".") or d_lower in IGNORED_DIR_NAMES:
        return True

    # App bundle keywords
    if any(kw in d_lower for kw in ("antigravity", "vscode", "electron", "node_modules", "ulauncher")):
        return True

    if d_lower.endswith((".app", ".appimage", ".asar")):
        return True

    # Check if folder contains code repository or app markers
    full_d = os.path.join(parent_dir, dir_name)
    try:
        if os.path.isdir(os.path.join(full_d, ".git")):
            return True
        for marker in APP_MARKER_FILES:
            if os.path.exists(os.path.join(full_d, marker)):
                return True
    except (PermissionError, OSError):
        return True

    return False


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human readable string (e.g. 2.4 MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_date_group_label(dt: datetime) -> str:
    """Group photos by user-friendly time period."""
    now = datetime.now()
    diff_days = (now.date() - dt.date()).days
    if diff_days == 0:
        return "Hôm nay"
    elif diff_days == 1:
        return "Hôm qua"
    elif 2 <= diff_days <= 7:
        return "Tuần này"
    elif dt.year == now.year and dt.month == now.month:
        return "Tháng này"
    elif dt.year == now.year:
        return dt.strftime("Tháng %m, %Y")
    else:
        return dt.strftime("%Y")


class PhotoItem:
    """Represents a discovered photo or video with lazy-evaluated metadata."""
    __slots__ = (
        'path', 'filename', 'folder', 'folder_name', 'size_bytes',
        'mtime', 'date_obj', 'date_str', 'date_group', 'ext',
        'format_name', 'is_favorite', 'is_screenshot', 'is_video',
        'duration_sec', 'duration_str', 'video_codec', 'audio_codec',
        'width', 'height', 'exif_data', '_thumb_path'
    )

    def __init__(self, path: str, size: int, mtime: float, is_favorite: bool = False):
        self.path = path
        self.filename = os.path.basename(path)
        self.folder = os.path.dirname(path)
        self.folder_name = os.path.basename(self.folder) or self.folder
        self.size_bytes = size
        self.mtime = mtime
        self.date_obj = datetime.fromtimestamp(mtime)
        self.date_str = self.date_obj.strftime("%d/%m/%Y %H:%M")
        self.date_group = get_date_group_label(self.date_obj)

        _, ext = os.path.splitext(self.filename)
        self.ext = ext.lower()
        self.format_name = self._detect_format_name(self.ext)
        self.is_favorite = is_favorite
        self.is_screenshot = (
            "screenshot" in self.filename.lower() or
            "screenshot" in self.folder.lower() or
            "ảnh chụp màn hình" in self.folder.lower()
        )
        self.is_video = self.ext in VIDEO_EXTENSIONS
        self.duration_sec = 0.0
        self.duration_str = ""
        self.video_codec = ""
        self.audio_codec = ""
        self.width = 0
        self.height = 0
        self.exif_data = None
        self._thumb_path = None

    def _detect_format_name(self, ext: str) -> str:
        mapping = {
            ".jpg": "JPEG", ".jpeg": "JPEG",
            ".png": "PNG", ".webp": "WEBP",
            ".gif": "GIF", ".bmp": "BMP",
            ".tiff": "TIFF", ".tif": "TIFF",
            ".heic": "HEIC", ".heif": "HEIF",
            ".raw": "RAW", ".dng": "RAW",
            ".mp4": "MP4", ".mov": "MOV",
            ".mkv": "MKV", ".webm": "WEBM",
            ".avi": "AVI", ".m4v": "M4V",
            ".flv": "FLV", ".wmv": "WMV",
            ".3gp": "3GP", ".mts": "MTS"
        }
        return mapping.get(ext, ext.replace(".", "").upper())

    @property
    def formatted_size(self) -> str:
        return format_file_size(self.size_bytes)

    @property
    def dimensions_str(self) -> str:
        if self.width > 0 and self.height > 0:
            mp = (self.width * self.height) / 1_000_000
            if mp >= 1.0:
                return f"{self.width} × {self.height} ({mp:.1f} MP)"
            return f"{self.width} × {self.height}"
        return "Đang tải..."

    def load_dimensions_and_exif(self):
        """Extract width, height, and EXIF/codec metadata using PIL, GdkPixbuf or GStreamer."""
        if self.width > 0 and self.height > 0 and self.exif_data is not None:
            return

        if self.is_video:
            try:
                res = subprocess.run(["gst-discoverer-1.0", self.path], capture_output=True, text=True, timeout=2)
                out = res.stdout
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out)
                if m:
                    h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                    self.duration_sec = h * 3600 + mn * 60 + s
                    if h > 0:
                        self.duration_str = f"{h:02d}:{mn:02d}:{int(s):02d}"
                    else:
                        self.duration_str = f"{mn:02d}:{int(s):02d}"
                m_w = re.search(r"Width:\s*(\d+)", out)
                m_h = re.search(r"Height:\s*(\d+)", out)
                if m_w and m_h:
                    self.width = int(m_w.group(1))
                    self.height = int(m_h.group(2))
                m_vc = re.search(r"video\s*#\d+:\s*([^\n]+)", out)
                if m_vc:
                    self.video_codec = m_vc.group(1).strip()
                m_ac = re.search(r"audio\s*#\d+:\s*([^\n]+)", out)
                if m_ac:
                    self.audio_codec = m_ac.group(1).strip()
                self.exif_data = {
                    "Thời lượng": self.duration_str or "—",
                    "Codec Video": self.video_codec or "—",
                    "Codec Audio": self.audio_codec or "—",
                    "Độ phân giải": f"{self.width} × {self.height}" if self.width else "—"
                }
            except Exception:
                self.exif_data = {}
            return

        if HAS_PIL and self.ext != ".svg":
            try:
                with Image.open(self.path) as img:
                    self.width, self.height = img.size
                    raw_exif = img.getexif()
                    if raw_exif:
                        exif = {}
                        for tag_id, val in raw_exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if isinstance(val, (bytes, bytearray)):
                                continue
                            exif[tag_name] = str(val).strip()
                        self.exif_data = exif
                    else:
                        self.exif_data = {}
                    return
            except Exception:
                pass

        # Fallback to GdkPixbuf
        try:
            info = GdkPixbuf.Pixbuf.get_file_info(self.path)
            if info and info[0]:
                self.width = info[1]
                self.height = info[2]
            self.exif_data = {}
        except Exception:
            self.width = 0
            self.height = 0
            self.exif_data = {}


class PhotoLibraryManager:
    """
    Manages photo discovery, thumbnail caching, configuration,
    and system desktop actions (Wallpaper, Trash, Reveal).
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = PhotoLibraryManager()
        return cls._instance

    def __init__(self):
        self.home_dir = os.path.expanduser("~")
        self.config_dir = os.path.join(self.home_dir, ".config", "macos-photos")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.cache_dir = os.path.join(self.home_dir, ".cache", "macos-photos", "thumbnails")

        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        self.photos: List[PhotoItem] = []
        self.photos_by_path: Dict[str, PhotoItem] = {}
        self.favorites: Set[str] = set()
        self.custom_folders: List[str] = []
        self.trash_paths: List[Dict] = []
        self.zoom_size: int = 170  # default thumbnail size (px)

        self._is_scanning = False
        self._scan_thread = None
        self._scan_lock = threading.Lock()
        self._rescan_requested = False
        self._directory_monitors: Dict[str, Gio.FileMonitor] = {}
        self._monitor_refresh_source = None
        self._thumb_queue = queue.Queue()
        self._thumb_workers = []
        self._stop_thumb_workers = False

        self._subscribers: List[Callable] = []

        self._load_config()
        self._start_thumb_workers(num_workers=3)

    def _load_config(self):
        """Loads user preferences, favorites, and custom folders."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = set(data.get("favorites", []))
                    self.custom_folders = data.get("custom_folders", [])
                    self.zoom_size = data.get("zoom_size", 170)
                    self.trash_paths = data.get("trash_history", [])
            except Exception as e:
                print(f"[PhotosEngine] Error reading config: {e}")

    def save_config(self):
        """Saves current state to config.json."""
        try:
            data = {
                "favorites": list(self.favorites),
                "custom_folders": self.custom_folders,
                "zoom_size": self.zoom_size,
                "trash_history": self.trash_paths[-50:],
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[PhotosEngine] Error saving config: {e}")

    def add_custom_folder(self, folder_path: str):
        """Adds a custom directory to watch and scans it."""
        abs_path = os.path.abspath(folder_path)
        if os.path.isdir(abs_path) and abs_path not in self.custom_folders:
            self.custom_folders.append(abs_path)
            self.save_config()
            self.start_scan(force=True)

    def remove_custom_folder(self, folder_path: str):
        """Removes a custom directory."""
        if folder_path in self.custom_folders:
            self.custom_folders.remove(folder_path)
            self.save_config()
            self.start_scan(force=True)

    def toggle_favorite(self, path: str) -> bool:
        """Toggle favorite state for a photo."""
        item = self.photos_by_path.get(path)
        if path in self.favorites:
            self.favorites.remove(path)
            if item:
                item.is_favorite = False
            is_fav = False
        else:
            self.favorites.add(path)
            if item:
                item.is_favorite = True
            is_fav = True
        self.save_config()
        self._notify_subscribers("favorite_changed", path, is_fav)
        return is_fav

    def is_favorite(self, path: str) -> bool:
        return path in self.favorites

    def subscribe(self, callback: Callable):
        """Register UI notification callback."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, event_type: str, *args):
        for cb in list(self._subscribers):
            try:
                GLib.idle_add(cb, event_type, *args)
            except Exception as e:
                print(f"[PhotosEngine] Subscriber error: {e}")

    # -------------------------------------------------------------------------
    # SCANNING ENGINE
    # -------------------------------------------------------------------------
    def get_default_scan_roots(self) -> List[str]:
        """Returns standard user directories to scan for images."""
        roots = []
        candidates = [
            os.path.join(self.home_dir, "Pictures"),
            os.path.join(self.home_dir, "Downloads"),
            os.path.join(self.home_dir, "Desktop"),
            os.path.join(self.home_dir, "Documents"),
            os.path.join(self.home_dir, "Photos"),
            os.path.join(self.home_dir, "Wallpapers"),
        ]
        for p in candidates:
            if os.path.exists(p) and os.path.isdir(p):
                roots.append(p)

        for cf in self.custom_folders:
            if os.path.exists(cf) and os.path.isdir(cf) and cf not in roots:
                roots.append(cf)

        return roots

    def start_scan(self, force: bool = False, on_progress: Optional[Callable] = None, on_finished: Optional[Callable] = None):
        """Start asynchronous background scanning."""
        with self._scan_lock:
            if self._is_scanning:
                # A forced refresh while scanning must run afterwards, not in
                # parallel with a scan that is still publishing its results.
                if force:
                    self._rescan_requested = True
                return
            self._is_scanning = True
        self._notify_subscribers("scan_started")

        def _worker():
            roots = self.get_default_scan_roots()
            discovered: List[PhotoItem] = []
            seen_paths = set()
            scanned_dirs = set(roots)

            batch_size = 30
            current_batch = []

            for root in roots:
                for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
                    # Prune hidden, app, or system directories in-place
                    dirnames[:] = [
                        d for d in dirnames
                        if not is_app_or_system_directory(dirpath, d)
                    ]
                    scanned_dirs.add(dirpath)

                    for fname in filenames:
                        if fname.startswith("."):
                            continue
                        _, ext = os.path.splitext(fname)
                        ext_lower = ext.lower()
                        if ext_lower in SUPPORTED_EXTENSIONS:
                            full_path = os.path.join(dirpath, fname)
                            if full_path in seen_paths:
                                continue
                            seen_paths.add(full_path)

                            try:
                                stat = os.stat(full_path)
                                # Filter out tiny image assets (< 2.5KB) that are placeholder icons
                                if stat.st_size < 2500 and ext_lower in IMAGE_EXTENSIONS:
                                    continue

                                is_fav = full_path in self.favorites
                                item = PhotoItem(
                                    path=full_path,
                                    size=stat.st_size,
                                    mtime=stat.st_mtime,
                                    is_favorite=is_fav
                                )
                                discovered.append(item)
                                current_batch.append(item)

                                if len(current_batch) >= batch_size:
                                    batch_copy = list(current_batch)
                                    current_batch.clear()
                                    GLib.idle_add(self._on_batch_discovered, batch_copy, on_progress)
                            except Exception:
                                continue

            if current_batch:
                batch_copy = list(current_batch)
                current_batch.clear()
                GLib.idle_add(self._on_batch_discovered, batch_copy, on_progress)

            # Sort all photos by modified time (newest first)
            discovered.sort(key=lambda x: x.mtime, reverse=True)
            self.photos = discovered
            self.photos_by_path = {p.path: p for p in discovered}

            GLib.idle_add(self._on_scan_completed, on_finished, scanned_dirs)

        self._scan_thread = threading.Thread(target=_worker, daemon=True)
        self._scan_thread.start()

    def _on_batch_discovered(self, batch: List[PhotoItem], progress_cb: Optional[Callable]):
        for item in batch:
            self.photos_by_path[item.path] = item
            if item not in self.photos:
                self.photos.append(item)
        if progress_cb:
            progress_cb(len(self.photos), batch)
        self._notify_subscribers("photos_batch_added", batch)

    def _on_scan_completed(self, finished_cb: Optional[Callable], scanned_dirs: Set[str]):
        # Re-sort complete list
        self.photos.sort(key=lambda x: x.mtime, reverse=True)
        self._sync_directory_monitors(scanned_dirs)
        if finished_cb:
            finished_cb(len(self.photos))
        self._notify_subscribers("scan_finished", len(self.photos))

        with self._scan_lock:
            self._is_scanning = False
            rescan_requested = self._rescan_requested
            self._rescan_requested = False
        if rescan_requested:
            self.start_scan()
        return False

    def _sync_directory_monitors(self, scanned_dirs: Set[str]):
        """Keep a recursive set of Gio directory monitors in sync with a scan."""
        wanted = {path for path in scanned_dirs if os.path.isdir(path)}

        for path in set(self._directory_monitors) - wanted:
            try:
                self._directory_monitors[path].cancel()
            except Exception:
                pass
            del self._directory_monitors[path]

        for path in wanted - set(self._directory_monitors):
            try:
                monitor = Gio.File.new_for_path(path).monitor_directory(
                    Gio.FileMonitorFlags.WATCH_MOVES,
                    None,
                )
                monitor.connect("changed", self._on_directory_changed)
                self._directory_monitors[path] = monitor
            except Exception as e:
                print(f"[PhotosEngine] Cannot watch '{path}': {e}")

    def _on_directory_changed(self, _monitor, file_obj, other_file, event_type):
        """Debounce filesystem changes before refreshing the library."""
        changed_paths = []
        if file_obj is not None:
            changed_paths.append(file_obj.get_path())
        if other_file is not None:
            changed_paths.append(other_file.get_path())

        # Ignore thumbnail/config churn and refresh only for media or directory
        # events. Directory events matter because a new folder needs a monitor.
        removal_events = {
            Gio.FileMonitorEvent.DELETED,
            Gio.FileMonitorEvent.MOVED_OUT,
        }
        relevant = not changed_paths or event_type in removal_events
        for path in changed_paths:
            if not path:
                relevant = True
                break
            if os.path.isdir(path) or os.path.splitext(path)[1].lower() in SUPPORTED_EXTENSIONS:
                relevant = True
                break
        if not relevant:
            return

        if self._monitor_refresh_source is not None:
            GLib.source_remove(self._monitor_refresh_source)
        self._monitor_refresh_source = GLib.timeout_add(450, self._refresh_after_file_change)

    def _refresh_after_file_change(self):
        self._monitor_refresh_source = None
        self.start_scan(force=True)
        return False

    # -------------------------------------------------------------------------
    # THUMBNAIL CACHE & WORKERS
    # -------------------------------------------------------------------------
    def _start_thumb_workers(self, num_workers: int = 3):
        for _ in range(num_workers):
            t = threading.Thread(target=self._thumb_worker_loop, daemon=True)
            t.start()
            self._thumb_workers.append(t)

    def _thumb_worker_loop(self):
        while not self._stop_thumb_workers:
            try:
                task = self._thumb_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            photo_item, target_size, callback = task
            try:
                thumb_path = self.get_or_create_thumbnail_file(photo_item, target_size)
                if callback:
                    GLib.idle_add(callback, photo_item, thumb_path)
            except Exception as e:
                pass
            finally:
                self._thumb_queue.task_done()

    def request_thumbnail(self, photo_item: PhotoItem, size: int, callback: Callable):
        """Enqueue request to generate thumbnail asynchronously."""
        # Fast path: check if cache already exists
        cached = self.get_cached_thumb_path(photo_item, size)
        if cached and os.path.exists(cached):
            GLib.idle_add(callback, photo_item, cached)
            return

        self._thumb_queue.put((photo_item, size, callback))

    def get_cached_thumb_path(self, photo_item: PhotoItem, size: int) -> str:
        """Returns deterministic path for the cached thumbnail."""
        key = f"{photo_item.path}:{photo_item.mtime}:{photo_item.size_bytes}:{size}"
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.jpg")

    def get_or_create_thumbnail_file(self, photo_item: PhotoItem, size: int) -> str:
        """Synchronously generates thumbnail file and returns its path."""
        thumb_path = self.get_cached_thumb_path(photo_item, size)
        if os.path.exists(thumb_path):
            return thumb_path

        # If it's a video file, use gst-video-thumbnailer
        if photo_item.is_video:
            try:
                res = subprocess.run([
                    "gst-video-thumbnailer",
                    "-p", photo_item.path,
                    "-o", thumb_path,
                    "-s", str(size)
                ], capture_output=True, timeout=5)
                if res.returncode == 0 and os.path.exists(thumb_path):
                    if not photo_item.duration_str:
                        photo_item.load_dimensions_and_exif()
                    return thumb_path
            except Exception as e:
                print(f"[Thumbnailer] Video thumb error: {e}")

        # If it's SVG, render directly with GdkPixbuf
        if photo_item.ext == ".svg":
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(photo_item.path, size, size, True)
                pb.savev(thumb_path, "jpeg", ["quality"], ["85"])
                photo_item.width = pb.get_width()
                photo_item.height = pb.get_height()
                return thumb_path
            except Exception:
                return photo_item.path

        # High-performance PIL thumbnail generation
        if HAS_PIL:
            try:
                with Image.open(photo_item.path) as img:
                    photo_item.width, photo_item.height = img.size
                    img.thumbnail((size, size), Image.Resampling.LANCZOS)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(thumb_path, "JPEG", quality=85, optimize=True)
                    return thumb_path
            except Exception:
                pass

        # Fallback using GdkPixbuf
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(photo_item.path, size, size, True)
            pb.savev(thumb_path, "jpeg", ["quality"], ["85"])
            photo_item.width = pb.get_width()
            photo_item.height = pb.get_height()
            return thumb_path
        except Exception:
            return photo_item.path

    # -------------------------------------------------------------------------
    # SYSTEM ACTIONS (WALLPAPER, TRASH, REVEAL, ROTATE)
    # -------------------------------------------------------------------------
    def set_as_desktop_wallpaper(self, photo_path: str) -> bool:
        """Set this image as Ubuntu GNOME desktop wallpaper."""
        if not os.path.exists(photo_path):
            return False
        uri = f"file://{os.path.abspath(photo_path)}"
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                check=True, timeout=2
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri],
                check=True, timeout=2
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-options", "zoom"],
                check=True, timeout=2
            )
            return True
        except Exception as e:
            print(f"[PhotosEngine] Error setting wallpaper: {e}")
            return False

    def move_to_trash(self, photo_path: str) -> bool:
        """Move photo to system Trash safely."""
        if not os.path.exists(photo_path):
            return False

        success = False
        try:
            # Use standard gio trash
            res = subprocess.run(["gio", "trash", photo_path], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

        if success:
            item = self.photos_by_path.pop(photo_path, None)
            if item and item in self.photos:
                self.photos.remove(item)
            self.favorites.discard(photo_path)
            self.trash_paths.append({
                "path": photo_path,
                "deleted_at": time.time(),
                "filename": os.path.basename(photo_path)
            })
            self.save_config()
            self._notify_subscribers("photo_deleted", photo_path)
            return True
        return False

    def rotate_photo(self, photo_path: str, angle: int = 90) -> bool:
        """Rotates image 90 degrees clockwise and updates cache."""
        if not HAS_PIL or not os.path.exists(photo_path):
            return False

        try:
            with Image.open(photo_path) as img:
                # PIL rotate counter-clockwise by default; angle=90 cw is 270 or -90
                rot = img.rotate(-angle, expand=True)
                fmt = img.format or "JPEG"
                rot.save(photo_path, format=fmt, quality=95)

            # Invalidate cached thumbnails
            item = self.photos_by_path.get(photo_path)
            if item:
                stat = os.stat(photo_path)
                item.mtime = stat.st_mtime
                item.size_bytes = stat.st_size
                item.width, item.height = rot.size

            self._notify_subscribers("photo_rotated", photo_path)
            return True
        except Exception as e:
            print(f"[PhotosEngine] Error rotating image: {e}")
            return False

    def reveal_in_file_manager(self, photo_path: str):
        """Reveal file in Nautilus or open parent folder."""
        if not os.path.exists(photo_path):
            return
        try:
            subprocess.Popen(["nautilus", "--select", photo_path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try:
                subprocess.Popen(["xdg-open", os.path.dirname(photo_path)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def open_with_default_viewer(self, photo_path: str):
        """Open with user's default system image viewer."""
        if not os.path.exists(photo_path):
            return
        try:
            subprocess.Popen(["xdg-open", photo_path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
