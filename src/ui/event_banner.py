"""
Transient Dynamic Event Banner for Volume Changes, Track Alerts, and System Notifications.
Features Apple-style dedicated Volume HUD with Cairo-rendered fluid pill slider,
and multi-line notification / now-playing capsule.
"""

import os
import math
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf
from src.utils.artwork import load_artwork_pixbuf

class VolumeBarArea(Gtk.DrawingArea):
    """
    Apple-style rounded pill volume progress slider.
    Features dark translucent glass track, vibrant cyan/white fluid fill,
    and a delicate specular sheen highlight.
    """
    def __init__(self):
        super().__init__()
        self.fraction = 1.0
        self.is_muted = False
        self.set_size_request(130, 10)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self.on_draw)

    def set_volume(self, fraction, is_muted=False):
        self.fraction = max(0.0, min(1.0, float(fraction)))
        self.is_muted = is_muted
        self.queue_draw()

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = h / 2.0

        # 1. Dark translucent track background
        cr.arc(w - r, r, r, -math.pi / 2, math.pi / 2)
        cr.arc(r, r, r, math.pi / 2, 3 * math.pi / 2)
        cr.close_path()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.20)
        cr.fill()

        # 2. Fluid progress fill
        fill_w = max(h, w * self.fraction)
        if self.fraction <= 0.001 or self.is_muted:
            return False

        cr.arc(fill_w - r, r, r, -math.pi / 2, math.pi / 2)
        cr.arc(r, r, r, math.pi / 2, 3 * math.pi / 2)
        cr.close_path()

        # Apple Cyan to Sky Blue gradient
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgba(0.0, 0.22, 0.74, 0.97, 1.0) # #38bdf8
        pat.add_color_stop_rgba(1.0, 0.38, 0.65, 0.98, 1.0) # #60a5fa
        cr.set_source(pat)
        cr.fill()

        # Specular highlight
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.35)
        cr.arc(fill_w - r, r, r, -math.pi / 2, 0)
        cr.set_line_width(1.0)
        cr.stroke()

        return False


