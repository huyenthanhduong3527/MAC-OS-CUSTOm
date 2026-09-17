"""
Desktop Notification Monitor & Manager for Dynamic Island.
Listens to both org.freedesktop.Notifications and org.gtk.Notifications via D-Bus.
Suppresses native GNOME popup banners so all notifications exclusively appear in Dynamic Island.
Provides unread notification tracking for the Apple-style Glowing Red Dot indicator.
"""

import os
import subprocess
import threading
import time
import re
import urllib.parse
from collections import deque
from gi.repository import Gio, GLib

class NotificationManager:
    """Stores notification history and tracks unread status for the Red Dot indicator."""
    def __init__(self, max_history=40):
        self.history = deque(maxlen=max_history)
        self.unread_count = 0
        self._listeners = []

    def add_notification(self, app_name, title, body, image_path=None):
        item = {
            "id": int(time.time() * 1000),
            "app": app_name or "Notification",
            "title": title or "Alert",
            "body": body or "",
            "image_path": image_path,
            "time_str": time.strftime("%H:%M"),
            "timestamp": time.time(),
            "unread": True
        }
        self.history.appendleft(item)
        self.unread_count += 1
        self._notify_listeners()
        return item

    def mark_all_read(self):
        if self.unread_count > 0:
            self.unread_count = 0
            for item in self.history:
                item["unread"] = False
            self._notify_listeners()

    def clear_all(self):
        self.history.clear()
        self.unread_count = 0
        self._notify_listeners()

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for cb in self._listeners:
            try:
                cb(self.unread_count)
            except Exception as e:
                print(f"[NotifManager] Listener error: {e}")


