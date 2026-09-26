import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import os
import sys
import time

sys.path.insert(0, "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX")

from src.ui.macos_settings_window import MacOSSettingsWindow

def run():
    win = MacOSSettingsWindow()
    win.show_window(tab="general")
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    time.sleep(0.3)

    # Navigate to about
    win.select_tab("about")
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    time.sleep(0.3)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    # 1. Capture Settings window on About page
    alloc = win.get_allocation()
    gdk_win = win.get_window()
    pb = Gdk.pixbuf_get_from_window(gdk_win, 0, 0, alloc.width, alloc.height)
    out_about = "/home/tramvo/.gemini/antigravity-ide/brain/8fd3bae4-ec4f-4f48-8776-28f41030d5f9/settings_about_nav_fixed.png"
    if pb:
        pb.savev(out_about, "png", [], [])
        print(f"[OK] Saved about page screenshot: {out_about} ({alloc.width}x{alloc.height})")
    else:
        print("[FAIL] Could not capture about page")

    # 2. Show the rename modal dialog and capture it
    dialog = Gtk.Dialog(
        title="Đổi tên thiết bị",
        transient_for=win,
        modal=True,
        destroy_with_parent=True
    )
    dialog.set_default_size(420, 220)
    dialog.get_style_context().add_class("mac-window")
    if getattr(win, "is_dark", False):
        dialog.get_style_context().add_class("mac-dark")
    else:
        dialog.get_style_context().add_class("mac-light")

    content = dialog.get_content_area()
    content.set_spacing(16)
    content.set_margin_start(22)
    content.set_margin_end(22)
    content.set_margin_top(18)
    content.set_margin_bottom(18)

    from src.ui.macos_settings_window import make_squircle_icon
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
    icon = make_squircle_icon("display", "#007aff", size=42, icon_size=24)
    header.pack_start(icon, False, False, 0)

    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    title_lbl = Gtk.Label(label="Đổi tên máy tính")
    title_lbl.get_style_context().add_class("mac-bento-title")
    title_lbl.set_xalign(0.0)

    desc_lbl = Gtk.Label(label="Tên này được hiển thị cho các thiết bị khác khi sử dụng AirDrop, Bluetooth và mạng cục bộ.")
    desc_lbl.get_style_context().add_class("mac-label-sub")
    desc_lbl.set_line_wrap(True)
    desc_lbl.set_max_width_chars(34)
    desc_lbl.set_xalign(0.0)

    text_box.pack_start(title_lbl, False, False, 0)
    text_box.pack_start(desc_lbl, False, False, 0)
    header.pack_start(text_box, True, True, 0)
    content.pack_start(header, False, False, 0)

    entry = Gtk.Entry()
    entry.set_text("tramvo-X99E")
    entry.get_style_context().add_class("mac-search-entry")
    content.pack_start(entry, False, False, 0)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    btn_box.set_halign(Gtk.Align.END)
    btn_box.set_margin_top(6)

    cancel_btn = Gtk.Button(label="Hủy")
    cancel_btn.get_style_context().add_class("mac-action-btn")

    save_btn = Gtk.Button(label="Lưu")
    save_btn.get_style_context().add_class("mac-action-btn")
    save_btn.get_style_context().add_class("primary")

    btn_box.pack_start(cancel_btn, False, False, 0)
    btn_box.pack_start(save_btn, False, False, 0)
    content.pack_start(btn_box, False, False, 0)

    dialog.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    time.sleep(0.3)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    d_alloc = dialog.get_allocation()
    d_win = dialog.get_window()
    pb_dlg = Gdk.pixbuf_get_from_window(d_win, 0, 0, d_alloc.width, d_alloc.height)
    out_dlg = "/home/tramvo/.gemini/antigravity-ide/brain/8fd3bae4-ec4f-4f48-8776-28f41030d5f9/settings_rename_dialog.png"
    if pb_dlg:
        pb_dlg.savev(out_dlg, "png", [], [])
        print(f"[OK] Saved rename dialog screenshot: {out_dlg} ({d_alloc.width}x{d_alloc.height})")
    else:
        print("[FAIL] Could not capture rename dialog")

    dialog.destroy()
    win.destroy()
    print("[ALL DONE]")

if __name__ == "__main__":
    run()
