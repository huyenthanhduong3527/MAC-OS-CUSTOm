#!/usr/bin/env python3
"""
Captures screenshots of macOS Settings Window Language & Region page
and the World Language Picker Dialog.
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from src.ui.macos_settings_window import MacOSSettingsWindow
from src.ui.macos_language_dialog import MacOSLanguagePickerDialog

ARTIFACTS_DIR = "/home/tramvo/.gemini/antigravity-ide/brain/84ee8d31-b613-4877-8fc9-f22ec3439582"

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
    win = MacOSSettingsWindow()
    win.show_all()
    win.select_tab("language_region")

    def _snap_and_open_picker():
        capture_widget(win, "macos_settings_language_page.png")

        dlg = MacOSLanguagePickerDialog(parent_window=win)
        dlg.show_all()

        def _snap_dialog():
            capture_widget(dlg, "macos_language_picker_dialog.png")
            dlg.destroy()
            win.destroy()
            Gtk.main_quit()
            return False

        GLib.timeout_add(600, _snap_dialog)
        return False

    GLib.timeout_add(800, _snap_and_open_picker)
    Gtk.main()

if __name__ == "__main__":
    main()