class NotificationListener:
    """Monitors D-Bus for desktop notifications and ensures exclusive display in Dynamic Island."""
    def __init__(self, on_notification=None, on_volume_change=None):
        self.on_notification = on_notification
        self.on_volume_change = on_volume_change
        self._running = True
        self._process = None

        # Deduplication cache (avoid double events from forwarded D-Bus calls)
        self._last_dedup_key = None
        self._last_dedup_time = 0

        # Enforce GNOME Shell to suppress external banner popups
        self._suppress_external_banners()

        # Inotify / Gio watcher for Screenshots directory
        self._init_screenshot_watcher()

        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _init_screenshot_watcher(self):
        """Watch ~/Pictures/Screenshots and ~/Pictures for newly saved screenshots."""
        self._last_shot_path = None
        self._last_shot_time = 0
        self._last_dispatched_shot_path = None
        self._shot_pending_timer = None
        self._shot_monitors = []

        shot_dirs = [
            os.path.expanduser("~/Pictures/Screenshots"),
            os.path.expanduser("~/Pictures")
        ]

        for d in shot_dirs:
            if os.path.exists(d):
                try:
                    gfile = Gio.File.new_for_path(d)
                    monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
                    monitor.connect("changed", self._on_dir_changed)
                    self._shot_monitors.append(monitor)
                except Exception as e:
                    print(f"[Notification] Error watching {d}: {e}")

    def _on_dir_changed(self, mon, file1, file2, event_type):
        if event_type in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED):
            path = file1.get_path()
            if not path or not path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                return

            basename = os.path.basename(path).lower()
            parent_dir = os.path.basename(os.path.dirname(path)).lower()
            is_screenshot = ("screenshots" in parent_dir or
                             "screenshot" in basename or
                             "screen" in basename or
                             "capture" in basename or
                             "chup" in basename)
            if not is_screenshot:
                return

            now = time.time()
            # If this exact path was already dispatched within 3 seconds, skip
            if path == self._last_dispatched_shot_path and (now - self._last_shot_time) < 3.0:
                return

            # Cancel any existing pending timer for this path and reschedule
            if self._shot_pending_timer:
                GLib.source_remove(self._shot_pending_timer)
                self._shot_pending_timer = None

            def _dispatch_shot():
                self._shot_pending_timer = None
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    self._last_dispatched_shot_path = path
                    self._last_shot_time = time.time()
                    print(f"[Notification] Screenshot file ready: {path}")
                    self._dispatch("Screen Capture", "Screenshot Captured", "Saved to Pictures & Clipboard", image_path=path)

            self._shot_pending_timer = GLib.timeout_add(250, _dispatch_shot)

    def _suppress_external_banners(self):
        """Disable native GNOME notification banners so notifications only route through Dynamic Island."""
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", "false"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Also disable for all application children so per-app overrides don't bypass global setting
            out = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.notifications", "application-children"],
                text=True
            ).strip()
            import ast
            apps = ast.literal_eval(out) if out.startswith("[") else []
            apps.extend(["org-gnome-shell", "org-gnome-shell-screenshot", "screenshot"])
            for app in apps:
                path = f"org.gnome.desktop.notifications.application:/org/gnome/desktop/notifications/application/{app}/"
                subprocess.run(["gsettings", "set", path, "show-banners", "false"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Notification] Warning: Could not disable GNOME banners: {e}")

    def _monitor_loop(self):
        """Monitors D-Bus for freedesktop notifications, portal signals, and GNOME Shell ShowOSD volume keys."""
        cmd = [
            "dbus-monitor",
            "--session",
            "type='method_call',interface='org.freedesktop.Notifications',member='Notify',eavesdrop='true'",
            "type='method_call',interface='org.gtk.Notifications',member='AddNotification',eavesdrop='true'",
            "type='signal',interface='org.freedesktop.portal.Request',member='Response',eavesdrop='true'",
            "type='method_call',interface='org.gnome.Shell',member='ShowOSD',eavesdrop='true'"
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
        except Exception as e:
            print(f"[Notification] Error launching dbus-monitor: {e}")
            return

        mode = None # 'freedesktop', 'gtk', or 'portal_response'
        f_strings = []
        g_app = ""
        g_title = ""
        g_body = ""
        last_key = None
        resp_code = None
        resp_uri = None

        while self._running and self._process.poll() is None:
            line = self._process.stdout.readline()
            if not line:
                break

            line_str = line.strip()

            if "member=Notify" in line_str:
                mode = "freedesktop"
                f_strings = []
                continue
            elif "member=AddNotification" in line_str:
                mode = "gtk"
                g_app = ""
                g_title = ""
                g_body = ""
                last_key = None
                continue
            elif "member=Response" in line_str and "/request/" in line_str:
                mode = "portal_response"
                resp_code = None
                resp_uri = None
                continue
            elif "member=ShowOSD" in line_str:
                mode = "osd"
                osd_icon = ""
                osd_level = None
                continue
            elif line_str.startswith("method call ") or line_str.startswith("signal "):
                if mode == "gtk" and (g_title or g_body):
                    self._dispatch(g_app or "System", g_title or "Notice", g_body)
                mode = None
                continue

            if mode == "freedesktop":
                m = re.search(r'string\s+"(.*)"', line_str)
                if m:
                    f_strings.append(m.group(1))
                    if len(f_strings) >= 4:
                        app_name = f_strings[0] or "Notification"
                        title = f_strings[2]
                        body = f_strings[3]
                        self._dispatch(app_name, title, body)
                        mode = None

            elif mode == "gtk":
                m = re.search(r'string\s+"(.*)"', line_str)
                if m:
                    val = m.group(1)
                    if not g_app:
                        g_app = val
                    elif val in ("title", "body"):
                        last_key = val
                    elif last_key == "title":
                        g_title = val
                        last_key = None
                    elif last_key == "body":
                        g_body = val
                        last_key = None

                    if g_title and g_body:
                        self._dispatch(g_app or "Screen Capture", g_title, g_body)
                        mode = None

            elif mode == "portal_response":
                if line_str.startswith("uint32"):
                    parts = line_str.split()
                    if len(parts) > 1 and parts[1].isdigit():
                        resp_code = int(parts[1])
                elif "string \"file://" in line_str:
                    m = re.search(r'string\s+"(.*)"', line_str)
                    if m:
                        resp_uri = m.group(1)

                if resp_code == 0 and resp_uri:
                    shot_path = urllib.parse.unquote(resp_uri.replace("file://", ""))
                    self._dispatch("Screen Capture", "Screenshot Captured", "Saved to Pictures & Clipboard", image_path=shot_path)
                    mode = None

            elif mode == "osd":
                if "variant" in line_str and "string" in line_str:
                    m = re.search(r'string\s+"(.*)"', line_str)
                    if m:
                        osd_icon = m.group(1)
                elif "variant" in line_str and "double" in line_str:
                    parts = line_str.split()
                    try:
                        osd_level = float(parts[-1])
                    except ValueError:
                        pass

                if osd_level is not None and osd_icon:
                    if "volume" in osd_icon.lower() or "audio" in osd_icon.lower():
                        is_muted = ("muted" in osd_icon.lower()) or (osd_level <= 0.001)
                        if self.on_volume_change:
                            GLib.idle_add(self.on_volume_change, osd_level, is_muted)
                    mode = None

    def _dispatch(self, app_name, summary, body, image_path=None):
        # Format / clean up app name
        clean_app = app_name.strip() if app_name else "Notification"
        if "gnome.shell" in clean_app.lower() or "screencapture" in clean_app.lower():
            clean_app = "Screen Capture"
        elif "." in clean_app:
            clean_app = clean_app.split(".")[-1].capitalize()
        elif clean_app.lower() == "notify-send":
            clean_app = "Notification"

        summary = summary.strip() if summary else "Alert"
        body = body.strip()

        # Deduplication check within 1.5 seconds
        now = time.time()
        dedup_key = (clean_app.lower(), summary.lower(), body.lower())
        if dedup_key == self._last_dedup_key and (now - self._last_dedup_time) < 1.5:
            return

        self._last_dedup_key = dedup_key
        self._last_dedup_time = now

        if self.on_notification:
            GLib.idle_add(self.on_notification, clean_app, summary, body, image_path)

    def stop(self):
        self._running = False
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
