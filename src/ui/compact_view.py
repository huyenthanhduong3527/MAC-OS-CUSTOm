"""
Compact Pill View for Dynamic Island.
Sleek minimal status bar with live clock, dynamic status icon, mini animated visualizer,
Apple-style Glowing Red Dot notification indicator,
Microphone & Camera Privacy Indicator dots (Orange & Green),
and Live Activity download/transfer progress rings.
Uses Gtk.EventBox to guarantee instant click and hover responsiveness on Wayland / XWayland.
"""

import time
import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_image, get_pixbuf
from src.utils.artwork import load_artwork_pixbuf
from src.modules.privacy import PrivacyMonitor
from src.modules.live_activity import LiveActivityManager

class NotificationDot(Gtk.DrawingArea):
    """
    Apple-style radiant glowing red circular notification indicator.
    Features a deep red core, pulsing outer ambient halo, and subtle specular highlight.
    """
    def __init__(self):
        super().__init__()
        self.set_size_request(12, 12)
        self.set_valign(Gtk.Align.CENTER)
        self.set_no_show_all(True)
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
        glow_alpha = 0.28 + 0.25 * pulse

        # 1. Outer soft glowing halo
        cr.set_source_rgba(0.94, 0.27, 0.27, glow_alpha) # #ef4444 glow
        cr.arc(cx, cy, radius + 2.5, 0, 2 * math.pi)
        cr.fill()

        # 2. Inner vibrant Apple OLED red core
        cr.set_source_rgba(0.96, 0.20, 0.20, 1.0) # #f43f5e / #ef4444
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()

        # 3. Specular highlight sheen
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.6)
        cr.arc(cx - 0.9, cy - 0.9, 1.0, 0, 2 * math.pi)
        cr.fill()

        return False


class PrivacyDot(Gtk.DrawingArea):
    """
    Apple-style radiant glowing indicator dot for Mic (Orange) or Camera (Green).
    Displays at most ONE dot at a time following Apple's Human Interface Guidelines:
    - Camera (Green) takes precedence when active.
    - Microphone (Orange) shows when only mic is active.
    - Stays completely hidden when neither is in use.
    """
    def __init__(self):
        super().__init__()
        self.color_type = None # 'mic', 'cam', or None
        self.set_size_request(10, 10)
        self.set_valign(Gtk.Align.CENTER)
        self.set_no_show_all(True)
        self.connect("draw", self.on_draw)

    def set_type(self, color_type):
        if self.color_type != color_type:
            self.color_type = color_type
            if color_type:
                self.show()
            else:
                self.hide()
            self.queue_draw()

    def on_draw(self, widget, cr):
        if not self.color_type:
            return False
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        cx = width / 2.0
        cy = height / 2.0
        radius = 3.0

        t = time.time()
        pulse = 0.5 + 0.5 * math.sin(t * 3.8)
        glow_alpha = 0.28 + 0.28 * pulse

        if self.color_type == "cam":
            # Green for Camera
            cr.set_source_rgba(0.13, 0.77, 0.37, glow_alpha) # #22c55e halo
            cr.arc(cx, cy, radius + 2.0, 0, 2 * math.pi)
            cr.fill()

            cr.set_source_rgba(0.20, 0.83, 0.35, 1.0) # #34c759 Apple green core
            cr.arc(cx, cy, radius, 0, 2 * math.pi)
            cr.fill()
        elif self.color_type == "mic":
            # Orange for Microphone
            cr.set_source_rgba(0.96, 0.62, 0.05, glow_alpha) # #f59e0b halo
            cr.arc(cx, cy, radius + 2.0, 0, 2 * math.pi)
            cr.fill()

            cr.set_source_rgba(0.98, 0.55, 0.0, 1.0) # #fb923c orange core
            cr.arc(cx, cy, radius, 0, 2 * math.pi)
            cr.fill()

        # Specular sheen
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.6)
        cr.arc(cx - 0.7, cy - 0.7, 0.8, 0, 2 * math.pi)
        cr.fill()

        return False


