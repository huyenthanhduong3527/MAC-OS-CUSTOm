"""
Quick Controls Tab for Expanded Dynamic Island.
Includes Volume control slider, Mute toggle, GNOME Screenshot tool, and Lock Screen action.
"""

import time
import threading
import subprocess
import dbus
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf
from src.utils.theme import is_dark_mode, toggle_dark_mode

class ControlsTab(Gtk.Box):
    def __init__(self, audio_ctrl, on_collapse=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.get_style_context().add_class("tab-content")

        self.audio_ctrl = audio_ctrl
        self.on_collapse = on_collapse

        # 1. Volume Row
        vol_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        vol_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.vol_icon = Gtk.Image.new_from_pixbuf(get_pixbuf("volume_high", 15, "#38bdf8"))
        vol_title = Gtk.Label(label="MASTER VOLUME")
        vol_title.get_style_context().add_class("vital-label")
        self.vol_pct_lbl = Gtk.Label(label="100%")
        self.vol_pct_lbl.get_style_context().add_class("vital-label")

        vol_header.pack_start(self.vol_icon, False, False, 0)
        vol_header.pack_start(vol_title, False, False, 0)
        vol_header.pack_end(self.vol_pct_lbl, False, False, 0)
        vol_box.pack_start(vol_header, False, False, 0)

        # Slider + Mute button
        slider_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.connect("value-changed", self._on_slider_change)

        self.mute_btn = Gtk.Button()
        self.mute_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("volume_mute", 14, "#f8fafc")))
        self.mute_btn.get_style_context().add_class("ctrl-btn")
        self.mute_btn.connect("clicked", self._on_mute_clicked)

        slider_row.pack_start(self.vol_scale, True, True, 0)
        slider_row.pack_end(self.mute_btn, False, False, 0)
        vol_box.pack_start(slider_row, False, False, 0)

        self.pack_start(vol_box, False, False, 0)

        # 2. Quick Action Buttons Row
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_homogeneous(True)

        # Screenshot button
        shot_btn = Gtk.Button()
        shot_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        shot_content.set_halign(Gtk.Align.CENTER)
        shot_content.pack_start(Gtk.Image.new_from_pixbuf(get_pixbuf("screenshot", 15, "#ffffff")), False, False, 0)
        shot_content.pack_start(Gtk.Label(label="Screenshot"), False, False, 0)
        shot_btn.add(shot_content)
        shot_btn.get_style_context().add_class("quick-action-btn")
        shot_btn.connect("clicked", self._on_screenshot)
        actions_box.pack_start(shot_btn, True, True, 0)

        # Lock Screen button
        lock_btn = Gtk.Button()
        lock_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lock_content.set_halign(Gtk.Align.CENTER)
        lock_content.pack_start(Gtk.Image.new_from_pixbuf(get_pixbuf("lock", 15, "#ffffff")), False, False, 0)
        lock_content.pack_start(Gtk.Label(label="Lock Screen"), False, False, 0)
        lock_btn.add(lock_content)
        lock_btn.get_style_context().add_class("quick-action-btn")
        lock_btn.connect("clicked", self._on_lock)
        actions_box.pack_start(lock_btn, True, True, 0)

        # Dark / Light Mode Toggle button
        self.theme_btn = Gtk.Button()
        theme_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        theme_content.set_halign(Gtk.Align.CENTER)
        self.theme_img = Gtk.Image.new_from_pixbuf(get_pixbuf("moon", 15, "#38bdf8"))
        self.theme_lbl = Gtk.Label(label="Dark Mode")
        theme_content.pack_start(self.theme_img, False, False, 0)
        theme_content.pack_start(self.theme_lbl, False, False, 0)
        self.theme_btn.add(theme_content)
        self.theme_btn.get_style_context().add_class("quick-action-btn")
        self.theme_btn.connect("clicked", self._on_toggle_theme)
        actions_box.pack_start(self.theme_btn, True, True, 0)

        self.pack_start(actions_box, False, False, 0)

        self._updating_slider = False
        self.update()

    def update(self):
        self.audio_ctrl.update_status()
        vol = self.audio_ctrl.volume
        is_muted = self.audio_ctrl.is_muted

        pct = int(vol * 100)
        self.vol_pct_lbl.set_text("MUTED" if is_muted else f"{pct}%")

        self._updating_slider = True
        self.vol_scale.set_value(pct)
        self._updating_slider = False

        if is_muted:
            self.vol_icon.set_from_pixbuf(get_pixbuf("volume_mute", 15, "#ef4444"))
        else:
            self.vol_icon.set_from_pixbuf(get_pixbuf("volume_high", 15, "#38bdf8"))

        self._sync_theme_ui()

    def _on_toggle_theme(self, btn):
        is_dark = toggle_dark_mode()
        self._sync_theme_ui(is_dark)

    def _sync_theme_ui(self, is_dark=None):
        if is_dark is None:
            is_dark = is_dark_mode()
        self.theme_img.set_from_pixbuf(get_pixbuf("sun" if is_dark else "moon", 15, "#fbbf24" if is_dark else "#38bdf8"))
        self.theme_lbl.set_text("Light Mode" if is_dark else "Dark Mode")

    def _on_slider_change(self, scale):
        if self._updating_slider:
            return
        val = scale.get_value() / 100.0
        self.audio_ctrl.set_volume(val)
        self.vol_pct_lbl.set_text(f"{int(scale.get_value())}%")

    def _on_mute_clicked(self, btn):
        self.audio_ctrl.toggle_mute()
        self.update()

    def _on_screenshot(self, btn):
        if self.on_collapse:
            self.on_collapse()

        def _do_screenshot():
            time.sleep(0.2)
            # 1. Primary modern method: XDG Desktop Portal Screenshot (GNOME 42 / 45 / 46 / 50)
            try:
                bus = dbus.SessionBus()
                portal = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
                iface = dbus.Interface(portal, "org.freedesktop.portal.Screenshot")
                iface.Screenshot("", {"interactive": dbus.Boolean(True)})
                return
            except Exception as e:
                print(f"[Controls] Portal screenshot error: {e}")

            # 2. Fallback: gdbus CLI call to portal
            try:
                subprocess.Popen([
                    "gdbus", "call", "--session",
                    "--dest", "org.freedesktop.portal.Desktop",
                    "--object-path", "/org/freedesktop/portal/desktop",
                    "--method", "org.freedesktop.portal.Screenshot.Screenshot",
                    "", "{'interactive': <true>}"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass

            # 3. Fallback: Standalone tools
            for tool in [["gnome-screenshot", "-i"], ["spectacle"], ["flameshot", "gui"]]:
                try:
                    subprocess.Popen(tool, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except FileNotFoundError:
                    continue

        threading.Thread(target=_do_screenshot, daemon=True).start()

    def _on_lock(self, btn):
        if self.on_collapse:
            self.on_collapse()

        def _do_lock():
            time.sleep(0.15)
            # 1. loginctl lock-session (standard systemd/GNOME)
            try:
                subprocess.Popen(["loginctl", "lock-session"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass

            # 2. GNOME ScreenSaver D-Bus
            try:
                bus = dbus.SessionBus()
                obj = bus.get_object("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver")
                saver = dbus.Interface(obj, "org.gnome.ScreenSaver")
                saver.Lock()
                return
            except Exception:
                pass

            # 3. CLI fallback
            try:
                subprocess.Popen(["gnome-screensaver-command", "-l"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        threading.Thread(target=_do_lock, daemon=True).start()
