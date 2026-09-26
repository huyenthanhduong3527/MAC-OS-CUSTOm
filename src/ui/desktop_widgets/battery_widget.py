"""
Apple macOS Desktop Battery Rings Widget.
Displays 4 circular battery gauge rings (Laptop, AirPods with charging bolt ⚡, Case, Mouse)
with Apple green progress arcs, device icons, and percentage values.
"""

import math
import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo
from src.config import config
from src.modules.battery import BatteryManager
from src.ui.desktop_widgets import (
    register_widget,
    animate_widget_open,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)
from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item
from src.utils.i18n import t

class DesktopBatteryWidget(Gtk.Window):
    def __init__(self, battery_mgr=None, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_close = on_close
        self.battery_mgr = battery_mgr or BatteryManager(on_update=self._on_battery_update)

        self.layout_mode = config.get("desktop_battery_layout", "compact")
        if self.layout_mode == "compact":
            self.card_w = 112
            self.card_h = 100
            self.pad = 8
            self.radius = 22.0
        else:
            self.card_w = 330
            self.card_h = 135
            self.pad = 12
            self.radius = 26.0
        self.total_w = self.card_w + 2 * self.pad
        self.total_h = self.card_h + 2 * self.pad

        self.keep_below = True
        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
        except Exception:
            self.dark_mode = False

        # Window setup
        self.set_title("macOS Battery Rings Widget")
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
        self.set_wmclass("desktop-widget-battery", "DesktopWidgetBattery")
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

        # Position window from config
        self._current_x = int(config.get("desktop_battery_x", 30))
        self._current_y = int(config.get("desktop_battery_y", 600))
        self.move(self._current_x, self._current_y)

        # Events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )

        register_widget(self)
        self.is_locked = config.get("lock_desktop_widgets", True)

        self._dragging = False
        self._has_moved = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = self._current_x
        self._win_start_y = self._current_y

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("map-event", self._on_map_event)

    def _on_map_event(self, widget, event):
        GLib.idle_add(lambda: self.move(self._current_x, self._current_y))
        return False

    def set_locked(self, locked: bool):
        """Locks or unlocks battery widget movement."""
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

    def set_layout_mode(self, mode: str):
        """Switches between compact (single MacBook card matching photo) and 4-ring layouts."""
        self.layout_mode = mode
        config.set("desktop_battery_layout", mode)
        if mode == "compact":
            self.card_w = 112
            self.card_h = 100
            self.pad = 8
            self.radius = 22.0
        else:
            self.card_w = 330
            self.card_h = 135
            self.pad = 12
            self.radius = 26.0
        self.total_w = self.card_w + 2 * self.pad
        self.total_h = self.card_h + 2 * self.pad
        self.resize(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)
        self.queue_draw()

    def _on_battery_update(self):
        self.queue_draw()

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

    def _draw_text(self, cr, x, y, text, font_desc_str, color, align="center"):
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

    def _draw_device_icon(self, cr, cx, cy, dev_type, color=(1.0, 1.0, 1.0, 0.95)):
        """Draw minimalist crisp vector icons for Laptop, AirPods, Case, and Mouse."""
        cr.save()
        cr.set_source_rgba(*color)
        cr.set_line_width(1.4)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if dev_type == "laptop":
            # Screen
            sw, sh = 16.0, 10.0
            sx, sy = cx - sw / 2.0, cy - sh / 2.0 - 1.5
            self._path_rounded_rect(cr, sx, sy, sw, sh, 2.0)
            cr.stroke()
            # Base
            bw = 20.0
            by = cy + sh / 2.0 - 0.5
            cr.move_to(cx - bw / 2.0, by)
            cr.line_to(cx + bw / 2.0, by)
            cr.stroke()

        elif dev_type == "earbuds":
            # Left earbud
            cr.arc(cx - 4.5, cy - 3.5, 3.2, 0, 2 * math.pi)
            cr.stroke()
            cr.move_to(cx - 3.5, cy - 1.0)
            cr.line_to(cx - 1.5, cy + 6.0)
            cr.stroke()

            # Right earbud
            cr.arc(cx + 4.5, cy - 3.5, 3.2, 0, 2 * math.pi)
            cr.stroke()
            cr.move_to(cx + 3.5, cy - 1.0)
            cr.line_to(cx + 1.5, cy + 6.0)
            cr.stroke()

        elif dev_type == "case":
            # Earbuds Case
            cw, ch = 14.0, 14.0
            cx0, cy0 = cx - cw / 2.0, cy - ch / 2.0
            self._path_rounded_rect(cr, cx0, cy0, cw, ch, 4.0)
            cr.stroke()
            # LED dot
            cr.arc(cx, cy, 1.2, 0, 2 * math.pi)
            cr.fill()

        elif dev_type == "mouse":
            # Mouse body
            mw, mh = 12.0, 17.0
            mx0, my0 = cx - mw / 2.0, cy - mh / 2.0
            self._path_rounded_rect(cr, mx0, my0, mw, mh, 5.5)
            cr.stroke()
            # Scroll line
            cr.move_to(cx, my0 + 2.5)
            cr.line_to(cx, my0 + 6.5)
            cr.stroke()

        else:
            # Generic accessory bolt
            cr.move_to(cx + 1.0, cy - 6.0)
            cr.line_to(cx - 3.5, cy)
            cr.line_to(cx, cy)
            cr.line_to(cx - 1.0, cy + 6.0)
            cr.line_to(cx + 3.5, cy)
            cr.line_to(cx, cy)
            cr.close_path()
            cr.fill()

        cr.restore()

    def _draw_charging_bolt(self, cr, cx, cy):
        """Draws a mini bright yellow lightning bolt badge."""
        cr.save()
        cr.set_source_rgba(1.0, 0.84, 0.0, 1.0) # #ffd700
        cr.new_sub_path()
        cr.move_to(cx + 1.5, cy - 5.5)
        cr.line_to(cx - 3.0, cy + 0.5)
        cr.line_to(cx + 0.5, cy + 0.5)
        cr.line_to(cx - 1.5, cy + 5.5)
        cr.line_to(cx + 3.0, cy - 0.5)
        cr.line_to(cx - 0.5, cy - 0.5)
        cr.close_path()
        cr.fill()
        cr.restore()

    def _on_draw(self, widget, cr):
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        x = self.pad
        y = self.pad
        w = self.card_w
        h = self.card_h
        r = self.radius
        dark = getattr(self, "dark_mode", False)

        # 1. Card Background (Translucent Apple Glass - Wallpaper visible)
        self._path_rounded_rect(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        if dark:
            # Apple dark battery glass card
            base_pat = cairo.LinearGradient(x, y, x, y + h)
            base_pat.add_color_stop_rgba(0.0, 0.08, 0.09, 0.12, 0.88)
            base_pat.add_color_stop_rgba(1.0, 0.05, 0.06, 0.08, 0.92)
            cr.set_source(base_pat)
            cr.paint()

            sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
            sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.06)
            sheen.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.01)
            sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
            cr.set_source(sheen)
            cr.paint()
        else:
            base_pat = cairo.LinearGradient(x, y, x, y + h)
            base_pat.add_color_stop_rgba(0.0, 0.98, 0.98, 1.0, 0.88)
            base_pat.add_color_stop_rgba(1.0, 0.92, 0.94, 0.97, 0.92)
            cr.set_source(base_pat)
            cr.paint()

            sheen = cairo.LinearGradient(x, y, x, y + h * 0.40)
            sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.15)
            sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
            cr.set_source(sheen)
            cr.paint()

        cr.restore()

        # 2. Subtle glass rim (Subtle and razor-sharp, no blurry outline)
        self._path_rounded_rect(cr, x, y, w, h, r)
        rim = cairo.LinearGradient(x, y, x, y + h)
        if dark:
            rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.10)
            rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.04)
            rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.06)
        else:
            rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.35)
            rim.add_color_stop_rgba(0.5, 0.0, 0.0, 0.0, 0.04)
            rim.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.02)
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

        if getattr(self, "layout_mode", "compact") == "compact":
            # -------------------------------------------------------------
            # LAYOUT: COMPACT LAPTOP CARD (MATCHING REFERENCE PHOTO)
            # -------------------------------------------------------------
            dev = self.battery_mgr.devices[0] if self.battery_mgr.devices else None
            pct = dev.percentage if dev else 100
            charging = dev.charging if dev else False

            center_x = x + w / 2.0

            # Laptop illustration with glowing cyan screen
            sw, sh = 40.0, 24.0
            sx, sy = center_x - sw / 2.0, y + 14.0
            self._path_rounded_rect(cr, sx, sy, sw, sh, 3.0)
            cr.set_source_rgba(0.12, 0.65, 0.95, 0.95) # cyan blue screen
            cr.fill_preserve()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.5)
            cr.set_line_width(1.0)
            cr.stroke()

            # Keyboard base
            bw = sw + 10.0
            by = sy + sh + 1.0
            self._path_rounded_rect(cr, center_x - bw / 2.0, by, bw, 3.5, 1.5)
            cr.set_source_rgba(0.85, 0.88, 0.92, 0.90)
            cr.fill()

            # Notch under trackpad
            cr.move_to(center_x - 3.5, by)
            cr.line_to(center_x + 3.5, by)
            cr.set_source_rgba(0.4, 0.45, 0.5, 0.8)
            cr.set_line_width(1.0)
            cr.stroke()

            # Device label & percentage e.g. "macpro (100%)"
            import socket
            hostname = socket.gethostname().lower()
            dev_name = hostname if ("mac" in hostname or "pro" in hostname) else "macpro"
            name_text = f"{dev_name} ({pct}%)"
            text_color = (0.95, 0.96, 0.98, 0.95) if dark else (0.12, 0.14, 0.18, 0.95)
            self._draw_text(cr, center_x, y + 50.0, name_text, "-apple-system, Inter, Ubuntu Semi-Bold 10.0", text_color, align="center")

            # Small bottom row: status or lightning bolt if charging
            bolt_y = y + 74.0
            if charging:
                self._draw_charging_bolt(cr, center_x, bolt_y)
            else:
                pw, ph = 20.0, 8.5
                px = center_x - pw / 2.0
                self._path_rounded_rect(cr, px, bolt_y - ph / 2.0, pw, ph, 2.5)
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.35)
                cr.set_line_width(1.0)
                cr.stroke()
                cr.move_to(px + pw + 1.2, bolt_y - 2.0)
                cr.line_to(px + pw + 1.2, bolt_y + 2.0)
                cr.stroke()
                frac = max(0.05, min(1.0, pct / 100.0))
                fill_color = (0.20, 0.85, 0.42, 0.95) if pct > 20 else (0.95, 0.35, 0.25, 0.95)
                self._path_rounded_rect(cr, px + 1.5, bolt_y - ph / 2.0 + 1.5, (pw - 3.0) * frac, ph - 3.0, 1.5)
                cr.set_source_rgba(*fill_color)
                cr.fill()

            return False

        # -------------------------------------------------------------
        # LAYOUT: FOUR BATTERY RINGS
        # -------------------------------------------------------------
        devices = self.battery_mgr.devices[:4]
        num_devs = len(devices) if devices else 1
        slot_w = w / float(num_devs)
        ring_r = 23.0
        ring_thickness = 4.0
        ring_y = y + 48.0

        track_rgba = (1.0, 1.0, 1.0, 0.16) if dark else (0.84, 0.87, 0.92, 0.90)
        icon_rgba = (1.0, 1.0, 1.0, 0.95) if dark else (0.15, 0.18, 0.22, 0.95)
        pct_color = (0.96, 0.97, 0.99, 0.95) if dark else (0.12, 0.14, 0.18, 0.95)

        for i, dev in enumerate(devices):
            cx = x + i * slot_w + slot_w / 2.0
            cy = ring_y
            frac = max(0.0, min(1.0, dev.percentage / 100.0))

            # A. Background track ring
            cr.save()
            cr.set_line_width(ring_thickness)
            cr.set_source_rgba(*track_rgba)
            cr.arc(cx, cy, ring_r, 0, 2 * math.pi)
            cr.stroke()
            cr.restore()

            # B. Active Battery Ring Arc (Apple Green / Amber if low)
            cr.save()
            cr.set_line_width(ring_thickness)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)

            if frac < 0.20 and not dev.charging:
                cr.set_source_rgba(0.96, 0.45, 0.15, 1.0)
            else:
                cr.set_source_rgba(0.18, 0.84, 0.38, 1.0)

            start_angle = -math.pi / 2.0
            end_angle = start_angle + frac * 2 * math.pi
            if frac > 0.02:
                cr.arc(cx, cy, ring_r, start_angle, end_angle)
                cr.stroke()
            cr.restore()

            # C. Charging lightning bolt indicator
            if dev.charging:
                self._draw_charging_bolt(cr, cx, cy - ring_r - 2.5)

            # D. Device Vector Icon in center
            self._draw_device_icon(cr, cx, cy, dev.dev_type, color=icon_rgba)

            # E. Percentage text below ring: "83%", "91%", ...
            pct_text = f"{dev.percentage}%"
            self._draw_text(cr, cx, cy + ring_r + 14.0, pct_text, "-apple-system, Inter, Ubuntu Semi-Bold 13", pct_color, align="center")

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
                config.set("desktop_battery_x", int(self._current_x))
                config.set("desktop_battery_y", int(self._current_y))
            self._has_moved = False
            return True
        return False

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

        pin_label = t("widget_pin_desktop", "Ghim Nền Desktop") if not self.keep_below else t("widget_float_window", "Nổi Trên Cửa Sổ")
        pin_icon = "pin" if not self.keep_below else "pin.slash"
        pin_item = create_mac_menu_item(pin_icon, pin_label, self._toggle_keep_below)
        menu.append(pin_item)

        refresh_item = create_mac_menu_item("arrow.triangle.2.circlepath", t("battery_menu_refresh", "Cập Nhật Pin Thiết Bị"),
                                            lambda _: self.battery_mgr._poll_upower())
        menu.append(refresh_item)

        mode_label = t("battery_menu_to_rings", "Chuyển sang 4 Vòng Pin (Apple Rings)") if self.layout_mode == "compact" else t("battery_menu_to_compact", "Chuyển sang Chế độ Thu Gọn (MacBook)")
        mode_icon = "layout" if self.layout_mode == "compact" else "macbook"
        target_mode = "rings" if self.layout_mode == "compact" else "compact"
        layout_item = create_mac_menu_item(mode_icon, mode_label,
                                           lambda _, m=target_mode: self.set_layout_mode(m))
        menu.append(layout_item)

        menu.append(Gtk.SeparatorMenuItem())
        hide_item = create_mac_menu_item("xmark", t("battery_menu_hide", "Ẩn Widget Pin"),
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
        config.set("enable_desktop_battery", False)
        self.hide()
        if self.on_close:
            self.on_close()

    def show_widget(self):
        config.set("enable_desktop_battery", True)
        self.show_all()
        if getattr(self, "keep_below", True):
            self.set_keep_below(True)

    def destroy(self):
        unregister_widget(self)
        if self.battery_mgr:
            self.battery_mgr.stop()
        super().destroy()

if __name__ == "__main__":
    win = DesktopBatteryWidget()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