class CircularProgressArea(Gtk.DrawingArea):
    """Circular progress ring for downloads and AirDrop transfers."""
    def __init__(self):
        super().__init__()
        self.progress = 0.0 # 0.0 to 1.0, or -1 for spinner
        self.set_size_request(18, 18)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self.on_draw)

    def set_progress(self, p):
        self.progress = p
        self.queue_draw()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        cx = width / 2.0
        cy = height / 2.0
        r = min(cx, cy) - 2.5

        # Background track
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.18)
        cr.set_line_width(2.0)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()

        # Foreground progress ring
        if self.progress >= 0.0:
            cr.set_source_rgba(0.22, 0.74, 0.97, 0.95) # Cyan #38bdf8
            cr.set_line_width(2.2)
            start_angle = -math.pi / 2
            end_angle = start_angle + self.progress * 2 * math.pi
            cr.arc(cx, cy, r, start_angle, end_angle)
            cr.stroke()
        else:
            # Indeterminate animated spinner
            t = time.time() * 4.0
            cr.set_source_rgba(0.22, 0.74, 0.97, 0.95)
            cr.set_line_width(2.2)
            start_angle = t % (2 * math.pi)
            end_angle = start_angle + math.pi * 0.75
            cr.arc(cx, cy, r, start_angle, end_angle)
            cr.stroke()

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
    def __init__(self, media_mgr, system_mon, timer_mod, visualizer, notif_mgr=None, privacy_mgr=None, live_activity_mgr=None, on_click=None, on_context_menu=None):
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
        self.privacy_mgr = privacy_mgr or PrivacyMonitor.get_instance()
        self.live_activity_mgr = live_activity_mgr or LiveActivityManager.get_instance()

        # Inner layout box
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.box.set_name("compact-pill")
        self.box.get_style_context().add_class("compact-pill")
        self.box.set_valign(Gtk.Align.CENTER)
        self.box.set_halign(Gtk.Align.FILL)
        self.add(self.box)

        # Left Icon (Music note / Timer / Apple logo / Download Ring)
        self.left_icon = Gtk.Image()
        self.box.pack_start(self.left_icon, False, False, 2)

        # Live Activity Circular Progress Ring
        self.progress_ring = CircularProgressArea()
        self.progress_ring.set_no_show_all(True)
        self.box.pack_start(self.progress_ring, False, False, 2)
        self.progress_ring.hide()

        # Center Label (Time or Song snippet or Download filename)
        self.center_label = Gtk.Label(label="")
        self.center_label.get_style_context().add_class("compact-time")
        self.center_label.set_ellipsize(3) # PANGO_ELLIPSIZE_END
        self.center_label.set_max_width_chars(16)
        self.box.pack_start(self.center_label, True, True, 2)

        # Right Widget: Either Mini Visualizer, Battery %, or Timer text + Indicators
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.box.pack_end(self.right_box, False, False, 2)

        self.mini_vis = MiniVisualizerArea(visualizer)
        self.right_label = Gtk.Label(label="")
        self.right_label.get_style_context().add_class("compact-subtitle")

        # Single Apple-style Privacy Indicator Dot (Camera Green or Mic Orange, completely hidden when inactive)
        self.privacy_dot = PrivacyDot()
        self.privacy_dot.set_no_show_all(True)
        self.privacy_dot.hide()

        # Radiant Glowing Red Indicator Dot - signature aesthetic accent, only visible for unread notifications
        self.notif_dot = NotificationDot()
        self.notif_dot.set_no_show_all(True)
        self.notif_dot.hide()

        self.right_box.pack_start(self.mini_vis, False, False, 0)
        self.right_box.pack_start(self.right_label, False, False, 0)
        self.right_box.pack_end(self.notif_dot, False, False, 0)
        self.right_box.pack_end(self.privacy_dot, False, False, 0)

        # Cache to eliminate redundant 30 FPS GTK layout thrashing
        self._last_mode = None
        self._last_icon_key = None
        self._last_center_text = None
        self._last_right_text = None
        self._last_notif_unread = None
        self._last_privacy_type = None

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
        """Periodic status update with strict diff-caching to prevent GTK lag."""
        # 1. Update Apple-style Privacy Indicator: Camera (Green) takes priority, then Mic (Orange), else Hidden
        if self.privacy_mgr:
            mic, cam = self.privacy_mgr.get_status()
            privacy_type = "cam" if cam else ("mic" if mic else None)
            if privacy_type != self._last_privacy_type:
                self._last_privacy_type = privacy_type
                self.privacy_dot.set_type(privacy_type)

        # 2. Glowing Red Dot indicator: Apple-style, only visible when unread notifications exist
        unread_count = getattr(self.notif_mgr, "unread_count", 0) if self.notif_mgr else 0
        has_unread = unread_count > 0
        if has_unread != self._last_notif_unread:
            self._last_notif_unread = has_unread
            if has_unread:
                self.notif_dot.show()
            else:
                self.notif_dot.hide()

        # 3. Priority 0: Live Activity (Download / Transfer Progress)
        if self.live_activity_mgr and self.live_activity_mgr.active:
            if self._last_mode != "live_activity":
                self._last_mode = "live_activity"
                self.left_icon.hide()
                self.progress_ring.show()
                self.mini_vis.hide()
                self.right_label.show()

            self.progress_ring.set_progress(self.live_activity_mgr.progress)

            act_title = self.live_activity_mgr.title
            if len(act_title) > 13:
                act_title = act_title[:12] + "…"

            if self._last_center_text != act_title:
                self._last_center_text = act_title
                self.center_label.set_text(act_title)

            act_sub = self.live_activity_mgr.subtitle
            if self._last_right_text != act_sub:
                self._last_right_text = act_sub
                self.right_label.set_text(act_sub)
            return
        else:
            if self.progress_ring.get_visible():
                self.progress_ring.hide()
                self.left_icon.show()

        # 4. Priority 1: Timer running
        if self.timer_mod.is_running:
            new_text = self.timer_mod.get_display_text()
            if self._last_mode != "timer":
                self._last_mode = "timer"
                self.left_icon.set_from_pixbuf(self._get_pixbuf_cached("timer", 16, "#38bdf8"))
                self.mini_vis.hide()
                self.right_label.hide()
            if self._last_center_text != new_text:
                self._last_center_text = new_text
                self.center_label.set_text(new_text)
            return

        # 5. Priority 2: Media Playing (Only when actively playing)
        if self.media_mgr.is_playing():
            song_display = self.media_mgr.title
            if len(song_display) > 15:
                song_display = song_display[:14] + "…"

            art_url = self.media_mgr.art_url
            icon_key = ("art", art_url, song_display) if art_url else ("app", self.media_mgr.player_name, song_display)

            if self._last_mode != "media":
                self._last_mode = "media"
                self.mini_vis.show()
                self.right_label.hide()

            if self._last_icon_key != icon_key:
                self._last_icon_key = icon_key
                art_mini = load_artwork_pixbuf(art_url, size=18, radius=5, on_ready_callback=self.update)
                if art_mini:
                    self.left_icon.set_from_pixbuf(art_mini)
                else:
                    app_ico = self.media_mgr.get_app_icon(18)
                    if app_ico:
                        self.left_icon.set_from_pixbuf(app_ico)
                    else:
                        self.left_icon.set_from_pixbuf(self._get_pixbuf_cached("music", 16, "#38bdf8"))

            if self._last_center_text != song_display:
                self._last_center_text = song_display
                self.center_label.set_text(song_display)

            self.mini_vis.queue_draw()
            return

        # 6. Priority 3: Default Clock & Battery (when media is paused / stopped / idle)
        now_str = time.strftime("%H:%M")
        if self._last_mode != "clock":
            self._last_mode = "clock"
            self._last_icon_key = "apple"
            self.left_icon.set_from_pixbuf(self._get_pixbuf_cached("apple", 16, "#ffffff"))

        # Explicitly ensure mini visualizer bars are hidden whenever not playing
        if self.mini_vis.get_visible():
            self.mini_vis.hide()

        if self._last_center_text != now_str:
            self._last_center_text = now_str
            self.center_label.set_text(now_str)

        if self.system_mon.has_battery:
            b_text = f"{self.system_mon.battery_pct}%"
            if self._last_right_text != b_text:
                self._last_right_text = b_text
                self.right_label.set_text(b_text)
                self.right_label.show()
        else:
            if self._last_right_text != "":
                self._last_right_text = ""
                self.right_label.hide()

    def _get_pixbuf_cached(self, name, size, color):
        return get_pixbuf(name, size, color)
