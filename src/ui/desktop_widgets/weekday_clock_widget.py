"""
Desktop Weekday Typography Clock Widget for Ubuntu Linux.
Displays large, wide-spaced futuristic typography:
    F R I D A Y
  25 APRIL, 2025.
     - 10:19 -
Guaranteed 100% REAL live system time updating dynamically every second.
Features:
- Apple spring-expand opening animation (0.52 -> 1.0 with fluid physics)
- Movable & resizable with position memory
- Lock/unlock desktop pinning
- Language selection (English / Vietnamese / Bilingual)
- Aesthetic glow presets (Minimal White, Anime Red Glow, Cyber Cyan, Luxury Gold)
- Background modes (Pure Transparent Wallpaper Overlay vs Frosted Glass Card)
- Context menu with animation replay and live customization
"""

import os
import math
import time
import datetime
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo

from src.config import config
from src.animator import SpringValue
from src.ui.desktop_widgets import (
    register_widget,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)
from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item

# Auto-register Anurati font with Fontconfig for Pango
try:
    import ctypes
    _app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    _anurati_path = os.path.join(_app_root, "assets", "fonts", "Anurati-Regular.otf")
    if os.path.exists(_anurati_path):
        _libfc = ctypes.cdll.LoadLibrary("libfontconfig.so.1")
        _libfc.FcConfigAppFontAddFile(None, _anurati_path.encode("utf-8"))
except Exception:
    pass


