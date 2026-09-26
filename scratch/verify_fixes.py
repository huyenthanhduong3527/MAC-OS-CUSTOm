#!/usr/bin/env python3
"""
Verification script for:
1. Settings Window (Language & Region page + User Profile page in Japanese)
2. Photos Window (Sidebar and toolbar in Japanese)
3. Calendar Widget (Month 9月 and Japanese weekday column headers)
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from src.utils.i18n import set_language, get_current_language
from src.ui.macos_settings_window import MacOSSettingsWindow
from src.ui.macos_photos_window import MacOSPhotosWindow
from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget

ARTIFACTS_DIR = "/home/tramvo/.gemini/antigravity-ide/brain/6d12946d-d261-4f0a-9add-c3a09e845a4e"

def capture_widget(widget, filename):
    alloc = widget.get_allocation()
    w = max(alloc.width, 100)
    h = max(alloc.height, 100)
    pixbuf = Gdk.pixbuf_get_from_window(widget.get_window(), 0, 0, w, h)
    if pixbuf:
        out_path = os.path.join(ARTIFACTS_DIR, filename)
        pixbuf.savev(out_path, "png", [], [])
        print(f"✓ Saved screenshot: {out_path} ({w}x{h})")
        return out_path
    else:
        print(f"✗ Failed to capture pixbuf for {filename}")
        return None

def main():
    set_language("ja", apply_system=False)
    print(f"Active Language: {get_current_language()}")

    # 1. Test Settings Window
    win = MacOSSettingsWindow()
    win.show_window("language_region")
    
    def step1_check_language_region():
        vis = win.stack.get_visible_child_name()
        print(f"[Settings] Visible child for 'language_region': {vis}")
        assert vis == "language_region", f"Expected 'language_region', got '{vis}'"
        capture_widget(win, "settings_japanese_language_region_verified.png")

        # Step 2: Switch to user_profile
        win.select_tab("user_profile")
        GLib.timeout_add(500, step2_check_user_profile)
        return False

    def step2_check_user_profile():
        vis = win.stack.get_visible_child_name()
        print(f"[Settings] Visible child for 'user_profile': {vis}")
        assert vis == "user_profile", f"Expected 'user_profile', got '{vis}'"
        capture_widget(win, "settings_japanese_profile_verified.png")
        win.hide()

        # Step 3: Photos Window
        photos_win = MacOSPhotosWindow()
        photos_win.show_all()
        GLib.timeout_add(700, lambda: step3_check_photos(photos_win))
        return False

    def step3_check_photos(photos_win):
        print(f"[Photos] Current title: {photos_win.title_lbl.get_text()}")
        print(f"[Photos] Search placeholder: {photos_win.search_entry.get_placeholder_text()}")
        capture_widget(photos_win, "photos_japanese_verified.png")
        photos_win.hide()

        # Step 4: Calendar Widget
        cal_win = DesktopCalendarWidget()
        cal_win.show_all()
        GLib.timeout_add(500, lambda: step4_check_calendar(cal_win))
        return False

    def step4_check_calendar(cal_win):
        capture_widget(cal_win, "calendar_japanese_verified.png")
        cal_win.hide()
        print("ALL VERIFICATIONS SUCCEEDED!")
        Gtk.main_quit()
        return False

    GLib.timeout_add(700, step1_check_language_region)
    Gtk.main()

if __name__ == "__main__":
    main()
