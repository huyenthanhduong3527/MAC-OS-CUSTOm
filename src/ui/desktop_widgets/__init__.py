"""
Desktop Widgets Package for Dynamic Island & macOS on Ubuntu.
Provides beautiful, draggable Apple macOS widgets for the Linux desktop:
- DesktopCalendarWidget (Apple Calendar & Vietnamese Lunar Date)
- DesktopWeatherWidget (Apple Weather with precipitation & wind)
- DesktopBatteryWidget (Apple 4-Ring Battery Gauge)
- DesktopClockWidget (macOS Analog Clock)
- DesktopMusicWidget (Apple Music Player)
- DesktopPhotoWidget (macOS Pinned Photo Frame)
"""

from src.config import config
from gi.repository import GLib
import time

ACTIVE_DESKTOP_WIDGETS = []
_blur_cleanup_done = False

def cleanup_blur_effects():
    """Ensure desktop widgets and dynamic island are NOT in blur-my-shell whitelist.
    Blur-my-shell blurs window bounding boxes as rectangles, causing ugly fuzzy square
    borders around rounded widgets and pills.
    """
    global _blur_cleanup_done
    if _blur_cleanup_done:
        return
    _blur_cleanup_done = True

    import threading
    def _worker():
        import subprocess
        import os
        import shutil
        import ast

        if not shutil.which("gsettings"):
            return

        schema_dir = os.path.expanduser("~/.local/share/gnome-shell/extensions/blur-my-shell@aunetx/schemas")
        cmd_base = ["gsettings"]
        if os.path.isdir(schema_dir):
            cmd_base += ["--schemadir", schema_dir]

        try:
            res = subprocess.run(
                cmd_base + ["get", "org.gnome.shell.extensions.blur-my-shell.applications", "whitelist"],
                capture_output=True, text=True, timeout=1.0
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    current_list = ast.literal_eval(res.stdout.strip())
                except Exception:
                    current_list = []

                unwanted_prefixes = [
                    "macos-", "MacOS", "dynamic-island", "DynamicIsland",
                    "desktop-widget", "DesktopWidget"
                ]
                filtered = [
                    item for item in current_list
                    if not any(item.startswith(p) for p in unwanted_prefixes)
                ]

                if len(filtered) != len(current_list):
                    subprocess.run(
                        cmd_base + ["set", "org.gnome.shell.extensions.blur-my-shell.applications", "whitelist", str(filtered)],
                        capture_output=True, timeout=1.0
                    )
                if not filtered:
                    subprocess.run(
                        cmd_base + ["set", "org.gnome.shell.extensions.blur-my-shell.applications", "blur", "false"],
                        capture_output=True, timeout=1.0
                    )
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()

# Automatically clean up blur on module load
cleanup_blur_effects()

def register_widget(widget):
    cleanup_blur_effects()
    if widget not in ACTIVE_DESKTOP_WIDGETS:
        ACTIVE_DESKTOP_WIDGETS.append(widget)

def unregister_widget(widget):
    if widget in ACTIVE_DESKTOP_WIDGETS:
        ACTIVE_DESKTOP_WIDGETS.remove(widget)

def set_all_desktop_widgets_locked(locked: bool):
    config.set("lock_desktop_widgets", locked)
    for w in list(ACTIVE_DESKTOP_WIDGETS):
        try:
            if hasattr(w, "set_locked"):
                w.set_locked(locked)
        except Exception:
            pass

def is_desktop_widgets_locked() -> bool:
    return config.get("lock_desktop_widgets", True)


def animate_widget_open(window):
    """Reveal desktop cards. Positioning is preserved and animated via Cairo spring physics."""
    pass


from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
from src.ui.desktop_widgets.battery_widget import DesktopBatteryWidget
from src.ui.desktop_widgets.clock_widget import DesktopClockWidget
from src.ui.desktop_widgets.music_widget import DesktopMusicWidget
from src.ui.desktop_widgets.photo_widget import DesktopPhotoWidget
from src.ui.desktop_widgets.weekday_clock_widget import DesktopWeekdayClockWidget
from src.ui.desktop_widgets.macbook_widget import DesktopMacBookWidget

__all__ = [
    "DesktopCalendarWidget",
    "DesktopWeatherWidget",
    "DesktopBatteryWidget",
    "DesktopClockWidget",
    "DesktopMusicWidget",
    "DesktopPhotoWidget",
    "DesktopWeekdayClockWidget",
    "DesktopMacBookWidget",
    "register_widget",
    "unregister_widget",
    "set_all_desktop_widgets_locked",
    "is_desktop_widgets_locked",
    "animate_widget_open",
]
