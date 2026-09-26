import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
import os
import sys
import subprocess
import time

sys.path.insert(0, "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX")

from src.ui.macos_settings_window import MacOSSettingsWindow

def capture_screens():
    win = MacOSSettingsWindow()
    win.show_window(tab="general")
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    time.sleep(0.5)

    # Navigate to about
    win.select_tab("about")
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    time.sleep(0.5)

    # Capture About page screenshot
    out_about = "/home/tramvo/.gemini/antigravity-ide/brain/8fd3bae4-ec4f-4f48-8776-28f41030d5f9/settings_about_nav_fixed.png"
    subprocess.run(["import", "-window", "root", out_about])
    print(f"Captured about page to {out_about}")

    # Now show rename dialog in an idle callback and capture it
    def show_dialog():
        dialog = Gtk.Dialog(
            title="Đổi tên thiết bị",
            transient_for=win,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        dialog.set_default_size(390, 210)
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
        desc_lbl.set_max_width_chars(32)
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
        cancel_btn.connect("clicked", lambda _: dialog.response(Gtk.ResponseType.CANCEL))

        save_btn = Gtk.Button(label="Lưu")
        save_btn.get_style_context().add_class("mac-action-btn")
        save_btn.get_style_context().add_class("primary")
        save_btn.connect("clicked", lambda _: dialog.response(Gtk.ResponseType.OK))

        btn_box.pack_start(cancel_btn, False, False, 0)
        btn_box.pack_start(save_btn, False, False, 0)
        content.pack_start(btn_box, False, False, 0)

        dialog.show_all()

        def do_capture():
            out_dlg = "/home/tramvo/.gemini/antigravity-ide/brain/8fd3bae4-ec4f-4f48-8776-28f41030d5f9/settings_rename_dialog.png"
            subprocess.run(["import", "-window", "root", out_dlg])
            print(f"Captured rename dialog to {out_dlg}")
            dialog.destroy()
            win.destroy()
            Gtk.main_quit()
            return False

        GLib.timeout_add(600, do_capture)
        return False

    GLib.idle_add(show_dialog)
    Gtk.main()

if __name__ == "__main__":
    capture_screens()
