"""
macOS Desktop Music Player Widget for Ubuntu Linux.
Renders an authentic, frosted glassmorphism Apple Music widget directly on the desktop
with album art, live progress scrubber, playback controls, open spring animation,
and smooth resizing (corner drag handle, scroll wheel zoom, size presets).
Supports lock/unlock mode (fixed desktop placement with right-click unlock to move & resize).
"""

import math
import time
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo

from src.config import config
from src.animator import SpringValue
from src.utils.artwork import load_artwork_pixbuf
from src.ui.desktop_widgets import (
    register_widget,
    animate_widget_open,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)
from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item, get_sf_symbol_pixbuf


class DesktopMusicWidget(Gtk.Window):
    def __init__(self, media_mgr, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.media_mgr = media_mgr
        self.on_close = on_close

        # Register in active widgets pool
        register_widget(self)
        animate_widget_open(self)

        # Locked state: when True, widget is fixed in place and cannot be accidentally moved or resized
        self.is_locked = config.get("lock_desktop_widgets", True)

        # Layout mode: 'photo_vertical' (iOS / reference photo style) or 'classic' (macOS square)
        self.layout_mode = config.get("desktop_music_layout", "photo_vertical")
        if self.layout_mode == "photo_vertical":
            self.base_card_w = 236.0
            self.base_card_h = 380.0
            self.base_radius = 28.0
        else:
            self.base_card_w = 236.0
            self.base_card_h = 246.0
            self.base_radius = 26.0

        self.base_pad = 14.0
        self.base_total_w = self.base_card_w + 2 * self.base_pad
        self.base_total_h = self.base_card_h + 2 * self.base_pad

        # User scale factor (clamped between 0.65 and 1.85)
        raw_scale = config.get("desktop_music_scale", 1.0)
        try:
            self.scale = max(0.65, min(1.85, round(float(raw_scale), 2)))
        except Exception:
            self.scale = 1.0

        # Effective window dimensions
        self.card_w = self.base_card_w
        self.card_h = self.base_card_h
        self.pad = self.base_pad
        self.radius = self.base_radius
        self.total_w = max(100, int(self.base_total_w * self.scale))
        self.total_h = max(100, int(self.base_total_h * self.scale))

        # Desktop pinning state
        self.keep_below = True
        self.shuffle = False
        self.repeat = False

        # Theme mode: 'auto', 'light', 'dark'
        self.theme_mode = config.get("desktop_music_theme", "auto")
        self._update_dark_mode_state()

        # Spring Open Animation
        self.anim_scale = SpringValue(1.0, stiffness=260.0, damping=19.0)
        self.anim_alpha = SpringValue(1.0, stiffness=220.0, damping=21.0)
        self._anim_timer_id = None
        self._anim_last_time = 0.0

        # Window properties
        self.set_title("macOS Music Widget")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.stick()
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.connect("map-event", lambda *_: self.set_keep_below(True) if getattr(self, "keep_below", True) else None)
        self.connect("realize", lambda *_: self.set_keep_below(True) if getattr(self, "keep_below", True) else None)
        self.set_wmclass("desktop-widget-music", "DesktopWidgetMusic")
        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)

        # Connect system dark/light theme listener
        try:
            from gi.repository import Gio
            self._gnome_settings = Gio.Settings.new("org.gnome.desktop.interface")
            self._gnome_settings.connect("changed::color-scheme", self._on_system_theme_changed)
            self._gnome_settings.connect("changed::gtk-theme", self._on_system_theme_changed)
        except Exception:
            pass

        # RGBA transparent visual
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
        self.get_style_context().add_class("transparent-window")
        self.get_style_context().add_class("desktop-widget-music")

        # Position window from config
        self._current_x = int(config.get("desktop_music_x", 380))
        self._current_y = int(config.get("desktop_music_y", 290))
        self.move(self._current_x, self._current_y)

        # Dragging state
        self._dragging = False
        self._has_moved = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = self._current_x
        self._win_start_y = self._current_y

        # Resizing state (bottom-right corner drag)
        self._resizing = False
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_scale = 1.0

        # Event handling
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("scroll-event", self._on_scroll)
        self.connect("map-event", self._on_map_event)
        self._lyrics_window = None

        # Timer for UI refresh (250ms for smooth scrubber animation)
        self._timer_id = GLib.timeout_add(250, self._on_tick)

    def set_locked(self, locked: bool):
        """Sets whether the widget is fixed in place or can be moved/resized."""
        self.is_locked = bool(locked)
        self._dragging = False
        self._resizing = False
        gdk_win = self.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            cursor_name = "default" if self.is_locked else "grab"
            cursor = Gdk.Cursor.new_from_name(display, cursor_name)
            if cursor:
                gdk_win.set_cursor(cursor)
        self.queue_draw()

    def _update_dark_mode_state(self):
        if self.theme_mode == "light":
            self.dark_mode = False
        elif self.theme_mode == "dark":
            self.dark_mode = True
        else:
            try:
                from src.utils.theme import is_dark_mode
                self.dark_mode = is_dark_mode()
            except Exception:
                self.dark_mode = True

    def _on_realize(self, widget):
        gdk_win = widget.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            cursor_name = "default" if self.is_locked else "grab"
            cursor = Gdk.Cursor.new_from_name(display, cursor_name)
            if cursor:
                gdk_win.set_cursor(cursor)

    def _on_map_event(self, widget, event):
        GLib.idle_add(lambda: self.move(self._current_x, self._current_y))
        self.play_open_animation()
        return False

    def play_open_animation(self):
        """Triggers fluid Apple spring-expand opening animation."""
        self.anim_scale.set_immediate(0.52)
        self.anim_scale.set_target(1.0)
        self.anim_alpha.set_immediate(0.0)
        self.anim_alpha.set_target(1.0)
        self._anim_last_time = time.monotonic()
        if self._anim_timer_id is None:
            self._anim_timer_id = GLib.timeout_add(16, self._on_anim_step)
        self.queue_draw()

    def _on_anim_step(self):
        now = time.monotonic()
        dt = min(now - self._anim_last_time, 0.05)
        self._anim_last_time = now

        settled_s = self.anim_scale.step(dt)
        settled_a = self.anim_alpha.step(dt)
        self.queue_draw()

        if settled_s and settled_a:
            self._anim_timer_id = None
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def set_scale(self, new_scale, save=True):
        """Scales the widget dynamically and updates the window geometry."""
        new_scale = max(0.65, min(1.85, round(float(new_scale), 2)))
        self.scale = new_scale
        if save:
            config.set("desktop_music_scale", self.scale)

        self.total_w = max(100, int(self.base_total_w * self.scale))
        self.total_h = max(100, int(self.base_total_h * self.scale))
        self.set_size_request(self.total_w, self.total_h)
        self.resize(self.total_w, self.total_h)
        self.queue_draw()

    def _on_tick(self):
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _on_system_theme_changed(self, *args):
        if self.theme_mode == "auto":
            self._update_dark_mode_state()
            self.queue_draw()

    def _draw_squircle(self, cr, x, y, w, h, radius):
        cr.new_sub_path()
        cr.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
        cr.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _format_time(self, seconds):
        if seconds < 0:
            seconds = 0
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"

    def _draw_pango_text(self, cr, x, y, text, font_desc, color_rgba, align="left", max_w=-1):
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        desc = Pango.FontDescription(font_desc)
        layout.set_font_description(desc)

        if max_w > 0:
            layout.set_width(int(max_w * Pango.SCALE))
            layout.set_ellipsize(Pango.EllipsizeMode.END)

        _, logical_rect = layout.get_pixel_extents()

        draw_x = x
        if align == "center":
            draw_x = x - logical_rect.width / 2.0
        elif align == "right":
            draw_x = x - logical_rect.width

        cr.save()
        cr.set_source_rgba(*color_rgba)
        cr.move_to(draw_x, y)
        PangoCairo.show_layout(cr, layout)
        cr.restore()
        return logical_rect.width, logical_rect.height

    # Vector Icon Helpers
    def _draw_play_icon(self, cr, cx, cy, r, color=(1, 1, 1, 1)):
        cr.save()
        cr.set_source_rgba(*color)
        cr.new_sub_path()
        cr.move_to(cx - r * 0.45, cy - r * 0.65)
        cr.line_to(cx + r * 0.70, cy)
        cr.line_to(cx - r * 0.45, cy + r * 0.65)
        cr.close_path()
        cr.fill()
        cr.restore()

    def _draw_pause_icon(self, cr, cx, cy, r, color=(1, 1, 1, 1)):
        cr.save()
        cr.set_source_rgba(*color)
        bar_w = r * 0.36
        bar_h = r * 1.2
        gap = r * 0.28
        cr.rectangle(cx - gap / 2.0 - bar_w, cy - bar_h / 2.0, bar_w, bar_h)
        cr.rectangle(cx + gap / 2.0, cy - bar_h / 2.0, bar_w, bar_h)
        cr.fill()
        cr.restore()

    def _draw_prev_icon(self, cr, cx, cy, r, color=(1, 1, 1, 1)):
        cr.save()
        cr.set_source_rgba(*color)
        s = r * 0.70
        # Left triangle
        cr.new_sub_path()
        cr.move_to(cx - 1.5, cy - s)
        cr.line_to(cx - s - 1.5, cy)
        cr.line_to(cx - 1.5, cy + s)
        cr.close_path()
        cr.fill()
        # Right triangle
        cr.new_sub_path()
        cr.move_to(cx + s * 0.85, cy - s)
        cr.line_to(cx - 0.5, cy)
        cr.line_to(cx + s * 0.85, cy + s)
        cr.close_path()
        cr.fill()
        cr.restore()

    def _draw_next_icon(self, cr, cx, cy, r, color=(1, 1, 1, 1)):
        cr.save()
        cr.set_source_rgba(*color)
        s = r * 0.70
        # Left triangle
        cr.new_sub_path()
        cr.move_to(cx - s * 0.85, cy - s)
        cr.line_to(cx + 0.5, cy)
        cr.line_to(cx - s * 0.85, cy + s)
        cr.close_path()
        cr.fill()
        # Right triangle
        cr.new_sub_path()
        cr.move_to(cx + 1.5, cy - s)
        cr.line_to(cx + s + 1.5, cy)
        cr.line_to(cx + 1.5, cy + s)
        cr.close_path()
        cr.fill()
        cr.restore()

    def _draw_lyrics_pill(self, cr, lx, ly, lw, lh, dark):
        lr = lh / 2.0
        self._draw_squircle(cr, lx, ly, lw, lh, lr)
        pill_bg = (1.0, 1.0, 1.0, 0.16) if dark else (0.0, 0.0, 0.0, 0.08)
        cr.set_source_rgba(*pill_bg)
        cr.fill_preserve()
        pill_stroke = (1.0, 1.0, 1.0, 0.28) if dark else (0.0, 0.0, 0.0, 0.12)
        cr.set_source_rgba(*pill_stroke)
        cr.set_line_width(0.9)
        cr.stroke()
        # Text with lyric symbol
        text_color = (0.95, 0.97, 1.0, 0.95) if dark else (0.15, 0.18, 0.22, 0.95)
        self._draw_pango_text(cr, lx + lw / 2.0, ly + 3.5, "💬 Lyrics", "Ubuntu Bold 8.5", text_color, align="center")

    def _draw_chevron_right(self, cr, cx, cy, size, color):
        cr.save()
        cr.set_source_rgba(*color)
        cr.set_line_width(1.4)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        hs = size * 0.5
        cr.move_to(cx - hs * 0.4, cy - hs)
        cr.line_to(cx + hs * 0.5, cy)
        cr.line_to(cx - hs * 0.4, cy + hs)
        cr.stroke()
        cr.restore()

    def _draw_shuffle_icon(self, cr, cx, cy, size, color=(0.58, 0.64, 0.72, 0.8)):
        cr.save()
        cr.set_source_rgba(*color)
        cr.set_line_width(1.6)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        hs = size * 0.5

        cr.move_to(cx - hs, cy - hs * 0.5)
        cr.curve_to(cx - hs * 0.2, cy - hs * 0.5, cx + hs * 0.2, cy + hs * 0.5, cx + hs, cy + hs * 0.5)
        cr.stroke()

        cr.move_to(cx - hs, cy + hs * 0.5)
        cr.curve_to(cx - hs * 0.2, cy + hs * 0.5, cx + hs * 0.2, cy - hs * 0.5, cx + hs, cy - hs * 0.5)
        cr.stroke()

        cr.move_to(cx + hs - 3, cy - hs * 0.5 - 3)
        cr.line_to(cx + hs, cy - hs * 0.5)
        cr.line_to(cx + hs - 3, cy - hs * 0.5 + 3)
        cr.stroke()

        cr.move_to(cx + hs - 3, cy + hs * 0.5 - 3)
        cr.line_to(cx + hs, cy + hs * 0.5)
        cr.line_to(cx + hs - 3, cy + hs * 0.5 + 3)
        cr.stroke()
        cr.restore()

    def _draw_repeat_icon(self, cr, cx, cy, size, color=(0.58, 0.64, 0.72, 0.8)):
        cr.save()
        cr.set_source_rgba(*color)
        cr.set_line_width(1.6)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        hs = size * 0.5
        r = 3.0

        cr.move_to(cx - hs, cy - hs * 0.3)
        cr.line_to(cx + hs - r, cy - hs * 0.3)
        cr.arc(cx + hs - r, cy, r, -math.pi / 2, math.pi / 2)
        cr.line_to(cx - hs + r, cy + hs * 0.3)
        cr.arc(cx - hs + r, cy, r, math.pi / 2, 3 * math.pi / 2)
        cr.stroke()

        cr.move_to(cx + hs - 2, cy - hs * 0.3 - 3)
        cr.line_to(cx + hs + 1, cy - hs * 0.3)
        cr.line_to(cx + hs - 2, cy - hs * 0.3 + 3)
        cr.stroke()
        cr.restore()

    def _draw_resize_grip(self, cr, rx, ry, dark):
        """Draws subtle modern Apple resize indicator at bottom-right corner."""
        cr.save()
        grip_color = (0.23, 0.51, 0.96, 0.90) if not self.is_locked else ((1.0, 1.0, 1.0, 0.35) if dark else (0.28, 0.32, 0.40, 0.35))
        cr.set_source_rgba(*grip_color)
        cr.set_line_width(1.8)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for offset in (6, 11, 16):
            cr.move_to(rx - offset, ry - 3)
            cr.line_to(rx - 3, ry - offset)
            cr.stroke()
        cr.restore()

    def _is_over_resize_handle(self, unscaled_x, unscaled_y):
        """Checks if unscaled cursor is inside the bottom-right corner resize zone."""
        rx = self.base_pad + self.base_card_w
        ry = self.base_pad + self.base_card_h
        return (rx - 26 <= unscaled_x <= rx + 8) and (ry - 26 <= unscaled_y <= ry + 8)

    def _on_draw(self, widget, cr):
        # 0. Clear transparent background
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        open_scale = max(0.01, self.anim_scale.current)
        open_alpha = max(0.0, min(1.0, self.anim_alpha.current))

        if open_alpha <= 0.001:
            return False

        win_w = widget.get_allocated_width()
        win_h = widget.get_allocated_height()
        cx = win_w / 2.0
        cy = win_h / 2.0

        cr.save()

        # Apply opening scale animation around center
        cr.translate(cx, cy)
        cr.scale(open_scale, open_scale)
        cr.translate(-cx, -cy)

        # Scale coordinates according to user scale factor
        cr.scale(self.scale, self.scale)

        # Use group blending during open animation for seamless alpha fade
        use_group = (open_alpha < 0.999)
        if use_group:
            cr.push_group()

        x = self.base_pad
        y = self.base_pad
        w = self.base_card_w
        h = self.base_card_h
        r = self.base_radius
        dark = getattr(self, "dark_mode", True)

        # 1. Card Background (Translucent Apple Glass - Wallpaper clearly visible through card)
        self._draw_squircle(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        dark = True  # Always use luminous white typography on transparent glass

        # Translucent dark frosted glass card
        base_pat = cairo.LinearGradient(x, y, x, y + h)
        base_pat.add_color_stop_rgba(0.0, 0.08, 0.10, 0.14, 0.35)
        base_pat.add_color_stop_rgba(1.0, 0.04, 0.05, 0.08, 0.42)
        cr.set_source(base_pat)
        cr.paint()

        # Specular top highlight catching ambient light
        sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
        sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.14)
        sheen.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.02)
        sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(sheen)
        cr.paint()

        cr.restore()

        # 2. Subtle Glass Rim (Subtle and razor-sharp, no blurry outline)
        self._draw_squircle(cr, x, y, w, h, r)
        rim = cairo.LinearGradient(x, y, x, y + h)
        rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.22)
        rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.08)
        rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.12)
        cr.set_source(rim)
        cr.set_line_width(0.8)
        cr.stroke()

        # If Unlocked (Edit Mode), draw glowing Apple blue border
        if not self.is_locked:
            cr.save()
            self._draw_squircle(cr, x, y, w, h, r)
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.65)
            cr.set_line_width(2.0)
            cr.stroke()
            cr.restore()

        if getattr(self, "layout_mode", "photo_vertical") == "photo_vertical":
            # -------------------------------------------------------------
            # LAYOUT: iOS / REFERENCE PHOTO VERTICAL CARD
            # -------------------------------------------------------------
            art_margin = 14.0
            art_size = w - 2 * art_margin
            art_x = x + art_margin
            art_y = y + art_margin
            art_r = 18.0

            # 4. Large Album Artwork (Crisp, High-Resolution Rendering)
            cr.save()
            self._draw_squircle(cr, art_x, art_y, art_size, art_size, art_r)
            cr.clip()

            render_size = int(max(256.0, art_size * max(1.0, getattr(self, "scale", 1.0)) * 1.5))
            render_radius = int(art_r * (render_size / art_size))
            art_pixbuf = load_artwork_pixbuf(self.media_mgr.art_url, size=render_size, radius=render_radius, on_ready_callback=self.queue_draw)
            if art_pixbuf:
                pw = art_pixbuf.get_width()
                ph = art_pixbuf.get_height()
                cr.save()
                cr.translate(art_x, art_y)
                cr.scale(art_size / float(pw), art_size / float(ph))
                Gdk.cairo_set_source_pixbuf(cr, art_pixbuf, 0, 0)
                try:
                    cr.get_source().set_filter(cairo.FILTER_BEST)
                except Exception:
                    pass
                cr.paint()
                cr.restore()
            else:
                pat = cairo.LinearGradient(art_x, art_y, art_x + art_size, art_y + art_size)
                pat.add_color_stop_rgb(0.0, 0.28, 0.32, 0.42)
                pat.add_color_stop_rgb(1.0, 0.12, 0.14, 0.18)
                cr.set_source(pat)
                cr.paint()
                pb = get_sf_symbol_pixbuf("music", size=36, color=(1.0, 1.0, 1.0))
                Gdk.cairo_set_source_pixbuf(cr, pb, art_x + (art_size - 36) / 2.0, art_y + (art_size - 36) / 2.0)
                cr.paint_with_alpha(0.4)

            cr.restore()

            # Art border
            self._draw_squircle(cr, art_x, art_y, art_size, art_size, art_r)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
            cr.set_line_width(1.0)
            cr.stroke()

            # 5. Metadata & Lyrics Row
            meta_y = art_y + art_size + 14.0
            title = self.media_mgr.title or "No Track Playing"
            artist = self.media_mgr.artist or "Apple Music"

            lyr_w = 64.0
            lyr_h = 23.0
            lyr_x = art_x + art_size - lyr_w
            lyr_y = meta_y + 3.0
            text_max_w = (lyr_x - 10.0) - art_x

            # Song Title (Bold)
            title_color = (0.98, 0.99, 1.0, 1.0) if dark else (0.10, 0.12, 0.16, 0.95)
            self._draw_pango_text(cr, art_x, meta_y, title, "Ubuntu Bold 13.5", title_color, align="left", max_w=text_max_w)

            # Artist
            artist_color = (0.78, 0.82, 0.88, 0.90) if dark else (0.38, 0.42, 0.48, 0.88)
            self._draw_pango_text(cr, art_x, meta_y + 21, artist, "Ubuntu 11", artist_color, align="left", max_w=text_max_w)

            # Lyrics pill button
            self._draw_lyrics_pill(cr, lyr_x, lyr_y, lyr_w, lyr_h, dark)

            # 6. Playback Controls Row (Centered)
            btn_y = meta_y + 60.0
            center_x = x + w / 2.0
            ctrl_color = (0.96, 0.98, 1.0, 1.0) if dark else (0.14, 0.16, 0.20, 0.95)

            # Prev <<
            self._draw_prev_icon(cr, center_x - 56.0, btn_y, 11.0, ctrl_color)

            # Play / Pause in center
            is_playing = self.media_mgr.is_playing()
            if is_playing:
                self._draw_pause_icon(cr, center_x, btn_y, 10.5, ctrl_color)
            else:
                self._draw_play_icon(cr, center_x + 1.5, btn_y, 10.5, ctrl_color)

            # Next >>
            self._draw_next_icon(cr, center_x + 56.0, btn_y, 11.0, ctrl_color)

            # 7. Progress Scrubber (Below controls, matching photo)
            scrubber_y = btn_y + 42.0
            bar_x = x + 16.0
            bar_w = w - 32.0
            bar_h = 3.0

            pos_sec = getattr(self.media_mgr, 'position', 0)
            len_sec = getattr(self.media_mgr, 'duration', 0)
            fraction = (pos_sec / len_sec) if len_sec > 0 else 0.0
            fraction = max(0.0, min(1.0, fraction))

            # Background bar
            track_bg = (1.0, 1.0, 1.0, 0.22) if dark else (0.0, 0.0, 0.0, 0.12)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_width(bar_h)
            cr.set_source_rgba(*track_bg)
            cr.move_to(bar_x, scrubber_y)
            cr.line_to(bar_x + bar_w, scrubber_y)
            cr.stroke()

            # Filled progress
            fill_x = bar_x + bar_w * fraction
            if fraction > 0:
                fill_color = (1.0, 1.0, 1.0, 0.95) if dark else (0.10, 0.12, 0.16, 0.95)
                cr.set_source_rgba(*fill_color)
                cr.move_to(bar_x, scrubber_y)
                cr.line_to(fill_x, scrubber_y)
                cr.stroke()

            # Small scrubber thumb dot
            if fraction > 0:
                cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
                cr.arc(fill_x, scrubber_y, 4.0, 0, 2 * math.pi)
                cr.fill()

            # Elapsed time (Left) & Duration with chevron (Right)
            time_color = (0.72, 0.76, 0.82, 0.85) if dark else (0.42, 0.46, 0.52, 0.85)
            time_y = scrubber_y + 11.0
            elapsed_str = self._format_time(pos_sec)
            self._draw_pango_text(cr, bar_x, time_y, elapsed_str, "Ubuntu 8.5", time_color, align="left")

            rem_str = self._format_time(len_sec) if len_sec > 0 else "0:00"
            chev_x = bar_x + bar_w - 38.0
            self._draw_chevron_right(cr, chev_x, time_y + 6.0, 6.0, time_color)
            self._draw_pango_text(cr, bar_x + bar_w, time_y, rem_str, "Ubuntu 8.5", time_color, align="right")

        else:
            # -------------------------------------------------------------
            # LAYOUT: CLASSIC macOS SQUARE CARD
            # -------------------------------------------------------------
            art_size = 78
            art_x = x + 16
            art_y = y + 16
            art_r = 12.0

            cr.save()
            self._draw_squircle(cr, art_x, art_y, art_size, art_size, art_r)
            cr.clip()

            render_s = int(art_size * 2)
            art_pixbuf = load_artwork_pixbuf(self.media_mgr.art_url, size=render_s, radius=int(art_r * 2), on_ready_callback=self.queue_draw)
            if art_pixbuf:
                pw = art_pixbuf.get_width()
                ph = art_pixbuf.get_height()
                cr.save()
                cr.translate(art_x, art_y)
                cr.scale(art_size / float(pw), art_size / float(ph))
                Gdk.cairo_set_source_pixbuf(cr, art_pixbuf, 0, 0)
                try:
                    cr.get_source().set_filter(cairo.FILTER_BEST)
                except Exception:
                    pass
                cr.paint()
                cr.restore()
            else:
                pat = cairo.LinearGradient(art_x, art_y, art_x + art_size, art_y + art_size)
                pat.add_color_stop_rgb(0.0, 0.48, 0.32, 0.20)
                pat.add_color_stop_rgb(1.0, 0.18, 0.15, 0.14)
                cr.set_source(pat)
                cr.paint()
                pb = get_sf_symbol_pixbuf("music", size=24, color=(1.0, 1.0, 1.0))
                Gdk.cairo_set_source_pixbuf(cr, pb, art_x + (art_size - 24) / 2.0, art_y + (art_size - 24) / 2.0)
                cr.paint_with_alpha(0.5)

            cr.restore()

            self._draw_squircle(cr, art_x, art_y, art_size, art_size, art_r)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.18)
            cr.set_line_width(1.0)
            cr.stroke()

            text_x = art_x + art_size + 14
            text_max_w = (x + w - 16) - text_x

            title = self.media_mgr.title or "No Track Playing"
            artist = self.media_mgr.artist or "Apple Music"
            album = self.media_mgr.album or "Desktop Widget"

            title_color = (0.98, 0.99, 1.0, 1.0) if dark else (0.10, 0.12, 0.16, 0.95)
            self._draw_pango_text(cr, text_x, art_y + 8, title, "Ubuntu Bold 13", title_color, align="left", max_w=text_max_w)

            artist_color = (0.82, 0.86, 0.92, 0.90) if dark else (0.40, 0.44, 0.50, 0.88)
            self._draw_pango_text(cr, text_x, art_y + 32, artist, "Ubuntu 11", artist_color, align="left", max_w=text_max_w)

            album_color = (0.60, 0.65, 0.72, 0.75) if dark else (0.55, 0.60, 0.68, 0.75)
            self._draw_pango_text(cr, text_x, art_y + 52, album, "Ubuntu 10", album_color, align="left", max_w=text_max_w)

            scrubber_y = y + 130
            bar_x = x + 50
            bar_w = w - 100
            bar_h = 3.5

            pos_sec = getattr(self.media_mgr, 'position', 0)
            len_sec = getattr(self.media_mgr, 'duration', 0)
            fraction = (pos_sec / len_sec) if len_sec > 0 else 0.0
            fraction = max(0.0, min(1.0, fraction))

            time_color = (0.70, 0.75, 0.82, 0.85) if dark else (0.42, 0.48, 0.55, 0.85)
            elapsed_str = self._format_time(pos_sec)
            self._draw_pango_text(cr, bar_x - 8, scrubber_y - 6, elapsed_str, "Ubuntu 8.5", time_color, align="right")

            rem_sec = max(0, len_sec - pos_sec)
            rem_str = f"-{self._format_time(rem_sec)}"
            self._draw_pango_text(cr, bar_x + bar_w + 8, scrubber_y - 6, rem_str, "Ubuntu 8.5", time_color, align="left")

            track_bg = (0.28, 0.32, 0.40, 0.75) if dark else (0.84, 0.87, 0.92, 0.90)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_width(bar_h)
            cr.set_source_rgba(*track_bg)
            cr.move_to(bar_x, scrubber_y)
            cr.line_to(bar_x + bar_w, scrubber_y)
            cr.stroke()

            fill_x = bar_x + bar_w * fraction
            if fraction > 0:
                cr.set_source_rgba(0.23, 0.51, 0.96, 1.0)
                cr.move_to(bar_x, scrubber_y)
                cr.line_to(fill_x, scrubber_y)
                cr.stroke()

            pill_w = 20.0
            pill_h = 9.0
            pill_r = pill_h / 2.0
            px = max(bar_x, min(bar_x + bar_w - pill_w, fill_x - pill_w / 2.0))
            py = scrubber_y - pill_h / 2.0

            self._draw_squircle(cr, px, py, pill_w, pill_h, pill_r)
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.fill_preserve()
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.15)
            cr.set_line_width(0.75)
            cr.stroke()

            btn_y = y + 185
            center_x = x + w / 2.0

            sub_btn_color = (0.58, 0.64, 0.72, 0.85) if dark else (0.45, 0.50, 0.58, 0.85)
            main_btn_color = (0.95, 0.97, 1.0, 1.0) if dark else (0.18, 0.22, 0.28, 0.95)
            active_accent = (0.23, 0.51, 0.96, 1.0)

            is_shuffle = getattr(self.media_mgr, "shuffle", False) or getattr(self, "shuffle", False)
            shuf_color = active_accent if is_shuffle else sub_btn_color
            if is_shuffle:
                cr.save()
                cr.set_source_rgba(0.23, 0.51, 0.96, 0.24 if dark else 0.16)
                cr.arc(center_x - 72, btn_y, 14, 0, 2 * math.pi)
                cr.fill()
                cr.restore()
            self._draw_shuffle_icon(cr, center_x - 72, btn_y, 15, shuf_color)

            self._draw_prev_icon(cr, center_x - 36, btn_y, 8.5, main_btn_color)

            play_r = 19.0
            is_playing = self.media_mgr.is_playing()

            circle_bg = (1.0, 1.0, 1.0, 0.15) if dark else (0.0, 0.0, 0.0, 0.06)
            cr.set_source_rgba(*circle_bg)
            cr.arc(center_x, btn_y, play_r, 0, 2 * math.pi)
            cr.fill()

            circle_stroke = (1.0, 1.0, 1.0, 0.28) if dark else (0.0, 0.0, 0.0, 0.12)
            cr.set_source_rgba(*circle_stroke)
            cr.set_line_width(1.0)
            cr.arc(center_x, btn_y, play_r, 0, 2 * math.pi)
            cr.stroke()

            play_icon_color = (1, 1, 1, 1) if dark else (0.10, 0.12, 0.16, 1.0)
            if is_playing:
                self._draw_pause_icon(cr, center_x, btn_y, 7.5, play_icon_color)
            else:
                self._draw_play_icon(cr, center_x + 1, btn_y, 7.5, play_icon_color)

            self._draw_next_icon(cr, center_x + 36, btn_y, 8.5, main_btn_color)

            loop_status = getattr(self.media_mgr, "loop_status", "None")
            is_repeat = (loop_status in ("Track", "Playlist")) or getattr(self, "repeat", False)
            rep_color = active_accent if is_repeat else sub_btn_color
            if is_repeat:
                cr.save()
                cr.set_source_rgba(0.23, 0.51, 0.96, 0.24 if dark else 0.16)
                cr.arc(center_x + 72, btn_y, 14, 0, 2 * math.pi)
                cr.fill()
                cr.restore()
            self._draw_repeat_icon(cr, center_x + 72, btn_y, 15, rep_color)
            if loop_status == "Track":
                self._draw_pango_text(cr, center_x + 72 + 6, btn_y - 9, "1", "Ubuntu Bold 7", active_accent, align="center")

        # 8. Modern Corner Resize Grip (Only shown when unlocked / editing)
        if not self.is_locked:
            self._draw_resize_grip(cr, x + w, y + h, dark)

        if use_group:
            cr.pop_group_to_source()
            cr.paint_with_alpha(open_alpha)

        cr.restore()
        return False

    def _on_lyrics_clicked(self):
        try:
            if not getattr(self, "_lyrics_window", None):
                from src.ui.macos_lyrics_window import MacOSLyricsWindow
                self._lyrics_window = MacOSLyricsWindow(self.media_mgr)
            self._lyrics_window.toggle(parent_window=self)
        except Exception as e:
            print(f"[MusicWidget] Error opening lyrics: {e}")

    def _on_button_press(self, widget, event):
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        x = unscaled_x - self.base_pad
        y = unscaled_y - self.base_pad

        if event.button == 1:
            # 1. Check corner resize handle (Only active when widget is UNLOCKED)
            if not self.is_locked and self._is_over_resize_handle(unscaled_x, unscaled_y):
                self._resizing = True
                self._resize_start_x = event.x_root
                self._resize_start_y = event.y_root
                self._resize_start_scale = self.scale
                gdk_win = widget.get_window()
                if gdk_win:
                    display = Gdk.Display.get_default()
                    cursor = Gdk.Cursor.new_from_name(display, "se-resize")
                    if cursor:
                        gdk_win.set_cursor(cursor)
                return True

            if getattr(self, "layout_mode", "photo_vertical") == "photo_vertical":
                art_margin = 14.0
                art_size = self.base_card_w - 2 * art_margin
                meta_y = art_margin + art_size + 14.0
                lyr_w = 64.0
                lyr_h = 23.0
                lyr_x = art_margin + art_size - lyr_w
                lyr_y = meta_y + 3.0

                # Check Lyrics button click
                if (lyr_x - 4) <= x <= (lyr_x + lyr_w + 4) and (lyr_y - 4) <= y <= (lyr_y + lyr_h + 4):
                    self._on_lyrics_clicked()
                    return True

                # Check Playback Controls click
                btn_y = meta_y + 60.0
                center_x = self.base_card_w / 2.0
                if abs(y - btn_y) <= 22:
                    # Prev
                    if abs(x - (center_x - 56.0)) <= 22:
                        self.media_mgr.prev_track()
                        self.queue_draw()
                        return True
                    # Play / Pause
                    elif abs(x - center_x) <= 24:
                        self.media_mgr.play_pause()
                        self.queue_draw()
                        return True
                    # Next
                    elif abs(x - (center_x + 56.0)) <= 22:
                        self.media_mgr.next_track()
                        self.queue_draw()
                        return True

                # Check Scrubber click
                scrubber_y = btn_y + 42.0
                bar_x = 16.0
                bar_w = self.base_card_w - 32.0
                if abs(y - scrubber_y) <= 14 and (bar_x - 8) <= x <= (bar_x + bar_w + 8):
                    frac = max(0.0, min(1.0, (x - bar_x) / bar_w))
                    dur = getattr(self.media_mgr, 'duration', 0)
                    if dur > 0:
                        self.media_mgr.seek(frac * dur)
                    self.queue_draw()
                    return True

            else:
                # 2. Check scrubber click (Seek) -> Always responsive!
                scrubber_y = 130
                bar_x = 50
                bar_w = self.base_card_w - 100
                if abs(y - scrubber_y) <= 14 and (bar_x - 8) <= x <= (bar_x + bar_w + 8):
                    frac = max(0.0, min(1.0, (x - bar_x) / bar_w))
                    dur = getattr(self.media_mgr, 'duration', 0)
                    if dur > 0:
                        self.media_mgr.seek(frac * dur)
                    self.queue_draw()
                    return True

                # 3. Check control buttons click -> Always responsive!
                btn_y = 185
                center_x = self.base_card_w / 2.0
                if abs(y - btn_y) <= 22:
                    # Shuffle (leftmost: center_x - 72)
                    if abs(x - (center_x - 72)) <= 16:
                        self.shuffle = self.media_mgr.toggle_shuffle()
                        self.queue_draw()
                        return True
                    # Previous (center_x - 36)
                    elif abs(x - (center_x - 36)) <= 16:
                        self.media_mgr.prev_track()
                        self.queue_draw()
                        return True
                    # Play / Pause (center_x)
                    elif abs(x - center_x) <= 22:
                        self.media_mgr.play_pause()
                        self.queue_draw()
                        return True
                    # Next (center_x + 36)
                    elif abs(x - (center_x + 36)) <= 16:
                        self.media_mgr.next_track()
                        self.queue_draw()
                        return True
                    # Repeat (rightmost: center_x + 72)
                    elif abs(x - (center_x + 72)) <= 16:
                        self.media_mgr.toggle_repeat()
                        self.repeat = getattr(self.media_mgr, "loop_status", "None") != "None"
                        self.queue_draw()
                        return True

            # 4. Dragging -> ONLY permitted when UNLOCKED!
            if not self.is_locked:
                self._dragging = True
                self._has_moved = False
                self._drag_start_x = event.x_root
                self._drag_start_y = event.y_root
                self._win_start_x = getattr(self, "_current_x", self.get_position()[0])
                self._win_start_y = getattr(self, "_current_y", self.get_position()[1])

                gdk_win = widget.get_window()
                if gdk_win:
                    display = Gdk.Display.get_default()
                    cursor = Gdk.Cursor.new_from_name(display, "grabbing")
                    if cursor:
                        gdk_win.set_cursor(cursor)
                return True
            else:
                # When locked, clicking the background does NOT accidentally move the widget
                return False

        elif event.button == 3:
            # Right-click -> Context Menu
            self._show_context_menu(event)
            return True

        return False

    def _on_motion_notify(self, widget, event):
        if self._resizing:
            dx = event.x_root - self._resize_start_x
            dy = event.y_root - self._resize_start_y
            delta = (dx + dy) / 2.0
            new_scale = self._resize_start_scale + (delta / 220.0)
            self.set_scale(new_scale, save=False)
            return True

        if self._dragging:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            if abs(dx) > 3 or abs(dy) > 3:
                self._has_moved = True
                self._current_x = int(self._win_start_x + dx)
                self._current_y = int(self._win_start_y + dy)
                self.move(self._current_x, self._current_y)
            return True

        # Interactive cursor hover feedback
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        x = unscaled_x - self.base_pad
        y = unscaled_y - self.base_pad
        center_x = self.base_card_w / 2.0

        is_hover_resize = not self.is_locked and self._is_over_resize_handle(unscaled_x, unscaled_y)
        if getattr(self, "layout_mode", "photo_vertical") == "photo_vertical":
            art_margin = 14.0
            art_size = self.base_card_w - 2 * art_margin
            meta_y = art_margin + art_size + 14.0
            lyr_w = 64.0
            lyr_h = 23.0
            lyr_x = art_margin + art_size - lyr_w
            lyr_y = meta_y + 3.0
            btn_y = meta_y + 60.0
            scrubber_y = btn_y + 42.0

            is_hover_lyrics = (lyr_x - 4) <= x <= (lyr_x + lyr_w + 4) and (lyr_y - 4) <= y <= (lyr_y + lyr_h + 4)
            is_hover_scrubber = abs(y - scrubber_y) <= 12 and 12 <= x <= (self.base_card_w - 12)
            is_hover_controls = abs(y - btn_y) <= 20 and abs(x - center_x) <= 75
        else:
            is_hover_lyrics = False
            is_hover_scrubber = abs(y - 130) <= 14 and 42 <= x <= (self.base_card_w - 42)
            is_hover_controls = abs(y - 185) <= 20 and abs(x - center_x) <= 90

        gdk_win = widget.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            if is_hover_resize:
                cursor_name = "se-resize"
            elif is_hover_lyrics or is_hover_scrubber or is_hover_controls:
                cursor_name = "pointer"
            elif not self.is_locked:
                cursor_name = "grab"
            else:
                cursor_name = "default"
            cursor = Gdk.Cursor.new_from_name(display, cursor_name)
            if cursor:
                gdk_win.set_cursor(cursor)

        return False

    def _on_button_release(self, widget, event):
        if event.button == 1:
            if self._resizing:
                self._resizing = False
                config.set("desktop_music_scale", self.scale)
                gdk_win = widget.get_window()
                if gdk_win:
                    display = Gdk.Display.get_default()
                    cursor_name = "default" if self.is_locked else "grab"
                    cursor = Gdk.Cursor.new_from_name(display, cursor_name)
                    if cursor:
                        gdk_win.set_cursor(cursor)
                return True

            if self._dragging:
                self._dragging = False
                gdk_win = widget.get_window()
                if gdk_win:
                    display = Gdk.Display.get_default()
                    cursor_name = "default" if self.is_locked else "grab"
                    cursor = Gdk.Cursor.new_from_name(display, cursor_name)
                    if cursor:
                        gdk_win.set_cursor(cursor)

                if getattr(self, "_has_moved", False):
                    config.set("desktop_music_x", int(self._current_x))
                    config.set("desktop_music_y", int(self._current_y))
                self._has_moved = False
                return True
        return False

    def _on_scroll(self, widget, event):
        """Scroll wheel zoom when unlocked and Ctrl is held or hovering corner."""
        if self.is_locked:
            return False

        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        ctrl_held = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        over_handle = self._is_over_resize_handle(unscaled_x, unscaled_y)

        if ctrl_held or over_handle:
            step = 0.05
            if event.direction == Gdk.ScrollDirection.UP:
                self.set_scale(self.scale + step)
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.set_scale(self.scale - step)
                return True
            elif event.direction == Gdk.ScrollDirection.SMOOTH:
                _, _, dy = event.get_scroll_deltas()
                if dy < 0:
                    self.set_scale(self.scale + step)
                    return True
                elif dy > 0:
                    self.set_scale(self.scale - step)
                    return True
        return False

    def _show_context_menu(self, event):
        from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item

        menu = create_mac_context_menu()

        # 1. Lock / Unlock State
        if self.is_locked:
            lock_item = create_mac_menu_item("lock.open", "Mở khóa Widget (Cho phép Di chuyển & Đổi kích thước)",
                                             lambda _: self.set_locked(False))
        else:
            lock_item = create_mac_menu_item("lock", "Khóa cố định Widget (Chống dịch chuyển)",
                                             lambda _: self.set_locked(True))
        menu.append(lock_item)

        # Global Lock / Unlock All Desktop Widgets
        all_locked = is_desktop_widgets_locked()
        all_label = "Mở khóa TẤT CẢ Widget trên màn hình" if all_locked else "Khóa cố định TẤT CẢ Widget"
        all_icon = "lock.open" if all_locked else "lock.all"
        lock_all = create_mac_menu_item(all_icon, all_label,
                                        lambda _: set_all_desktop_widgets_locked(not all_locked))
        menu.append(lock_all)

        menu.append(Gtk.SeparatorMenuItem())

        # 1.5. Layout Submenu (iOS Vertical like photo vs macOS classic square)
        layout_menu = create_mac_context_menu()
        layouts = [
            ("photo_vertical", "Thẻ dọc iOS (Theo ảnh mẫu)", "iphone"),
            ("classic", "Thẻ vuông macOS (Cổ điển)", "macbook"),
        ]
        cur_layout = getattr(self, "layout_mode", "photo_vertical")
        for l_mode, l_label, l_icon in layouts:
            chk = (cur_layout == l_mode)
            item = create_mac_menu_item(l_icon, l_label, lambda _, m=l_mode: self.set_layout_mode(m), is_checked=chk)
            layout_menu.append(item)
        menu.append(create_mac_menu_item("layout", "Bố cục hiển thị (Layout)", submenu=layout_menu))

        # 2. Size Presets Submenu
        size_menu = create_mac_context_menu()
        presets = [
            ("Nhỏ (Mini - 80%)", 0.80),
            ("Tiêu chuẩn (Vừa - 100%)", 1.00),
            ("Lớn (Rộng - 125%)", 1.25),
            ("Cực lớn (To - 150%)", 1.50),
        ]
        for label, s_val in presets:
            chk = (abs(self.scale - s_val) < 0.04)
            item = create_mac_menu_item(None, label, lambda _, s=s_val: self.set_scale(s), is_checked=chk)
            size_menu.append(item)

        size_menu.append(Gtk.SeparatorMenuItem())
        reset_size = create_mac_menu_item("reset", "Đặt lại kích thước mặc định (100%)", lambda _: self.set_scale(1.00))
        size_menu.append(reset_size)
        menu.append(create_mac_menu_item("size", "Kích thước (Size)", submenu=size_menu))

        # 3. Theme Submenu
        theme_menu = create_mac_context_menu()
        themes = [
            ("auto", "Tự động theo hệ thống (Auto)", "auto"),
            ("light", "Giao diện Sáng (Light Glass)", "sun.max"),
            ("dark", "Giao diện Tối (Dark Glass)", "moon.fill"),
        ]
        for t_mode, t_label, t_icon in themes:
            chk = (self.theme_mode == t_mode)
            item = create_mac_menu_item(t_icon, t_label, lambda _, m=t_mode: self._set_theme(m), is_checked=chk)
            theme_menu.append(item)
        menu.append(create_mac_menu_item("theme", "Giao diện (Theme)", submenu=theme_menu))

        # 4. Animation Replay
        menu.append(create_mac_menu_item("sparkles", "Phát lại hiệu ứng mở (Replay Open Effect)",
                                         lambda _: self.play_open_animation()))

        menu.append(Gtk.SeparatorMenuItem())

        # 5. Pin / Keep Below
        pin_label = "Ghim Nền Desktop (Keep Below)" if not self.keep_below else "Nổi Trên Cửa Sổ (Keep Above)"
        pin_icon = "pin" if not self.keep_below else "pin.slash"
        menu.append(create_mac_menu_item(pin_icon, pin_label, self._toggle_keep_below))

        # 6. Reset Position
        menu.append(create_mac_menu_item("reset", "Đặt lại vị trí ban đầu", self._reset_position))

        menu.append(Gtk.SeparatorMenuItem())

        # 7. Hide
        menu.append(create_mac_menu_item("xmark", "Ẩn Widget Âm Nhạc", lambda _: self.hide_widget(), is_destructive=True))

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def set_layout_mode(self, mode):
        self.layout_mode = mode
        config.set("desktop_music_layout", mode)
        if mode == "photo_vertical":
            self.base_card_w = 236.0
            self.base_card_h = 380.0
            self.base_radius = 28.0
        else:
            self.base_card_w = 236.0
            self.base_card_h = 246.0
            self.base_radius = 26.0
        self.base_total_w = self.base_card_w + 2 * self.base_pad
        self.base_total_h = self.base_card_h + 2 * self.base_pad
        self.total_w = max(100, int(self.base_total_w * self.scale))
        self.total_h = max(100, int(self.base_total_h * self.scale))
        self.set_size_request(self.total_w, self.total_h)
        self.resize(self.total_w, self.total_h)
        self.queue_draw()

    def _set_theme(self, mode):
        config.set("desktop_music_theme", mode)
        self.theme_mode = mode
        self._update_dark_mode_state()
        self.queue_draw()

    def _reset_position(self, _):
        self.move(80, 310)
        config.set("desktop_music_x", 80)
        config.set("desktop_music_y", 310)

    def _toggle_keep_below(self, _):
        self.keep_below = not self.keep_below
        if self.keep_below:
            self.set_keep_below(True)
            self.set_keep_above(False)
        else:
            self.set_keep_below(False)
            self.set_keep_above(True)

    def hide_widget(self):
        config.set("enable_desktop_music", False)
        self.hide()
        if self.on_close:
            self.on_close()

    def show_widget(self):
        config.set("enable_desktop_music", True)
        self.show_all()
        if getattr(self, "keep_below", True):
            self.set_keep_below(True)
        self.play_open_animation()

    def destroy(self):
        unregister_widget(self)
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        if self._anim_timer_id:
            GLib.source_remove(self._anim_timer_id)
            self._anim_timer_id = None
        super().destroy()


if __name__ == "__main__":
    from src.modules.media import MediaManager
    mm = MediaManager()
    win = DesktopMusicWidget(mm)
    win.connect("destroy", Gtk.main_quit)
    win.show_widget()
    Gtk.main()
