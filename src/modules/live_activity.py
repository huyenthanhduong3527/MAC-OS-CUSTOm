"""
Live Activity Manager for Dynamic Island.
Tracks real-time download and transfer progress:
- Browser downloads in ~/Downloads (*.crdownload, *.part, *.download)
- AirDrop incoming/outgoing file transfers
Calculates transfer rate, elapsed/remaining progress, and notifies Dynamic Island
to display an Apple-style Live Activity progress ring capsule.
"""

import os
import glob
import time
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

class LiveActivityManager:
    _instance = None

    @classmethod
    def get_instance(cls, on_activity=None):
        if cls._instance is None:
            cls._instance = LiveActivityManager(on_activity=on_activity)
        elif on_activity:
            cls._instance.callbacks.append(on_activity)
        return cls._instance

    def __init__(self, on_activity=None):
        self.callbacks = [on_activity] if on_activity else []
        self.downloads_dir = os.path.expanduser("~/Downloads")
        self._running = True
        self._lock = threading.Lock()

        # Current live activity state
        self.active = False
        self.title = ""
        self.subtitle = ""
        self.progress = 0.0 # 0.0 to 1.0, or -1 for indeterminate
        self.activity_type = "download" # 'download' or 'airdrop'
        self.is_complete = False

        # File tracking for speed calculation
        self._last_tracked_file = None
        self._last_size = 0
        self._last_time = 0
        self._recent_completed_file = None
        self._complete_expire_time = 0

        # Start watcher thread (runs every 0.8s)
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def add_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def set_airdrop_progress(self, filename, progress, speed_str="", is_complete=False):
        """Update Live Activity directly from AirDropManager."""
        with self._lock:
            self.active = True
            self.activity_type = "airdrop"
            self.title = filename
            self.progress = progress
            self.is_complete = is_complete
            if is_complete:
                self.subtitle = "Đã nhận tệp thành công ✓"
                self._complete_expire_time = time.time() + 4.0
            else:
                pct = int(progress * 100)
                self.subtitle = f"{pct}%" + (f" • {speed_str}" if speed_str else "")

        GLib.idle_add(self._notify_callbacks)

    def _watch_loop(self):
        while self._running:
            try:
                self._check_downloads()
            except Exception as e:
                pass
            time.sleep(0.8)

    def _check_downloads(self):
        now = time.time()

        # Handle completion expiration
        with self._lock:
            if self.is_complete and now >= self._complete_expire_time:
                self.active = False
                self.is_complete = False
                self.title = ""
                self.subtitle = ""
                self.progress = 0.0
                GLib.idle_add(self._notify_callbacks)
                return

            if self.activity_type == "airdrop" and self.active:
                # Let AirDrop manage its own lifecycle
                return

        # Scan ~/Downloads for active temporary download files
        if not os.path.exists(self.downloads_dir):
            return

        patterns = [
            os.path.join(self.downloads_dir, "*.crdownload"),
            os.path.join(self.downloads_dir, "*.part"),
            os.path.join(self.downloads_dir, "*.download"),
        ]

        active_files = []
        for pat in patterns:
            active_files.extend(glob.glob(pat))

        if active_files:
            # Sort by most recently modified
            active_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            target = active_files[0]

            try:
                size = os.path.getsize(target)
            except OSError:
                size = 0

            # Calculate speed
            speed_str = ""
            if self._last_tracked_file == target and self._last_time > 0:
                dt = now - self._last_time
                if dt > 0.3:
                    bytes_per_sec = max(0, (size - self._last_size) / dt)
                    speed_str = self._format_speed(bytes_per_sec)

            self._last_tracked_file = target
            self._last_size = size
            self._last_time = now

            # Clean filename
            base_name = os.path.basename(target)
            for ext in (".crdownload", ".part", ".download"):
                if base_name.endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break

            size_str = self._format_size(size)
            subtitle = f"{size_str} • {speed_str}" if speed_str else size_str

            with self._lock:
                self.active = True
                self.activity_type = "download"
                self.title = base_name
                self.subtitle = subtitle
                self.progress = -1.0 # Indeterminate dynamic spinner
                self.is_complete = False

            GLib.idle_add(self._notify_callbacks)

        else:
            # No active downloads in progress
            with self._lock:
                if self._last_tracked_file and self.active and not self.is_complete:
                    # Download just finished!
                    base_name = os.path.basename(self._last_tracked_file)
                    for ext in (".crdownload", ".part", ".download"):
                        if base_name.endswith(ext):
                            base_name = base_name[:-len(ext)]
                            break

                    self.active = True
                    self.is_complete = True
                    self.title = base_name
                    self.subtitle = "Tải hoàn tất ✓"
                    self.progress = 1.0
                    self._complete_expire_time = now + 3.5
                    self._last_tracked_file = None
                    GLib.idle_add(self._notify_callbacks)
                elif not self.is_complete and self.active:
                    self.active = False
                    self.title = ""
                    self.subtitle = ""
                    self.progress = 0.0
                    self._last_tracked_file = None
                    GLib.idle_add(self._notify_callbacks)

    def _format_size(self, b):
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        elif b < 1024 * 1024 * 1024:
            return f"{b / (1024*1024):.1f} MB"
        else:
            return f"{b / (1024*1024*1024):.2f} GB"

    def _format_speed(self, bps):
        if bps < 1024:
            return f"{bps:.0f} B/s"
        elif bps < 1024 * 1024:
            return f"{bps / 1024:.1f} KB/s"
        else:
            return f"{bps / (1024*1024):.1f} MB/s"

    def _notify_callbacks(self):
        with self._lock:
            data = {
                "active": self.active,
                "title": self.title,
                "subtitle": self.subtitle,
                "progress": self.progress,
                "type": self.activity_type,
                "is_complete": self.is_complete
            }
        for cb in self.callbacks:
            try:
                cb(data)
            except Exception as e:
                print(f"[LiveActivity] Callback error: {e}")
        return False

    def stop(self):
        self._running = False