class EventBanner(Gtk.EventBox):
    def __init__(self, on_click=None):
        super().__init__()
        self.set_visible_window(False)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.on_click = on_click
        self.connect("button-press-event", self._on_button_press)
        self.connect("realize", self._on_realize)

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.box.get_style_context().add_class("event-banner")
        self.box.set_valign(Gtk.Align.CENTER)
        self.add(self.box)

        # -------------------------------------------------------------
        # Mode A: Dedicated Apple iOS Volume HUD Row
        # -------------------------------------------------------------
        self.volume_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.volume_row.set_valign(Gtk.Align.CENTER)
        self.volume_row.set_hexpand(True)

        self.vol_icon_box = Gtk.Box()
        self.vol_icon_box.get_style_context().add_class("event-icon-box")
        self.vol_icon = Gtk.Image()
        self.vol_icon_box.pack_start(self.vol_icon, False, False, 0)
        self.volume_row.pack_start(self.vol_icon_box, False, False, 0)

        self.vol_bar_area = VolumeBarArea()
        self.volume_row.pack_start(self.vol_bar_area, True, True, 0)

        self.vol_pct_lbl = Gtk.Label(label="100%")
        self.vol_pct_lbl.get_style_context().add_class("volume-pct")
        self.vol_pct_lbl.set_valign(Gtk.Align.CENTER)
        self.volume_row.pack_end(self.vol_pct_lbl, False, False, 0)

        # -------------------------------------------------------------
        # Mode B: Notification & Now-Playing Track Alert
        # -------------------------------------------------------------
        self.notif_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.notif_row.set_valign(Gtk.Align.CENTER)
        self.notif_row.set_hexpand(True)

        self.notif_icon_box = Gtk.Box()
        self.notif_icon_box.get_style_context().add_class("event-icon-box")
        self.notif_icon = Gtk.Image()
        self.notif_icon_box.pack_start(self.notif_icon, False, False, 0)
        self.notif_row.pack_start(self.notif_icon_box, False, False, 0)

        self.content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.content_vbox.set_hexpand(True)
        self.content_vbox.set_valign(Gtk.Align.CENTER)

        self.app_lbl = Gtk.Label(label="")
        self.app_lbl.get_style_context().add_class("event-app")
        self.app_lbl.set_xalign(0.0)
        self.content_vbox.pack_start(self.app_lbl, False, False, 0)

        self.title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.title_lbl = Gtk.Label(label="")
        self.title_lbl.get_style_context().add_class("event-title")
        self.title_lbl.set_xalign(0.0)
        self.title_lbl.set_ellipsize(3)

        self.sub_lbl = Gtk.Label(label="")
        self.sub_lbl.get_style_context().add_class("event-subtitle")
        self.sub_lbl.set_xalign(0.0)
        self.sub_lbl.set_ellipsize(3)

        self.title_row.pack_start(self.title_lbl, False, False, 0)
        self.title_row.pack_start(self.sub_lbl, True, True, 0)
        self.content_vbox.pack_start(self.title_row, False, False, 0)

        self.notif_row.pack_start(self.content_vbox, True, True, 0)
        self.box.pack_start(self.notif_row, True, True, 0)

    def _switch_mode(self, mode):
        """Ensure only the active row is attached to self.box to prevent layout displacement."""
        for ch in self.box.get_children():
            self.box.remove(ch)
        if mode == "volume":
            self.box.pack_start(self.volume_row, True, True, 0)
            self.volume_row.show_all()
        else:
            self.box.pack_start(self.notif_row, True, True, 0)
            self.notif_row.show_all()

    def _on_realize(self, widget):
        gdk_win = widget.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            cursor = Gdk.Cursor.new_from_name(display, "pointer")
            if cursor:
                gdk_win.set_cursor(cursor)

    def _on_button_press(self, widget, event):
        if event.button == 1:
            if self.on_click:
                self.on_click()
            return True
        return False

    def show_volume(self, volume, is_muted):
        """Configure banner for Apple iOS style Volume HUD."""
        self._switch_mode("volume")

        if is_muted:
            self.vol_icon.set_from_pixbuf(get_pixbuf("volume_mute", 16, "#ef4444"))
            self.vol_pct_lbl.set_text("MUTED")
            self.vol_pct_lbl.get_style_context().remove_class("volume-pct")
            self.vol_pct_lbl.get_style_context().add_class("volume-muted")
            self.vol_bar_area.set_volume(0.0, is_muted=True)
        else:
            pct = int(volume * 100)
            icon_name = "volume_low" if volume < 0.33 else ("volume_medium" if volume < 0.66 else "volume_high")
            self.vol_icon.set_from_pixbuf(get_pixbuf(icon_name, 16, "#38bdf8"))
            self.vol_pct_lbl.set_text(f"{pct}%")
            self.vol_pct_lbl.get_style_context().remove_class("volume-muted")
            self.vol_pct_lbl.get_style_context().add_class("volume-pct")
            self.vol_bar_area.set_volume(volume, is_muted=False)

    def show_track(self, title, artist):
        """Configure banner for track change."""
        self._switch_mode("notif")

        self.app_lbl.set_text("NOW PLAYING")
        self.app_lbl.show()
        self.notif_icon_box.get_style_context().remove_class("event-shot-box")
        self.notif_icon_box.get_style_context().add_class("event-icon-box")
        self.notif_icon.set_from_pixbuf(get_pixbuf("music", 16, "#0ea5e9"))
        self.title_lbl.set_text(title)
        if artist:
            self.sub_lbl.set_text(f"— {artist}")
            self.sub_lbl.show()
        else:
            self.sub_lbl.set_text("")
            self.sub_lbl.hide()

    def show_notification(self, app_name, title, body, image_path=None):
        """Configure banner for system notification."""
        self._switch_mode("notif")

        self.app_lbl.set_text(app_name.upper())
        self.app_lbl.show()

        icon_name = "bell"
        icon_color = "#f59e0b"
        if "screen" in app_name.lower() or "shot" in app_name.lower():
            icon_name = "screenshot"
            icon_color = "#38bdf8"
        elif "music" in app_name.lower():
            icon_name = "music"
            icon_color = "#a855f7"

        # If screenshot image preview is available, display rounded thumbnail
        if image_path and os.path.exists(image_path):
            thumb = load_artwork_pixbuf(image_path, size=28, radius=6)
            if thumb:
                self.notif_icon_box.get_style_context().remove_class("event-icon-box")
                self.notif_icon_box.get_style_context().add_class("event-shot-box")
                self.notif_icon.set_from_pixbuf(thumb)
            else:
                self.notif_icon_box.get_style_context().remove_class("event-shot-box")
                self.notif_icon_box.get_style_context().add_class("event-icon-box")
                self.notif_icon.set_from_pixbuf(get_pixbuf(icon_name, 16, icon_color))
        else:
            self.notif_icon_box.get_style_context().remove_class("event-shot-box")
            self.notif_icon_box.get_style_context().add_class("event-icon-box")
            self.notif_icon.set_from_pixbuf(get_pixbuf(icon_name, 16, icon_color))

        self.title_lbl.set_text(title)

        if body:
            self.sub_lbl.set_text(f"· {body}")
            self.sub_lbl.show()
        else:
            self.sub_lbl.set_text("")
            self.sub_lbl.hide()
