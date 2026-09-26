"""
Apple macOS Desktop Weather Widget.
Displays Location, Big Current Temperature, High/Low range,
Precipitation forecast, and Wind Speed on a translucent frosted sky-blue glass card.
"""

import math
import random
import datetime
import cairo
import threading
import time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo
from src.config import config
from src.animator import SpringValue
from src.modules.weather import WeatherManager
from src.utils.i18n import t, get_current_language, add_language_listener
from src.ui.desktop_widgets import (
    register_widget,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)
from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item

class DesktopWeatherWidget(Gtk.Window):
    def __init__(self, weather_mgr=None, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_close = on_close
        self.weather_mgr = weather_mgr or WeatherManager(on_update=self._on_weather_update)

        self.card_w = 175
        self.card_h = 175
        self.pad = 12
        self.total_w = self.card_w + 2 * self.pad
        self.total_h = self.card_h + 2 * self.pad
        self.radius = 26.0

        self.keep_below = True
        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
        except Exception:
            self.dark_mode = False

        # Window setup
        self.set_title("macOS Weather Widget")
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
        self.set_wmclass("desktop-widget-weather", "DesktopWidgetWeather")
        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

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
        self.get_style_context().add_class("desktop-widget-weather")

        # Position window from config
        self._current_x = int(config.get("desktop_weather_x", 380))
        self._current_y = int(config.get("desktop_weather_y", 70))
        self.move(self._current_x, self._current_y)

        # Spring Open Animation
        self.anim_scale = SpringValue(1.0, stiffness=260.0, damping=19.0)
        self.anim_alpha = SpringValue(1.0, stiffness=220.0, damping=21.0)
        self._anim_timer_id = None
        self._anim_last_time = 0.0

        # Events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )

        register_widget(self)
        self.is_locked = config.get("lock_desktop_widgets", True)

        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = self._current_x
        self._win_start_y = self._current_y

        self._has_moved = False
        self._location_dialog = None

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("map-event", self._on_map_event)

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

    def set_locked(self, locked: bool):
        """Locks or unlocks weather widget movement."""
        self.is_locked = bool(locked)
        self._dragging = False
        gdk_win = self.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            cursor_name = "default" if self.is_locked else "grab"
            cursor = Gdk.Cursor.new_from_name(display, cursor_name)
            if cursor:
                gdk_win.set_cursor(cursor)
        self.queue_draw()

    def _on_weather_update(self):
        self.queue_draw()

    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self.queue_draw)

    def _on_system_theme_changed(self, *args):
        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
            self.queue_draw()
        except Exception:
            pass

    def _path_rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    _draw_squircle = _path_rounded_rect

    def _draw_text(self, cr, x, y, text, font_desc_str, color, align="left", max_width=None):
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription(font_desc_str)
        layout.set_font_description(desc)
        if max_width is not None:
            layout.set_width(int(max_width * Pango.SCALE))
            layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_text(text, -1)

        ink_rect, log_rect = layout.get_pixel_extents()
        tw = log_rect.width

        if align == "center":
            draw_x = x - tw / 2.0
        elif align == "right":
            draw_x = x - tw
        else:
            draw_x = x

        cr.set_source_rgba(*color)
        cr.move_to(draw_x, y)
        PangoCairo.show_layout(cr, layout)

    def _on_draw(self, widget, cr):
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        open_scale = max(0.01, self.anim_scale.current)
        open_alpha = max(0.0, min(1.0, self.anim_alpha.current))
        if open_alpha <= 0.001:
            return False

        win_w = widget.get_allocated_width()
        win_h = widget.get_allocated_height()
        mid_x = win_w / 2.0
        mid_y = win_h / 2.0

        cr.save()
        cr.translate(mid_x, mid_y)
        cr.scale(open_scale, open_scale)
        cr.translate(-mid_x, -mid_y)

        use_group = (open_alpha < 0.999)
        if use_group:
            cr.push_group()

        x = self.pad
        y = self.pad
        w = self.card_w
        h = self.card_h
        r = self.radius

        # 1. Apple Weather Frosted Card Background (Translucent - wallpaper shows through)
        self._path_rounded_rect(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        pat = cairo.LinearGradient(x, y, x, y + h)
        pat.add_color_stop_rgba(0.0, 0.08, 0.12, 0.20, 0.35)
        pat.add_color_stop_rgba(1.0, 0.04, 0.06, 0.12, 0.42)
        cr.set_source(pat)
        cr.paint()

        # Specular top highlight
        sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
        sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.14)
        sheen.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.02)
        sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(sheen)
        cr.paint()

        cr.restore()

        # 2. Subtle glass rim (Subtle and razor-sharp, no blurry outline)
        self._path_rounded_rect(cr, x, y, w, h, r)
        rim = cairo.LinearGradient(x, y, x, y + h)
        rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.22)
        rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.08)
        rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.12)
        cr.set_source(rim)
        cr.set_line_width(0.8)
        cr.stroke()

        # Unlocked Edit Mode Highlight
        if not getattr(self, "is_locked", True):
            cr.save()
            self._path_rounded_rect(cr, x, y, w, h, r)
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.65)
            cr.set_line_width(2.0)
            cr.stroke()
            cr.restore()

        wm = self.weather_mgr

        # -------------------------------------------------------------
        # Header: City Name ↗ (Left) & Weather Condition Icon (Right)
        # -------------------------------------------------------------
        custom_cfg = config.get("weather_city", "").strip()
        if custom_cfg and custom_cfg.lower() not in ("auto", "tự động", "hiện tại"):
            raw_city = custom_cfg
        else:
            raw_city = getattr(wm, "district", "").strip() or getattr(wm, "city", "").strip() or getattr(wm, "province", "").strip() or getattr(wm, "ward", "").strip() or t("weather_title", "Thời tiết")

        for prefix in ("Thành phố ", "TP. ", "Huyện ", "Quận ", "Thị xã ", "Tỉnh ", "Phường ", "Xã "):
            if raw_city.lower().startswith(prefix.lower()):
                raw_city = raw_city[len(prefix):].strip()
                break

        header_text = f"{raw_city} ↗"
        self._draw_text(cr, x + 16, y + 15, header_text, "-apple-system, Inter, Ubuntu Bold 12", (1.0, 1.0, 1.0, 0.95), align="left", max_width=w - 32 - 28)

        # Condition Emoji Icon (Day/Night & Condition Aware)
        desc_lower = (getattr(wm, "desc", "") or "").lower()
        icon_t = getattr(wm, "icon_type", "")
        now_hour = datetime.datetime.now().hour
        is_night = now_hour < 6 or now_hour >= 18

        if "dông" in desc_lower or icon_t == "storm":
            cond_icon = "⛈️"
        elif "mưa" in desc_lower or icon_t == "rain":
            cond_icon = "🌧️"
        elif icon_t == "moon" or (is_night and ("quang" in desc_lower or "nắng" in desc_lower)):
            cond_icon = "🌙"
        elif is_night and "mây" in desc_lower:
            cond_icon = "☁️"
        elif "nắng" in desc_lower or "quang" in desc_lower or icon_t == "sun":
            cond_icon = "☀️"
        else:
            cond_icon = "⛅"
        self._draw_text(cr, x + w - 16, y + 14, cond_icon, "-apple-system, Inter, Ubuntu 14", (1.0, 1.0, 1.0, 1.0), align="right")

        # -------------------------------------------------------------
        # Temperature Section: Big "26°" and High/Low
        # -------------------------------------------------------------
        temp_str = f"{wm.temp}°"
        self._draw_text(cr, x + 16, y + 36, temp_str, "-apple-system, Inter, Ubuntu Semi-Bold 38", (1.0, 1.0, 1.0, 1.0), align="left")

        # High/Low indicators with clear spacing and localized labels
        high_lbl = t("weather_high_short", "C")
        low_lbl = t("weather_low_short", "T")
        hl_str = t("weather_hl_format", "{high_lbl}: {high}°\n{low_lbl}: {low}°",
                   high_lbl=high_lbl, low_lbl=low_lbl, high=wm.temp_high, low=wm.temp_low)
        self._draw_text(cr, x + w - 16, y + 42, hl_str, "-apple-system, Inter, Ubuntu Medium 10", (1.0, 1.0, 1.0, 0.90), align="right")

        # -------------------------------------------------------------
        # Section 3: Condition text
        # -------------------------------------------------------------
        cond_text = getattr(wm, "desc", "") or "Có mây"
        self._draw_text(cr, x + 16, y + 90, cond_text, "-apple-system, Inter, Ubuntu Medium 11", (1.0, 1.0, 1.0, 0.95), align="left", max_width=w - 32)

        # -------------------------------------------------------------
        # Section 4: Metrics (Rain on left, Wind on right - Separated non-overlapping columns)
        # -------------------------------------------------------------
        metrics_y = y + 116
        col1_x = x + 16
        col2_x = x + w - 16

        # Column 1: Lượng mưa (Precipitation) - Left aligned
        self._draw_text(cr, col1_x, metrics_y, t("weather_precipitation", "Lượng mưa"), "-apple-system, Inter, Ubuntu Medium 9", (0.85, 0.92, 1.0, 0.75), align="left")

        p_val = getattr(wm, "precipitation_24h", "0.0 mm")
        try:
            p_num = float(p_val.replace("mm", "").strip())
        except Exception:
            p_num = 0.0

        if p_num >= 0.1:
            rain_str = f"🌧️ {p_num:.1f} mm" if p_num < 10 else f"🌧️ {int(round(p_num))} mm"
        else:
            rain_str = "💧 0 mm"
        self._draw_text(cr, col1_x, metrics_y + 16, rain_str, "-apple-system, Inter, Ubuntu Semi-Bold 9.5", (1.0, 1.0, 1.0, 0.95), align="left", max_width=74)

        # Column 2: Gió (Wind) - Right aligned
        self._draw_text(cr, col2_x, metrics_y, t("weather_wind", "Gió"), "-apple-system, Inter, Ubuntu Medium 9", (0.85, 0.92, 1.0, 0.75), align="right")
        wind_str = f"💨 {wm.wind_speed} km/h"
        self._draw_text(cr, col2_x, metrics_y + 16, wind_str, "-apple-system, Inter, Ubuntu Semi-Bold 9.5", (1.0, 1.0, 1.0, 0.95), align="right", max_width=66)

        if use_group:
            cr.pop_group_to_source()
            cr.paint_with_alpha(open_alpha)
        cr.restore()
        return False

    def _on_button_press(self, widget, event):
        if event.button == 1:
            if not getattr(self, "is_locked", True):
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
                self._on_widget_clicked()
                return True
        elif event.button == 3:
            self._show_context_menu(event)
            return True
        return False

    def _on_motion_notify(self, widget, event):
        if self._dragging:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            if abs(dx) > 3 or abs(dy) > 3:
                self._has_moved = True
                self._current_x = int(self._win_start_x + dx)
                self._current_y = int(self._win_start_y + dy)
                self.move(self._current_x, self._current_y)
            return True
        return False

    def _on_button_release(self, widget, event):
        if event.button == 1 and self._dragging:
            self._dragging = False
            gdk_win = widget.get_window()
            if gdk_win:
                display = Gdk.Display.get_default()
                cursor = Gdk.Cursor.new_from_name(display, "grab")
                if cursor:
                    gdk_win.set_cursor(cursor)
            if self._has_moved:
                config.set("desktop_weather_x", int(self._current_x))
                config.set("desktop_weather_y", int(self._current_y))
            else:
                self._on_widget_clicked()
            self._has_moved = False
            return True
        return False

    def _on_widget_clicked(self):
        import time
        if time.time() - getattr(self, "_last_closed_time", 0) < 0.35:
            return
        if self._location_dialog and self._location_dialog.get_visible():
            self._location_dialog.destroy()
            self._location_dialog = None
            return
        self._location_dialog = WeatherLocationDialog(self, self.weather_mgr)
        self._location_dialog.show_all()
        self._location_dialog.present()

    def _show_context_menu(self, event):
        menu = create_mac_context_menu()

        # 1. Lock / Unlock State
        if getattr(self, "is_locked", True):
            lock_item = create_mac_menu_item("lock.open", t("widget_unlock", "Mở khóa Widget (Cho phép Di chuyển)"),
                                              lambda _: self.set_locked(False))
        else:
            lock_item = create_mac_menu_item("lock", t("widget_lock", "Khóa cố định Widget (Chống dịch chuyển)"),
                                              lambda _: self.set_locked(True))
        menu.append(lock_item)

        all_locked = is_desktop_widgets_locked()
        all_label = t("widget_unlock_all", "Mở khóa TẤT CẢ Widget trên màn hình") if all_locked else t("widget_lock_all", "Khóa cố định TẤT CẢ Widget")
        lock_all = create_mac_menu_item("lock.all", all_label,
                                        lambda _, l=all_locked: set_all_desktop_widgets_locked(not l))
        menu.append(lock_all)

        menu.append(Gtk.SeparatorMenuItem())

        loc_item = create_mac_menu_item("location", t("weather_menu_change_loc", "Đổi Địa Điểm Thời Tiết…"),
                                         lambda _: self._on_widget_clicked())
        menu.append(loc_item)

        pin_label = t("widget_pin_desktop", "Ghim Nền Desktop") if not self.keep_below else t("widget_float_window", "Nổi Trên Cửa Sổ")
        pin_icon = "pin" if not self.keep_below else "pin.slash"
        pin_item = create_mac_menu_item(pin_icon, pin_label, self._toggle_keep_below)
        menu.append(pin_item)

        anim_item = create_mac_menu_item("sparkles", t("widget_replay_open", "Phát lại hiệu ứng mở (Replay Open)"),
                                         lambda _: self.play_open_animation())
        menu.append(anim_item)

        refresh_item = create_mac_menu_item("arrow.triangle.2.circlepath", t("weather_menu_refresh", "Cập Nhật Thời Tiết Ngay"),
                                            lambda _: self.weather_mgr.refresh())
        menu.append(refresh_item)

        menu.append(Gtk.SeparatorMenuItem())
        hide_item = create_mac_menu_item("xmark", t("weather_menu_hide", "Ẩn Widget Thời Tiết"),
                                         lambda _: self.hide_widget(), is_destructive=True)
        menu.append(hide_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def _toggle_keep_below(self, _):
        self.keep_below = not self.keep_below
        if self.keep_below:
            self.set_keep_below(True)
            self.set_keep_above(False)
        else:
            self.set_keep_below(False)
            self.set_keep_above(True)

    def hide_widget(self):
        config.set("enable_desktop_weather", False)
        self.hide()
        if self.on_close:
            self.on_close()

    def show_widget(self):
        config.set("enable_desktop_weather", True)
        self.show_all()
        if getattr(self, "keep_below", True):
            self.set_keep_below(True)
        self.play_open_animation()

    def destroy(self):
        unregister_widget(self)
        if self.weather_mgr:
            self.weather_mgr.stop()
        if self._location_dialog:
            self._location_dialog.destroy()
        super().destroy()

class WeatherAnimationEngine:
    """
    Apple macOS Weather Live Animated Background Engine.
    Simulates:
    - Sun mode: Dynamic volumetric god rays radiating, pulsing solar core, floating golden light motes.
    - Rain mode: Dual-layer slanted raindrops, splash puddle ripples, and atmospheric mist.
    - Storm mode: Intense rain with randomized electric lightning flashes.
    - Clouds mode: Drifting soft volumetric cloud masses.
    - Night mode: Midnight sky with twinkling stars and soft glowing moon.
    """
    def __init__(self, weather_mgr=None):
        self.weather_mgr = weather_mgr
        self.override_mode = None  # None = Auto, "sun", "rain", "storm", "clouds", "night"
        self.time_sec = 0.0
        self.dt = 0.025  # 40 FPS
        self.timer_id = None
        self.window = None

        # Sun motes (38 floating atmospheric light particles)
        self.sun_motes = []
        for _ in range(38):
            self.sun_motes.append({
                'nx': random.uniform(0.05, 0.95),
                'ny': random.uniform(0.05, 0.95),
                'speed_y': random.uniform(0.015, 0.045),
                'drift_phase': random.uniform(0, math.pi * 2),
                'drift_amp': random.uniform(0.012, 0.035),
                'pulse_speed': random.uniform(1.2, 2.8),
                'r': random.uniform(1.2, 2.8),
                'base_alpha': random.uniform(0.25, 0.70),
            })

        # Raindrops (110 dual-depth drops)
        self.raindrops = []
        # Layer 0: Background (45 drops, thinner, slower, dimmer)
        for _ in range(45):
            self.raindrops.append({
                'layer': 0,
                'nx': random.uniform(-0.1, 1.1),
                'ny': random.uniform(-0.2, 1.0),
                'speed': random.uniform(550, 750),
                'length': random.uniform(14, 20),
                'width': 1.0,
                'alpha': random.uniform(0.22, 0.38),
            })
        # Layer 1: Foreground (65 drops, bolder, faster, brighter)
        for _ in range(65):
            self.raindrops.append({
                'layer': 1,
                'nx': random.uniform(-0.1, 1.1),
                'ny': random.uniform(-0.2, 1.0),
                'speed': random.uniform(900, 1300),
                'length': random.uniform(24, 36),
                'width': 1.8,
                'alpha': random.uniform(0.55, 0.85),
            })
        self.wind_angle = -0.24  # Slanted radians (~14 degrees)

        # Splashes (expanding ground puddle ripples)
        self.splashes = []

        # Storm lightning
        self.lightning_timer = random.uniform(4.0, 8.0)
        self.lightning_flash = 0.0
        self.lightning_x = 0.5

        # Clouds (5 drifting masses)
        self.clouds = []
        for i in range(5):
            self.clouds.append({
                'nx': i * 0.22 + random.uniform(-0.05, 0.05),
                'ny': random.uniform(0.08, 0.32),
                'speed': random.uniform(0.008, 0.018),
                'scale': random.uniform(0.8, 1.4),
                'alpha': random.uniform(0.12, 0.25),
            })

        # Stars (36 twinkling stars for night)
        self.stars = []
        for _ in range(36):
            self.stars.append({
                'nx': random.uniform(0.04, 0.96),
                'ny': random.uniform(0.04, 0.55),
                'r': random.uniform(0.8, 2.0),
                'phase': random.uniform(0, math.pi * 2),
                'twinkle_speed': random.uniform(1.0, 3.5),
                'base_alpha': random.uniform(0.3, 0.9),
            })

    def set_override_mode(self, mode):
        """Force a specific mode: 'sun', 'rain', 'storm', 'clouds', 'night', or None (Auto)"""
        self.override_mode = mode
        if self.window:
            self.window.queue_draw()

    def get_effective_mode(self):
        if self.override_mode:
            return self.override_mode
        if not self.weather_mgr:
            return "sun"
        desc = getattr(self.weather_mgr, "desc", "").lower()
        icon = getattr(self.weather_mgr, "icon_type", "").lower()

        # Check time for night mode
        now = datetime.datetime.now().time()
        is_night = False
        try:
            sr = getattr(self.weather_mgr, "sunrise", "05:45")
            ss = getattr(self.weather_mgr, "sunset", "17:45")
            sr_h, sr_m = map(int, sr.split(":"))
            ss_h, ss_m = map(int, ss.split(":"))
            now_m = now.hour * 60 + now.minute
            if now_m < (sr_h * 60 + sr_m) or now_m > (ss_h * 60 + ss_m):
                is_night = True
        except Exception:
            if now.hour < 6 or now.hour >= 18:
                is_night = True

        if any(k in desc for k in ["dông", "bão", "sét"]) or "storm" in icon:
            return "storm"
        if any(k in desc for k in ["mưa", "phùn", "rào"]) or "rain" in icon:
            return "rain"
        if any(k in desc for k in ["mây", "sương", "u ám"]) or "cloud" in icon:
            return "clouds"
        if is_night:
            return "night"
        return "sun"

    def update(self, dt=0.025):
        """Advance physics state by dt seconds."""
        self.time_sec += dt
        mode = self.get_effective_mode()

        if mode == "sun":
            # Update sun motes
            for mote in self.sun_motes:
                mote['ny'] -= mote['speed_y'] * dt
                if mote['ny'] < 0.02:
                    mote['ny'] = random.uniform(0.92, 0.98)
                    mote['nx'] = random.uniform(0.05, 0.95)

        elif mode in ("rain", "storm"):
            # Update raindrops
            for drop in self.raindrops:
                dy = (drop['speed'] * dt) / 600.0
                drop['ny'] += dy
                drop['nx'] += dy * math.tan(self.wind_angle)

                if drop['ny'] > 0.96:
                    if drop['layer'] == 1 and random.random() < 0.35 and len(self.splashes) < 22:
                        self.splashes.append({
                            'nx': drop['nx'],
                            'ny': random.uniform(0.94, 0.98),
                            'r': 1.5,
                            'max_r': random.uniform(6.0, 12.0),
                            'alpha': drop['alpha'] * 0.75,
                        })
                    drop['ny'] = random.uniform(-0.15, -0.02)
                    drop['nx'] = random.uniform(-0.1, 1.1)

            # Update splash ripples
            for s in self.splashes[:]:
                s['r'] += 18.0 * dt
                s['alpha'] -= 1.4 * dt
                if s['alpha'] <= 0.05 or s['r'] >= s['max_r']:
                    self.splashes.remove(s)

            # Update lightning if storm
            if mode == "storm":
                self.lightning_timer -= dt
                if self.lightning_timer <= 0:
                    self.lightning_flash = 0.85
                    self.lightning_x = random.uniform(0.2, 0.8)
                    self.lightning_timer = random.uniform(5.0, 10.0)
                if self.lightning_flash > 0:
                    self.lightning_flash = max(0.0, self.lightning_flash - 3.2 * dt)

        elif mode == "clouds":
            for c in self.clouds:
                c['nx'] += c['speed'] * dt
                if c['nx'] > 1.25:
                    c['nx'] = -0.25
                    c['ny'] = random.uniform(0.08, 0.35)

    def draw(self, cr, x, y, w, h, r):
        """Render the complete dynamic weather scene inside the squircle."""
        mode = self.get_effective_mode()

        cr.save()
        # Squircle Path
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.clip()

        if mode == "sun":
            self._draw_sun(cr, x, y, w, h)
        elif mode in ("rain", "storm"):
            self._draw_rain(cr, x, y, w, h, is_storm=(mode == "storm"))
        elif mode == "clouds":
            self._draw_clouds(cr, x, y, w, h)
        elif mode == "night":
            self._draw_night(cr, x, y, w, h)

        cr.restore()

        # Specular glass rim on top of clipped background
        cr.save()
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        rim = cairo.LinearGradient(x, y, x, y + h)
        rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.42)
        rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.18)
        rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.08)
        cr.set_source(rim)
        cr.set_line_width(1.0)
        cr.stroke()
        cr.restore()

    def _draw_sun(self, cr, x, y, w, h):
        # 1. Authentic Apple macOS Sunny Sky Gradient
        sky = cairo.LinearGradient(x, y, x, y + h)
        sky.add_color_stop_rgba(0.0, 0.08, 0.44, 0.88, 0.98)
        sky.add_color_stop_rgba(0.45, 0.12, 0.52, 0.94, 0.98)
        sky.add_color_stop_rgba(1.0, 0.22, 0.64, 0.98, 0.99)
        cr.set_source(sky)
        cr.rectangle(x, y, w, h)
        cr.fill()

        # Sun origin: upper-center region
        cx = x + w * 0.48
        cy = y + 42

        # 2. Dynamic Volumetric God Rays (8 rays with sine sway & radial falloff)
        ray_angles = [0.15, 0.52, 0.90, 1.28, 1.68, 2.08, 2.48, 2.85]
        max_dist = math.sqrt(w * w + h * h) * 1.1

        for i, base_angle in enumerate(ray_angles):
            sway = 0.07 * math.sin(self.time_sec * 0.35 + i * 1.25)
            spread = 0.20 + 0.04 * math.cos(self.time_sec * 0.28 + i * 0.9)
            a1 = base_angle + sway - spread / 2
            a2 = base_angle + sway + spread / 2

            p1x = cx + max_dist * math.cos(a1)
            p1y = cy + max_dist * math.sin(a1)
            p2x = cx + max_dist * math.cos(a2)
            p2y = cy + max_dist * math.sin(a2)

            cr.save()
            cr.move_to(cx, cy)
            cr.line_to(p1x, p1y)
            cr.line_to(p2x, p2y)
            cr.close_path()

            ray_pat = cairo.RadialGradient(cx, cy, 25, cx, cy, max_dist * 0.70)
            alpha_ray = 0.14 + 0.06 * math.sin(self.time_sec * 0.75 + i * 1.4)
            ray_pat.add_color_stop_rgba(0.0, 1.0, 0.98, 0.85, alpha_ray)
            ray_pat.add_color_stop_rgba(0.25, 1.0, 0.95, 0.80, alpha_ray * 0.55)
            ray_pat.add_color_stop_rgba(0.70, 1.0, 0.92, 0.75, alpha_ray * 0.12)
            ray_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
            cr.set_source(ray_pat)
            cr.fill()
            cr.restore()

        # 3. Solar Corona Lens Flare
        pulse = 1.0 + 0.08 * math.sin(self.time_sec * 1.3)
        corona = cairo.RadialGradient(cx, cy, 8, cx, cy, 280 * pulse)
        corona.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.45)
        corona.add_color_stop_rgba(0.18, 1.0, 0.96, 0.75, 0.26)
        corona.add_color_stop_rgba(0.45, 1.0, 0.88, 0.60, 0.08)
        corona.add_color_stop_rgba(1.0, 1.0, 0.80, 0.40, 0.0)
        cr.set_source(corona)
        cr.rectangle(x, y, w, h)
        cr.fill()

        # 4. Sun Motes (Golden atmospheric dust motes)
        for mote in self.sun_motes:
            px = x + mote['nx'] * w + math.sin(self.time_sec * mote['pulse_speed'] + mote['drift_phase']) * (mote['drift_amp'] * w)
            py = y + mote['ny'] * h
            r_mote = mote['r']
            alpha = mote['base_alpha'] * (0.65 + 0.35 * math.sin(self.time_sec * 2.2 + mote['drift_phase']))

            mote_pat = cairo.RadialGradient(px, py, 0, px, py, r_mote * 2.4)
            mote_pat.add_color_stop_rgba(0.0, 1.0, 0.98, 0.85, alpha)
            mote_pat.add_color_stop_rgba(0.35, 1.0, 0.85, 0.45, alpha * 0.5)
            mote_pat.add_color_stop_rgba(1.0, 1.0, 0.80, 0.20, 0.0)
            cr.set_source(mote_pat)
            cr.arc(px, py, r_mote * 2.4, 0, 2 * math.pi)
            cr.fill()

    def _draw_rain(self, cr, x, y, w, h, is_storm=False):
        # 1. Moody Rainy Sky Gradient
        sky = cairo.LinearGradient(x, y, x, y + h)
        if is_storm:
            sky.add_color_stop_rgba(0.0, 0.07, 0.10, 0.17, 0.98)
            sky.add_color_stop_rgba(0.5, 0.11, 0.15, 0.23, 0.98)
            sky.add_color_stop_rgba(1.0, 0.14, 0.19, 0.28, 0.99)
        else:
            sky.add_color_stop_rgba(0.0, 0.12, 0.19, 0.29, 0.98)
            sky.add_color_stop_rgba(0.5, 0.16, 0.24, 0.35, 0.98)
            sky.add_color_stop_rgba(1.0, 0.21, 0.30, 0.42, 0.99)
        cr.set_source(sky)
        cr.rectangle(x, y, w, h)
        cr.fill()

        # 2. Lightning Flash (for storm)
        if is_storm and self.lightning_flash > 0.02:
            flash_pat = cairo.RadialGradient(x + w * self.lightning_x, y + 50, 15, x + w * self.lightning_x, y + 50, max(w, h))
            flash_pat.add_color_stop_rgba(0.0, 0.88, 0.94, 1.0, self.lightning_flash * 0.48)
            flash_pat.add_color_stop_rgba(0.4, 0.72, 0.84, 1.0, self.lightning_flash * 0.28)
            flash_pat.add_color_stop_rgba(1.0, 0.55, 0.70, 0.95, 0.0)
            cr.set_source(flash_pat)
            cr.rectangle(x, y, w, h)
            cr.fill()

        # 3. Dual-Layer Slanted Raindrops
        cos_w = math.cos(self.wind_angle)
        sin_w = math.sin(self.wind_angle)

        for drop in self.raindrops:
            dx = x + drop['nx'] * w
            dy = y + drop['ny'] * h
            l = drop['length']

            x2 = dx + l * sin_w
            y2 = dy + l * cos_w

            pat = cairo.LinearGradient(dx, dy, x2, y2)
            pat.add_color_stop_rgba(0.0, 0.80, 0.90, 1.0, 0.0)
            pat.add_color_stop_rgba(0.6, 0.85, 0.93, 1.0, drop['alpha'] * 0.6)
            pat.add_color_stop_rgba(1.0, 0.92, 0.97, 1.0, drop['alpha'])

            cr.set_source(pat)
            cr.set_line_width(drop['width'])
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(dx, dy)
            cr.line_to(x2, y2)
            cr.stroke()

        # 4. Splash Ripples at Window Base
        for s in self.splashes:
            sx = x + s['nx'] * w
            sy = y + s['ny'] * h
            cr.save()
            cr.translate(sx, sy)
            cr.scale(1.0, 0.30)
            cr.arc(0, 0, s['r'], 0, 2 * math.pi)
            cr.set_source_rgba(0.85, 0.92, 1.0, s['alpha'])
            cr.set_line_width(1.2)
            cr.stroke()
            cr.restore()

        # 5. Bottom Atmospheric Wet Mist
        mist = cairo.LinearGradient(x, y + h - 55, x, y + h)
        mist.add_color_stop_rgba(0.0, 0.70, 0.82, 0.95, 0.0)
        mist.add_color_stop_rgba(1.0, 0.70, 0.82, 0.95, 0.14)
        cr.set_source(mist)
        cr.rectangle(x, y + h - 55, w, 55)
        cr.fill()

    def _draw_clouds(self, cr, x, y, w, h):
        sky = cairo.LinearGradient(x, y, x, y + h)
        sky.add_color_stop_rgba(0.0, 0.28, 0.35, 0.44, 0.98)
        sky.add_color_stop_rgba(0.5, 0.36, 0.44, 0.54, 0.98)
        sky.add_color_stop_rgba(1.0, 0.45, 0.53, 0.64, 0.99)
        cr.set_source(sky)
        cr.rectangle(x, y, w, h)
        cr.fill()

        for c in self.clouds:
            cx = x + c['nx'] * w
            cy = y + c['ny'] * h
            r_cloud = 140 * c['scale']

            cpat = cairo.RadialGradient(cx, cy, 20, cx, cy, r_cloud)
            cpat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, c['alpha'])
            cpat.add_color_stop_rgba(0.5, 0.92, 0.94, 0.98, c['alpha'] * 0.6)
            cpat.add_color_stop_rgba(1.0, 0.85, 0.90, 0.95, 0.0)
            cr.set_source(cpat)
            cr.arc(cx, cy, r_cloud, 0, 2 * math.pi)
            cr.fill()

    def _draw_night(self, cr, x, y, w, h):
        sky = cairo.LinearGradient(x, y, x, y + h)
        sky.add_color_stop_rgba(0.0, 0.04, 0.06, 0.14, 0.98)
        sky.add_color_stop_rgba(0.6, 0.08, 0.12, 0.22, 0.98)
        sky.add_color_stop_rgba(1.0, 0.12, 0.16, 0.28, 0.99)
        cr.set_source(sky)
        cr.rectangle(x, y, w, h)
        cr.fill()

        for star in self.stars:
            sx = x + star['nx'] * w
            sy = y + star['ny'] * h
            alpha = star['base_alpha'] * (0.55 + 0.45 * math.sin(self.time_sec * star['twinkle_speed'] + star['phase']))
            cr.set_source_rgba(0.95, 0.98, 1.0, alpha)
            cr.arc(sx, sy, star['r'], 0, 2 * math.pi)
            cr.fill()

        mx = x + w * 0.78
        my = y + 55
        moon_glow = cairo.RadialGradient(mx, my, 12, mx, my, 90)
        moon_glow.add_color_stop_rgba(0.0, 0.95, 0.96, 1.0, 0.35)
        moon_glow.add_color_stop_rgba(0.3, 0.88, 0.92, 1.0, 0.12)
        moon_glow.add_color_stop_rgba(1.0, 0.80, 0.88, 1.0, 0.0)
        cr.set_source(moon_glow)
        cr.arc(mx, my, 90, 0, 2 * math.pi)
        cr.fill()

        cr.set_source_rgba(0.96, 0.97, 1.0, 0.92)
        cr.arc(mx, my, 18, 0, 2 * math.pi)
        cr.fill()

