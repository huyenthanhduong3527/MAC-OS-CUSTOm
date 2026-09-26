#!/usr/bin/env python3
"""
Captures high-resolution renders of:
1. Dynamic Island Siri Tab (Apple Intelligence & Local Qwen 2.5 1.5B)
2. macOS Settings Window focused on Local Siri & Multilingual Voice
"""

import os
import sys
import cairo

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

ARTIFACTS_DIR = "/home/tramvo/.gemini/antigravity-ide/brain/f5b95faa-56bc-454c-ab4e-0e3352cdd412"

def load_app_css():
    css_path = os.path.join(BASE_DIR, "src", "ui", "styles.css")
    if os.path.exists(css_path):
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

def capture_siri_card():
    from src.ui.tabs.gemini_tab import GeminiTab

    win = Gtk.Window()
    win.set_default_size(560, 290)
    win.set_app_paintable(True)

    tab = GeminiTab()
    tab.response_lbl.set_text(
        "Xin chào! Tôi là Siri (Apple Intelligence) được tiếp sức mạnh bởi mô hình AI Qwen 2.5 1.5B "
        "chạy cục bộ 100% trên máy tính của bạn.\n\n"
        "⚡ Tôi có thể mở ứng dụng, tìm kiếm tệp tin, tự động soạn thảo và tạo file văn bản trên Desktop."
    )

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.get_style_context().add_class("island-window")
    box.set_margin_start(16)
    box.set_margin_end(16)
    box.set_margin_top(16)
    box.set_margin_bottom(16)
    box.pack_start(tab, True, True, 0)

    win.add(box)
    win.show_all()

    def _snap():
        alloc = win.get_allocation()
        w = max(alloc.width, 560)
        h = max(alloc.height, 290)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surf)
        win.draw(cr)
        out_path = os.path.join(ARTIFACTS_DIR, "dynamic_island_siri_tab.png")
        surf.write_to_png(out_path)
        print(f"Saved: {out_path} ({w}x{h})")
        win.destroy()
        _start_settings()
        return False

    GLib.timeout_add(400, _snap)

def _start_settings():
    from src.ui.macos_settings_window import MacOSSettingsWindow
    win = MacOSSettingsWindow()
    win.show_all()
    win.select_tab("internet_accounts")

    def _scroll_and_snap():
        page = win.stack.get_child_by_name("internet_accounts")
        if isinstance(page, Gtk.ScrolledWindow):
            adj = page.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())

        def _do_capture():
            alloc = win.get_allocation()
            w = max(alloc.width, 800)
            h = max(alloc.height, 600)
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            cr = cairo.Context(surf)
            win.draw(cr)
            out_path = os.path.join(ARTIFACTS_DIR, "macos_settings_siri_voice.png")
            surf.write_to_png(out_path)
            print(f"Saved: {out_path} ({w}x{h})")
            win.destroy()
            Gtk.main_quit()
            return False

        GLib.timeout_add(300, _do_capture)
        return False

    GLib.timeout_add(500, _scroll_and_snap)

if __name__ == "__main__":
    load_app_css()
    capture_siri_card()
    Gtk.main()
