"""
Settings Tab for Dynamic Island.
Configures Top Y-offset, hover expansion, auto-collapse duration, demo mode, and quit button.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.config import config
from src.utils.icons import get_pixbuf
from src.utils.theme import is_dark_mode, toggle_dark_mode

class SettingsTab(Gtk.Box):
    def __init__(self, on_offset_change=None, on_quit=None, on_cosmos_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.get_style_context().add_class("tab-content")

        self.on_offset_change = on_offset_change
        self.on_quit = on_quit
        self.on_cosmos_change = on_cosmos_change

        # 1. Top Y-Offset Slider
        y_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        y_lbl = Gtk.Label(label="Top Offset (Y Margin)")
        y_lbl.get_style_context().add_class("vital-label")
        y_lbl.set_xalign(0.0)

        self.y_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 120, 2)
        self.y_scale.set_draw_value(False)
        self.y_scale.set_value(config.get("y_offset", 44))
        self.y_scale.set_hexpand(True)
        self.y_scale.connect("value-changed", self._on_y_change)

        self.y_val_lbl = Gtk.Label(label=f"{int(self.y_scale.get_value())}px")
        self.y_val_lbl.get_style_context().add_class("vital-label")

        y_box.pack_start(y_lbl, False, False, 0)
        y_box.pack_start(self.y_scale, True, True, 0)
        y_box.pack_end(self.y_val_lbl, False, False, 0)
        self.pack_start(y_box, False, False, 0)

        # 2. Options Grid: Hover Expand & Auto-Collapse
        opt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        # Hover toggle
        hover_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hover_lbl = Gtk.Label(label="Expand on Hover")
        hover_lbl.get_style_context().add_class("vital-label")
        self.hover_switch = Gtk.Switch()
        self.hover_switch.set_active(config.get("expand_on_hover", False))
        self.hover_switch.connect("state-set", self._on_hover_toggle)
        hover_box.pack_start(hover_lbl, False, False, 0)
        hover_box.pack_start(self.hover_switch, False, False, 0)
        opt_box.pack_start(hover_box, False, False, 0)

        # Demo Mode toggle
        demo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        demo_lbl = Gtk.Label(label="Demo Playlist")
        demo_lbl.get_style_context().add_class("vital-label")
        self.demo_switch = Gtk.Switch()
        self.demo_switch.set_active(config.get("demo_mode", False))
        self.demo_switch.connect("state-set", self._on_demo_toggle)
        demo_box.pack_start(demo_lbl, False, False, 0)
        demo_box.pack_start(self.demo_switch, False, False, 0)
        opt_box.pack_end(demo_box, False, False, 0)

        self.pack_start(opt_box, False, False, 0)

        # GNOME Notification Banner toggle
        notif_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        notif_lbl = Gtk.Label(label="Replace GNOME Banners (Show in Island)")
        notif_lbl.get_style_context().add_class("vital-label")
        self.notif_switch = Gtk.Switch()
        try:
            res = subprocess.run(["gsettings", "get", "org.gnome.desktop.notifications", "show-banners"], capture_output=True, text=True)
            self.notif_switch.set_active("false" in res.stdout.lower())
        except Exception:
            self.notif_switch.set_active(True)
        self.notif_switch.connect("state-set", self._on_notif_banner_toggle)
        notif_box.pack_start(notif_lbl, False, False, 0)
        notif_box.pack_end(self.notif_switch, False, False, 0)
        self.pack_start(notif_box, False, False, 0)

        # Dark Mode Toggle row
        dark_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dark_lbl = Gtk.Label(label="Dark Mode (Giao diện Tối)")
        dark_lbl.get_style_context().add_class("vital-label")
        self.dark_switch = Gtk.Switch()
        self.dark_switch.set_active(is_dark_mode())
        self.dark_switch.connect("state-set", self._on_dark_toggle)
        dark_box.pack_start(dark_lbl, False, False, 0)
        dark_box.pack_end(self.dark_switch, False, False, 0)
        self.pack_start(dark_box, False, False, 0)

        # Cosmic Orbit App Launcher toggle row
        cosmos_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cosmos_lbl = Gtk.Label(label="🪐 Vũ trụ Orbit (Solar App Launcher)")
        cosmos_lbl.get_style_context().add_class("vital-label")
        self.cosmos_switch = Gtk.Switch()
        self.cosmos_switch.set_active(config.get("enable_cosmic_orbit", True))
        self.cosmos_switch.connect("state-set", self._on_cosmos_toggle)
        cosmos_box.pack_start(cosmos_lbl, False, False, 0)
        cosmos_box.pack_end(self.cosmos_switch, False, False, 0)
        self.pack_start(cosmos_box, False, False, 0)

        # 3. Actions: Quit Button
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.CENTER)

        quit_btn = Gtk.Button(label="Quit Dynamic Island")
        quit_btn.get_style_context().add_class("ctrl-btn")
        quit_btn.connect("clicked", lambda b: self.on_quit() if self.on_quit else Gtk.main_quit())
        action_box.pack_start(quit_btn, False, False, 0)

        self.pack_start(action_box, False, False, 4)

    def _on_y_change(self, scale):
        val = int(scale.get_value())
        self.y_val_lbl.set_text(f"{val}px")
        config.set("y_offset", val)
        if self.on_offset_change:
            self.on_offset_change(val)

    def _on_hover_toggle(self, switch, state):
        config.set("expand_on_hover", state)
        return False

    def _on_demo_toggle(self, switch, state):
        config.set("demo_mode", state)
        return False

    def _on_notif_banner_toggle(self, switch, state):
        # state == True means user wants Dynamic Island to handle banners (hide GNOME banners)
        val = "false" if state else "true"
        subprocess.run(["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", val], check=False)
        return False

    def _on_dark_toggle(self, switch, state):
        toggle_dark_mode()
        return False

    def _on_cosmos_toggle(self, switch, state):
        config.set("enable_cosmic_orbit", state)
        if self.on_cosmos_change:
            self.on_cosmos_change(state)
        return False