class MacOSWeatherWindow(Gtk.Window):
    def __init__(self, parent_widget, weather_mgr):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.parent_widget = parent_widget
        self.weather_mgr = weather_mgr

        self.set_title(t("weather_title", "Thời Tiết macOS"))
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_modal(False)
        self.set_app_paintable(True)
        self.set_name("weather-popover")

        self.set_position(Gtk.WindowPosition.CENTER)

        self.pad = 16
        self.dialog_w = 780
        self.dialog_h = 600
        self.radius = 24.0
        self.set_default_size(self.dialog_w + self.pad * 2, self.dialog_h + self.pad * 2)

        # RGBA transparent background
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        self.anim_engine = WeatherAnimationEngine(self.weather_mgr)
        self.anim_engine.window = self
        self._anim_timer_id = None
        self.connect("map-event", self._on_window_map)
        self.connect("unmap-event", self._on_window_unmap)

        self.connect("draw", self._on_draw)

        # Dragging & Focus events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.FOCUS_CHANGE_MASK
        )
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("key-press-event", self._on_key_press)
        self.connect("focus-out-event", self._on_focus_out)

        # 100% Valid GTK3 CSS scoped to #weather-popover
        css = b"""
        #weather-popover {
            background: transparent;
        }
        #weather-popover-box {
            padding: 14px 18px;
        }
        #weather-popover button {
            background-image: none;
            box-shadow: none;
            text-shadow: none;
            border: none;
            outline: none;
        }
        .mac-mode-switcher-box {
            background-color: rgba(0, 0, 0, 0.16);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 12px;
            padding: 2px 4px;
        }
        .mac-effect-btn {
            background-color: transparent;
            border: none;
            border-radius: 9px;
            color: rgba(255, 255, 255, 0.72);
            font-size: 11px;
            font-weight: 500;
            padding: 2px 8px;
        }
        .mac-effect-btn:hover {
            background-color: rgba(255, 255, 255, 0.18);
            color: #ffffff;
        }
        .mac-effect-btn.active {
            background-color: rgba(255, 255, 255, 0.30);
            color: #ffffff;
            font-weight: 700;
        }
        .mac-dot-red {
            background-color: #ff5f56;
            border: 1px solid #e0443e;
            border-radius: 7px;
            min-width: 13px;
            min-height: 13px;
            padding: 0;
            margin: 0;
        }
        .mac-dot-red:hover { background-color: #ff3b30; }
        .mac-dot-yellow {
            background-color: #ffbd2e;
            border: 1px solid #dea123;
            border-radius: 7px;
            min-width: 13px;
            min-height: 13px;
            padding: 0;
            margin: 0;
        }
        .mac-dot-green {
            background-color: #27c93f;
            border: 1px solid #1aab29;
            border-radius: 7px;
            min-width: 13px;
            min-height: 13px;
            padding: 0;
            margin: 0;
        }
        .mac-pill-btn {
            background-color: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 12px;
            color: #ffffff;
            font-size: 11.5px;
            font-weight: 600;
            padding: 3px 10px;
        }
        .mac-pill-btn:hover {
            background-color: rgba(255, 255, 255, 0.28);
        }
        .mac-search-box {
            background-color: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 12px;
            padding: 2px 8px;
        }
        .mac-search-entry {
            background-color: transparent;
            color: #ffffff;
            border: none;
            box-shadow: none;
            font-size: 12px;
        }
        .mac-search-entry placeholder {
            color: rgba(255, 255, 255, 0.50);
        }
        .mac-card {
            background-color: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 16px;
            padding: 12px 14px;
        }
        .mac-card-title {
            color: rgba(255, 255, 255, 0.65);
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .mac-hero-location-pill {
            background-color: rgba(255, 255, 255, 0.16);
            border: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 13px;
            padding: 4px 14px;
        }
        .mac-city-chip {
            background-color: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 10px;
            color: #f1f5f9;
            font-size: 11px;
            font-weight: 500;
            padding: 3px 9px;
        }
        .mac-city-chip:hover {
            background-color: rgba(255, 255, 255, 0.25);
            color: #ffffff;
        }
        .mac-suggest-card {
            background-color: rgba(14, 28, 54, 0.96);
            border: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 14px;
            padding: 6px;
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.60);
        }
        .mac-suggest-item {
            background-color: transparent;
            border: none;
            border-radius: 9px;
            padding: 5px 8px;
        }
        .mac-suggest-item:hover {
            background-color: rgba(255, 255, 255, 0.20);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 100
            )

        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_name("weather-popover-box")
        self.main_box.set_margin_start(self.pad)
        self.main_box.set_margin_end(self.pad)
        self.main_box.set_margin_top(self.pad)
        self.main_box.set_margin_bottom(self.pad)
        self.overlay.add(self.main_box)

        # Floating Suggestion Dropdown Overlay
        self.suggest_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.suggest_box.get_style_context().add_class("mac-suggest-card")
        self.suggest_box.set_halign(Gtk.Align.END)
        self.suggest_box.set_valign(Gtk.Align.START)
        self.suggest_box.set_margin_top(self.pad + 38)
        self.suggest_box.set_margin_end(self.pad + 140)
        self.suggest_box.set_size_request(285, -1)
        self.suggest_box.set_no_show_all(True)
        self.suggest_box.hide()
        self.overlay.add_overlay(self.suggest_box)

        # 1. Top Navigation Bar: Traffic Lights + Search + Auto location
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Traffic light dots
        dots_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        close_btn = Gtk.Button()
        close_btn.get_style_context().add_class("mac-dot-red")
        close_btn.set_valign(Gtk.Align.CENTER)
        close_btn.set_halign(Gtk.Align.CENTER)
        close_btn.connect("clicked", lambda _: self.destroy())

        min_btn = Gtk.Button()
        min_btn.get_style_context().add_class("mac-dot-yellow")
        min_btn.set_valign(Gtk.Align.CENTER)
        min_btn.set_halign(Gtk.Align.CENTER)

        max_btn = Gtk.Button()
        max_btn.get_style_context().add_class("mac-dot-green")
        max_btn.set_valign(Gtk.Align.CENTER)
        max_btn.set_halign(Gtk.Align.CENTER)

        dots_box.pack_start(close_btn, False, False, 0)
        dots_box.pack_start(min_btn, False, False, 0)
        dots_box.pack_start(max_btn, False, False, 0)
        nav_bar.pack_start(dots_box, False, False, 0)

        # Effect Switcher Chips
        switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        switcher_box.get_style_context().add_class("mac-mode-switcher-box")

        self.effect_buttons = {}
        effects = [
            (None, "⚡ Tự động"),
            ("sun", "☀️ Nắng"),
            ("rain", "🌧️ Mưa"),
            ("storm", "⛈️ Dông"),
            ("clouds", "⛅ Mây"),
        ]
        for mode_key, mode_label in effects:
            btn = Gtk.Button(label=mode_label)
            btn.get_style_context().add_class("mac-effect-btn")
            if mode_key is None:
                btn.get_style_context().add_class("active")
            btn.connect("clicked", lambda _, k=mode_key: self._on_switch_effect(k))
            switcher_box.pack_start(btn, False, False, 0)
            self.effect_buttons[mode_key] = btn

        nav_bar.pack_start(switcher_box, False, False, 10)

        # Search Bar
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        search_box.get_style_context().add_class("mac-search-box")
        self.search_entry = Gtk.Entry()
        self.search_entry.get_style_context().add_class("mac-search-entry")
        self.search_entry.set_placeholder_text(t("weather_search_placeholder", "Tìm thành phố, quận huyện…"))
        self.search_entry.set_width_chars(22)
        self.search_entry.connect("activate", lambda _: self._on_search_submit())
        self._suggest_timer_id = None
        self.search_entry.connect("changed", self._on_search_changed)

        self.search_btn = Gtk.Button(label=t("weather_search_btn", "Tìm"))
        self.search_btn.get_style_context().add_class("mac-pill-btn")
        self.search_btn.connect("clicked", lambda _: self._on_search_submit())

        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(self.search_btn, False, False, 0)

        self.auto_btn = Gtk.Button(label=t("weather_auto_loc", "Định vị tự động"))
        auto_btn = self.auto_btn
        auto_btn.get_style_context().add_class("mac-pill-btn")
        auto_btn.connect("clicked", lambda _: self._on_auto_location())

        nav_bar.pack_end(auto_btn, False, False, 0)
        nav_bar.pack_end(search_box, False, False, 10)
        self.main_box.pack_start(nav_bar, False, False, 0)

        # 2. Hero Weather Section (Centered Apple typography)
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero_box.set_halign(Gtk.Align.CENTER)

        self.my_loc_lbl = Gtk.Label(label=t("weather_my_location", "VỊ TRÍ CỦA TÔI"))
        my_loc_lbl = self.my_loc_lbl
        my_loc_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.70))
        my_loc_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Bold 10.5"))

        # Main City / District Title
        self.hero_city_lbl = Gtk.Label(label=self.weather_mgr.district or "Thành Phố")
        self.hero_city_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0))
        self.hero_city_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Bold 26"))

        # 4-Tier Administrative Pill (Xã - Huyện - Tỉnh - Quốc Gia)
        self.location_pill_lbl = Gtk.Label()
        self.location_pill_lbl.get_style_context().add_class("mac-hero-location-pill")

        # Large Temperature
        self.hero_temp_lbl = Gtk.Label(label=f"{self.weather_mgr.temp}°")
        self.hero_temp_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0))
        self.hero_temp_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Light 58"))

        # Condition & High/Low
        self.hero_sub_lbl = Gtk.Label()
        self.hero_sub_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.90))
        self.hero_sub_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Medium 13"))

        hero_box.pack_start(my_loc_lbl, False, False, 0)
        hero_box.pack_start(self.hero_city_lbl, False, False, 0)
        hero_box.pack_start(self.location_pill_lbl, False, False, 4)
        hero_box.pack_start(self.hero_temp_lbl, False, False, 0)
        hero_box.pack_start(self.hero_sub_lbl, False, False, 0)
        self.main_box.pack_start(hero_box, False, False, 0)

        # 3. 24-Hour Hourly Forecast Banner Card
        self.hourly_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.hourly_card.get_style_context().add_class("mac-card")

        self.hourly_summary_lbl = Gtk.Label()
        self.hourly_summary_lbl.set_xalign(0.0)
        self.hourly_summary_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.92))
        self.hourly_summary_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Medium 11.5"))
        self.hourly_card.pack_start(self.hourly_summary_lbl, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.hourly_card.pack_start(sep, False, False, 2)

        self.hourly_scroll_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.hourly_card.pack_start(self.hourly_scroll_box, False, False, 2)
        self.main_box.pack_start(self.hourly_card, False, False, 0)

        # 4. Bento 3-Column Grid Cards
        bento_grid = Gtk.Grid()
        bento_grid.set_column_homogeneous(True)
        bento_grid.set_column_spacing(10)

        # Col 1: 7-Day Forecast Card
        self.daily_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.daily_card.get_style_context().add_class("mac-card")
        self.d_title = Gtk.Label(label=t("weather_7day_forecast", "DỰ BÁO 7 NGÀY"))
        d_title = self.d_title
        d_title.set_xalign(0.0)
        d_title.get_style_context().add_class("mac-card-title")
        self.daily_card.pack_start(d_title, False, False, 0)

        self.daily_rows_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.daily_card.pack_start(self.daily_rows_box, True, True, 0)
        bento_grid.attach(self.daily_card, 0, 0, 1, 1)

        # Col 2: Air Quality (AQI) + Wind & Humidity
        col2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # AQI Card
        self.aqi_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.aqi_card.get_style_context().add_class("mac-card")
        self.aqi_title = Gtk.Label(label=t("weather_aqi", "CHẤT LƯỢNG KHÔNG KHÍ (AQI)"))
        aqi_title = self.aqi_title
        aqi_title.set_xalign(0.0)
        aqi_title.get_style_context().add_class("mac-card-title")
        self.aqi_card.pack_start(aqi_title, False, False, 0)

        self.aqi_val_lbl = Gtk.Label()
        self.aqi_val_lbl.set_xalign(0.0)
        self.aqi_card.pack_start(self.aqi_val_lbl, False, False, 0)

        self.aqi_bar_area = Gtk.DrawingArea()
        self.aqi_bar_area.set_size_request(-1, 12)
        self.aqi_bar_area.connect("draw", self._draw_aqi_bar)
        self.aqi_card.pack_start(self.aqi_bar_area, False, False, 2)

        self.aqi_desc_lbl = Gtk.Label()
        self.aqi_desc_lbl.set_xalign(0.0)
        self.aqi_desc_lbl.set_line_wrap(True)
        self.aqi_desc_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.80))
        self.aqi_desc_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu 10.5"))
        self.aqi_card.pack_start(self.aqi_desc_lbl, False, False, 0)
        col2_box.pack_start(self.aqi_card, True, True, 0)

        # Wind & Humidity Card
        self.wind_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.wind_card.get_style_context().add_class("mac-card")
        self.wind_title = Gtk.Label(label=t("weather_wind_feels", "GIÓ & CẢM NHẬN"))
        wind_title = self.wind_title
        wind_title.set_xalign(0.0)
        wind_title.get_style_context().add_class("mac-card-title")
        self.wind_card.pack_start(wind_title, False, False, 0)

        self.wind_info_lbl = Gtk.Label()
        self.wind_info_lbl.set_xalign(0.0)
        self.wind_card.pack_start(self.wind_info_lbl, False, False, 0)
        col2_box.pack_start(self.wind_card, True, True, 0)

        bento_grid.attach(col2_box, 1, 0, 1, 1)

        # Col 3: 4-Tier Administrative Details & Precipitation
        self.admin_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.admin_card.get_style_context().add_class("mac-card")
        self.admin_title = Gtk.Label(label=t("weather_admin_tier", "ĐỊA DANH HÀNH CHÍNH (4 CẤP)"))
        admin_title = self.admin_title
        admin_title.set_xalign(0.0)
        admin_title.get_style_context().add_class("mac-card-title")
        self.admin_card.pack_start(admin_title, False, False, 0)

        self.admin_details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.admin_card.pack_start(self.admin_details_box, True, True, 0)
        bento_grid.attach(self.admin_card, 2, 0, 1, 1)

        self.main_box.pack_start(bento_grid, True, True, 0)

        # 5. Quick Location Chips
        chips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chips_box.set_halign(Gtk.Align.CENTER)
        popular_cities = ["Vị trí hiện tại", "Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Biên Hòa", "Nha Trang", "Cần Thơ", "Huế"]
        for c_name in popular_cities:
            btn = Gtk.Button(label=c_name)
            btn.get_style_context().add_class("mac-city-chip")
            btn.connect("clicked", lambda _, name=c_name: self._on_chip_clicked(name))
            chips_box.pack_start(btn, False, False, 0)
        self.main_box.pack_start(chips_box, False, False, 2)

        # Connect update listener
        self.weather_mgr.add_listener(self._on_weather_updated)
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

        self._update_ui_data()

    def _on_language_changed(self, lang_code: str):
        try:
            self._retranslate_ui()
        except Exception:
            GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("weather_title", "Thời Tiết macOS"))
            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("weather_search_placeholder", "Tìm thành phố, quận huyện…"))
            if hasattr(self, "search_btn"):
                self.search_btn.set_label(t("weather_search_btn", "Tìm"))
            if hasattr(self, "auto_btn"):
                self.auto_btn.set_label(t("weather_auto_loc", "Định vị tự động"))
            if hasattr(self, "my_loc_lbl"):
                self.my_loc_lbl.set_text(t("weather_my_location", "VỊ TRÍ CỦA TÔI"))
            if hasattr(self, "d_title"):
                self.d_title.set_text(t("weather_7day_forecast", "DỰ BÁO 7 NGÀY"))
            if hasattr(self, "aqi_title"):
                self.aqi_title.set_text(t("weather_aqi", "CHẤT LƯỢNG KHÔNG KHÍ (AQI)"))
            if hasattr(self, "wind_title"):
                self.wind_title.set_text(t("weather_wind_feels", "GIÓ & CẢM NHẬN"))
            if hasattr(self, "admin_title"):
                self.admin_title.set_text(t("weather_admin_tier", "ĐỊA DANH HÀNH CHÍNH (4 CẤP)"))
            self._update_ui_data()
        except Exception as e:
            print(f"[MacOSWeatherWindow] _retranslate_ui error: {e}")

    def _on_weather_updated(self):
        GLib.idle_add(self._update_ui_data)
        if hasattr(self, "search_btn"):
            GLib.idle_add(lambda: self.search_btn.set_label("Tìm"))

    def _on_switch_effect(self, mode_key):
        self.anim_engine.set_override_mode(mode_key)
        for k, btn in getattr(self, "effect_buttons", {}).items():
            if k == mode_key:
                btn.get_style_context().add_class("active")
            else:
                btn.get_style_context().remove_class("active")
        self.queue_draw()

    def _on_window_map(self, widget, event):
        self._start_animation()
        return False

    def _on_window_unmap(self, widget, event):
        self._stop_animation()
        return False

    def _start_animation(self):
        if self._anim_timer_id is None:
            self._anim_timer_id = GLib.timeout_add(25, self._on_animation_tick)

    def _stop_animation(self):
        if self._anim_timer_id is not None:
            GLib.source_remove(self._anim_timer_id)
            self._anim_timer_id = None

    def _on_animation_tick(self):
        if not self.get_visible():
            self._stop_animation()
            return False
        self.anim_engine.update(0.025)
        self.queue_draw()
        return True

    def _on_focus_out(self, widget, event):
        GLib.idle_add(self._auto_close_on_unfocus)
        return False

    def _auto_close_on_unfocus(self):
        if not self.get_visible() or self.in_destruction():
            return
        if not self.has_toplevel_focus() or not self.is_active():
            self.destroy()

    def destroy(self):
        self._stop_animation()
        if hasattr(self, "_suggest_timer_id") and self._suggest_timer_id:
            GLib.source_remove(self._suggest_timer_id)
            self._suggest_timer_id = None
        self.weather_mgr.remove_listener(self._on_weather_updated)
        if self.parent_widget:
            import time
            self.parent_widget._last_closed_time = time.time()
            if hasattr(self.parent_widget, "_location_dialog"):
                self.parent_widget._location_dialog = None
        super().destroy()

    def _update_ui_data(self):
        wm = self.weather_mgr

        # Hero
        custom_city = config.get("weather_city", "").strip() or getattr(wm, "city", "").strip()
        if custom_city and custom_city.lower() not in ("auto", "tự động", "hiện tại"):
            hero_title = custom_city
        else:
            hero_title = wm.district or wm.city or wm.province or wm.ward or "Thành Phố"

        for p in ("Thành phố ", "TP. ", "Huyện ", "Quận ", "Thị xã ", "Tỉnh ", "Phường ", "Xã "):
            if hero_title.lower().startswith(p.lower()):
                hero_title = hero_title[len(p):].strip()
                break

        self.hero_city_lbl.set_text(hero_title)
        
        # 4-tier location pill
        ward_text = wm.ward if wm.ward else "---"
        dist_text = wm.district if wm.district else "---"
        prov_text = wm.province if wm.province else "---"
        country_text = wm.country if wm.country else "Việt Nam"

        self.location_pill_lbl.set_markup(
            f"📍 <b>Xã/Phường:</b> {ward_text}  •  <b>Quận/Huyện:</b> {dist_text}  •  <b>Tỉnh:</b> {prov_text}  •  <b>Quốc gia:</b> {country_text} 🇻🇳"
        )

        self.hero_temp_lbl.set_text(f"{wm.temp}°")
        self.hero_sub_lbl.set_text(f"{wm.desc}  •  Cao: {wm.temp_high}°  Thấp: {wm.temp_low}°")

        # Hourly Banner
        summary_icon = "⛈️" if wm.icon_type == "storm" else ("🌧️" if wm.icon_type == "rain" else ("🌙" if wm.icon_type == "moon" else ("⛅" if wm.icon_type == "cloud" else "☀️")))
        self.hourly_summary_lbl.set_text(f"{summary_icon} {wm.summary}")
        for child in self.hourly_scroll_box.get_children():
            self.hourly_scroll_box.remove(child)

        icon_map = {"sun": "☀️", "cloud": "⛅", "rain": "🌧️", "storm": "⛈️", "sunset": "🌅", "moon": "🌙"}

        for item in wm.hourly[:14]:
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            col.set_halign(Gtk.Align.CENTER)

            t_lbl = Gtk.Label(label=item["time"])
            t_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.75))
            t_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Semi-Bold 10"))

            ic_char = icon_map.get(item["icon"], "☀️")
            ic_lbl = Gtk.Label(label=ic_char)
            ic_lbl.override_font(Pango.FontDescription("15"))

            deg_lbl = Gtk.Label(label=item["temp"])
            if item.get("is_sunset"):
                deg_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 0.8, 0.3, 0.95))
                deg_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Bold 9.5"))
            else:
                deg_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.95))
                deg_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Semi-Bold 11"))

            col.pack_start(t_lbl, False, False, 0)
            col.pack_start(ic_lbl, False, False, 0)
            col.pack_start(deg_lbl, False, False, 0)
            self.hourly_scroll_box.pack_start(col, False, False, 0)
        self.hourly_scroll_box.show_all()

        # Daily Forecast
        for child in self.daily_rows_box.get_children():
            self.daily_rows_box.remove(child)

        global_min = min([d["min"] for d in wm.daily], default=22)
        global_max = max([d["max"] for d in wm.daily], default=34)

        for idx, day_info in enumerate(wm.daily):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            day_lbl = Gtk.Label(label=day_info["day"])
            day_lbl.set_xalign(0.0)
            day_lbl.set_width_chars(7)
            day_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.92))
            day_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Semi-Bold 11"))
            row.pack_start(day_lbl, False, False, 0)

            d_ic = icon_map.get(day_info["icon"], "☀️")
            ic_lbl = Gtk.Label(label=d_ic)
            ic_lbl.set_width_chars(2)
            row.pack_start(ic_lbl, False, False, 0)

            min_lbl = Gtk.Label(label=f"{day_info['min']}°")
            min_lbl.set_width_chars(3)
            min_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.65))
            min_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu 11"))
            row.pack_start(min_lbl, False, False, 0)

            # Temp range bar
            bar = Gtk.DrawingArea()
            bar.set_size_request(65, 12)
            cur_v = wm.temp if idx == 0 else None
            bar.connect("draw", lambda w, cr, lo=day_info['min'], hi=day_info['max'], cv=cur_v, gmin=global_min, gmax=global_max: 
                        self._draw_temp_bar(w, cr, lo, hi, cv, gmin, gmax))
            row.pack_start(bar, True, True, 2)

            max_lbl = Gtk.Label(label=f"{day_info['max']}°")
            max_lbl.set_width_chars(3)
            max_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.95))
            max_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Semi-Bold 11"))
            row.pack_start(max_lbl, False, False, 0)

            self.daily_rows_box.pack_start(row, False, False, 0)
        self.daily_rows_box.show_all()

        # AQI
        if wm.aqi <= 25:
            aqi_color = "#4ade80" # Green
            aqi_text = f"Chỉ số AQI là {wm.aqi} ({wm.aqi_desc}), chất lượng không khí rất trong lành, lý tưởng cho mọi hoạt động ngoài trời."
        elif wm.aqi <= 50:
            aqi_color = "#a3e635" # Lime
            aqi_text = f"Chỉ số AQI là {wm.aqi} ({wm.aqi_desc}), chất lượng không khí đạt chuẩn an toàn, thích hợp cho hoạt động ngoài trời."
        elif wm.aqi <= 75:
            aqi_color = "#facc15" # Yellow
            aqi_text = f"Chỉ số AQI là {wm.aqi} ({wm.aqi_desc}), mức chấp nhận được. Người cực kỳ nhạy cảm nên chú ý nếu vận động mạnh."
        elif wm.aqi <= 100:
            aqi_color = "#fb923c" # Orange
            aqi_text = f"Chỉ số AQI là {wm.aqi} ({wm.aqi_desc}), không khí kém đối với nhóm nhạy cảm (trẻ em, người cao tuổi, hen suyễn)."
        else:
            aqi_color = "#f87171" # Red
            aqi_text = f"Chỉ số AQI là {wm.aqi} ({wm.aqi_desc}), không khí ô nhiễm. Nên đeo khẩu trang chống bụi mịn khi ra ngoài."

        self.aqi_val_lbl.set_markup(f"<span font_size='22000' font_weight='bold' color='#ffffff'>{wm.aqi}</span>  <span font_size='13000' font_weight='bold' color='{aqi_color}'>{wm.aqi_desc}</span>")
        self.aqi_desc_lbl.set_text(aqi_text)
        self.aqi_bar_area.queue_draw()

        # Wind & Humidity (Localized)
        self.wind_info_lbl.set_markup(
            f"💨 <b>{t('weather_wind', 'Gió')}:</b> {wm.wind_speed} km/h  ({wm.wind_dir_name})\n"
            f"💧 <b>{t('weather_humidity', 'Độ ẩm')}:</b> {wm.humidity}%  •  🌡️ <b>{t('weather_feels_like', 'Cảm nhận')}:</b> {wm.apparent_temp}°C\n"
            f"☀️ <b>{t('weather_uv', 'Chỉ số UV')}:</b> {wm.uv_index}  •  🌧️ <b>{t('weather_precipitation', 'Lượng mưa')}:</b> {wm.precipitation_24h}"
        )

        # 4-Tier Administrative Details Box
        for child in self.admin_details_box.get_children():
            self.admin_details_box.remove(child)

        admin_items = [
            ("🏷️ Xã / Phường:", ward_text, "#38bdf8"),
            ("🏢 Quận / Huyện / TP:", dist_text, "#ffffff"),
            ("🏛️ Tỉnh / Thành phố:", prov_text, "#ffffff"),
            ("🌍 Quốc gia:", country_text, "#fde047"),
            (f"🌅 {t('weather_sunrise', 'Mặt trời mọc')}:", f"{wm.sunrise}   |   🌇 {t('weather_sunset', 'Lặn')}: {wm.sunset}", "#cbd5e1"),
        ]
        for title, val, col in admin_items:
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl_title = Gtk.Label(label=title)
            lbl_title.set_xalign(0.0)
            lbl_title.set_width_chars(16)
            lbl_title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.70))
            lbl_title.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu 10.5"))

            v = Gtk.Label()
            v.set_xalign(0.0)
            v.set_markup(f"<span color='{col}' font_weight='bold'>{val}</span>")
            v.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu 11"))

            r.pack_start(lbl_title, False, False, 0)
            r.pack_start(v, True, True, 0)
            self.admin_details_box.pack_start(r, False, False, 0)
        self.admin_details_box.show_all()

    def _draw_temp_bar(self, widget, cr, min_val, max_val, cur_val, global_min=20, global_max=36):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height
        bar_h = 4.5
        y_bar = (h - bar_h) / 2.0
        r = bar_h / 2.0

        # Background track
        cr.new_sub_path()
        cr.arc(w - r, y_bar + r, r, -math.pi/2, math.pi/2)
        cr.arc(r, y_bar + r, r, math.pi/2, 3*math.pi/2)
        cr.close_path()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.25)
        cr.fill()

        # Active range segment
        denom = max(1, global_max - global_min)
        x_start = max(0.0, min(w, (min_val - global_min) / denom * w))
        x_end = max(x_start + bar_h, min(w, (max_val - global_min) / denom * w))
        seg_w = x_end - x_start

        cr.new_sub_path()
        cr.arc(x_start + seg_w - r, y_bar + r, r, -math.pi/2, math.pi/2)
        cr.arc(x_start + r, y_bar + r, r, math.pi/2, 3*math.pi/2)
        cr.close_path()

        pat = cairo.LinearGradient(x_start, 0, x_end, 0)
        pat.add_color_stop_rgba(0.0, 0.35, 0.85, 1.0, 1.0)
        pat.add_color_stop_rgba(0.5, 0.98, 0.85, 0.25, 1.0)
        pat.add_color_stop_rgba(1.0, 1.0, 0.45, 0.20, 1.0)
        cr.set_source(pat)
        cr.fill()

        # Current temp dot indicator
        if cur_val is not None:
            dot_x = max(r, min(w - r, (cur_val - global_min) / denom * w))
            cr.arc(dot_x, y_bar + r, 4.0, 0, 2*math.pi)
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.fill()
            cr.arc(dot_x, y_bar + r, 4.0, 0, 2*math.pi)
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.3)
            cr.set_line_width(1.0)
            cr.stroke()
        return False

    def _draw_aqi_bar(self, widget, cr):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height
        bar_h = 5.5
        y_bar = (h - bar_h) / 2.0
        r = bar_h / 2.0

        cr.new_sub_path()
        cr.arc(w - r, y_bar + r, r, -math.pi/2, math.pi/2)
        cr.arc(r, y_bar + r, r, math.pi/2, 3*math.pi/2)
        cr.close_path()

        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgba(0.0, 0.15, 0.85, 0.35, 1.0) # Green
        pat.add_color_stop_rgba(0.25, 0.95, 0.85, 0.15, 1.0) # Yellow
        pat.add_color_stop_rgba(0.50, 0.98, 0.50, 0.15, 1.0) # Orange
        pat.add_color_stop_rgba(0.75, 0.92, 0.25, 0.25, 1.0) # Red
        pat.add_color_stop_rgba(1.0, 0.65, 0.25, 0.85, 1.0) # Purple
        cr.set_source(pat)
        cr.fill()

        # Dot indicator
        aqi = self.weather_mgr.aqi
        dot_x = max(r, min(w - r, (min(aqi, 200) / 200.0) * w))
        cr.arc(dot_x, y_bar + r, 4.5, 0, 2*math.pi)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.fill()
        cr.arc(dot_x, y_bar + r, 4.5, 0, 2*math.pi)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.4)
        cr.set_line_width(1.0)
        cr.stroke()
        return False

    def _path_squircle(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _on_draw(self, widget, cr):
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        alloc = widget.get_allocation()
        x = self.pad
        y = self.pad
        w = max(self.dialog_w, alloc.width - self.pad * 2)
        h = max(self.dialog_h, alloc.height - self.pad * 2)
        r = self.radius


        # Live Animated Weather Background (Sun, Rain, Storm, Clouds, Night)
        self.anim_engine.draw(cr, x, y, w, h, r)

        return False

    def _on_button_press(self, widget, event):
        if hasattr(self, "suggest_box") and self.suggest_box.get_visible():
            self._hide_suggestions()
        if event.button == 1:
            self._dragging = True
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            pos = self.get_position()
            self._win_start_x = pos[0]
            self._win_start_y = pos[1]
            return False
        return False

    def _on_motion_notify(self, widget, event):
        if self._dragging:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            self.move(int(self._win_start_x + dx), int(self._win_start_y + dy))
            return True
        return False

    def _on_button_release(self, widget, event):
        if event.button == 1 and self._dragging:
            self._dragging = False
            return False
        return False

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if hasattr(self, "suggest_box") and self.suggest_box.get_visible():
                self._hide_suggestions()
                return True
            self.destroy()
            return True
        return False

    def _on_search_changed(self, entry):
        if self._suggest_timer_id:
            GLib.source_remove(self._suggest_timer_id)
            self._suggest_timer_id = None

        query = entry.get_text().strip()
        if len(query) < 2:
            self._hide_suggestions()
            return

        # Debounce 280ms
        self._suggest_timer_id = GLib.timeout_add(280, self._trigger_suggestion_fetch, query)

    def _trigger_suggestion_fetch(self, query):
        self._suggest_timer_id = None
        threading.Thread(target=self._fetch_suggestions_thread, args=(query,), daemon=True).start()
        return False

    def _fetch_suggestions_thread(self, query):
        from src.modules.weather import WeatherManager
        results = WeatherManager.get_suggestions(query, limit=5)
        GLib.idle_add(self._render_suggestions, query, results)

    def _render_suggestions(self, orig_query, results):
        if self.search_entry.get_text().strip() != orig_query:
            return

        for ch in self.suggest_box.get_children():
            self.suggest_box.remove(ch)

        if not results:
            empty_lbl = Gtk.Label(label="Không tìm thấy địa danh phù hợp")
            empty_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.60))
            empty_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu 10.5"))
            empty_lbl.set_margin_top(6)
            empty_lbl.set_margin_bottom(6)
            self.suggest_box.pack_start(empty_lbl, False, False, 0)
            empty_lbl.show_all()
            self.suggest_box.show()
            return

        for item in results:
            btn = Gtk.Button()
            btn.get_style_context().add_class("mac-suggest-item")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            ic = Gtk.Label(label="📍")
            ic.override_font(Pango.FontDescription("11"))
            row.pack_start(ic, False, False, 0)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            name_lbl = Gtk.Label(label=item["name"])
            name_lbl.set_xalign(0.0)
            name_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0))
            name_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Bold 11"))
            vbox.pack_start(name_lbl, False, False, 0)

            detail_lbl = Gtk.Label(label=item["detail"])
            detail_lbl.set_xalign(0.0)
            detail_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.70))
            detail_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu 9.5"))
            vbox.pack_start(detail_lbl, False, False, 0)

            row.pack_start(vbox, True, True, 0)
            btn.add(row)

            btn.connect("clicked", lambda _, it=item: self._on_select_suggestion(it))
            self.suggest_box.pack_start(btn, False, False, 0)
            btn.show_all()

        self.suggest_box.show()

    def _on_select_suggestion(self, item):
        self._hide_suggestions()
        name = item["name"]
        self.search_entry.set_text(name)
        if hasattr(self, "search_btn"):
            self.search_btn.set_label("Đang tải...")
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is not None and lon is not None:
            self.weather_mgr.set_coords(lat, lon, name)
        else:
            self.weather_mgr.set_city(name)

    def _hide_suggestions(self):
        if hasattr(self, "suggest_box"):
            self.suggest_box.hide()

    def _on_search_submit(self):
        self._hide_suggestions()
        query = self.search_entry.get_text().strip()
        if query:
            if hasattr(self, "search_btn"):
                self.search_btn.set_label("Đang tìm...")
            self.weather_mgr.set_city(query)

    def _on_auto_location(self):
        self._hide_suggestions()
        if hasattr(self, "search_btn"):
            self.search_btn.set_label("Đang định vị...")
        self.weather_mgr.set_city("")

    def _on_chip_clicked(self, city_name):
        self._hide_suggestions()
        if "tự động" in city_name.lower() or "hiện tại" in city_name.lower():
            self._on_auto_location()
        else:
            if hasattr(self, "search_btn"):
                self.search_btn.set_label("Đang tải...")
            self.search_entry.set_text(city_name)
            self.weather_mgr.set_city(city_name)

WeatherLocationDialog = MacOSWeatherWindow


if __name__ == "__main__":
    win = DesktopWeatherWidget()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

