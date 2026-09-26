#!/usr/bin/env python3
"""
Captures screenshots of:
1. macOS Settings: "Tài khoản Google & Đám mây"
2. Dynamic Island Expanded View with Gemini Siri Tab
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from src.ui.macos_settings_window import MacOSSettingsWindow
from src.window import DynamicIslandWindow

ARTIFACTS_DIR = "/home/tramvo/.gemini/antigravity-ide/brain/f5b95faa-56bc-454c-ab4e-0e3352cdd412"

def capture_widget(widget, filename):
    alloc = widget.get_allocation()
    w = max(alloc.width, 100)
    h = max(alloc.height, 100)
    pixbuf = Gdk.pixbuf_get_from_window(widget.get_window(), 0, 0, w, h)
    if pixbuf:
        out_path = os.path.join(ARTIFACTS_DIR, filename)
        pixbuf.savev(out_path, "png", [], [])
        print(f"Saved screenshot: {out_path}")

def main():
    # 1. Settings Window
    win_settings = MacOSSettingsWindow()
    win_settings.show_all()
    win_settings.select_tab("internet_accounts")

    def _snap_settings():
        capture_widget(win_settings, "macos_settings_google_gemini_page.png")
        win_settings.destroy()

        # 2. Dynamic Island Window
        island_win = DynamicIslandWindow()
        island_win.show_all()
        island_win.expand()
        island_win.expanded_view.switch_to_tab("gemini")

        def _snap_island():
            capture_widget(island_win, "dynamic_island_gemini_siri.png")
            island_win.destroy()
            Gtk.main_quit()
            return False

        GLib.timeout_add(700, _snap_island)
        return False

    GLib.timeout_add(800, _snap_settings)
    Gtk.main()

if __name__ == "__main__":
    main()
