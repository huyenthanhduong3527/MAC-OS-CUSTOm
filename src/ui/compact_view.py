"""
Compact Pill View for Dynamic Island.
Sleek minimal status bar with live clock, dynamic status icon, mini animated visualizer,
and Apple-style Glowing Red Dot notification indicator.
Uses Gtk.EventBox to guarantee instant click and hover responsiveness on Wayland / XWayland.
"""

import time
import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_image, get_pixbuf
from src.utils.artwork import load_artwork_pixbuf

class NotificationDot(Gtk.DrawingArea):
    """
    Apple-style radiant glowing red circular notification indicator.
    Features a deep red core, pulsing outer ambient halo, and subtle specular highlight.
    """
    def __init__(self):
        super().__init__()
        self.set_size_request(12, 12)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self.on_draw)

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        cx = width / 2.0
        cy = height / 2.0
        radius = 3.5

        t = time.time()
        # Smooth organic breathing pulse
        pulse = 0.5 + 0.5 * math.sin(t * 3.5)
        glow_alpha = 0.25 + 0.25 * pulse

        # 1. Outer soft glowing halo
        cr.set_source_rgba(0.94, 0.27, 0.27, glow_alpha) # #ef4444 glow
        cr.arc(cx, cy, radius + 2.5, 0, 2 * math.pi)
        cr.fill()

        # 2. Inner vibrant Apple OLED red core
        cr.set_source_rgba(0.96, 0.20, 0.20, 1.0) # #f43f5e / #ef4444
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()

        # 3. Specular highlight sheen
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.55)
        cr.arc(cx - 1.0, cy - 1.0, 1.0, 0, 2 * math.pi)
        cr.fill()

        return False


class MiniVisualizerArea(Gtk.DrawingArea):
    """Custom Cairo drawing area for 4 bouncing audio equalizer bars."""
    def __init__(self, visualizer):
        super().__init__()
        self.visualizer = visualizer
        self.set_size_request(24, 16)
        self.connect("draw", self.on_draw)

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        bars = self.visualizer.bars[:4] # First 4 bars
        bar_w = 2.5
        spacing = 2.0
        start_x = (width - (len(bars) * bar_w + (len(bars) - 1) * spacing)) / 2

        cr.set_source_rgba(0.05, 0.65, 0.95, 0.95) # Cyan accent

        for i, val in enumerate(bars):
            h = max(2.5, val * height)
            y = height - h
            x = start_x + i * (bar_w + spacing)
            cr.rectangle(x, y, bar_w, h)
            cr.fill()
        return False


class CompactView(Gtk.EventBox):
    def __init__(self, media_mgr, system_mon, timer_mod, visualizer, notif_mgr=None, on_click=None, on_context_menu=None):
        super().__init__()
        self.set_visible_window(False) # Transparent input window for Cairo overlay
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.on_click = on_click
        self.on_context_menu = on_context_menu

        self.connect("button-press-event", self._on_button_press)
        self.connect("realize", self._on_realize)

        self.media_mgr = media_mgr
        self.system_mon = system_mon
        self.timer_mod = timer_mod
        self.visualizer = visualizer
        self.notif_mgr = notif_mgr

        # Inner layout box
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.box.set_name("compact-pill")
        self.box.get_style_context().add_class("compact-pill")
        self.box.set_valign(Gtk.Align.CENTER)
        self.box.set_halign(Gtk.Align.FILL)
        self.add(self.box)

        # Left Icon (Music note / Timer / Apple logo)
        self.left_icon = Gtk.Image()
        self.box.pack_start(self.left_icon, False, False, 2)

        # Center Label (Time or Song snippet)
        self.center_label = Gtk.Label(label="")
        self.center_label.get_style_context().add_class("compact-time")
        self.center_label.set_ellipsize(3) # PANGO_ELLIPSIZE_END
        self.center_label.set_max_width_chars(16)
        self.box.pack_start(self.center_label, True, True, 2)

        # Right Widget: Either Mini Visualizer, Battery %, or Timer text + Red Dot
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.box.pack_end(self.right_box, False, False, 2)

        self.mini_vis = MiniVisualizerArea(visualizer)
        self.right_label = Gtk.Label(label="")
        self.right_label.get_style_context().add_class("compact-subtitle")

        # Glowing Red Dot notification indicator
        self.notif_dot = NotificationDot()

        self.right_box.pack_start(self.mini_vis, False, False, 0)
        self.right_box.pack_start(self.right_label, False, False, 0)
        self.right_box.pack_end(self.notif_dot, False, False, 0)

        self.update()

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
        elif event.button == 3:
            if self.on_context_menu:
                self.on_context_menu(event)
            return True
        return False

    def update(self):
        """Periodic status update."""
        # 1. Update Red Dot Notification Indicator
        if self.notif_mgr and self.notif_mgr.unread_count > 0:
            self.notif_dot.show()
            self.notif_dot.queue_draw()
        else:
            self.notif_dot.hide()

        # 2. Priority 1: Timer running
        if self.timer_mod.is_running:
            self.left_icon.set_from_pixbuf(self._get_pixbuf_cached("timer", 16, "#38bdf8"))
            self.center_label.set_text(self.timer_mod.get_display_text())
            self.mini_vis.hide()
            self.right_label.hide()
            return

        # 3. Priority 2: Media Playing
        if self.media_mgr.is_playing():
            art_mini = load_artwork_pixbuf(self.media_mgr.art_url, size=18, radius=5, on_ready_callback=self.update)
            if art_mini:
                self.left_icon.set_from_pixbuf(art_mini)
            else:
                self.left_icon.set_from_pixbuf(self._get_pixbuf_cached("music", 16, "#38bdf8"))

            song_display = self.media_mgr.title
            if len(song_display) > 15:
                song_display = song_display[:14] + "…"
            self.center_label.set_text(song_display)

            self.mini_vis.show()
            self.mini_vis.queue_draw()
            self.right_label.hide()
            return

        # 4. Priority 3: Default Clock & Battery
        self.left_icon.set_from_pixbuf(self._get_pixbuf_cached("apple", 16, "#ffffff"))
        now_str = time.strftime("%H:%M")
        self.center_label.set_text(now_str)

        self.mini_vis.hide()
        if self.system_mon.has_battery:
            self.right_label.set_text(f"{self.system_mon.battery_pct}%")
            self.right_label.show()
        else:
            self.right_label.hide()

    def _get_pixbuf_cached(self, name, size, color):
        return get_pixbuf(name, size, color)
