"""
macOS Analog Clock Desktop Widget for Ubuntu Linux.
Renders an authentic, vector anti-aliased Apple squircle analog clock directly
on the desktop wallpaper with live ticking or smooth fluid sweep hands.
Supports dragging to any position, position memory, dark/light face, and context menu.
"""

import math
import time
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.config import config
from src.animator import SpringValue
from src.ui.desktop_widgets import (
    register_widget,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)
from src.utils.i18n import t

class DesktopClockWidget(Gtk.Window):
    def __init__(self, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.on_close = on_close
        self.size = config.get("desktop_clock_size", 180)
        self.pad = 16  # Padding for soft ambient drop shadow
        self.total_w = self.size + 2 * self.pad
        self.total_h = self.size + 2 * self.pad

        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
        except Exception:
            self.dark_mode = config.get("desktop_clock_dark_mode", False)
        self.smooth_seconds = config.get("desktop_clock_smooth_sec", True)
        self.keep_below = True

        # Spring Open Animation
        self.anim_scale = SpringValue(1.0, stiffness=260.0, damping=19.0)
        self.anim_alpha = SpringValue(1.0, stiffness=220.0, damping=21.0)
        self._anim_timer_id = None
        self._anim_last_time = 0.0

        # Window styling & desktop integration
        self.set_title("macOS Clock Widget")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.stick() # Visible across all workspaces
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.connect("map-event", lambda *_: self.set_keep_below(True) if getattr(self, "keep_below", True) else None)
        self.connect("realize", lambda *_: self.set_keep_below(True) if getattr(self, "keep_below", True) else None)
        self.set_wmclass("desktop-widget-clock", "DesktopWidgetClock")
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
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.get_style_context().add_class("transparent-window")
        self.get_style_context().add_class("desktop-widget-clock")

        # Position window from config
        self._current_x = int(config.get("desktop_clock_x", 1680))
        self._current_y = int(config.get("desktop_clock_y", 24))
        self.move(self._current_x, self._current_y)

        # Event handling for dragging & context menu
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        register_widget(self)
        self.is_locked = config.get("lock_desktop_widgets", True)

        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = self._current_x
        self._win_start_y = self._current_y

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("map-event", self._on_map_event)
        self.connect("realize", self._on_realize)

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
        """Locks or unlocks clock widget movement."""
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

        # Start animation timer
        self._timer_id = None
        self._start_timer()

    def _on_realize(self, widget):
        gdk_win = widget.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            cursor = Gdk.Cursor.new_from_name(display, "grab")
            if cursor:
                gdk_win.set_cursor(cursor)

    def _start_timer(self):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

        interval_ms = 50 if self.smooth_seconds else 1000
        self._timer_id = GLib.timeout_add(interval_ms, self._on_tick)

    def _on_tick(self):
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _on_system_theme_changed(self, *args):
        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
            self.queue_draw()
        except Exception:
            pass

    def _draw_squircle(self, cr, x, y, w, h, radius):
        """Draws an Apple-style continuous smooth curvature squircle."""
        cr.new_sub_path()
        cr.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
        cr.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _on_draw(self, widget, cr):
        # Clear transparent background
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
        w = self.size
        h = self.size
        radius = 38.0

        # 1. Card Background: Apple Frosted Glass (Translucent - Wallpaper visible)
        self._draw_squircle(cr, x, y, w, h, radius)
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
        self._draw_squircle(cr, x, y, w, h, radius)
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
            self._draw_squircle(cr, x, y, w, h, radius)
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.65)
            cr.set_line_width(2.0)
            cr.stroke()
            cr.restore()

        # 4. Dial Center & Geometry
        cx = x + w / 2.0
        cy = y + h / 2.0
        R = w * 0.44  # Outer dial radius (~79px on 180 size)

        # 5. Minute Tick Marks (60 subtle fine ticks)
        cr.set_line_width(1.1)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.35)

        r_min_in = R * 0.86
        r_min_out = R * 0.96

        for i in range(60):
            # Skip positions where hour marks sit
            if i % 5 == 0:
                continue
            angle = i * (math.pi / 30.0) - math.pi / 2.0
            cr.move_to(cx + r_min_in * math.cos(angle), cy + r_min_in * math.sin(angle))
            cr.line_to(cx + r_min_out * math.cos(angle), cy + r_min_out * math.sin(angle))
            cr.stroke()

        # 6. Hour Tick Marks (8 bold radial lines at 1, 2, 4, 5, 7, 8, 10, 11)
        cr.set_line_width(2.8)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        r_hr_in = R * 0.62
        r_hr_out = R * 0.96

        for h_idx in (1, 2, 4, 5, 7, 8, 10, 11):
            angle = h_idx * (math.pi / 6.0) - math.pi / 2.0
            # Shadow
            cr.save()
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.60)
            cr.move_to(cx + r_hr_in * math.cos(angle), cy + r_hr_in * math.sin(angle) + 1.2)
            cr.line_to(cx + r_hr_out * math.cos(angle), cy + r_hr_out * math.sin(angle) + 1.2)
            cr.stroke()
            cr.restore()

            cr.set_source_rgba(0.96, 0.98, 1.0, 0.95)
            cr.move_to(cx + r_hr_in * math.cos(angle), cy + r_hr_in * math.sin(angle))
            cr.line_to(cx + r_hr_out * math.cos(angle), cy + r_hr_out * math.sin(angle))
            cr.stroke()

        # 7. Numbers (12, 3, 6, 9)
        cr.select_font_face("Ubuntu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(23)

        r_num = R * 0.68
        numbers = [
            ("12", cx, cy - r_num + 3),
            ("3", cx + r_num - 1, cy + 1),
            ("6", cx, cy + r_num),
            ("9", cx - r_num + 1, cy + 1),
        ]

        for text, nx, ny in numbers:
            extents = cr.text_extents(text)
            tx = nx - (extents.width / 2.0 + extents.x_bearing)
            ty = ny - (extents.height / 2.0 + extents.y_bearing)
            # Soft shadow
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.60)
            cr.move_to(tx, ty + 1.2)
            cr.show_text(text)
            # Crisp white foreground
            cr.set_source_rgba(0.98, 0.99, 1.0, 0.95)
            cr.move_to(tx, ty)
            cr.show_text(text)

        # 8. Compute Angles from Current Time
        now = time.time()
        local = time.localtime(now)
        if self.smooth_seconds:
            sec_val = local.tm_sec + (now - int(now))
        else:
            sec_val = float(local.tm_sec)

        min_val = local.tm_min + sec_val / 60.0
        hr_val = (local.tm_hour % 12) + min_val / 60.0

        angle_hr = hr_val * (2.0 * math.pi / 12.0) - math.pi / 2.0
        angle_min = min_val * (2.0 * math.pi / 60.0) - math.pi / 2.0
        angle_sec = sec_val * (2.0 * math.pi / 60.0) - math.pi / 2.0

        # 9. Hour Hand (Rounded White Pill with Shadow)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(5.8)
        hr_len = R * 0.48

        # Shadow
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
        cr.move_to(cx - 3 * math.cos(angle_hr), cy - 3 * math.sin(angle_hr) + 1.5)
        cr.line_to(cx + hr_len * math.cos(angle_hr), cy + hr_len * math.sin(angle_hr) + 1.5)
        cr.stroke()
        cr.restore()

        cr.set_source_rgba(0.98, 0.99, 1.0, 1.0)
        cr.move_to(cx - 3 * math.cos(angle_hr), cy - 3 * math.sin(angle_hr))
        cr.line_to(cx + hr_len * math.cos(angle_hr), cy + hr_len * math.sin(angle_hr))
        cr.stroke()

        # 10. Minute Hand (Rounded White Pill with Shadow)
        cr.set_line_width(4.2)
        min_len = R * 0.76

        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
        cr.move_to(cx - 4 * math.cos(angle_min), cy - 4 * math.sin(angle_min) + 1.5)
        cr.line_to(cx + min_len * math.cos(angle_min), cy + min_len * math.sin(angle_min) + 1.5)
        cr.stroke()
        cr.restore()

        cr.set_source_rgba(0.98, 0.99, 1.0, 1.0)
        cr.move_to(cx - 4 * math.cos(angle_min), cy - 4 * math.sin(angle_min))
        cr.line_to(cx + min_len * math.cos(angle_min), cy + min_len * math.sin(angle_min))
        cr.stroke()

        # 11. Second Hand (Apple Radiant Orange Needle)
        # Apple Orange: #f59e0b / (0.96, 0.62, 0.05)
        cr.set_source_rgba(0.96, 0.62, 0.05, 1.0)
        cr.set_line_width(1.8)
        sec_len = R * 0.88

        cr.move_to(cx + 4.5 * math.cos(angle_sec), cy + 4.5 * math.sin(angle_sec))
        cr.line_to(cx + sec_len * math.cos(angle_sec), cy + sec_len * math.sin(angle_sec))
        cr.stroke()

        # 12. Center Pin / Ring Hub
        # Outer orange ring
        cr.set_line_width(1.6)
        cr.arc(cx, cy, 4.0, 0, 2 * math.pi)
        cr.stroke()

        # Inner center dot
        if self.dark_mode:
            cr.set_source_rgba(0.09, 0.11, 0.15, 1.0)
        else:
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.arc(cx, cy, 2.5, 0, 2 * math.pi)
        cr.fill()

        # Center micro pivot
        cr.set_source_rgba(0.10, 0.12, 0.16, 1.0)
        cr.arc(cx, cy, 1.2, 0, 2 * math.pi)
        cr.fill()

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
                return False

        elif event.button == 3:
            # Right click -> Context Menu
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

            if getattr(self, "_has_moved", False):
                config.set("desktop_clock_x", int(self._current_x))
                config.set("desktop_clock_y", int(self._current_y))
            self._has_moved = False
            return True
        return False

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

        # 2. Dark / Light Face toggle
        face_label = t("clock_menu_dark_face", "Chuyển Mặt Đồng Hồ Tối") if not self.dark_mode else t("clock_menu_light_face", "Chuyển Mặt Đồng Hồ Sáng")
        face_icon = "moon.fill" if not self.dark_mode else "sun.max"
        menu.append(create_mac_menu_item(face_icon, face_label, self._toggle_face_theme))

        # 3. Smooth / Ticking seconds toggle
        sec_label = t("clock_menu_smooth_sec", "Kim Giây Lướt Mượt (Smooth)") if not self.smooth_seconds else t("clock_menu_ticking_sec", "Kim Giây Nhảy Từng Giây")
        menu.append(create_mac_menu_item("clock", sec_label, self._toggle_smooth_sec))

        # 4. Pin to Desktop (Keep Below)
        pin_label = t("widget_pin_desktop", "Ghim Nền Desktop") if not self.keep_below else t("widget_float_window", "Nổi Trên Cửa Sổ")
        pin_icon = "pin" if not self.keep_below else "pin.slash"
        menu.append(create_mac_menu_item(pin_icon, pin_label, self._toggle_keep_below))

        menu.append(create_mac_menu_item("sparkles", t("widget_replay_open", "Phát lại hiệu ứng mở (Replay Open)"),
                                         lambda _: self.play_open_animation()))

        menu.append(Gtk.SeparatorMenuItem())

        # 5. Hide Widget
        menu.append(create_mac_menu_item("xmark", t("clock_menu_hide", "Ẩn Widget Đồng Hồ"),
                                         lambda _: self.hide_widget(), is_destructive=True))

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def _toggle_face_theme(self, _):
        self.dark_mode = not self.dark_mode
        config.set("desktop_clock_dark_mode", self.dark_mode)
        self.queue_draw()

    def _toggle_smooth_sec(self, _):
        self.smooth_seconds = not self.smooth_seconds
        config.set("desktop_clock_smooth_sec", self.smooth_seconds)
        self._start_timer()
        self.queue_draw()

    def _toggle_keep_below(self, _):
        self.keep_below = not self.keep_below
        if self.keep_below:
            self.set_keep_below(True)
            self.set_keep_above(False)
        else:
            self.set_keep_below(False)
            self.set_keep_above(True)

    def hide_widget(self):
        config.set("enable_desktop_clock", False)
        self.hide()
        if self.on_close:
            self.on_close()

    def show_widget(self):
        config.set("enable_desktop_clock", True)
        self.show_all()
        if getattr(self, "keep_below", True):
            self.set_keep_below(True)
        self.play_open_animation()

    def destroy(self):
        unregister_widget(self)
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        super().destroy()

if __name__ == "__main__":
    win = DesktopClockWidget()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
