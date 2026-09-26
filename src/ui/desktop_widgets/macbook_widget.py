"""
Desktop MacBook & Power Profile Battery Widget for Ubuntu Linux.
Displays a photorealistic MacBook laptop graphic with live battery status,
authentic macOS display wallpapers, dynamic battery pill, and a 3-mode power
profile switcher (Power Saver / Balanced / Performance).
Supports dynamic resizing via corner drag handle, mouse wheel scroll, and context menu.
Clicking on the MacBook opens the authentic 'About This Mac' hardware window.
"""

import math
import time
import subprocess
import re
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


class DesktopMacBookWidget(Gtk.Window):
    def __init__(self, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_close = on_close

        register_widget(self)
        self.is_locked = config.get("lock_desktop_widgets", True)

        # Base geometry at 1.0x scale (luxurious squircle card)
        self.base_card_w = 156.0
        self.base_card_h = 156.0
        self.base_pad = 12.0
        self.base_radius = 26.0
        self.base_total_w = self.base_card_w + 2 * self.base_pad
        self.base_total_h = self.base_card_h + 2 * self.base_pad

        # Scale factor (0.65x to 2.0x)
        raw_scale = config.get("desktop_macbook_scale", 1.0)
        try:
            self.scale = max(0.65, min(2.0, round(float(raw_scale), 2)))
        except Exception:
            self.scale = 1.0

        self.total_w = max(110, int(self.base_total_w * self.scale))
        self.total_h = max(110, int(self.base_total_h * self.scale))

        self.keep_below = True

        # Customization themes
        self.chassis_theme = config.get("desktop_macbook_chassis", "space_gray")
        self.wallpaper_theme = config.get("desktop_macbook_wallpaper", "sonoma")

        # Spring Open & Smooth Transition Animations
        self.anim_scale = SpringValue(1.0, stiffness=260.0, damping=19.0)
        self.anim_alpha = SpringValue(1.0, stiffness=220.0, damping=21.0)
        self._anim_timer_id = None
        self._anim_last_time = 0.0

        # Power profile state: 0 = power-saver, 1 = balanced, 2 = performance
        self.active_profile_idx = 1
        self._detect_initial_profile()
        self.anim_pill_idx = SpringValue(float(self.active_profile_idx), stiffness=280.0, damping=22.0)

        # Battery / device state
        self.device_name = config.get("desktop_macbook_name", "MacBook Pro")
        self.battery_pct = 100
        self.is_charging = True
        self.has_real_battery = False
        self._update_battery_status()

        # Window properties
        self.set_title("macOS MacBook Widget")
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
        self.set_wmclass("desktop-widget-macbook", "DesktopWidgetMacbook")
        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)

        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        # Position window from config (default placed neatly: x=30, y=600)
        self._current_x = int(config.get("desktop_macbook_x", 30))
        self._current_y = int(config.get("desktop_macbook_y", 600))
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

        # Hover states
        self._hover_mac = False
        self._hover_pill_idx = -1
        self._hover_resize = False

        # Events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.SCROLL_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        self.connect("scroll-event", self._on_scroll)
        self.connect("map-event", self._on_map_event)

        # Periodic refresh every 10s for battery & power profile
        self._timer_id = GLib.timeout_add_seconds(10, self._on_tick)

    def _detect_initial_profile(self):
        try:
            res = subprocess.check_output(["powerprofilesctl", "get"], stderr=subprocess.DEVNULL, timeout=1.0).decode().strip()
            if "power-saver" in res:
                self.active_profile_idx = 0
            elif "performance" in res:
                self.active_profile_idx = 2
            else:
                self.active_profile_idx = 1
        except Exception:
            self.active_profile_idx = 1

    def _update_battery_status(self):
        try:
            # 1. Try checking primary DisplayDevice
            out = subprocess.check_output(
                ["upower", "-i", "/org/freedesktop/UPower/devices/DisplayDevice"],
                stderr=subprocess.DEVNULL, timeout=1.0
            ).decode()
            pct_match = re.search(r"percentage:\s+(\d+)%", out)
            state_match = re.search(r"state:\s+(\w+)", out)
            if pct_match and int(pct_match.group(1)) > 0:
                self.battery_pct = int(pct_match.group(1))
                self.is_charging = (state_match.group(1) in ("charging", "fully-charged")) if state_match else True
                self.has_real_battery = True
                return

            # 2. Try querying any individual battery device
            dev_list = subprocess.check_output(["upower", "-e"], stderr=subprocess.DEVNULL, timeout=1.0).decode().splitlines()
            for dev in dev_list:
                if "battery" in dev.lower():
                    b_out = subprocess.check_output(["upower", "-i", dev], stderr=subprocess.DEVNULL, timeout=1.0).decode()
                    b_pct = re.search(r"percentage:\s+(\d+)%", b_out)
                    b_state = re.search(r"state:\s+(\w+)", b_out)
                    if b_pct:
                        self.battery_pct = int(b_pct.group(1))
                        self.is_charging = (b_state.group(1) in ("charging", "fully-charged")) if b_state else True
                        self.has_real_battery = True
                        return

            # 3. Fallback: AC Desktop or full charge
            self.battery_pct = 100
            self.is_charging = True
            self.has_real_battery = False
        except Exception:
            self.battery_pct = 100
            self.is_charging = True
            self.has_real_battery = False

    def _on_tick(self):
        self._update_battery_status()
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def set_scale(self, new_scale, save=True):
        """Scales the widget dynamically and updates the GTK window geometry."""
        new_scale = max(0.65, min(2.0, round(float(new_scale), 2)))
        self.scale = new_scale
        if save:
            config.set("desktop_macbook_scale", self.scale)

        self.total_w = max(110, int(self.base_total_w * self.scale))
        self.total_h = max(110, int(self.base_total_h * self.scale))
        self.set_size_request(self.total_w, self.total_h)
        self.resize(self.total_w, self.total_h)
        self.queue_draw()

    def set_chassis_theme(self, theme):
        if theme in ("space_gray", "silver", "midnight", "starlight"):
            self.chassis_theme = theme
            config.set("desktop_macbook_chassis", theme)
            self.queue_draw()

    def set_wallpaper_theme(self, wp):
        if wp in ("sonoma", "sequoia", "aurora", "cyber", "minimal"):
            self.wallpaper_theme = wp
            config.set("desktop_macbook_wallpaper", wp)
            self.queue_draw()

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
        self.anim_scale.set_immediate(0.55)
        self.anim_scale.set_target(1.0)
        self.anim_alpha.set_immediate(0.0)
        self.anim_alpha.set_target(1.0)
        self._start_anim_loop()

    def _start_anim_loop(self):
        if self._anim_timer_id is None:
            self._anim_last_time = time.monotonic()
            self._anim_timer_id = GLib.timeout_add(16, self._on_anim_step)
        self.queue_draw()

    def _on_anim_step(self):
        now = time.monotonic()
        dt = min(now - self._anim_last_time, 0.05)
        self._anim_last_time = now

        settled_s = self.anim_scale.step(dt)
        settled_a = self.anim_alpha.step(dt)
        settled_p = self.anim_pill_idx.step(dt)
        self.queue_draw()

        if settled_s and settled_a and settled_p:
            self._anim_timer_id = None
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

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
        grip_color = (0.23, 0.51, 0.96, 0.95) if not self.is_locked else (1.0, 1.0, 1.0, 0.28)
        cr.set_source_rgba(*grip_color)
        cr.set_line_width(1.8)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for offset in (6, 11, 16):
            cr.move_to(rx - offset, ry - 3.5)
            cr.line_to(rx - 3.5, ry - offset)
            cr.stroke()
        cr.restore()

    def _is_over_resize_handle(self, unscaled_x, unscaled_y):
        rx = self.base_pad + self.base_card_w
        ry = self.base_pad + self.base_card_h
        return (rx - 26 <= unscaled_x <= rx + 8) and (ry - 26 <= unscaled_y <= ry + 8)

    # -------------------------------------------------------------
    # High-End Photorealistic Vector Rendering
    # -------------------------------------------------------------
    def _draw_screen_wallpaper(self, cr, sx, sy, sw, sh):
        """Draws authentic vibrant macOS wallpaper inside the Liquid Retina display."""
        wp = self.wallpaper_theme

        if wp == "sonoma":
            # 1. macOS Sonoma: Dynamic Organic Flowing Ribbons
            bg_pat = cairo.LinearGradient(sx, sy, sx + sw, sy + sh)
            bg_pat.add_color_stop_rgb(0.0, 0.04, 0.08, 0.22) # Deep oceanic night
            bg_pat.add_color_stop_rgb(1.0, 0.12, 0.08, 0.28) # Indigo twilight
            cr.set_source(bg_pat)
            cr.paint()

            # Deep Purple Back Wave
            cr.save()
            cr.move_to(sx, sy + sh * 0.85)
            cr.curve_to(sx + sw * 0.35, sy + sh * 0.40, sx + sw * 0.65, sy + sh * 0.90, sx + sw, sy + sh * 0.30)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            w1_pat = cairo.LinearGradient(sx, sy + sh * 0.3, sx + sw, sy + sh)
            w1_pat.add_color_stop_rgba(0.0, 0.55, 0.25, 0.95, 0.85) # Electric violet
            w1_pat.add_color_stop_rgba(1.0, 0.30, 0.15, 0.75, 0.80)
            cr.set_source(w1_pat)
            cr.fill()
            cr.restore()

            # Vibrant Cyan/Blue Mid Wave
            cr.save()
            cr.move_to(sx, sy + sh * 0.60)
            cr.curve_to(sx + sw * 0.25, sy + sh * 0.15, sx + sw * 0.70, sy + sh * 0.75, sx + sw, sy + sh * 0.45)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            w2_pat = cairo.LinearGradient(sx, sy, sx + sw, sy + sh)
            w2_pat.add_color_stop_rgba(0.0, 0.15, 0.65, 0.98, 0.90) # Cyan blue
            w2_pat.add_color_stop_rgba(0.8, 0.08, 0.38, 0.92, 0.85) # Royal blue
            cr.set_source(w2_pat)
            cr.fill()
            cr.restore()

            # Warm Golden / Magenta Front Ribbon Crest
            cr.save()
            cr.move_to(sx, sy + sh * 0.92)
            cr.curve_to(sx + sw * 0.40, sy + sh * 0.55, sx + sw * 0.75, sy + sh * 0.82, sx + sw, sy + sh * 0.62)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            w3_pat = cairo.LinearGradient(sx, sy + sh * 0.5, sx + sw, sy + sh)
            w3_pat.add_color_stop_rgba(0.0, 0.96, 0.25, 0.45, 0.92) # Radiant magenta
            w3_pat.add_color_stop_rgba(0.6, 0.98, 0.55, 0.18, 0.90) # Sunset amber
            w3_pat.add_color_stop_rgba(1.0, 1.00, 0.75, 0.25, 0.85) # Golden highlight
            cr.set_source(w3_pat)
            cr.fill()
            cr.restore()

        elif wp == "sequoia":
            # 2. macOS Sequoia: Golden Sunset Dusk & Forest Ridges
            sky_pat = cairo.LinearGradient(sx, sy, sx, sy + sh)
            sky_pat.add_color_stop_rgb(0.0, 0.12, 0.10, 0.28) # Violet twilight
            sky_pat.add_color_stop_rgb(0.5, 0.65, 0.18, 0.32) # Rose dusk
            sky_pat.add_color_stop_rgb(1.0, 0.95, 0.62, 0.15) # Warm golden horizon
            cr.set_source(sky_pat)
            cr.paint()

            # Glowing Sun disc near horizon
            cr.save()
            sun_cx = sx + sw * 0.65
            sun_cy = sy + sh * 0.68
            sun_pat = cairo.RadialGradient(sun_cx, sun_cy, 1.0, sun_cx, sun_cy, sw * 0.35)
            sun_pat.add_color_stop_rgba(0.0, 1.0, 0.95, 0.75, 0.75)
            sun_pat.add_color_stop_rgba(0.5, 0.98, 0.65, 0.20, 0.35)
            sun_pat.add_color_stop_rgba(1.0, 0.95, 0.45, 0.10, 0.0)
            cr.set_source(sun_pat)
            cr.arc(sun_cx, sun_cy, sw * 0.35, 0, 2 * math.pi)
            cr.fill()
            cr.restore()

            # Mountain ridge 1 (Back)
            cr.move_to(sx, sy + sh * 0.72)
            cr.line_to(sx + sw * 0.30, sy + sh * 0.56)
            cr.line_to(sx + sw * 0.60, sy + sh * 0.68)
            cr.line_to(sx + sw * 0.82, sy + sh * 0.52)
            cr.line_to(sx + sw, sy + sh * 0.65)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            cr.set_source_rgba(0.48, 0.18, 0.12, 0.75)
            cr.fill()

            # Mountain ridge 2 (Foreground Forest)
            cr.move_to(sx, sy + sh * 0.84)
            cr.line_to(sx + sw * 0.25, sy + sh * 0.70)
            cr.line_to(sx + sw * 0.52, sy + sh * 0.80)
            cr.line_to(sx + sw * 0.78, sy + sh * 0.66)
            cr.line_to(sx + sw, sy + sh * 0.78)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            cr.set_source_rgba(0.08, 0.16, 0.12, 0.95)
            cr.fill()

        elif wp == "aurora":
            # 3. Aurora Borealis: Cosmic Stars & Emerald Aurora Curtains
            bg_pat = cairo.LinearGradient(sx, sy, sx, sy + sh)
            bg_pat.add_color_stop_rgb(0.0, 0.01, 0.03, 0.08)
            bg_pat.add_color_stop_rgb(1.0, 0.02, 0.06, 0.14)
            cr.set_source(bg_pat)
            cr.paint()

            # Aurora curtain 1 (Green/Emerald)
            cr.save()
            cr.move_to(sx, sy + sh * 0.75)
            cr.curve_to(sx + sw * 0.30, sy + sh * 0.20, sx + sw * 0.70, sy + sh * 0.65, sx + sw, sy + sh * 0.15)
            cr.line_to(sx + sw, sy + sh * 0.45)
            cr.curve_to(sx + sw * 0.65, sy + sh * 0.85, sx + sw * 0.25, sy + sh * 0.40, sx, sy + sh * 0.90)
            cr.close_path()
            a1 = cairo.LinearGradient(sx, sy, sx, sy + sh)
            a1.add_color_stop_rgba(0.0, 0.06, 0.85, 0.55, 0.85)
            a1.add_color_stop_rgba(1.0, 0.02, 0.65, 0.80, 0.25)
            cr.set_source(a1)
            cr.fill()
            cr.restore()

            # Aurora curtain 2 (Cyan/Magenta glow)
            cr.save()
            cr.move_to(sx, sy + sh * 0.45)
            cr.curve_to(sx + sw * 0.40, sy + sh * 0.75, sx + sw * 0.65, sy + sh * 0.25, sx + sw, sy + sh * 0.50)
            cr.line_to(sx + sw, sy + sh * 0.68)
            cr.curve_to(sx + sw * 0.60, sy + sh * 0.42, sx + sw * 0.35, sy + sh * 0.88, sx, sy + sh * 0.62)
            cr.close_path()
            a2 = cairo.LinearGradient(sx, sy, sx + sw, sy)
            a2.add_color_stop_rgba(0.0, 0.12, 0.75, 0.98, 0.75)
            a2.add_color_stop_rgba(1.0, 0.75, 0.25, 0.92, 0.70)
            cr.set_source(a2)
            cr.fill()
            cr.restore()

        elif wp == "cyber":
            # 4. Cyber Neon: Synthwave Grid & High-Voltage Neon Trails
            cr.set_source_rgb(0.04, 0.04, 0.07)
            cr.paint()

            # Neon grid lines
            cr.save()
            cr.set_line_width(0.6)
            cr.set_source_rgba(0.15, 0.35, 0.65, 0.35)
            for gy in range(int(sy + sh * 0.55), int(sy + sh), 5):
                cr.move_to(sx, gy)
                cr.line_to(sx + sw, gy)
                cr.stroke()
            cr.restore()

            # Hot Pink & Cyan Neon Trail
            cr.save()
            cr.move_to(sx - 5, sy + sh * 0.95)
            cr.curve_to(sx + sw * 0.35, sy + sh * 0.35, sx + sw * 0.60, sy + sh * 0.80, sx + sw + 5, sy + sh * 0.20)
            cr.set_source_rgba(0.96, 0.15, 0.55, 0.95)
            cr.set_line_width(2.8)
            cr.stroke_preserve()
            cr.set_source_rgba(1.0, 0.60, 0.85, 1.0)
            cr.set_line_width(1.0)
            cr.stroke()

            cr.move_to(sx - 5, sy + sh * 0.70)
            cr.curve_to(sx + sw * 0.45, sy + sh * 0.85, sx + sw * 0.55, sy + sh * 0.15, sx + sw + 5, sy + sh * 0.45)
            cr.set_source_rgba(0.05, 0.85, 0.98, 0.95)
            cr.set_line_width(2.2)
            cr.stroke_preserve()
            cr.set_source_rgba(0.80, 0.98, 1.0, 1.0)
            cr.set_line_width(0.8)
            cr.stroke()
            cr.restore()

        else:
            # 5. Minimal Dark / Obsidian with Centered Glowing Apple Logo
            m_pat = cairo.LinearGradient(sx, sy, sx, sy + sh)
            m_pat.add_color_stop_rgb(0.0, 0.11, 0.12, 0.15)
            m_pat.add_color_stop_rgb(1.0, 0.04, 0.05, 0.07)
            cr.set_source(m_pat)
            cr.paint()

            # Glowing Apple Logo in the screen center
            acx = sx + sw / 2.0
            acy = sy + sh / 2.0 + 1.0
            self._draw_apple_logo(cr, acx, acy, scale=1.05)

    def _draw_apple_logo(self, cr, x, y, scale=1.0):
        cr.save()
        cr.translate(x, y)
        cr.scale(scale, scale)
        cr.set_source_rgba(0.92, 0.94, 0.98, 0.88)

        # Apple leaf
        cr.new_sub_path()
        cr.move_to(0.6, -4.5)
        cr.curve_to(2.2, -4.5, 2.8, -3.0, 2.8, -3.0)
        cr.curve_to(1.2, -2.8, 0.6, -4.5, 0.6, -4.5)
        cr.close_path()
        cr.fill()

        # Apple body
        cr.new_sub_path()
        cr.move_to(0.0, -2.0)
        cr.curve_to(-1.3, -2.0, -2.4, -1.0, -2.9, 0.0)
        cr.curve_to(-3.5, 1.2, -3.3, 2.9, -2.2, 4.0)
        cr.curve_to(-1.4, 4.7, -0.5, 4.4, 0.0, 4.4)
        cr.curve_to(0.5, 4.4, 1.4, 4.7, 2.2, 4.0)
        cr.curve_to(3.1, 3.1, 3.4, 1.6, 3.4, 1.6)
        cr.curve_to(2.2, 1.1, 2.2, -0.7, 3.1, -1.4)
        cr.curve_to(2.5, -2.2, 1.4, -2.0, 0.9, -2.0)
        cr.curve_to(0.5, -2.0, 0.2, -2.0, 0.0, -2.0)
        cr.close_path()
        cr.fill()
        cr.restore()

    def _draw_macbook_vector(self, cr, cx, cy):
        """Draws photorealistic MacBook Pro vector illustration matching Apple hardware."""
        mw = 86.0
        mh = 52.0

        # Chassis finish palettes
        theme = self.chassis_theme
        if theme == "silver":
            shell_top = (0.94, 0.95, 0.97)
            shell_bot = (0.76, 0.79, 0.84)
            base_top = (0.95, 0.96, 0.98)
            base_bot = (0.72, 0.76, 0.81)
            stroke_col = (0.35, 0.40, 0.46, 0.80)
            spec_col = (1.0, 1.0, 1.0, 0.90)
        elif theme == "midnight":
            shell_top = (0.16, 0.20, 0.27)
            shell_bot = (0.09, 0.12, 0.17)
            base_top = (0.18, 0.23, 0.31)
            base_bot = (0.08, 0.10, 0.15)
            stroke_col = (0.05, 0.07, 0.10, 0.95)
            spec_col = (0.45, 0.55, 0.70, 0.65)
        elif theme == "starlight":
            shell_top = (0.96, 0.94, 0.90)
            shell_bot = (0.84, 0.81, 0.75)
            base_top = (0.97, 0.95, 0.91)
            base_bot = (0.80, 0.77, 0.71)
            stroke_col = (0.42, 0.39, 0.34, 0.80)
            spec_col = (1.0, 0.98, 0.94, 0.85)
        else: # Default Space Gray
            shell_top = (0.46, 0.49, 0.54)
            shell_bot = (0.28, 0.30, 0.34)
            base_top = (0.48, 0.51, 0.56)
            base_bot = (0.26, 0.28, 0.32)
            stroke_col = (0.16, 0.18, 0.21, 0.90)
            spec_col = (0.85, 0.88, 0.94, 0.75)

        # 0. Diffused Contact Shadow & Ambient Occlusion underneath
        cr.save()
        cr.translate(cx, cy + mh * 0.46)
        cr.scale(1.0, 0.18)
        cr.arc(0, 0, mw * 0.48, 0, 2 * math.pi)
        sh_pat = cairo.RadialGradient(0, 0, 0, 0, 0, mw * 0.48)
        sh_pat.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.65)
        sh_pat.add_color_stop_rgba(0.7, 0.0, 0.0, 0.0, 0.20)
        sh_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        cr.set_source(sh_pat)
        cr.fill()
        cr.restore()

        # 1. Screen Lid (Open front elevation)
        lid_w = mw * 0.90   # 77.4
        lid_h = mh * 0.82   # 42.6
        lx = cx - lid_w / 2.0
        ly = cy - lid_h / 2.0 - 2.0

        r = 3.8
        cr.new_sub_path()
        cr.arc(lx + lid_w - r, ly + r, r, -math.pi / 2, 0)
        cr.arc(lx + lid_w - r, ly + lid_h - r, r, 0, math.pi / 2)
        cr.arc(lx + r, ly + lid_h - r, r, math.pi / 2, math.pi)
        cr.arc(lx + r, ly + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        # Outer chassis shell gradient
        shell_pat = cairo.LinearGradient(lx, ly, lx, ly + lid_h)
        shell_pat.add_color_stop_rgb(0.0, *shell_top)
        shell_pat.add_color_stop_rgb(1.0, *shell_bot)
        cr.set_source(shell_pat)
        cr.fill_preserve()
        cr.set_source_rgba(*stroke_col)
        cr.set_line_width(0.7)
        cr.stroke()

        # Display Bezel (Black obsidian anodized aluminum)
        bw_side = 1.8
        bw_bot = 2.4
        sx = lx + bw_side
        sy = ly + bw_side
        sw = lid_w - 2 * bw_side
        sh = lid_h - bw_side - bw_bot

        # Outer bezel fill
        cr.rectangle(lx + 0.8, ly + 0.8, lid_w - 1.6, lid_h - 1.6)
        cr.set_source_rgba(0.04, 0.05, 0.06, 0.98)
        cr.fill()

        # Liquid Retina Screen Clip (with rounded top display corners)
        cr.save()
        sr = 2.4
        cr.new_sub_path()
        cr.arc(sx + sw - sr, sy + sr, sr, -math.pi / 2, 0)
        cr.line_to(sx + sw, sy + sh)
        cr.line_to(sx, sy + sh)
        cr.arc(sx + sr, sy + sr, sr, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.clip()

        # Draw Wallpaper inside screen
        self._draw_screen_wallpaper(cr, sx, sy, sw, sh)

        # Realistic Glass Diagonal Sheen
        refl = cairo.LinearGradient(sx, sy, sx + sw * 0.75, sy + sh)
        refl.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.18)
        refl.add_color_stop_rgba(0.35, 1.0, 1.0, 1.0, 0.03)
        refl.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(refl)
        cr.paint()

        # Modern MacBook Camera Notch (Centered at top)
        notch_w = 11.5
        notch_h = 2.8
        nx = cx - notch_w / 2.0
        ny = sy
        cr.new_sub_path()
        cr.move_to(nx, ny)
        cr.line_to(nx + notch_w, ny)
        cr.arc(nx + notch_w - 1.0, ny + notch_h - 1.0, 1.0, 0, math.pi / 2)
        cr.arc(nx + 1.0, ny + notch_h - 1.0, 1.0, math.pi / 2, math.pi)
        cr.close_path()
        cr.set_source_rgba(0.02, 0.02, 0.04, 1.0)
        cr.fill()

        # FaceTime HD Camera Lens (Deep optical blue + reflection)
        cr.arc(cx - 1.2, ny + 1.3, 0.65, 0, 2 * math.pi)
        cr.set_source_rgba(0.05, 0.12, 0.22, 1.0)
        cr.fill()
        cr.arc(cx - 1.4, ny + 1.1, 0.22, 0, 2 * math.pi)
        cr.set_source_rgba(0.38, 0.75, 0.98, 0.9)
        cr.fill()

        # Privacy LED dot (Apple Green)
        cr.arc(cx + 2.4, ny + 1.3, 0.40, 0, 2 * math.pi)
        cr.set_source_rgba(0.13, 0.77, 0.37, 0.95)
        cr.fill()

        # Subtle display glass inner rim
        cr.rectangle(sx, sy, sw, sh)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.set_line_width(0.6)
        cr.stroke()

        cr.restore()

        # 2. MacBook Base (Precision CNC Unibody Chassis)
        base_w = mw
        base_h = 6.8
        bx = cx - base_w / 2.0
        by = ly + lid_h - 1.2

        cr.new_sub_path()
        cr.arc(bx + base_w - 2.8, by + 2.4, 2.4, -math.pi / 2, 0)
        cr.arc(bx + base_w - 2.8, by + base_h - 2.2, 2.2, 0, math.pi / 2)
        cr.arc(bx + 2.8, by + base_h - 2.2, 2.2, math.pi / 2, math.pi)
        cr.arc(bx + 2.8, by + 2.4, 2.4, math.pi, 3 * math.pi / 2)
        cr.close_path()

        base_pat = cairo.LinearGradient(bx, by, bx, by + base_h)
        base_pat.add_color_stop_rgb(0.0, *base_top)
        base_pat.add_color_stop_rgb(1.0, *base_bot)
        cr.set_source(base_pat)
        cr.fill_preserve()
        cr.set_source_rgba(*stroke_col)
        cr.set_line_width(0.7)
        cr.stroke()

        # Recessed Titanium Hinge
        hinge_w = 32.0
        hinge_h = 1.6
        hx = cx - hinge_w / 2.0
        hy = by - 0.4
        cr.rectangle(hx, hy, hinge_w, hinge_h)
        cr.set_source_rgba(0.10, 0.12, 0.15, 0.98)
        cr.fill()

        # Display-opening Thumb Scoop (Center Notch)
        cr.save()
        cr.arc(cx, by + 1.2, 4.2, 0, math.pi)
        cr.set_source_rgba(0.18, 0.20, 0.24, 0.65)
        cr.fill()
        # Lip highlight
        cr.arc(cx, by + 1.2, 4.2, 0, math.pi)
        cr.set_source_rgba(*spec_col)
        cr.set_line_width(0.6)
        cr.stroke()
        cr.restore()

        # Subtle Magic Keyboard Well Silhouette
        kw = base_w - 18.0
        kh = 1.6
        kx = cx - kw / 2.0
        ky = by + 2.4
        cr.rectangle(kx, ky, kw, kh)
        cr.set_source_rgba(0.12, 0.14, 0.18, 0.70)
        cr.fill()

        # Razor-sharp Front Edge Specular Chamfer Line
        cr.move_to(bx + 3.0, by + base_h - 0.8)
        cr.line_to(bx + base_w - 3.0, by + base_h - 0.8)
        cr.set_source_rgba(*spec_col)
        cr.set_line_width(0.6)
        cr.stroke()

        # Subtle Rubber Feet underneath (Left & Right)
        cr.rectangle(bx + 6.0, by + base_h - 0.4, 5.0, 0.8)
        cr.rectangle(bx + base_w - 11.0, by + base_h - 0.4, 5.0, 0.8)
        cr.set_source_rgba(0.05, 0.06, 0.08, 0.85)
        cr.fill()

    # -------------------------------------------------------------
    # Device Name & Battery Badge Rendering
    # -------------------------------------------------------------
    def _draw_device_and_battery(self, cr, widget, center_card_x, y):
        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_GRAY)
        fo.set_hint_style(cairo.HINT_STYLE_SLIGHT)
        cr.set_font_options(fo)

        pctx = widget.get_pango_context()
        PangoCairo.context_set_font_options(pctx, fo)

        # 1. Device Name (e.g. "MacBook Pro")
        layout_name = Pango.Layout(pctx)
        layout_name.set_font_description(Pango.FontDescription.from_string("Inter, Montserrat, SF Pro Display, Ubuntu Bold 10.5"))
        layout_name.set_text(self.device_name, -1)
        layout_name.set_alignment(Pango.Alignment.CENTER)
        nw, nh = layout_name.get_pixel_size()

        tx_name = center_card_x - nw / 2.0
        ty_name = y + 77.0

        # Drop shadow
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.65)
        cr.move_to(tx_name, ty_name + 1.2)
        PangoCairo.show_layout(cr, layout_name)
        cr.restore()

        cr.save()
        cr.set_source_rgba(0.96, 0.98, 1.0, 0.96)
        cr.move_to(tx_name, ty_name)
        PangoCairo.show_layout(cr, layout_name)
        cr.restore()

        # 2. Sleek Battery Pill Badge (Icon + Percentage e.g. "100%")
        ty_badge = y + 95.0

        # Percentage text
        layout_pct = Pango.Layout(pctx)
        layout_pct.set_font_description(Pango.FontDescription.from_string("Inter, Montserrat, Ubuntu Medium 8.8"))
        pct_str = f"{self.battery_pct}%"
        layout_pct.set_text(pct_str, -1)
        pw_t, ph_t = layout_pct.get_pixel_size()

        # Battery icon dimensions
        bw = 18.0
        bh = 9.2
        br = 2.4
        gap = 4.5
        total_badge_w = bw + gap + pw_t
        start_bx = center_card_x - total_badge_w / 2.0

        # Draw battery outline
        by_icon = ty_badge + (ph_t - bh) / 2.0
        self._path_rounded_rect(cr, start_bx, by_icon, bw, bh, br)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.65)
        cr.set_line_width(0.9)
        cr.stroke()

        # Battery terminal cap
        cr.new_sub_path()
        cr.arc(start_bx + bw + 1.0, by_icon + bh / 2.0, 1.2, -math.pi / 2, math.pi / 2)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.60)
        cr.fill()

        # Battery fill bar
        fill_ratio = max(0.05, min(1.0, self.battery_pct / 100.0))
        fill_w = max(2.0, (bw - 2.8) * fill_ratio)
        fill_h = bh - 2.8

        if self.is_charging:
            fill_color = (0.19, 0.82, 0.35) # Vivid Apple Green
        elif self.battery_pct > 20:
            fill_color = (0.20, 0.78, 0.35) # Green
        elif self.battery_pct > 10:
            fill_color = (1.00, 0.62, 0.04) # Amber
        else:
            fill_color = (1.00, 0.27, 0.23) # Crimson Red

        self._path_rounded_rect(cr, start_bx + 1.4, by_icon + 1.4, fill_w, fill_h, 1.4)
        cr.set_source_rgba(*fill_color, 0.95)
        cr.fill()

        # Centered vector lightning bolt inside battery when charging
        if self.is_charging:
            cr.save()
            bcx = start_bx + bw / 2.0
            bcy = by_icon + bh / 2.0
            cr.translate(bcx, bcy)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.98)
            cr.move_to(0.5, -3.2)
            cr.line_to(-1.8, -0.2)
            cr.line_to(-0.2, -0.2)
            cr.line_to(-0.7, 3.2)
            cr.line_to(1.8, 0.2)
            cr.line_to(0.2, 0.2)
            cr.close_path()
            cr.fill()
            cr.restore()

        # Draw Percentage Text next to battery
        tx_pct = start_bx + bw + gap
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
        cr.move_to(tx_pct, ty_badge + 1.0)
        PangoCairo.show_layout(cr, layout_pct)
        cr.restore()

        cr.save()
        cr.set_source_rgba(0.92, 0.95, 0.98, 0.92)
        cr.move_to(tx_pct, ty_badge)
        PangoCairo.show_layout(cr, layout_pct)
        cr.restore()

    # -------------------------------------------------------------
    # 3-Mode Power Profile Switcher
    # -------------------------------------------------------------
    def _draw_power_mode_pill(self, cr, px, py, pw, ph):
        """Draws 3-button segmented power profile pill with animated active slider."""
        pr = ph / 2.0

        # Outer pill container (Frosted Dark Glass)
        self._path_rounded_rect(cr, px, py, pw, ph, pr)
        cr.set_source_rgba(0.06, 0.07, 0.10, 0.72)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.14)
        cr.set_line_width(0.8)
        cr.stroke()

        # Inset subtle shadow
        cr.save()
        self._path_rounded_rect(cr, px, py, pw, ph, pr)
        cr.clip()
        in_sh = cairo.LinearGradient(px, py, px, py + ph * 0.4)
        in_sh.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.35)
        in_sh.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        cr.set_source(in_sh)
        cr.paint()
        cr.restore()

        # Segments geometry
        seg_w = (pw - 4.0) / 3.0

        # Hover indicator on inactive segments
        if self._hover_pill_idx >= 0 and self._hover_pill_idx != self.active_profile_idx:
            hov_x = px + 2.0 + self._hover_pill_idx * seg_w
            self._path_rounded_rect(cr, hov_x, py + 2.0, seg_w, ph - 4.0, pr - 2.0)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
            cr.fill()

        # Animated Active Capsule Slider using Spring Physics
        active_pos = max(0.0, min(2.0, self.anim_pill_idx.current))
        slider_x = px + 2.0 + active_pos * seg_w
        slider_y = py + 2.0
        slider_w = seg_w
        slider_h = ph - 4.0
        slider_r = pr - 2.0

        self._path_rounded_rect(cr, slider_x, slider_y, slider_w, slider_h, slider_r)

        # Profile-specific active colors
        idx = self.active_profile_idx
        if idx == 0:
            # Power-Saver: Emerald Green Glow
            cap_fill = cairo.LinearGradient(slider_x, slider_y, slider_x, slider_y + slider_h)
            cap_fill.add_color_stop_rgba(0.0, 0.20, 0.78, 0.35, 0.36)
            cap_fill.add_color_stop_rgba(1.0, 0.12, 0.55, 0.24, 0.24)
            cap_stroke = (0.20, 0.78, 0.35, 0.75)
        elif idx == 2:
            # Performance: Solar Amber / Flame Glow
            cap_fill = cairo.LinearGradient(slider_x, slider_y, slider_x, slider_y + slider_h)
            cap_fill.add_color_stop_rgba(0.0, 1.00, 0.58, 0.00, 0.38)
            cap_fill.add_color_stop_rgba(1.0, 0.85, 0.28, 0.00, 0.26)
            cap_stroke = (1.00, 0.62, 0.05, 0.80)
        else:
            # Balanced: Apple System Blue Glow
            cap_fill = cairo.LinearGradient(slider_x, slider_y, slider_x, slider_y + slider_h)
            cap_fill.add_color_stop_rgba(0.0, 0.04, 0.52, 1.00, 0.36)
            cap_fill.add_color_stop_rgba(1.0, 0.00, 0.36, 0.85, 0.24)
            cap_stroke = (0.04, 0.52, 1.00, 0.75)

        cr.set_source(cap_fill)
        cr.fill_preserve()
        cr.set_source_rgba(*cap_stroke)
        cr.set_line_width(0.7)
        cr.stroke()

        # Segment 0: Leaf Icon (Eco / Power-Saver)
        leaf_cx = px + 2.0 + seg_w * 0.5
        leaf_cy = py + ph * 0.5
        self._draw_leaf_icon(cr, leaf_cx, leaf_cy, is_active=(self.active_profile_idx == 0))

        # Segment 1: Gauge / Dial Icon (Balanced)
        gauge_cx = px + 2.0 + seg_w * 1.5
        gauge_cy = py + ph * 0.5
        self._draw_gauge_icon(cr, gauge_cx, gauge_cy, is_active=(self.active_profile_idx == 1))

        # Segment 2: Turbo Lightning Bolt (Performance / High Power)
        bolt_cx = px + 2.0 + seg_w * 2.5
        bolt_cy = py + ph * 0.5
        self._draw_bolt_icon(cr, bolt_cx, bolt_cy, is_active=(self.active_profile_idx == 2))

    def _draw_leaf_icon(self, cr, cx, cy, is_active):
        cr.save()
        color = (0.24, 0.86, 0.42, 1.0) if is_active else (0.75, 0.78, 0.84, 0.65)
        cr.set_source_rgba(*color)
        cr.set_line_width(1.3)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        # Smooth organic leaf curve
        cr.move_to(cx - 5.2, cy + 4.2)
        cr.curve_to(cx - 5.2, cy - 4.5, cx, cy - 5.6, cx + 5.2, cy - 5.0)
        cr.curve_to(cx + 4.6, cy + 1.0, cx + 1.0, cy + 4.6, cx - 5.2, cy + 4.2)
        cr.stroke()

        # Leaf center vein
        cr.move_to(cx - 5.2, cy + 4.2)
        cr.line_to(cx + 2.0, cy - 2.0)
        cr.stroke()
        cr.restore()

    def _draw_gauge_icon(self, cr, cx, cy, is_active):
        cr.save()
        color = (0.25, 0.65, 1.0, 1.0) if is_active else (0.75, 0.78, 0.84, 0.65)
        cr.set_source_rgba(*color)
        cr.set_line_width(1.3)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Outer speedometer arc (240 degrees)
        cr.arc(cx, cy, 5.0, math.pi * 0.75, math.pi * 2.25)
        cr.stroke()

        # Center dial dot
        cr.arc(cx, cy, 1.3, 0, 2 * math.pi)
        cr.fill()

        # Indicator needle pointed slightly past center
        cr.move_to(cx, cy)
        cr.line_to(cx + 2.4, cy - 2.4)
        cr.stroke()
        cr.restore()

    def _draw_bolt_icon(self, cr, cx, cy, is_active):
        cr.save()
        color = (1.00, 0.72, 0.15, 1.0) if is_active else (0.75, 0.78, 0.84, 0.65)
        cr.set_source_rgba(*color)

        # Sharp multi-point lightning bolt
        cr.move_to(cx + 0.6, cy - 5.6)
        cr.line_to(cx - 3.6, cy - 0.4)
        cr.line_to(cx - 0.6, cy - 0.4)
        cr.line_to(cx - 1.6, cy + 5.6)
        cr.line_to(cx + 3.6, cy + 0.4)
        cr.line_to(cx + 0.6, cy + 0.4)
        cr.close_path()
        cr.fill()
        cr.restore()

    # -------------------------------------------------------------
    # Main Draw Function
    # -------------------------------------------------------------
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
        cr.translate(cx, cy)
        cr.scale(open_scale, open_scale)
        cr.translate(-cx, -cy)

        # Apply user scale factor
        cr.scale(self.scale, self.scale)

        use_group = (open_alpha < 0.999)
        if use_group:
            cr.push_group()

        x = self.base_pad
        y = self.base_pad
        w = self.base_card_w
        h = self.base_card_h
        r = self.base_radius

        # 0. Outer Diffuse Card Shadow
        cr.save()
        self._path_rounded_rect(cr, x, y + 2.0, w, h, r)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.35)
        cr.fill()
        cr.restore()

        # 1. Translucent Frosted Glass Card Background
        self._path_rounded_rect(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        base_pat = cairo.LinearGradient(x, y, x, y + h)
        base_pat.add_color_stop_rgba(0.0, 0.09, 0.11, 0.15, 0.58)
        base_pat.add_color_stop_rgba(1.0, 0.05, 0.06, 0.09, 0.68)
        cr.set_source(base_pat)
        cr.paint()

        # Subtle Ambient Screen Glow reflecting on card surface
        glow_pat = cairo.RadialGradient(x + w / 2.0, y + 42.0, 5.0, x + w / 2.0, y + 42.0, 65.0)
        glow_pat.add_color_stop_rgba(0.0, 0.15, 0.45, 0.95, 0.18)
        glow_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        cr.set_source(glow_pat)
        cr.paint()

        # Specular Top Sheen
        sheen = cairo.LinearGradient(x, y, x, y + h * 0.38)
        sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.15)
        sheen.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.02)
        sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(sheen)
        cr.paint()

        cr.restore()

        # 2. Sleek Glass Rim Border
        self._path_rounded_rect(cr, x, y, w, h, r)
        rim = cairo.LinearGradient(x, y, x + w, y + h)
        rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.24)
        rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.08)
        rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.14)
        cr.set_source(rim)
        cr.set_line_width(0.8)
        cr.stroke()

        # Edit Mode Highlight & Resize Grip when Unlocked
        if not self.is_locked:
            cr.save()
            self._path_rounded_rect(cr, x, y, w, h, r)
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.70)
            cr.set_line_width(1.8)
            cr.stroke()
            cr.restore()

            # Draw bottom-right resize grip neatly clipped inside the squircle card
            cr.save()
            self._path_rounded_rect(cr, x, y, w, h, r)
            cr.clip()
            rx = x + w - 3.0
            ry = y + h - 3.0
            self._draw_resize_grip(cr, rx, ry)
            cr.restore()

        center_card_x = x + w / 2.0

        # 3. MacBook Vector Graphic
        mac_cy = y + 42.0
        self._draw_macbook_vector(cr, center_card_x, mac_cy)

        # 4. Device Name & Battery Badge
        self._draw_device_and_battery(cr, widget, center_card_x, y)

        # 5. 3-Button Power Mode Pill
        pill_w = 122.0
        pill_h = 28.0
        pill_x = center_card_x - pill_w / 2.0
        pill_y = y + 116.0
        self._draw_power_mode_pill(cr, pill_x, pill_y, pill_w, pill_h)

        # 6. Floating Scale Badge HUD during Resizing
        if self._resizing:
            cr.save()
            hud_w = 54.0
            hud_h = 20.0
            hud_x = center_card_x - hud_w / 2.0
            hud_y = y + 6.0
            self._path_rounded_rect(cr, hud_x, hud_y, hud_w, hud_h, hud_h / 2.0)
            cr.set_source_rgba(0.08, 0.10, 0.14, 0.88)
            cr.fill_preserve()
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.90)
            cr.set_line_width(1.0)
            cr.stroke()

            pctx = widget.get_pango_context()
            layout_hud = Pango.Layout(pctx)
            layout_hud.set_font_description(Pango.FontDescription.from_string("Inter, Ubuntu Bold 8.5"))
            layout_hud.set_text(f"{int(round(self.scale * 100))}%", -1)
            hw, hh = layout_hud.get_pixel_size()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.move_to(center_card_x - hw / 2.0, hud_y + (hud_h - hh) / 2.0)
            PangoCairo.show_layout(cr, layout_hud)
            cr.restore()

        if use_group:
            cr.pop_group_to_source()
            cr.paint_with_alpha(open_alpha)

        cr.restore()
        return False

    # -------------------------------------------------------------
    # Profile & Hardware Controls
    # -------------------------------------------------------------
    def _set_power_profile(self, index):
        profiles = ["power-saver", "balanced", "performance"]
        if 0 <= index < len(profiles):
            self.active_profile_idx = index
            self.anim_pill_idx.set_target(float(index))
            target_profile = profiles[index]
            try:
                subprocess.Popen(["powerprofilesctl", "set", target_profile])
            except Exception:
                pass
            self._start_anim_loop()
            self.queue_draw()

    def _open_about_mac(self):
        try:
            from src.ui.macos_about_window import MacOSAboutWindow
            MacOSAboutWindow.show_window()
        except Exception as e:
            print(f"[MacBookWidget] Error opening About Mac: {e}")

    def _prompt_rename_device(self):
        dialog = Gtk.Dialog(
            title="Đổi tên thiết bị",
            parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        dialog.add_buttons(
            "Hủy", Gtk.ResponseType.CANCEL,
            "Lưu", Gtk.ResponseType.OK
        )
        dialog.set_default_size(320, 140)
        dialog.set_border_width(12)

        content = dialog.get_content_area()
        content.set_spacing(10)

        label = Gtk.Label(label="Nhập tên hiển thị mới cho máy MacBook:")
        label.set_xalign(0.0)
        content.pack_start(label, False, False, 0)

        entry = Gtk.Entry()
        entry.set_text(self.device_name)
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_name = entry.get_text().strip()
            if new_name:
                self.device_name = new_name
                config.set("desktop_macbook_name", new_name)
                self.queue_draw()
        dialog.destroy()

    # -------------------------------------------------------------
    # Event Handlers (Click, Drag, Resize, Scroll)
    # -------------------------------------------------------------
    def _on_button_press(self, widget, event):
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        x = unscaled_x - self.base_pad
        y = unscaled_y - self.base_pad

        if event.button == 1:
            # 1. Corner Resize Drag Handle
            if not self.is_locked and self._is_over_resize_handle(unscaled_x, unscaled_y):
                self._resizing = True
                self._resize_start_x = event.x_root
                self._resize_start_y = event.y_root
                self._resize_start_scale = self.scale
                gdk_win = widget.get_window()
                if gdk_win:
                    cursor = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "se-resize")
                    if cursor:
                        gdk_win.set_cursor(cursor)
                self.queue_draw()
                return True

            # 2. Power Mode Pill click: pill at y in [116, 144]
            pill_w = 122.0
            pill_h = 28.0
            pill_x = (self.base_card_w - pill_w) / 2.0
            pill_y = 116.0

            if pill_x <= x <= (pill_x + pill_w) and pill_y <= y <= (pill_y + pill_h):
                rel_x = x - pill_x
                seg_w = pill_w / 3.0
                clicked_idx = int(rel_x / seg_w)
                clicked_idx = max(0, min(2, clicked_idx))
                self._set_power_profile(clicked_idx)
                return True

            # 3. MacBook illustration or device name click -> Open About This Mac
            if y < 112.0:
                self._open_about_mac()
                return True

            # 4. Dragging when unlocked
            if not self.is_locked:
                self._dragging = True
                self._has_moved = False
                self._drag_start_x = event.x_root
                self._drag_start_y = event.y_root
                self._win_start_x = getattr(self, "_current_x", self.get_position()[0])
                self._win_start_y = getattr(self, "_current_y", self.get_position()[1])
                gdk_win = widget.get_window()
                if gdk_win:
                    cursor = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grabbing")
                    if cursor:
                        gdk_win.set_cursor(cursor)
                return True

        elif event.button == 3:
            # Right-click -> Context menu
            self._show_context_menu(event)
            return True

        return False

    def _on_motion_notify(self, widget, event):
        # 1. Handle live corner resizing
        if self._resizing:
            dx = event.x_root - self._resize_start_x
            dy = event.y_root - self._resize_start_y
            delta = (dx + dy) / 2.0
            new_scale = self._resize_start_scale + (delta / 220.0)
            self.set_scale(new_scale, save=False)
            return True

        # 2. Handle dragging window
        if self._dragging:
            dx = int(event.x_root - self._drag_start_x)
            dy = int(event.y_root - self._drag_start_y)
            if abs(dx) > 3 or abs(dy) > 3:
                self._has_moved = True
                self._current_x = int(self._win_start_x + dx)
                self._current_y = int(self._win_start_y + dy)
                self.move(self._current_x, self._current_y)
            return True

        # 3. Update cursor & hover states
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        x = unscaled_x - self.base_pad
        y = unscaled_y - self.base_pad

        is_hover_resize = not self.is_locked and self._is_over_resize_handle(unscaled_x, unscaled_y)
        self._hover_resize = is_hover_resize

        pill_w = 122.0
        pill_h = 28.0
        pill_x = (self.base_card_w - pill_w) / 2.0
        pill_y = 116.0
        is_over_pill = (pill_x <= x <= (pill_x + pill_w)) and (pill_y <= y <= (pill_y + pill_h))
        if is_over_pill:
            seg_w = pill_w / 3.0
            self._hover_pill_idx = max(0, min(2, int((x - pill_x) / seg_w)))
        else:
            self._hover_pill_idx = -1

        self._hover_mac = (y < 112.0)

        gdk_win = widget.get_window()
        if gdk_win:
            display = Gdk.Display.get_default()
            if is_hover_resize:
                cursor_name = "se-resize"
            elif is_over_pill or self._hover_mac:
                cursor_name = "pointer"
            elif not self.is_locked:
                cursor_name = "grab"
            else:
                cursor_name = "default"

            cursor = Gdk.Cursor.new_from_name(display, cursor_name)
            if cursor:
                gdk_win.set_cursor(cursor)

        self.queue_draw()
        return False

    def _on_button_release(self, widget, event):
        if event.button == 1:
            if self._resizing:
                self._resizing = False
                config.set("desktop_macbook_scale", self.scale)
                gdk_win = widget.get_window()
                if gdk_win:
                    display = Gdk.Display.get_default()
                    cursor_name = "default" if self.is_locked else "grab"
                    cursor = Gdk.Cursor.new_from_name(display, cursor_name)
                    if cursor:
                        gdk_win.set_cursor(cursor)
                self.queue_draw()
                return True

            if self._dragging:
                self._dragging = False
                if getattr(self, "_has_moved", False):
                    config.set("desktop_macbook_x", int(self._current_x))
                    config.set("desktop_macbook_y", int(self._current_y))
                self._has_moved = False
                gdk_win = widget.get_window()
                if gdk_win:
                    display = Gdk.Display.get_default()
                    cursor_name = "default" if self.is_locked else "grab"
                    cursor = Gdk.Cursor.new_from_name(display, cursor_name)
                    if cursor:
                        gdk_win.set_cursor(cursor)
                return True
        return False

    def _on_scroll(self, widget, event):
        """Allows scaling the widget smoothly via mouse scroll wheel."""
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale
        ctrl_held = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        over_handle = self._is_over_resize_handle(unscaled_x, unscaled_y)

        if not self.is_locked or ctrl_held or over_handle:
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

    def _on_leave_notify(self, widget, event):
        self._hover_pill_idx = -1
        self._hover_mac = False
        self._hover_resize = False
        gdk_win = widget.get_window()
        if gdk_win:
            cursor_name = "default" if self.is_locked else "grab"
            cursor = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), cursor_name)
            if cursor:
                gdk_win.set_cursor(cursor)
        self.queue_draw()
        return False

    # -------------------------------------------------------------
    # Context Menu
    # -------------------------------------------------------------
    def _show_context_menu(self, event):
        from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item

        menu = create_mac_context_menu()

        # 1. About This Mac
        menu.append(create_mac_menu_item("info.circle", "Giới thiệu về máy Mac (About This Mac)",
                                         lambda _: self._open_about_mac()))

        menu.append(Gtk.SeparatorMenuItem())

        # 2. Size presets submenu
        size_menu = create_mac_context_menu()
        presets = [
            ("Rất nhỏ (Mini - 70%)", 0.70),
            ("Nhỏ (Compact - 85%)", 0.85),
            ("Tiêu chuẩn (Normal - 100%)", 1.00),
            ("Lớn (Medium - 120%)", 1.20),
            ("Rất lớn (Large - 145%)", 1.45),
            ("Cực đại (Huge - 175%)", 1.75),
        ]
        for label, s_val in presets:
            chk = (abs(self.scale - s_val) < 0.04)
            item = create_mac_menu_item(None, label, lambda _, s=s_val: self.set_scale(s), is_checked=chk)
            size_menu.append(item)

        size_menu.append(Gtk.SeparatorMenuItem())
        reset_size = create_mac_menu_item("reset", "Đặt lại kích thước mặc định (100%)", lambda _: self.set_scale(1.00))
        size_menu.append(reset_size)
        menu.append(create_mac_menu_item("size", "Kích thước (Size)", submenu=size_menu))

        # 3. Chassis Finish submenu
        color_menu = create_mac_context_menu()
        finishes = [
            ("Xám không gian (Space Gray)", "space_gray"),
            ("Bạc ánh kim (Silver)", "silver"),
            ("Đen bóng đêm (Midnight)", "midnight"),
            ("Ánh sao vàng kim (Starlight)", "starlight"),
        ]
        for label, val in finishes:
            chk = (self.chassis_theme == val)
            item = create_mac_menu_item(None, label, lambda _, v=val: self.set_chassis_theme(v), is_checked=chk)
            color_menu.append(item)
        menu.append(create_mac_menu_item("paintpalette", "Màu vỏ máy (Finish)", submenu=color_menu))

        # 4. Wallpaper submenu
        wp_menu = create_mac_context_menu()
        wallpapers = [
            ("Sóng Sonoma (Sonoma Wave)", "sonoma"),
            ("Rừng Sequoia (Sequoia Sunset)", "sequoia"),
            ("Cực quang (Aurora Glow)", "aurora"),
            ("Cyber Neon (Cyber Neon)", "cyber"),
            ("Tối giản Apple (Minimal Obsidian)", "minimal"),
        ]
        for label, val in wallpapers:
            chk = (self.wallpaper_theme == val)
            item = create_mac_menu_item(None, label, lambda _, v=val: self.set_wallpaper_theme(v), is_checked=chk)
            wp_menu.append(item)
        menu.append(create_mac_menu_item("photo", "Màn hình nền (Wallpaper)", submenu=wp_menu))

        # 5. Power Profile Submenu
        prof_menu = create_mac_context_menu()
        profiles = [
            ("Tiết kiệm pin (Power Saver)", 0),
            ("Cân bằng (Balanced)", 1),
            ("Hiệu năng cao (Performance)", 2)
        ]
        for label, idx in profiles:
            chk = (self.active_profile_idx == idx)
            item = create_mac_menu_item(None, label, lambda _, i=idx: self._set_power_profile(i), is_checked=chk)
            prof_menu.append(item)
        menu.append(create_mac_menu_item("battery", "Chế độ hiệu năng (Power Profile)", submenu=prof_menu))

        menu.append(Gtk.SeparatorMenuItem())

        # 6. Rename Device
        menu.append(create_mac_menu_item("macbook", "Đổi tên thiết bị (Rename Device)...",
                                         lambda _: self._prompt_rename_device()))

        # 7. Replay Open animation
        menu.append(create_mac_menu_item("sparkles", "Phát lại hiệu ứng mở (Replay Open)",
                                         lambda _: self.play_open_animation()))

        menu.append(Gtk.SeparatorMenuItem())

        # 8. Lock / Unlock Position
        lock_text = "Khóa vị trí (Lock)" if not self.is_locked else "Mở khóa di chuyển (Unlock)"
        lock_icon = "lock" if not self.is_locked else "lock.open"
        menu.append(create_mac_menu_item(lock_icon, lock_text,
                                         lambda _: set_all_desktop_widgets_locked(not self.is_locked)))

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)