class DesktopWeekdayClockWidget(Gtk.Window):
    def __init__(self, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_close = on_close

        register_widget(self)
        self.is_locked = config.get("lock_desktop_widgets", True)

        # Base geometry - ample width for "W E D N E S D A Y" in Anurati
        self.base_card_w = 420.0
        self.base_card_h = 136.0
        self.base_pad = 16.0
        self.base_radius = 24.0
        self.base_total_w = self.base_card_w + 2 * self.base_pad
        self.base_total_h = self.base_card_h + 2 * self.base_pad

        # Scale factor
        raw_scale = config.get("desktop_weekday_scale", 1.0)
        try:
            self.scale = max(0.65, min(2.2, round(float(raw_scale), 2)))
        except Exception:
            self.scale = 1.0

        self.total_w = max(120, int(self.base_total_w * self.scale))
        self.total_h = max(80, int(self.base_total_h * self.scale))

        self.keep_below = True

        # Customization modes
        # lang_mode: 'en', 'vi', 'dual'
        self.lang_mode = config.get("desktop_weekday_lang", "en")
        # style_theme: 'white', 'anime_red', 'cyber_cyan', 'gold'
        self.style_theme = config.get("desktop_weekday_theme", "white")
        # bg_mode: 'transparent', 'frosted'
        self.bg_mode = config.get("desktop_weekday_bg", "transparent")
        # show_seconds: bool
        self.show_seconds = config.get("desktop_weekday_show_sec", False)

        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
        except Exception:
            self.dark_mode = True

        # Spring Open Animation
        self.anim_scale = SpringValue(1.0, stiffness=260.0, damping=19.0)
        self.anim_alpha = SpringValue(1.0, stiffness=220.0, damping=21.0)
        self._anim_timer_id = None
        self._anim_last_time = 0.0

        # Window properties
        self.set_title("macOS Weekday Typography Widget")
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
        self.set_wmclass("desktop-widget-weekday", "DesktopWidgetWeekday")
        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)

        # RGBA transparent visual
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        # Position window from config (default centered around top: x=580, y=177)
        self._current_x = int(config.get("desktop_weekday_x", 580))
        self._current_y = int(config.get("desktop_weekday_y", 177))
        self.move(self._current_x, self._current_y)

        # Dragging state
        self._dragging = False
        self._has_moved = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = self._current_x
        self._win_start_y = self._current_y

        # Resizing state
        self._resizing = False
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_scale = 1.0

        # Events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("scroll-event", self._on_scroll)
        self.connect("map-event", self._on_map_event)

        # Timer for live real-time clock updates (every 500ms)
        self._tick_timer_id = GLib.timeout_add(500, self._on_tick)

    def set_locked(self, locked: bool):
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

    def _on_tick(self):
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def set_scale(self, new_scale, save=True):
        new_scale = max(0.65, min(2.2, round(float(new_scale), 2)))
        self.scale = new_scale
        if save:
            config.set("desktop_weekday_scale", self.scale)

        self.total_w = max(120, int(self.base_total_w * self.scale))
        self.total_h = max(80, int(self.base_total_h * self.scale))
        self.set_size_request(self.total_w, self.total_h)
        self.resize(self.total_w, self.total_h)
        self.queue_draw()

    def set_lang_mode(self, lang):
        if lang in ("en", "vi", "dual"):
            self.lang_mode = lang
            config.set("desktop_weekday_lang", lang)
            self.queue_draw()

    def set_style_theme(self, theme):
        if theme in ("white", "anime_red", "cyber_cyan", "gold"):
            self.style_theme = theme
            config.set("desktop_weekday_theme", theme)
            self.queue_draw()

    def set_bg_mode(self, bg):
        if bg in ("transparent", "frosted"):
            self.bg_mode = bg
            config.set("desktop_weekday_bg", bg)
            self.queue_draw()

    def toggle_show_seconds(self):
        self.show_seconds = not self.show_seconds
        config.set("desktop_weekday_show_sec", self.show_seconds)
        self.queue_draw()

    def _path_rounded_rect(self, cr, x, y, w, h, r):
        r = min(r, w / 2.0, h / 2.0)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw_resize_grip(self, cr, rx, ry):
        cr.save()
        grip_color = (0.23, 0.51, 0.96, 0.90) if not self.is_locked else (1.0, 1.0, 1.0, 0.35)
        cr.set_source_rgba(*grip_color)
        cr.set_line_width(1.8)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for offset in (6, 11, 16):
            cr.move_to(rx - offset, ry - 3)
            cr.line_to(rx - 3, ry - offset)
            cr.stroke()
        cr.restore()

    def _is_over_resize_handle(self, unscaled_x, unscaled_y):
        rx = self.base_pad + self.base_card_w
        ry = self.base_pad + self.base_card_h
        return (rx - 26 <= unscaled_x <= rx + 8) and (ry - 26 <= unscaled_y <= ry + 8)

    def _get_time_strings(self):
        now = datetime.datetime.now()

        # 1. Day of Week
        en_days = ["M O N D A Y", "T U E S D A Y", "W E D N E S D A Y", "T H U R S D A Y", "F R I D A Y", "S A T U R D A Y", "S U N D A Y"]
        vi_days = ["T H Ứ   H A I", "T H Ứ   B A", "T H Ứ   T Ư", "T H Ứ   N Ă M", "T H Ứ   S Á U", "T H Ứ   B Ả Y", "C H Ủ   N H Ậ T"]
        idx = now.weekday()

        if self.lang_mode == "vi":
            weekday_str = vi_days[idx]
        elif self.lang_mode == "dual":
            weekday_str = f"{en_days[idx]}  •  {vi_days[idx]}"
        else:
            weekday_str = en_days[idx]

        # 2. Date
        en_months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
        vi_months = ["THÁNG 1", "THÁNG 2", "THÁNG 3", "THÁNG 4", "THÁNG 5", "THÁNG 6", "THÁNG 7", "THÁNG 8", "THÁNG 9", "THÁNG 10", "THÁNG 11", "THÁNG 12"]

        if self.lang_mode == "vi":
            date_str = f"{now.day:02d} {vi_months[now.month - 1]}, {now.year}."
        else:
            date_str = f"{now.day:02d} {en_months[now.month - 1]}, {now.year}."

        # 3. Time
        if self.show_seconds:
            time_str = f"- {now.hour:02d}:{now.minute:02d}:{now.second:02d} -"
        else:
            time_str = f"- {now.hour:02d}:{now.minute:02d} -"

        return weekday_str, date_str, time_str

    def _get_theme_palette(self):
        if self.style_theme == "anime_red":
            # Fiery red neon anime glow (as in reference wallpaper)
            return {
                "day": (1.0, 0.28, 0.35, 1.0),
                "day_glow": (0.95, 0.15, 0.25, 0.55),
                "date": (1.0, 0.88, 0.90, 0.95),
                "time": (0.95, 0.55, 0.65, 0.90),
            }
        elif self.style_theme == "cyber_cyan":
            # High-tech sci-fi cyan glow
            return {
                "day": (0.25, 0.88, 1.0, 1.0),
                "day_glow": (0.12, 0.65, 0.95, 0.55),
                "date": (0.85, 0.96, 1.0, 0.95),
                "time": (0.45, 0.80, 0.95, 0.90),
            }
        elif self.style_theme == "gold":
            # Luxurious Apple champagne gold
            return {
                "day": (1.0, 0.84, 0.42, 1.0),
                "day_glow": (0.95, 0.72, 0.25, 0.50),
                "date": (1.0, 0.95, 0.82, 0.95),
                "time": (0.92, 0.82, 0.58, 0.90),
            }
        else:
            # Minimal Pure White with crisp contrast shadow
            return {
                "day": (1.0, 1.0, 1.0, 1.0),
                "day_glow": (1.0, 1.0, 1.0, 0.40),
                "date": (0.94, 0.96, 0.98, 0.92),
                "time": (0.78, 0.82, 0.88, 0.88),
            }

    def _on_draw(self, widget, cr):
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

        # Spring expansion
        cr.translate(cx, cy)
        cr.scale(open_scale, open_scale)
        cr.translate(-cx, -cy)

        # Scale coordinates
        cr.scale(self.scale, self.scale)

        use_group = (open_alpha < 0.999)
        if use_group:
            cr.push_group()

        x = self.base_pad
        y = self.base_pad
        w = self.base_card_w
        h = self.base_card_h
        r = self.base_radius

        # Optional frosted glass backdrop if requested (Translucent - wallpaper visible)
        if self.bg_mode == "frosted":
            # Glass card
            self._path_rounded_rect(cr, x, y, w, h, r)
            cr.save()
            cr.clip()

            base_pat = cairo.LinearGradient(x, y, x, y + h)
            base_pat.add_color_stop_rgba(0.0, 0.08, 0.09, 0.12, 0.88)
            base_pat.add_color_stop_rgba(1.0, 0.05, 0.06, 0.08, 0.92)
            cr.set_source(base_pat)
            cr.paint()

            # Specular top highlight
            sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
            sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.06)
            sheen.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.01)
            sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
            cr.set_source(sheen)
            cr.paint()
            cr.restore()

            # Subtle Glass Rim (Crisp and razor-sharp, no blurry outline)
            self._path_rounded_rect(cr, x, y, w, h, r)
            rim = cairo.LinearGradient(x, y, x, y + h)
            rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.10)
            rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.04)
            rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.06)
            cr.set_source(rim)
            cr.set_line_width(0.8)
            cr.stroke()

        # Edit mode highlight
        if not self.is_locked:
            cr.save()
            self._path_rounded_rect(cr, x, y, w, h, r)
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.65)
            cr.set_line_width(1.8)
            cr.stroke()
            cr.restore()

        # Get strings & palette
        weekday_str, date_str, time_str = self._get_time_strings()
        palette = self._get_theme_palette()

        center_x = x + w / 2.0

        # Set antialiasing to GRAY to prevent LCD subpixel chromatic color fringes on transparent background
        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_GRAY)
        fo.set_hint_style(cairo.HINT_STYLE_SLIGHT)
        cr.set_font_options(fo)

        # Create Pango layout
        pctx = widget.get_pango_context()
        PangoCairo.context_set_font_options(pctx, fo)

        # 1. Draw Weekday in iconic Anurati font ("F R I D A Y")
        layout_day = Pango.Layout(pctx)
        font_desc_day = Pango.FontDescription.from_string("Anurati 30")
        layout_day.set_font_description(font_desc_day)
        layout_day.set_text(weekday_str, -1)
        layout_day.set_alignment(Pango.Alignment.CENTER)
        dw, dh = layout_day.get_pixel_size()

        day_x = center_x - dw / 2.0
        day_y = y + 14.0

        # Ambient soft text shadow for perfect legibility on any wallpaper
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
        cr.move_to(day_x, day_y + 1.8)
        PangoCairo.show_layout(cr, layout_day)
        cr.restore()

        # Sharp foreground text
        cr.save()
        cr.set_source_rgba(*palette["day"])
        cr.move_to(day_x, day_y)
        PangoCairo.show_layout(cr, layout_day)
        cr.restore()

        # 2. Draw Date ("24 SEPTEMBER, 2026.")
        layout_date = Pango.Layout(pctx)
        font_desc_date = Pango.FontDescription.from_string("Inter, Montserrat, Outfit, Sans 13")
        layout_date.set_font_description(font_desc_date)
        layout_date.set_text(date_str, -1)
        layout_date.set_alignment(Pango.Alignment.CENTER)
        date_w, date_h = layout_date.get_pixel_size()

        date_x = center_x - date_w / 2.0
        date_y = day_y + dh + 10.0

        # Subtle dark backdrop shadow
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
        cr.move_to(date_x, date_y + 1.2)
        PangoCairo.show_layout(cr, layout_date)
        cr.restore()

        cr.save()
        cr.set_source_rgba(*palette["date"])
        cr.move_to(date_x, date_y)
        PangoCairo.show_layout(cr, layout_date)
        cr.restore()

        # 3. Draw Time ("- 10:19 -")
        layout_time = Pango.Layout(pctx)
        font_desc_time = Pango.FontDescription.from_string("Inter, Montserrat, Outfit, Sans 11")
        layout_time.set_font_description(font_desc_time)
        layout_time.set_text(time_str, -1)
        layout_time.set_alignment(Pango.Alignment.CENTER)
        tw, th = layout_time.get_pixel_size()

        time_x = center_x - tw / 2.0
        time_y = date_y + date_h + 8.0

        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
        cr.move_to(time_x, time_y + 1.0)
        PangoCairo.show_layout(cr, layout_time)
        cr.restore()

        cr.save()
        cr.set_source_rgba(*palette["time"])
        cr.move_to(time_x, time_y)
        PangoCairo.show_layout(cr, layout_time)
        cr.restore()

        # 4. Corner Resize Grip (Only shown when unlocked)
        if not self.is_locked:
            self._draw_resize_grip(cr, x + w, y + h)

        if use_group:
            cr.pop_group_to_source()
            cr.paint_with_alpha(open_alpha)

        cr.restore()
        return False

    def _on_button_press(self, widget, event):
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale

        if event.button == 1:
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

        elif event.button == 3:
            self._show_context_menu(event)
            return True
        return False

    def _on_motion_notify(self, widget, event):
        if self._resizing:
            dx = event.x_root - self._resize_start_x
            dy = event.y_root - self._resize_start_y
            delta = (dx + dy) / 2.0
            new_scale = self._resize_start_scale + (delta / 240.0)
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

        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        is_hover_resize = not self.is_locked and self._is_over_resize_handle(unscaled_x, unscaled_y)
        gdk_win = widget.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            if is_hover_resize:
                cursor_name = "se-resize"
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
                config.set("desktop_weekday_scale", self.scale)
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

                if self._has_moved:
                    config.set("desktop_weekday_x", int(self._current_x))
                    config.set("desktop_weekday_y", int(self._current_y))
                self._has_moved = False
                return True
        return False

    def _on_scroll(self, widget, event):
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
        menu = create_mac_context_menu()

        # 1. Lock / Unlock State
        if self.is_locked:
            lock_item = create_mac_menu_item("lock.open", "Mở khóa Widget (Cho phép Di chuyển & Đổi kích thước)",
                                              lambda _: self.set_locked(False))
        else:
            lock_item = create_mac_menu_item("lock", "Khóa cố định Widget (Chống dịch chuyển)",
                                              lambda _: self.set_locked(True))
        menu.append(lock_item)

        all_locked = is_desktop_widgets_locked()
        all_label = "Mở khóa TẤT CẢ Widget trên màn hình" if all_locked else "Khóa cố định TẤT CẢ Widget"
        lock_all = create_mac_menu_item("lock.all", all_label,
                                        lambda _: set_all_desktop_widgets_locked(not all_locked))
        menu.append(lock_all)

        menu.append(Gtk.SeparatorMenuItem())

        # 2. Language Submenu
        lang_menu = create_mac_context_menu()
        lang_item = create_mac_menu_item("globe", "Kiểu ngôn ngữ (Language)", submenu=lang_menu)

        lang_opts = [
            ("Tiếng Anh (F R I D A Y)", "en"),
            ("Tiếng Việt (T H Ứ   S Á U)", "vi"),
            ("Song ngữ (FRIDAY • THỨ SÁU)", "dual"),
        ]
        for label, code in lang_opts:
            is_active = (self.lang_mode == code)
            m_item = create_mac_menu_item("globe", label, lambda _, c=code: self.set_lang_mode(c), is_checked=is_active)
            lang_menu.append(m_item)
        menu.append(lang_item)

        # 3. Theme Glow Submenu
        theme_menu = create_mac_context_menu()
        theme_item = create_mac_menu_item("paintpalette", "Màu sắc & Hiệu ứng Glow", submenu=theme_menu)

        theme_opts = [
            ("Trắng Cyber tinh tế (Minimal White)", "white", (0.92, 0.94, 0.98)),
            ("Đỏ Lửa Anime (Anime Red Glow)", "anime_red", (1.0, 0.27, 0.23)),
            ("Xanh Neon Tương Lai (Cyber Cyan)", "cyber_cyan", (0.0, 0.88, 1.0)),
            ("Vàng Hoàng Gia Apple (Luxury Gold)", "gold", (1.0, 0.84, 0.04)),
        ]
        for label, t_code, col in theme_opts:
            is_active = (self.style_theme == t_code)
            t_item = create_mac_menu_item("circle.fill", label, lambda _, t=t_code: self.set_style_theme(t),
                                          is_checked=is_active, icon_color=col)
            theme_menu.append(t_item)
        menu.append(theme_item)

        # 4. Background Mode Submenu
        bg_menu = create_mac_context_menu()
        bg_item = create_mac_menu_item("rectangle", "Kiểu nền (Background)", submenu=bg_menu)

        bg_opts = [
            ("Trong suốt hoà cùng hình nền (Wallpaper Overlay)", "transparent"),
            ("Kính mờ macOS (Frosted Glass Card)", "frosted"),
        ]
        for label, b_code in bg_opts:
            is_active = (self.bg_mode == b_code)
            b_item = create_mac_menu_item("rectangle", label, lambda _, b=b_code: self.set_bg_mode(b), is_checked=is_active)
            bg_menu.append(b_item)
        menu.append(bg_item)

        # Toggle seconds
        sec_item = create_mac_menu_item("stopwatch", "Hiển thị giây",
                                         lambda _: self.toggle_show_seconds(), is_checked=self.show_seconds)
        menu.append(sec_item)

        menu.append(Gtk.SeparatorMenuItem())

        # 5. Size Submenu
        size_menu = create_mac_context_menu()
        size_item = create_mac_menu_item("size", "Kích thước (Size)", submenu=size_menu)

        presets = [
            ("Nhỏ (Mini - 80%)", 0.80),
            ("Tiêu chuẩn (Vừa - 100%)", 1.00),
            ("Lớn (Rộng - 125%)", 1.25),
            ("Cực lớn (To - 150%)", 1.50),
        ]
        for label, s_val in presets:
            is_active = (abs(self.scale - s_val) < 0.04)
            p_item = create_mac_menu_item("size", label, lambda _, s=s_val: self.set_scale(s), is_checked=is_active)
            size_menu.append(p_item)

        size_menu.append(Gtk.SeparatorMenuItem())
        reset_size = create_mac_menu_item("reset", "Đặt lại kích thước mặc định (100%)",
                                          lambda _: self.set_scale(1.00))
        size_menu.append(reset_size)
        menu.append(size_item)

        # Open animation replay
        anim_item = create_mac_menu_item("sparkles", "Phát lại hiệu ứng mở (Replay Open)",
                                         lambda _: self.play_open_animation())
        menu.append(anim_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Reset Position
        reset_pos = create_mac_menu_item("dot.circle", "Đặt lại vị trí ban đầu (Giữa màn hình)",
                                         lambda _: self._reset_position())
        menu.append(reset_pos)

        menu.append(Gtk.SeparatorMenuItem())

        hide_item = create_mac_menu_item("xmark", "Ẩn widget này",
                                         lambda _: self.hide_widget(), is_destructive=True)
        menu.append(hide_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def _reset_position(self):
        self.move(790, 260)
        config.set("desktop_weekday_x", 790)
        config.set("desktop_weekday_y", 260)

    def show_widget(self):
        self.show_all()
        self.set_keep_below(True)
        config.set("enable_desktop_weekday", True)
        self.play_open_animation()

    def hide_widget(self):
        self.hide()
        config.set("enable_desktop_weekday", False)
        if self.on_close:
            self.on_close()

    def destroy(self):
        unregister_widget(self)
        if self._anim_timer_id:
            GLib.source_remove(self._anim_timer_id)
            self._anim_timer_id = None
        if self._tick_timer_id:
            GLib.source_remove(self._tick_timer_id)
            self._tick_timer_id = None
        super().destroy()
