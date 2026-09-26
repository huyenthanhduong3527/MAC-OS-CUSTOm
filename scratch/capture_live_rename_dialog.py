import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import subprocess, time

from src.ui.macos_settings_window import MacOSSettingsWindow

win = MacOSSettingsWindow()
win.show_window("about")

def step1():
    # Call _show_rename_device_dialog non-blockingly or open it
    # We can inspect the dialog
    dialog = Gtk.Dialog(
        title="Đổi tên thiết bị",
        transient_for=win,
        modal=True,
        destroy_with_parent=True
    )
    dialog.set_default_size(390, 210)
    dialog.get_style_context().add_class("mac-window")
    dialog.get_style_context().add_class("mac-dark")

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

    save_btn = Gtk.Button(label="Lưu")
    save_btn.get_style_context().add_class("mac-action-btn")
    save_btn.get_style_context().add_class("primary")

    btn_box.pack_start(cancel_btn, False, False, 0)
    btn_box.pack_start(save_btn, False, False, 0)
    content.pack_start(btn_box, False, False, 0)

    dialog.show_all()

    def do_shot():
        out = subprocess.check_output(["wmctrl", "-l"]).decode()
        for line in out.splitlines():
            if "Đổi tên" in line:
                xid = line.split()[0]
                print("Found dialog XID:", xid)
                subprocess.run(["import", "-window", xid, "/home/tramvo/.gemini/antigravity-ide/brain/8fd3bae4-ec4f-4f48-8776-28f41030d5f9/real_rename_dialog.png"])
                print("Captured dialog successfully!")
        dialog.destroy()
        win.destroy()
        Gtk.main_quit()
        return False

    GLib.timeout_add(400, do_shot)
    return False

GLib.timeout_add(300, step1)
Gtk.main()
