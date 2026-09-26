"""
Apple macOS Desktop Photo Frame Widget.
Pins photos directly to the desktop in a frosted glass card:
- Displays 2 stacked photos (Duo Photo Frame) or 1 featured photo
- Rounded squircle clipping with specular glass rim and soft drop shadow
- Locked desktop placement with right-click unlock for moving & resizing
- Fluid Apple open spring animation and dynamic resizing
- Context menu for swapping, changing photos, scaling, locking, and presentation mode
"""

import os
import math
import time
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from src.config import config
from src.animator import SpringValue
from src.ui.desktop_widgets import (
    register_widget,
    animate_widget_open,
    unregister_widget,
    set_all_desktop_widgets_locked,
    is_desktop_widgets_locked
)


class DesktopPhotoWidget(Gtk.Window):
    def __init__(self, on_close=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_close = on_close

        register_widget(self)
        animate_widget_open(self)
        self.is_locked = config.get("lock_desktop_widgets", True)

        # Base card geometry
        self.base_card_w = 206.0
        self.base_card_h = 216.0
        self.base_pad = 12.0
        self.base_radius = 24.0
        self.base_total_w = self.base_card_w + 2 * self.base_pad
        self.base_total_h = self.base_card_h + 2 * self.base_pad

        # User scale factor
        raw_scale = config.get("desktop_photo_scale", 1.0)
        try:
            self.scale = max(0.65, min(1.85, round(float(raw_scale), 2)))
        except Exception:
            self.scale = 1.0

        self.card_w = self.base_card_w
        self.card_h = self.base_card_h
        self.pad = self.base_pad
        self.radius = self.base_radius
        self.total_w = max(100, int(self.base_total_w * self.scale))
        self.total_h = max(100, int(self.base_total_h * self.scale))

        self.keep_below = True
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

        # Window setup
        self.set_title("macOS Pinned Photo Widget")
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
        self.set_wmclass("desktop-widget-photo", "DesktopWidgetPhoto")
        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)

        # System theme listener
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
        self.get_style_context().add_class("desktop-widget-photo")

        # Position window from config (default near bottom-left: x=30, y=290)
        self._current_x = int(config.get("desktop_photo_x", 30))
        self._current_y = int(config.get("desktop_photo_y", 290))
        self.move(self._current_x, self._current_y)

        # Presentation & Layout modes
        # Default fit_mode: "fit" (100% full image visible, no cropping, with ambient backdrop)
        self.fit_mode = config.get("desktop_photo_fit_mode", "fit")
        # Layout mode: "columns" (2 vertical slots), "stack" (2 horizontal slots), "single_1", "single_2"
        self.layout_mode = config.get("desktop_photo_layout", "columns")

        # Photo paths
        self.strip_path = self._resolve_photo_path(
            config.get("desktop_photo_strip_path", ""),
            "assets/photos/photo_strip_duo.png",
            "scratch/photo_strip_duo.png"
        )
        self.photo1_path = self._resolve_photo_path(
            config.get("desktop_photo_path_1", ""),
            "assets/photos/photo_girl_top.png",
            "assets/photos/photo1.png"
        )
        self.photo2_path = self._resolve_photo_path(
            config.get("desktop_photo_path_2", ""),
            "assets/photos/photo_girl_bottom.png",
            "assets/photos/photo2.png"
        )

        # Cached pixbufs
        self._pix_strip = None
        self._pix1 = None
        self._pix2 = None
        self._load_photos()

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

    def _resolve_photo_path(self, path, *fallbacks):
        if path and os.path.isfile(path):
            return path
        for fb in fallbacks:
            candidate = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), fb)
            if os.path.isfile(candidate):
                return candidate
            if os.path.isfile(fb):
                return fb
        return ""

    def _load_photos(self):
        self._pix1 = None
        self._pix2 = None
        self._pix_strip = None

        try:
            if self.photo1_path and os.path.isfile(self.photo1_path):
                self._pix1 = GdkPixbuf.Pixbuf.new_from_file(self.photo1_path)
        except Exception:
            self._pix1 = None

        try:
            if self.photo2_path and os.path.isfile(self.photo2_path):
                self._pix2 = GdkPixbuf.Pixbuf.new_from_file(self.photo2_path)
        except Exception:
            self._pix2 = None

        # Only use legacy strip if neither photo 1 nor photo 2 is loaded
        if not self._pix1 and not self._pix2:
            try:
                if self.strip_path and os.path.isfile(self.strip_path):
                    self._pix_strip = GdkPixbuf.Pixbuf.new_from_file(self.strip_path)
            except Exception:
                self._pix_strip = None

    def _on_system_theme_changed(self, *args):
        try:
            from src.utils.theme import is_dark_mode
            self.dark_mode = is_dark_mode()
            self.queue_draw()
        except Exception:
            pass

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
            config.set("desktop_photo_scale", self.scale)

        self.total_w = max(100, int(self.base_total_w * self.scale))
        self.total_h = max(100, int(self.base_total_h * self.scale))
        self.set_size_request(self.total_w, self.total_h)
        self.resize(self.total_w, self.total_h)
        self.queue_draw()

    def set_fit_mode(self, mode):
        """Sets photo display fit mode: fit (100% visible), top (face bias), fill (cover)."""
        if mode in ("fit", "top", "fill"):
            self.fit_mode = mode
            config.set("desktop_photo_fit_mode", mode)
            self.queue_draw()

    def set_layout_mode(self, layout):
        """Sets photo presentation layout: columns (left/right), stack (top/bottom), single_1, single_2."""
        if layout in ("columns", "stack", "single_1", "single_2"):
            self.layout_mode = layout
            config.set("desktop_photo_layout", layout)
            self.queue_draw()

    def _path_rounded_rect(self, cr, x, y, w, h, r):
        r = min(r, w / 2.0, h / 2.0)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw_resize_grip(self, cr, rx, ry, dark):
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
        rx = self.base_pad + self.base_card_w
        ry = self.base_pad + self.base_card_h
        return (rx - 26 <= unscaled_x <= rx + 8) and (ry - 26 <= unscaled_y <= ry + 8)

    def _draw_photo_box(self, cr, pixbuf, target_x, target_y, target_w, target_h, radius=12.0, mode="fit"):
        cr.save()
        self._path_rounded_rect(cr, target_x, target_y, target_w, target_h, radius)
        cr.clip()

        # 1. Sleek Apple Dark Frosted Glass Card (Clean, modern, NO blurry image!)
        slot_bg = cairo.LinearGradient(target_x, target_y, target_x, target_y + target_h)
        slot_bg.add_color_stop_rgba(0.0, 0.10, 0.12, 0.16, 0.55)
        slot_bg.add_color_stop_rgba(1.0, 0.05, 0.07, 0.10, 0.70)
        cr.set_source(slot_bg)
        cr.paint()

        # Subtle specular top sheen on the slot
        sheen = cairo.LinearGradient(target_x, target_y, target_x, target_y + target_h * 0.45)
        sheen.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.08)
        sheen.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(sheen)
        cr.paint()

        if pixbuf:
            pw = pixbuf.get_width()
            ph = pixbuf.get_height()

            if mode == "fit":
                # Crisp contained photo (100% full visibility, zero cropping, NO blur)
                scale = min(target_w / pw, target_h / ph)
                scaled_w = max(1, int(pw * scale))
                scaled_h = max(1, int(ph * scale))
                scaled_pix = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.HYPER)

                offset_x = target_x + (target_w - scaled_w) / 2.0
                offset_y = target_y + (target_h - scaled_h) / 2.0

                photo_r = min(8.0, radius)

                # Soft drop shadow behind photo if letterboxed
                if scaled_w < target_w - 2 or scaled_h < target_h - 2:
                    cr.save()
                    cr.set_source_rgba(0.0, 0.0, 0.0, 0.40)
                    self._path_rounded_rect(cr, offset_x - 1, offset_y - 1, scaled_w + 2, scaled_h + 2, photo_r)
                    cr.fill()
                    cr.restore()

                # Crisp photo rendering
                cr.save()
                self._path_rounded_rect(cr, offset_x, offset_y, scaled_w, scaled_h, photo_r)
                cr.clip()
                Gdk.cairo_set_source_pixbuf(cr, scaled_pix, offset_x, offset_y)
                cr.paint()
                cr.restore()

                # Fine specular hairline border on photo
                cr.save()
                self._path_rounded_rect(cr, offset_x, offset_y, scaled_w, scaled_h, photo_r)
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.20)
                cr.set_line_width(0.8)
                cr.stroke()
                cr.restore()

            elif mode == "top":
                # Cover scaling anchored towards top (20%) so faces & heads are never cropped
                scale = max(target_w / pw, target_h / ph)
                scaled_w = max(1, int(pw * scale))
                scaled_h = max(1, int(ph * scale))
                scaled_pix = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.HYPER)
                offset_x = target_x + (target_w - scaled_w) / 2.0
                if scaled_h > target_h:
                    offset_y = target_y + (target_h - scaled_h) * 0.18
                else:
                    offset_y = target_y + (target_h - scaled_h) / 2.0

                Gdk.cairo_set_source_pixbuf(cr, scaled_pix, offset_x, offset_y)
                cr.paint()

            else:  # "fill" (center crop cover)
                scale = max(target_w / pw, target_h / ph)
                scaled_w = max(1, int(pw * scale))
                scaled_h = max(1, int(ph * scale))
                scaled_pix = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.HYPER)
                offset_x = target_x + (target_w - scaled_w) / 2.0
                offset_y = target_y + (target_h - scaled_h) / 2.0
                Gdk.cairo_set_source_pixbuf(cr, scaled_pix, offset_x, offset_y)
                cr.paint()
        else:
            pat = cairo.LinearGradient(target_x, target_y, target_x + target_w, target_y + target_h)
            pat.add_color_stop_rgb(0.0, 0.15, 0.18, 0.24)
            pat.add_color_stop_rgb(1.0, 0.08, 0.10, 0.14)
            cr.set_source(pat)
            cr.paint()

        cr.restore()

        # Inner border / specular rim
        cr.save()
        self._path_rounded_rect(cr, target_x, target_y, target_w, target_h, radius)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.14)
        cr.set_line_width(0.8)
        cr.stroke()
        cr.restore()

    def _draw_cropped_photo(self, cr, pixbuf, target_x, target_y, target_w, target_h, radius=12.0):
        # Backward compatibility alias
        self._draw_photo_box(cr, pixbuf, target_x, target_y, target_w, target_h, radius, mode=self.fit_mode)

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

        # Center open spring expansion
        cr.translate(cx, cy)
        cr.scale(open_scale, open_scale)
        cr.translate(-cx, -cy)

        # Scale widget coordinates
        cr.scale(self.scale, self.scale)

        use_group = (open_alpha < 0.999)
        if use_group:
            cr.push_group()

        x = self.base_pad
        y = self.base_pad
        w = self.base_card_w
        h = self.base_card_h
        r = self.base_radius

        # 1. Card Background: Apple frosted glass (Translucent - wallpaper visible)
        self._path_rounded_rect(cr, x, y, w, h, r)
        cr.save()
        cr.clip()

        base_pat = cairo.LinearGradient(x, y, x, y + h)
        base_pat.add_color_stop_rgba(0.0, 0.08, 0.10, 0.14, 0.32)
        base_pat.add_color_stop_rgba(1.0, 0.04, 0.05, 0.08, 0.38)
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
        if not self.is_locked:
            cr.save()
            self._path_rounded_rect(cr, x, y, w, h, r)
            cr.set_source_rgba(0.23, 0.51, 0.96, 0.65)
            cr.set_line_width(2.0)
            cr.stroke()
            cr.restore()

        # 4. Draw photo content
        inner_pad = 8.0
        photo_w = w - 2 * inner_pad
        photo_h = h - 2 * inner_pad
        px = x + inner_pad
        py = y + inner_pad

        if self._pix_strip and not self._pix1 and not self._pix2:
            self._draw_photo_box(cr, self._pix_strip, px, py, photo_w, photo_h, radius=14.0, mode=self.fit_mode)
        elif self.layout_mode == "columns" and self._pix1 and self._pix2:
            gap = 6.0
            each_w = (photo_w - gap) / 2.0
            self._draw_photo_box(cr, self._pix1, px, py, each_w, photo_h, radius=12.0, mode=self.fit_mode)
            self._draw_photo_box(cr, self._pix2, px + each_w + gap, py, each_w, photo_h, radius=12.0, mode=self.fit_mode)
        elif self.layout_mode == "single_1" or (self._pix1 and not self._pix2):
            self._draw_photo_box(cr, self._pix1, px, py, photo_w, photo_h, radius=14.0, mode=self.fit_mode)
        elif self.layout_mode == "single_2" or (self._pix2 and not self._pix1):
            self._draw_photo_box(cr, self._pix2, px, py, photo_w, photo_h, radius=14.0, mode=self.fit_mode)
        else:  # "stack" (default or fallback)
            gap = 6.0
            each_h = (photo_h - gap) / 2.0
            self._draw_photo_box(cr, self._pix1, px, py, photo_w, each_h, radius=12.0, mode=self.fit_mode)
            self._draw_photo_box(cr, self._pix2, px, py + each_h + gap, photo_w, each_h, radius=12.0, mode=self.fit_mode)

        # 5. Corner Resize Grip (Only shown when unlocked / editing)
        if not self.is_locked:
            self._draw_resize_grip(cr, x + w, y + h, self.dark_mode)

        if use_group:
            cr.pop_group_to_source()
            cr.paint_with_alpha(open_alpha)

        cr.restore()
        return False

    def _on_button_press(self, widget, event):
        unscaled_x = event.x / self.scale
        unscaled_y = event.y / self.scale

        if event.button == 1:
            # Check corner resize handle (Only when unlocked)
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

            # Dragging -> Only when unlocked!
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
                # When locked, simple left click can open photos app
                self._on_widget_clicked()
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
            new_scale = self._resize_start_scale + (delta / 200.0)
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

        # Cursor hover feedback
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
                config.set("desktop_photo_scale", self.scale)
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
                    config.set("desktop_photo_x", int(self._current_x))
                    config.set("desktop_photo_y", int(self._current_y))
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

    def _on_widget_clicked(self):
        try:
            import subprocess
            subprocess.Popen(["python3", "main.py", "--photos"])
        except Exception:
            pass

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

        all_locked = is_desktop_widgets_locked()
        all_label = "Mở khóa TẤT CẢ Widget trên màn hình" if all_locked else "Khóa cố định TẤT CẢ Widget"
        all_icon = "lock.open" if all_locked else "lock.all"
        menu.append(create_mac_menu_item(all_icon, all_label,
                                         lambda _: set_all_desktop_widgets_locked(not all_locked)))

        menu.append(Gtk.SeparatorMenuItem())

        # Fit Mode Submenu
        fit_menu = create_mac_context_menu()
        fit_presets = [
            ("Vừa vặn 100% (Đầy đủ ảnh, không hình mờ)", "fit"),
            ("Tràn viền sắc nét (Fill lấp đầy khung)", "fill"),
            ("Ưu tiên khuôn mặt & chủ thể (Top Crop)", "top"),
        ]
        for label, f_key in fit_presets:
            chk = (self.fit_mode == f_key)
            item = create_mac_menu_item(None, label, lambda _, k=f_key: self.set_fit_mode(k), is_checked=chk)
            fit_menu.append(item)
        menu.append(create_mac_menu_item("crop", "Chế độ ảnh (Fit / Fill)", submenu=fit_menu))

        # Layout Submenu
        layout_menu = create_mac_context_menu()
        layout_presets = [
            ("2 Tầng Ngang (Trên - Dưới)", "stack"),
            ("2 Cột Dọc (Song song Trái - Phải)", "columns"),
            ("1 Ảnh Đơn (Ảnh 1 lớn)", "single_1"),
            ("1 Ảnh Đơn (Ảnh 2 lớn)", "single_2"),
        ]
        for label, l_key in layout_presets:
            chk = (self.layout_mode == l_key)
            item = create_mac_menu_item(None, label, lambda _, k=l_key: self.set_layout_mode(k), is_checked=chk)
            layout_menu.append(item)
        menu.append(create_mac_menu_item("layout", "Bố cục hiển thị (Layout)", submenu=layout_menu))

        menu.append(Gtk.SeparatorMenuItem())

        # Size Submenu
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

        # Open animation replay
        menu.append(create_mac_menu_item("sparkles", "Phát lại hiệu ứng mở (Replay Open)",
                                         lambda _: self.play_open_animation()))

        menu.append(Gtk.SeparatorMenuItem())

        p1_desc = "(Bên trái)" if self.layout_mode == "columns" else ("(Ảnh 1)" if "single" in self.layout_mode else "(Ảnh trên)")
        p2_desc = "(Bên phải)" if self.layout_mode == "columns" else ("(Ảnh 2)" if "single" in self.layout_mode else "(Ảnh dưới)")
        menu.append(create_mac_menu_item("photo", f"Đổi ảnh 1 {p1_desc}...", lambda _: self._choose_photo(1)))
        menu.append(create_mac_menu_item("photo", f"Đổi ảnh 2 {p2_desc}...", lambda _: self._choose_photo(2)))
        menu.append(create_mac_menu_item("arrow.triangle.2.circlepath", "Đổi chỗ 2 ảnh", lambda _: self._swap_photos()))

        menu.append(Gtk.SeparatorMenuItem())

        pin_label = "Ghim cố định trên Desktop" if not self.keep_below else "Nổi trên cửa sổ (Keep Above)"
        pin_icon = "pin" if not self.keep_below else "pin.slash"
        menu.append(create_mac_menu_item(pin_icon, pin_label, self._on_toggle_keep_below))

        # Reset Position
        menu.append(create_mac_menu_item("reset", "Đặt lại vị trí ban đầu", lambda _: self._reset_position()))

        menu.append(Gtk.SeparatorMenuItem())
        menu.append(create_mac_menu_item("xmark", "Ẩn widget ảnh", lambda _: self.hide_widget(), is_destructive=True))

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def _reset_position(self):
        self.move(80, 500)
        config.set("desktop_photo_x", 80)
        config.set("desktop_photo_y", 500)

    def _choose_photo(self, photo_num):
        dialog = Gtk.FileChooserDialog(
            title=f"Chọn ảnh {photo_num} ghim Desktop",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons("Hủy", Gtk.ResponseType.CANCEL, "Chọn", Gtk.ResponseType.OK)

        filt = Gtk.FileFilter()
        filt.set_name("Hình ảnh (PNG, JPEG, WebP)")
        filt.add_mime_type("image/png")
        filt.add_mime_type("image/jpeg")
        filt.add_mime_type("image/webp")
        dialog.add_filter(filt)

        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if filename and os.path.isfile(filename):
                if photo_num == 1:
                    self.photo1_path = filename
                    config.set("desktop_photo_path_1", filename)
                else:
                    self.photo2_path = filename
                    config.set("desktop_photo_path_2", filename)
                self._load_photos()
                self.queue_draw()
        dialog.destroy()

    def _swap_photos(self):
        self.photo1_path, self.photo2_path = self.photo2_path, self.photo1_path
        self._pix1, self._pix2 = self._pix2, self._pix1
        config.set("desktop_photo_path_1", self.photo1_path)
        config.set("desktop_photo_path_2", self.photo2_path)
        self.queue_draw()

    def _on_toggle_keep_below(self, _):
        self.keep_below = not self.keep_below
        if self.keep_below:
            self.set_keep_below(True)
            self.set_keep_above(False)
        else:
            self.set_keep_below(False)
            self.set_keep_above(True)

    def show_widget(self):
        self.show_all()
        self.set_keep_below(True)
        config.set("enable_desktop_photo", True)
        self.play_open_animation()

    def hide_widget(self):
        self.hide()
        config.set("enable_desktop_photo", False)
        if self.on_close:
            self.on_close()

    def destroy(self):
        unregister_widget(self)
        if self._anim_timer_id:
            GLib.source_remove(self._anim_timer_id)
            self._anim_timer_id = None
        super().destroy()
