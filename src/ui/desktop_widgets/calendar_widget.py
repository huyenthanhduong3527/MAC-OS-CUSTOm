"""
Apple macOS Desktop Calendar & Vietnamese Lunar Widget.
Displays Month, Current Day, Weekday, Vietnamese Lunar Date (Âm Lịch),
and a full monthly calendar grid with solar and lunar dates, highlighting today in Apple red.
"""

import math
import calendar
import datetime
import cairo
import gi
import locale
import locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass
import os
import time
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo
from src.config import config
from src.animator import SpringValue
from src.utils.lunar import solar_to_lunar, get_lunar_string, get_can_chi
from src.utils.i18n import get_current_language, add_language_listener, t
from src.utils.date_locale import localized_month_name, localized_weekday_names
from src.ui.desktop_widgets import (
    register_widget,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)

WEEKDAY_NAMES = {
    "ja": ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
    "vi": ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
DAY_COLS = {
    "ja": ["月", "火", "水", "木", "金", "土", "日"],
    "vi": ["HAI", "BA", "TƯ", "NĂM", "SÁU", "BẢY", "CN"],
    "en": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
}
MONTH_NAMES_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

WEEKDAY_NAMES_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
DAY_COLS_VI = ["HAI", "BA", "TƯ", "NĂM", "SÁU", "BẢY", "CN"]
def get_system_language():
    try:
        # Lấy ngôn ngữ từ biến môi trường của hệ thống (phổ biến trên macOS/Linux)
        lang_code = os.environ.get('LANG')
        
        # Nếu không có, dùng locale mặc định của Python
        if not lang_code:
            lang_code, _ = locale.getdefaultlocale()
            
        # Lấy 2 ký tự đầu tiên để xác định mã ngôn ngữ (ví dụ: 'vi' từ 'vi_VN', 'ja' từ 'ja_JP')
        if lang_code and len(lang_code) >= 2:
            return lang_code[:2].lower()
    except Exception:
        pass
    
    return "en" # Fallback về tiếng Anh nếu có lỗi

class DesktopCalendarWidget(Gtk.Window):
    def __init__(self, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_close = on_close

        self.card_w = 330
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
            self.dark_mode = config.get("desktop_calendar_dark", False)

        # Window properties
        self.set_title(t("calendar_widget_title", "macOS Calendar & Lunar Widget"))
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
        self.set_wmclass("desktop-widget-calendar", "DesktopWidgetCalendar")
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

        try:
            add_language_listener(lambda *_: GLib.idle_add(self._refresh_language))
        except Exception:
            pass

        # RGBA transparent visual
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
        self.get_style_context().add_class("transparent-window")
        self.get_style_context().add_class("desktop-widget-calendar")

        # Position window from config
        self._current_x = int(config.get("desktop_calendar_x", 30))
        self._current_y = int(config.get("desktop_calendar_y", 70))
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
        self._calendar_window = None

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("map-event", self._on_map_event)

        # Periodic refresh every 60s
        self._timer_id = GLib.timeout_add_seconds(60, self._on_tick)

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
        """Locks or unlocks calendar widget movement."""
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

    def _on_tick(self):
        self.queue_draw()
        return True

    def _refresh_language(self):
        self.set_title(t("calendar_widget_title", "macOS Calendar & Lunar Widget"))
        self.queue_draw()
        return False

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

    def _draw_text(self, cr, x, y, text, font_desc_str, color, align="left"):
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        desc = Pango.FontDescription(font_desc_str)
        layout.set_font_description(desc)

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

        now = datetime.datetime.now()
        cur_day = now.day
        cur_month = now.month
        cur_year = now.year
        weekday_idx = now.weekday() # 0 = Monday

        x = self.pad
        y = self.pad
        w = self.card_w
        h = self.card_h
        r = self.radius

        # 1. Card Background: Apple Frosted Glassmorphism (Translucent - wallpaper shows through)
        self._path_rounded_rect(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        base_pat = cairo.LinearGradient(x, y, x, y + h)
        base_pat.add_color_stop_rgba(0.0, 0.08, 0.10, 0.14, 0.35)
        base_pat.add_color_stop_rgba(1.0, 0.04, 0.05, 0.08, 0.42)
        cr.set_source(base_pat)
        cr.paint()

        # Specular top highlight
        sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
        sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.14)
        sheen.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.02)
        sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(sheen)
        cr.paint()

        cr.restore()

        # 2. Subtle Glass Rim (Subtle and razor-sharp, no blurry outline)
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

        # Text color definitions: Luminous on transparent glass
        text_primary = (0.96, 0.98, 1.0, 0.95)
        text_secondary = (0.80, 0.84, 0.90, 0.90)
        text_muted = (0.60, 0.65, 0.72, 0.75)
        accent_red = (0.95, 0.26, 0.24, 0.98) # Apple Red / Coral

        # -------------------------------------------------------------
        # LEFT COLUMN: Big Weekday & Big Day Number (macOS Widget Style)
        # -------------------------------------------------------------
        left_center_x = x + 62

        cur_lang = get_current_language()

        # 1. Weekday in Apple Red/Coral on top (e.g. "Wed" or "Thứ Tư")
        if cur_lang == "vi":
            weekday_name = localized_weekday_names(cur_lang, width="wide")[weekday_idx]
        else:
            weekday_name = localized_weekday_names(cur_lang, width="abbreviated")[weekday_idx]
        accent_red = (0.95, 0.26, 0.24, 0.98) # Apple Red / Coral
        self._draw_text(cr, left_center_x, y + 20, weekday_name, "-apple-system, Inter, Ubuntu Bold 15", accent_red, align="center")

        # 2. Huge Day Number (e.g. 23) in bold Apple typography
        day_str = str(cur_day)
        day_font = "-apple-system, Inter, Ubuntu Bold 52"
        self._draw_text(cr, left_center_x, y + 44, day_str, day_font, text_primary, align="center")

        # 3. Lunar Date (or localized sub-date)
        if cur_lang == "ja":
            lunar_str = f"令和8年"
        elif cur_lang == "vi":
            lunar_str = get_lunar_string(cur_day, cur_month, cur_year)
        else:
            lunar_str = f"{cur_year}"
        self._draw_text(cr, left_center_x, y + 126, lunar_str, "-apple-system, Inter, Ubuntu Medium 9.5", text_muted, align="center")

        # -------------------------------------------------------------
        # RIGHT COLUMN: Month Header + Full Monthly Grid
        # -------------------------------------------------------------
        grid_x = x + 130
        grid_y = y + 16
        col_w = 26.0
        row_h = 19.5

        # Month title in uppercase: "SEPTEMBER" or "THÁNG 9"
        month_header = localized_month_name(cur_month, cur_lang).upper()
        self._draw_text(cr, grid_x, grid_y, month_header, "-apple-system, Inter, Ubuntu Bold 11.0", text_secondary, align="left")

        # Draw Day-of-week headers
        cols = ["S", "M", "T", "W", "T", "F", "S"] if cur_lang == "en" else localized_weekday_names(cur_lang, fallback=DAY_COLS["en"])
        header_y = grid_y + 20
        for c_idx, col_name in enumerate(cols):
            cx = grid_x + c_idx * col_w + col_w / 2.0
            col_color = accent_red if c_idx >= 5 else text_muted
            self._draw_text(cr, cx, header_y, col_name, "-apple-system, Inter, Ubuntu Semi-Bold 7.5", col_color, align="center")

        # Monthly calendar calculation
        cal = calendar.Calendar(firstweekday=0) # 0 = Monday
        month_dates = cal.monthdatescalendar(cur_year, cur_month)

        for r_idx, week in enumerate(month_dates[:6]):
            for c_idx, dt in enumerate(week):
                cx = grid_x + c_idx * col_w + col_w / 2.0
                cy = header_y + 16 + r_idx * row_h

                is_today = (dt.day == cur_day and dt.month == cur_month and dt.year == cur_year)
                in_month = (dt.month == cur_month)

                # Convert to lunar date
                lunar_d, lunar_m, _, _ = solar_to_lunar(dt.day, dt.month, dt.year)

                if is_today:
                    # Apple Badge for today: Solid white in dark mode, Red in light mode
                    badge_size = 19.0
                    bx = cx - badge_size / 2.0
                    by = cy - 2.0
                    cr.save()
                    self._path_rounded_rect(cr, bx, by, badge_size, badge_size, 9.5)
                    if self.dark_mode:
                        cr.set_source_rgba(0.98, 0.98, 1.0, 1.0)
                    else:
                        cr.set_source_rgba(0.93, 0.22, 0.22, 1.0)
                    cr.fill()
                    cr.restore()

                    # Solar number
                    badge_num_color = (0.08, 0.09, 0.11, 1.0) if self.dark_mode else (1.0, 1.0, 1.0, 1.0)
                    self._draw_text(cr, cx, cy, str(dt.day), "-apple-system, Inter, Ubuntu Bold 8.5", badge_num_color, align="center")
                else:
                    if in_month:
                        s_color = accent_red if c_idx >= 5 else text_primary
                        l_color = (0.75, 0.35, 0.35, 0.75) if c_idx >= 5 else text_muted
                    else:
                        # Dimmed previous/next month days
                        s_color = (0.45, 0.48, 0.54, 0.25) if not self.dark_mode else (0.55, 0.58, 0.64, 0.25)
                        l_color = (0.45, 0.48, 0.54, 0.20) if not self.dark_mode else (0.55, 0.58, 0.64, 0.20)

                    self._draw_text(cr, cx, cy, str(dt.day), "-apple-system, Inter, Ubuntu Medium 8.0", s_color, align="center")

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
                config.set("desktop_calendar_x", int(self._current_x))
                config.set("desktop_calendar_y", int(self._current_y))
            else:
                self._on_widget_clicked()
            self._has_moved = False
            return True
        return False

    def _on_widget_clicked(self):
        import time
        if time.time() - getattr(self, "_last_closed_time", 0) < 0.35:
            return
        if self._calendar_window and self._calendar_window.get_visible():
            self._calendar_window.destroy()
            self._calendar_window = None
            return
        self._calendar_window = InteractiveCalendarWindow(self)
        self._calendar_window.show_all()
        self._calendar_window.present()

    def _show_context_menu(self, event):
        from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item

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
        all_icon = "lock.open" if all_locked else "lock.all"
        menu.append(create_mac_menu_item(all_icon, all_label,
                                         lambda _: set_all_desktop_widgets_locked(not all_locked)))

        menu.append(Gtk.SeparatorMenuItem())

        menu.append(create_mac_menu_item("calendar", t("calendar_open_details", "Mở chi tiết Lịch…"),
                                         lambda _: self._on_widget_clicked()))

        pin_label = t("widget_pin_desktop", "Ghim Nền Desktop") if not self.keep_below else t("widget_float_window", "Nổi Trên Cửa Sổ")
        pin_icon = "pin" if not self.keep_below else "pin.slash"
        menu.append(create_mac_menu_item(pin_icon, pin_label, self._toggle_keep_below))

        menu.append(create_mac_menu_item("sparkles", t("widget_replay_open", "Phát lại hiệu ứng mở (Replay Open)"),
                                         lambda _: self.play_open_animation()))

        theme_label = t("widget_light_mode", "Giao diện Sáng (Light)") if self.dark_mode else t("widget_dark_mode", "Chế độ tối")
        theme_icon = "sun.max" if self.dark_mode else "moon.fill"
        menu.append(create_mac_menu_item(theme_icon, theme_label, self._toggle_theme))

        menu.append(Gtk.SeparatorMenuItem())
        menu.append(create_mac_menu_item("xmark", t("calendar_hide", "Ẩn Widget Lịch"),
                                         lambda _: self.hide_widget(), is_destructive=True))

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

    def _toggle_theme(self, _):
        self.dark_mode = not self.dark_mode
        config.set("desktop_calendar_dark", self.dark_mode)
        self.queue_draw()

    def hide_widget(self):
        config.set("enable_desktop_calendar", False)
        self.hide()
        if self.on_close:
            self.on_close()

    def show_widget(self):
        config.set("enable_desktop_calendar", True)
        self.show_all()
        if getattr(self, "keep_below", True):
            self.set_keep_below(True)
        self.play_open_animation()

    def destroy(self):
        unregister_widget(self)
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        if self._calendar_window:
            self._calendar_window.destroy()
        super().destroy()

class InteractiveCalendarWindow(Gtk.Window):
    def __init__(self, parent_widget):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.parent_widget = parent_widget

        now = datetime.datetime.now()
        self.cur_year = now.year
        self.cur_month = now.month
        self.selected_day = now.day

        try:
            from src.utils.theme import is_dark_mode
            self.is_dark = is_dark_mode()
        except Exception:
            self.is_dark = True

        self.set_title(t("calendar_title", "macOS Calendar & Lunar Calendar"))
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_modal(False)
        self.set_app_paintable(True)
        self.set_name("calendar-popover")

        self.set_position(Gtk.WindowPosition.CENTER)

        self.pad = 16
        self.dialog_w = 345
        self.dialog_h = 445
        self.radius = 24.0
        self.set_default_size(self.dialog_w + self.pad * 2, self.dialog_h + self.pad * 2)

        # RGBA visual
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

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

        # Authentic Apple macOS Sonoma / Sequoia Popover CSS
        css = """
        #calendar-popover {
            background: transparent;
        }
        #calendar-popover-box {
            padding: 12px 14px;
        }
        #calendar-popover button {
            background-image: none;
            box-shadow: none;
            text-shadow: none;
            border: none;
            outline: none;
        }

        /* Title */
        .cal-title-lbl {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.2px;
        }
        .mac-dark .cal-title-lbl {
            color: #ffffff;
        }
        .mac-light .cal-title-lbl {
            color: #1d1d1f;
        }

        /* Segmented Month Navigation Capsule [ < | > ] */
        .cal-segmented-box {
            border-radius: 9px;
            padding: 1px;
        }
        .mac-dark .cal-segmented-box {
            background-color: rgba(255, 255, 255, 0.08);
            border: 0.5px solid rgba(255, 255, 255, 0.12);
        }
        .mac-light .cal-segmented-box {
            background-color: rgba(0, 0, 0, 0.05);
            border: 0.5px solid rgba(0, 0, 0, 0.10);
        }

        .cal-seg-btn {
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            padding: 1px 8px;
            min-height: 24px;
            min-width: 26px;
            transition: background-color 100ms ease;
        }
        .mac-dark .cal-seg-btn {
            color: rgba(255, 255, 255, 0.85);
        }
        .mac-light .cal-seg-btn {
            color: rgba(0, 0, 0, 0.75);
        }
        .mac-dark .cal-seg-btn:hover {
            background-color: rgba(255, 255, 255, 0.16);
            color: #ffffff;
        }
        .mac-light .cal-seg-btn:hover {
            background-color: rgba(0, 0, 0, 0.08);
            color: #000000;
        }

        .cal-seg-sep {
            min-width: 1px;
            margin: 3px 0;
        }
        .mac-dark .cal-seg-sep {
            background-color: rgba(255, 255, 255, 0.14);
        }
        .mac-light .cal-seg-sep {
            background-color: rgba(0, 0, 0, 0.12);
        }

        /* Today pill button */
        .cal-today-btn {
            border-radius: 9px;
            font-size: 11.5px;
            font-weight: 600;
            padding: 2px 10px;
            min-height: 24px;
            transition: background-color 100ms ease;
        }
        .mac-dark .cal-today-btn {
            background-color: rgba(255, 255, 255, 0.08);
            border: 0.5px solid rgba(255, 255, 255, 0.12);
            color: #ffffff;
        }
        .mac-light .cal-today-btn {
            background-color: rgba(0, 0, 0, 0.05);
            border: 0.5px solid rgba(0, 0, 0, 0.10);
            color: #1d1d1f;
        }
        .mac-dark .cal-today-btn:hover {
            background-color: rgba(255, 255, 255, 0.18);
        }
        .mac-light .cal-today-btn:hover {
            background-color: rgba(0, 0, 0, 0.10);
        }

        /* Subtle close button */
        .cal-close-btn {
            border-radius: 12px;
            font-size: 12px;
            padding: 0 6px;
            min-height: 24px;
            min-width: 24px;
            transition: background-color 100ms ease;
        }
        .mac-dark .cal-close-btn {
            color: rgba(255, 255, 255, 0.40);
        }
        .mac-light .cal-close-btn {
            color: rgba(0, 0, 0, 0.35);
        }
        .mac-dark .cal-close-btn:hover {
            background-color: rgba(255, 255, 255, 0.12);
            color: #ffffff;
        }
        .mac-light .cal-close-btn:hover {
            background-color: rgba(0, 0, 0, 0.08);
            color: #000000;
        }

        /* Weekday Header */
        .cal-header-day {
            font-size: 11px;
            font-weight: 600;
        }
        .mac-dark .cal-header-day {
            color: rgba(255, 255, 255, 0.45);
        }
        .mac-light .cal-header-day {
            color: rgba(0, 0, 0, 0.45);
        }

        .cal-header-weekend {
            font-size: 11px;
            font-weight: 600;
        }
        .mac-dark .cal-header-weekend {
            color: #ff6961;
        }
        .mac-light .cal-header-weekend {
            color: #ff3b30;
        }

        /* Day cell */
        .cal-day-cell {
            background-color: transparent;
            border-radius: 13px;
            padding: 2px 0px;
            margin: 1px;
            min-width: 36px;
            min-height: 38px;
            transition: background-color 100ms ease;
        }
        .mac-dark .cal-day-cell:hover {
            background-color: rgba(255, 255, 255, 0.09);
        }
        .mac-light .cal-day-cell:hover {
            background-color: rgba(0, 0, 0, 0.06);
        }

        /* Today highlight: Apple signature red circular dot badge (chấm tròn đỏ) */
        .cal-solar-today {
            background-color: #ff3b30;
            color: #ffffff;
            border-radius: 9999px;
            min-width: 25px;
            min-height: 25px;
            box-shadow: 0 2px 6px rgba(255, 59, 48, 0.45);
        }
        .cal-day-today {
            background-color: transparent;
        }
        .mac-dark .cal-day-today:hover {
            background-color: rgba(255, 255, 255, 0.09);
        }
        .mac-light .cal-day-today:hover {
            background-color: rgba(0, 0, 0, 0.06);
        }

        /* Selected day highlight */
        .mac-dark .cal-day-selected {
            background-color: rgba(0, 122, 255, 0.22);
            border: 1.5px solid #007aff;
            border-radius: 13px;
        }
        .mac-light .cal-day-selected {
            background-color: rgba(0, 122, 255, 0.15);
            border: 1.5px solid #007aff;
            border-radius: 13px;
        }

        /* Bottom Detail Info Card */
        .cal-info-card {
            border-radius: 14px;
            padding: 10px 14px;
        }
        .mac-dark .cal-info-card {
            background-color: rgba(255, 255, 255, 0.05);
            border: 0.5px solid rgba(255, 255, 255, 0.10);
        }
        .mac-light .cal-info-card {
            background-color: rgba(0, 0, 0, 0.04);
            border: 0.5px solid rgba(0, 0, 0, 0.08);
        }
        .cal-info-sep {
            margin: 3px 0px;
        }
        .mac-dark .cal-info-sep {
            background-color: rgba(255, 255, 255, 0.08);
        }
        .mac-light .cal-info-sep {
            background-color: rgba(0, 0, 0, 0.07);
        }
        """.encode('utf-8')
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 100
            )

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_name("calendar-popover-box")
        self.main_box.get_style_context().add_class("mac-dark" if self.is_dark else "mac-light")
        self.main_box.set_margin_start(self.pad)
        self.main_box.set_margin_end(self.pad)
        self.main_box.set_margin_top(self.pad)
        self.main_box.set_margin_bottom(self.pad)
        self.add(self.main_box)

        # 1. Top Navigation Bar: Month/Year + Segmented Prev/Next + Today + Close
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        nav_bar.set_margin_bottom(2)

        # Month & Year title
        self.title_lbl = Gtk.Label()
        self.title_lbl.get_style_context().add_class("cal-title-lbl")
        nav_bar.pack_start(self.title_lbl, False, False, 2)

        # Right Controls: Segmented [ ‹ | › ] + [ Hôm Nay ] + [ ✕ ]
        nav_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        # Segmented Prev/Next capsule
        seg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        seg_box.get_style_context().add_class("cal-segmented-box")

        self.prev_btn = Gtk.Button(label="‹")
        self.prev_btn.get_style_context().add_class("cal-seg-btn")
        self.prev_btn.connect("clicked", lambda _: self._change_month(-1))

        sep_line = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep_line.get_style_context().add_class("cal-seg-sep")

        self.next_btn = Gtk.Button(label="›")
        self.next_btn.get_style_context().add_class("cal-seg-btn")
        self.next_btn.connect("clicked", lambda _: self._change_month(1))

        seg_box.pack_start(self.prev_btn, False, False, 0)
        seg_box.pack_start(sep_line, False, False, 0)
        seg_box.pack_start(self.next_btn, False, False, 0)
        nav_controls.pack_start(seg_box, False, False, 0)

        # Today button
        self.today_btn = Gtk.Button()
        self.today_btn.get_style_context().add_class("cal-today-btn")
        self.today_btn.connect("clicked", lambda _: self._go_today())
        nav_controls.pack_start(self.today_btn, False, False, 0)

        # Subtle close button
        self.close_btn = Gtk.Button(label="✕")
        self.close_btn.get_style_context().add_class("cal-close-btn")
        self.close_btn.connect("clicked", lambda _: self.destroy())
        nav_controls.pack_start(self.close_btn, False, False, 0)

        nav_bar.pack_end(nav_controls, False, False, 0)
        self.main_box.pack_start(nav_bar, False, False, 0)

        # 2. Weekday Header Row (T2 to CN)
        col_headers = localized_weekday_names(get_current_language(), fallback=DAY_COLS_VI)
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        hdr_box.set_homogeneous(True)
        self.header_labels = []
        for idx, name in enumerate(col_headers):
            lbl = Gtk.Label(label=name)
            self.header_labels.append(lbl)
            if idx >= 5:
                lbl.get_style_context().add_class("cal-header-weekend")
            else:
                lbl.get_style_context().add_class("cal-header-day")
            hdr_box.pack_start(lbl, True, True, 0)
        self.main_box.pack_start(hdr_box, False, False, 0)

        # 3. Calendar Month Grid Container
        self.grid_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_box.pack_start(self.grid_container, True, True, 0)

        # 4. Detailed Day Info Glass Card
        self.info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.info_box.get_style_context().add_class("cal-info-card")

        self.solar_info_lbl = Gtk.Label()
        self.solar_info_lbl.set_xalign(0.0)
        self.solar_info_lbl.set_line_wrap(True)

        info_sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        info_sep.get_style_context().add_class("cal-info-sep")

        self.lunar_info_lbl = Gtk.Label()
        self.lunar_info_lbl.set_xalign(0.0)
        self.lunar_info_lbl.set_line_wrap(True)

        self.extra_info_lbl = Gtk.Label()
        self.extra_info_lbl.set_xalign(0.0)
        self.extra_info_lbl.set_line_wrap(True)

        self.info_box.pack_start(self.solar_info_lbl, False, False, 0)
        self.info_box.pack_start(info_sep, False, False, 2)
        self.info_box.pack_start(self.lunar_info_lbl, False, False, 0)
        self.info_box.pack_start(self.extra_info_lbl, False, False, 0)
        self.main_box.pack_start(self.info_box, False, False, 0)

        self._build_grid()
        add_language_listener(lambda *_: GLib.idle_add(self._refresh_language))
        self._retranslate_controls()
        self._update_info(self.selected_day)

    def _retranslate_controls(self):
        lang = get_current_language()
        self.prev_btn.set_tooltip_text(t("calendar_prev_month", "Previous month"))
        self.next_btn.set_tooltip_text(t("calendar_next_month", "Next month"))
        self.today_btn.set_label(t("calendar_today", "Today"))
        self.today_btn.set_tooltip_text(t("calendar_today_tooltip", "Return to today"))
        self.close_btn.set_tooltip_text(t("calendar_close_tooltip", "Close calendar (Esc)"))
        for label, text in zip(self.header_labels, localized_weekday_names(lang, fallback=DAY_COLS_VI)):
            label.set_text(text)

    def _refresh_language(self):
        self.set_title(t("calendar_title", "macOS Calendar & Lunar Calendar"))
        self._retranslate_controls()
        self._build_grid()
        self._update_info(self.selected_day)
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

        # macOS Frosted Glass Card Background (Translucent)
        self._path_squircle(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        if self.is_dark:
            pat = cairo.LinearGradient(x, y, x, y + h)
            pat.add_color_stop_rgba(0.0, 0.08, 0.10, 0.14, 0.32)
            pat.add_color_stop_rgba(1.0, 0.04, 0.05, 0.08, 0.40)
            cr.set_source(pat)
            cr.paint()

            sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
            sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.08)
            sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
            cr.set_source(sheen)
            cr.paint()
        else:
            pat = cairo.LinearGradient(x, y, x, y + h)
            pat.add_color_stop_rgba(0.0, 0.98, 0.98, 1.0, 0.45)
            pat.add_color_stop_rgba(1.0, 0.92, 0.94, 0.97, 0.55)
            cr.set_source(pat)
            cr.paint()

            sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
            sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.25)
            sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
            cr.set_source(sheen)
            cr.paint()

        cr.restore()

        # Crisp specular rim
        self._path_squircle(cr, x, y, w, h, r)
        rim = cairo.LinearGradient(x, y, x, y + h)
        if self.is_dark:
            rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.22)
            rim.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.08)
            rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.04)
        else:
            rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.70)
            rim.add_color_stop_rgba(0.5, 0.0, 0.0, 0.0, 0.06)
            rim.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.04)
        cr.set_source(rim)
        cr.set_line_width(1.0)
        cr.stroke()

        return False

    def _on_button_press(self, widget, event):
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

    def _change_month(self, delta):
        self.cur_month += delta
        if self.cur_month < 1:
            self.cur_month = 12
            self.cur_year -= 1
        elif self.cur_month > 12:
            self.cur_month = 1
            self.cur_year += 1
        max_days = calendar.monthrange(self.cur_year, self.cur_month)[1]
        if self.selected_day > max_days:
            self.selected_day = max_days
        self._build_grid()
        self._update_info(self.selected_day)

    def _go_today(self):
        now = datetime.datetime.now()
        self.cur_year = now.year
        self.cur_month = now.month
        self.selected_day = now.day
        self._build_grid()
        self._update_info(self.selected_day)

    def _build_grid(self):
        for child in self.grid_container.get_children():
            self.grid_container.remove(child)

        self.title_lbl.set_text(t("calendar_month_year", "Month {month}, {year}", month=self.cur_month, year=self.cur_year))

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        grid.set_column_spacing(2)
        grid.set_row_spacing(2)

        now = datetime.datetime.now()
        cal = calendar.Calendar(firstweekday=0) # 0 = Monday
        month_dates = cal.monthdatescalendar(self.cur_year, self.cur_month)

        for row_idx, week in enumerate(month_dates[:6]):
            for col_idx, dt in enumerate(week):
                btn = Gtk.Button()
                btn.get_style_context().add_class("cal-day-cell")

                in_current_month = (dt.month == self.cur_month)
                is_today = (dt.day == now.day and dt.month == now.month and dt.year == now.year)
                is_selected = (dt.day == self.selected_day and in_current_month)

                if is_today:
                    btn.get_style_context().add_class("cal-day-today")
                elif is_selected:
                    btn.get_style_context().add_class("cal-day-selected")

                # Day cell content: Solar on top, Lunar below
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                vbox.set_valign(Gtk.Align.CENTER)
                vbox.set_halign(Gtk.Align.CENTER)

                s_lbl = Gtk.Label(label=str(dt.day))
                s_lbl.set_xalign(0.5)
                s_lbl.set_yalign(0.5)
                # Lunar date calculation
                ld, lm, _, _ = solar_to_lunar(dt.day, dt.month, dt.year)
                lunar_str = f"{ld}/{lm}" if ld == 1 else str(ld)
                l_lbl = Gtk.Label(label=lunar_str)
                l_lbl.set_xalign(0.5)

                if is_today:
                    s_lbl.get_style_context().add_class("cal-solar-today")
                    s_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0))
                    s_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Bold 11.5"))
                    if ld == 1 or ld == 15:
                        gold_color = Gdk.RGBA(0.99, 0.78, 0.20, 1.0) if self.is_dark else Gdk.RGBA(0.85, 0.55, 0.0, 1.0)
                        l_lbl.override_color(Gtk.StateFlags.NORMAL, gold_color)
                        l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Bold 7.5"))
                    else:
                        today_lunar = Gdk.RGBA(1.0, 0.45, 0.42, 1.0) if self.is_dark else Gdk.RGBA(0.85, 0.22, 0.22, 1.0)
                        l_lbl.override_color(Gtk.StateFlags.NORMAL, today_lunar)
                        l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Bold 7.5"))
                elif is_selected:
                    sel_color = Gdk.RGBA(1.0, 1.0, 1.0, 1.0) if self.is_dark else Gdk.RGBA(0.0, 0.48, 1.0, 1.0)
                    s_lbl.override_color(Gtk.StateFlags.NORMAL, sel_color)
                    s_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Bold 11.5"))
                    l_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.85, 0.92, 1.0, 0.90) if self.is_dark else Gdk.RGBA(0.0, 0.48, 1.0, 0.9))
                    l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Medium 7.5"))
                elif in_current_month:
                    if col_idx >= 5: # Weekend
                        wk_color = Gdk.RGBA(1.0, 0.42, 0.38, 0.95) if self.is_dark else Gdk.RGBA(0.9, 0.2, 0.15, 0.95)
                        s_lbl.override_color(Gtk.StateFlags.NORMAL, wk_color)
                    else:
                        norm_color = Gdk.RGBA(0.96, 0.96, 0.98, 0.95) if self.is_dark else Gdk.RGBA(0.12, 0.12, 0.13, 0.95)
                        s_lbl.override_color(Gtk.StateFlags.NORMAL, norm_color)
                    s_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Semi-Bold 11.5"))

                    if ld == 1 or ld == 15:
                        gold_color = Gdk.RGBA(0.99, 0.78, 0.20, 1.0) if self.is_dark else Gdk.RGBA(0.85, 0.55, 0.0, 1.0)
                        l_lbl.override_color(Gtk.StateFlags.NORMAL, gold_color) # Gold for Mùng 1 / Rằm
                        l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu Bold 8"))
                    elif col_idx >= 5:
                        wk_lunar = Gdk.RGBA(1.0, 0.55, 0.55, 0.65) if self.is_dark else Gdk.RGBA(0.9, 0.3, 0.3, 0.6)
                        l_lbl.override_color(Gtk.StateFlags.NORMAL, wk_lunar)
                        l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu 7.5"))
                    else:
                        sub_lunar = Gdk.RGBA(0.70, 0.72, 0.78, 0.60) if self.is_dark else Gdk.RGBA(0.35, 0.35, 0.40, 0.60)
                        l_lbl.override_color(Gtk.StateFlags.NORMAL, sub_lunar)
                        l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu 7.5"))
                else:
                    # Outside current month (subtly dimmed)
                    dim_solar = Gdk.RGBA(1.0, 1.0, 1.0, 0.22) if self.is_dark else Gdk.RGBA(0.0, 0.0, 0.0, 0.22)
                    dim_lunar = Gdk.RGBA(1.0, 1.0, 1.0, 0.14) if self.is_dark else Gdk.RGBA(0.0, 0.0, 0.0, 0.14)
                    s_lbl.override_color(Gtk.StateFlags.NORMAL, dim_solar)
                    s_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu 10.5"))
                    l_lbl.override_color(Gtk.StateFlags.NORMAL, dim_lunar)
                    l_lbl.override_font(Pango.FontDescription("-apple-system, SF Pro Text, Inter, Ubuntu 7.0"))

                vbox.pack_start(s_lbl, False, False, 0)
                vbox.pack_start(l_lbl, False, False, 0)
                btn.add(vbox)

                btn.connect("clicked", lambda b, d=dt: self._on_date_clicked(d))
                grid.attach(btn, col_idx, row_idx, 1, 1)

        self.grid_container.pack_start(grid, True, True, 0)
        self.grid_container.show_all()

    def _on_date_clicked(self, dt):
        if dt.month != self.cur_month or dt.year != self.cur_year:
            self.cur_month = dt.month
            self.cur_year = dt.year
        self.selected_day = dt.day
        self._build_grid()
        self._update_info(self.selected_day)

    def _select_day(self, day_num):
        self.selected_day = day_num
        self._build_grid()
        self._update_info(day_num)

    def _update_info(self, day_num):
        dt = datetime.date(self.cur_year, self.cur_month, day_num)
        weekday_idx = dt.weekday()
        lang = get_current_language()
        weekday_name = localized_weekday_names(lang, width="wide", fallback=WEEKDAY_NAMES_VI)[weekday_idx]

        ld, lm, ly, is_leap = solar_to_lunar(day_num, self.cur_month, self.cur_year)
        can_chi_year = get_can_chi(ly)
        leap_text = t("calendar_leap", " (Leap)") if is_leap else ""

        now = datetime.datetime.now()
        is_today = (now.year == self.cur_year and now.month == self.cur_month and now.day == day_num)

        text_color = "#ffffff" if self.is_dark else "#1d1d1f"
        sub_text_color = "#cbd5e1" if self.is_dark else "#475569"
        today_badge = f"  <span bgcolor='#ff3b30' color='#ffffff' font_weight='bold' font_size='small'>  {t('calendar_today_badge', 'TODAY')}  </span>" if is_today else ""

        self.solar_info_lbl.set_markup(
            f"<span font_weight='bold' font_size='large' color='{text_color}'>{weekday_name}</span>, <span color='{sub_text_color}'>{t('calendar_day_prefix', 'day')} {day_num:02d}/{self.cur_month:02d}/{self.cur_year}</span>{today_badge}"
        )

        lunar_color = "#38bdf8" if self.is_dark else "#0284c7"
        self.lunar_info_lbl.set_markup(
            f"🌙  <span color='{lunar_color}'><b>{t('calendar_lunar', 'Lunar calendar')}:</b> {t('calendar_day', 'Day')} {ld} {t('calendar_month', 'month')} {lm}{leap_text} {t('calendar_year', 'year')} {can_chi_year}</span>"
        )

        # Golden hour calculation indicator
        golden_hours = ["Tý (23-1)", "Sửu (1-3)", "Thìn (7-9)", "Tỵ (9-11)", "Mùi (13-15)", "Tuất (19-21)"]
        amber_color = "#fbbf24" if self.is_dark else "#b45309"
        self.extra_info_lbl.set_markup(
            f"✨  <span color='{amber_color}'><b>{t('calendar_lucky_hours', 'Lucky hours')}:</b> {', '.join(golden_hours[:4])}…</span>"
        )

    def _on_focus_out(self, widget, event):
        GLib.idle_add(self._auto_close_on_unfocus)
        return False

    def _auto_close_on_unfocus(self):
        if not self.get_visible() or self.in_destruction():
            return
        if not self.has_toplevel_focus() or not self.is_active():
            self.destroy()

    def destroy(self):
        if self.parent_widget:
            import time
            self.parent_widget._last_closed_time = time.time()
            if hasattr(self.parent_widget, "_calendar_window"):
                self.parent_widget._calendar_window = None
        super().destroy()

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

if __name__ == "__main__":
    win = DesktopCalendarWidget()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
