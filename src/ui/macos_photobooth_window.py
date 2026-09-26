"""
macOS Photo Booth Application for Ubuntu Linux.
Designed to match Image 2 (macOS Photo Booth on MacBook Pro) 100%:
- Header Titlebar:
  - Apple Traffic Lights on the left (🔴 🟡 🟢).
  - Centered window title: "Photo Booth".
  - Clean, unblemished titlebar with no right-side buttons.
- Main Viewfinder:
  - Full-frame live camera preview filling the window edge-to-edge.
  - Lower-right floating thumbnail preview card of the previous capture with 2px white border.
  - Realistic camera feed by default, or live iPhone / Android camera stream.
  - Screen flash, Apple countdown (3-2-1), and shutter sound.
- Bottom Controls Bar:
  - Bottom-Left: 3 mode icons in a segmented pill ([4-Up] [Single Photo (Selected)] [Video]).
  - Bottom-Center: Iconic 50px Red Shutter Button with white camera glyph inside.
  - Bottom-Right: "Live-Preview" capsule pill button.
- Continuity Camera / Phone Remote Camera:
  - Click "Live-Preview" or right-click to connect iPhone or Android via QR code.
  - High-resolution photo capture and live streaming straight to desktop Photo Booth.
- 3x3 Effects Drawer with real-time filter previews.
"""

import os
import sys
import time
import math
import glob
import subprocess
import threading
from typing import Optional

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo
from PIL import Image

from src.utils.theme import is_system_dark_mode
from src.utils.i18n import t, get_current_language, add_language_listener
from src.utils.qrcodegen import QrCode
from src.modules.sound import SoundManager
from src.modules.phone_camera import PhoneCameraServer, get_local_ip, PHOTOBOOTH_PORT
from src.modules.virtual_cam import (
    VirtualCameraManager,
    MODE_TROLL_IMAGE,
    MODE_FAKE_LAG,
    MODE_WEBCAM,
    MODE_PHONE_CAMERA,
    AVAILABLE_FILTERS,
    FILTER_NORMAL,
    FILTER_MIRROR,
)

PHOTOS_DIR = os.path.expanduser("~/Pictures/Photo Booth")
os.makedirs(PHOTOS_DIR, exist_ok=True)
PHOTOBOOTH_ASSETS_DIR = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth"

def get_pb_image(name: str, width: int = 24, height: Optional[int] = None) -> Gtk.Image:
    """Load a real PNG image asset from assets/photobooth."""
    if height is None:
        height = width
    path = os.path.join(PHOTOBOOTH_ASSETS_DIR, f"{name}.png")
    if os.path.exists(path):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, width, height, True)
            return Gtk.Image.new_from_pixbuf(pix)
        except Exception:
            pass
    return Gtk.Image()


class QRCodeWidget(Gtk.DrawingArea):
    """Renders a pixel-crisp, high-contrast QR code on a rounded white card."""
    def __init__(self, url: str, size: int = 180):
        super().__init__()
        self.url = url
        self.card_size = size
        self.set_size_request(size, size)
        self.connect("draw", self._on_draw)

        try:
            self.qr = QrCode.encode_text(url, QrCode.Ecc.MEDIUM)
        except Exception:
            self.qr = None

    def update_url(self, new_url: str):
        self.url = new_url
        try:
            self.qr = QrCode.encode_text(new_url, QrCode.Ecc.MEDIUM)
        except Exception:
            self.qr = None
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        r = 14.0
        cr.save()
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.fill_preserve()

        cr.set_source_rgba(0.0, 0.0, 0.0, 0.1)
        cr.set_line_width(1.0)
        cr.stroke()
        cr.restore()

        if not self.qr:
            return False

        qr_size = self.qr.get_size()
        quiet_zone = 3
        total_modules = qr_size + quiet_zone * 2
        module_scale = min(w, h) / float(total_modules)
        offset_x = (w - (total_modules * module_scale)) / 2.0
        offset_y = (h - (total_modules * module_scale)) / 2.0

        cr.save()
        cr.set_source_rgb(0.06, 0.06, 0.08)
        for y in range(qr_size):
            for x in range(qr_size):
                if self.qr.get_module(x, y):
                    mx = offset_x + (x + quiet_zone) * module_scale
                    my = offset_y + (y + quiet_zone) * module_scale
                    cr.rectangle(mx, my, module_scale + 0.3, module_scale + 0.3)
        cr.fill()

        # Center mini camera badge
        cx = w / 2.0
        cy = h / 2.0
        badge_r = module_scale * 2.8

        cr.arc(cx, cy, badge_r + 2, 0, 2 * math.pi)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.fill()

        cr.arc(cx, cy, badge_r, 0, 2 * math.pi)
        cr.set_source_rgb(0.0, 0.48, 1.0)
        cr.fill()

        # Crisp vector camera glyph in center
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cam_w = badge_r * 1.15
        cam_h = badge_r * 0.78
        cam_x0 = cx - cam_w / 2
        cam_y0 = cy - cam_h / 2 + badge_r * 0.08
        cam_r = 2.0

        cr.new_sub_path()
        cr.arc(cam_x0 + cam_w - cam_r, cam_y0 + cam_r, cam_r, -math.pi / 2, 0)
        cr.arc(cam_x0 + cam_w - cam_r, cam_y0 + cam_h - cam_r, cam_r, 0, math.pi / 2)
        cr.arc(cam_x0 + cam_r, cam_y0 + cam_h - cam_r, cam_r, math.pi / 2, math.pi)
        cr.arc(cam_x0 + cam_r, cam_y0 + cam_r, cam_r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill()

        # Top notch / flash bump
        cr.rectangle(cx - badge_r * 0.22, cam_y0 - badge_r * 0.16, badge_r * 0.44, badge_r * 0.16)
        cr.fill()

        # Camera lens circle
        cr.arc(cx, cam_y0 + cam_h / 2, badge_r * 0.26, 0, 2 * math.pi)
        cr.set_source_rgb(0.0, 0.48, 1.0)
        cr.fill()
        cr.restore()

        return False


class ShutterButton(Gtk.Button):
    """
    Apple Photo Booth red circular shutter button (matching Image 2).
    Features outer white ring, vibrant red circle, and white camera glyph in center.
    """
    def __init__(self, on_click=None):
        super().__init__()
        self.set_size_request(46, 46)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.get_style_context().add_class("pb-shutter-btn")
        self.connect("draw", self.on_draw)

        self.mode = "single" # "4up", "single", "video"
        self.is_recording = False
        self._is_pressed = False

        self.connect("button-press-event", self._on_press)
        self.connect("button-release-event", self._on_release)
        if on_click:
            self.connect("clicked", lambda w: on_click())

    def set_mode(self, mode: str):
        self.mode = mode
        self.queue_draw()

    def set_recording(self, recording: bool):
        self.is_recording = recording
        self.queue_draw()

    def _on_press(self, widget, event):
        self._is_pressed = True
        self.queue_draw()
        return False

    def _on_release(self, widget, event):
        self._is_pressed = False
        self.queue_draw()
        return False

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        cx, cy = width / 2.0, height / 2.0
        r = min(cx, cy) - 2.0

        if self._is_pressed:
            r -= 1.5

        # 1. Outer subtle white ring / halo
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.45)
        cr.set_line_width(1.5)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()

        # 2. Inner Red Circle
        red_r = r - 2.0
        if self.is_recording:
            cr.set_source_rgb(0.9, 0.15, 0.15)
            cr.arc(cx, cy, red_r, 0, 2 * math.pi)
            cr.fill()

            # White stop square
            sq_size = 14
            cr.set_source_rgb(1.0, 1.0, 1.0)
            sq_r = 2.5
            x0 = cx - sq_size / 2
            y0 = cy - sq_size / 2
            cr.new_sub_path()
            cr.arc(x0 + sq_size - sq_r, y0 + sq_r, sq_r, -math.pi / 2, 0)
            cr.arc(x0 + sq_size - sq_r, y0 + sq_size - sq_r, sq_r, 0, math.pi / 2)
            cr.arc(x0 + sq_r, y0 + sq_size - sq_r, sq_r, math.pi / 2, math.pi)
            cr.arc(x0 + sq_r, y0 + sq_r, sq_r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.fill()
        else:
            # Vibrant Poppy Red button matching Image 2
            cr.set_source_rgb(0.92, 0.28, 0.21)
            cr.arc(cx, cy, red_r, 0, 2 * math.pi)
            cr.fill()

            # Subtle top gloss highlight
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.18)
            cr.arc(cx, cy - red_r * 0.4, red_r * 0.5, 0, math.pi)
            cr.fill()

            if self.mode == "video":
                # Video Camera glyph
                cr.set_source_rgb(1.0, 1.0, 1.0)
                bw, bh = 13, 9
                bx0, by0 = cx - bw / 2 - 2, cy - bh / 2
                br_r = 2.0
                cr.new_sub_path()
                cr.arc(bx0 + bw - br_r, by0 + br_r, br_r, -math.pi / 2, 0)
                cr.arc(bx0 + bw - br_r, by0 + bh - br_r, br_r, 0, math.pi / 2)
                cr.arc(bx0 + br_r, by0 + bh - br_r, br_r, math.pi / 2, math.pi)
                cr.arc(bx0 + br_r, by0 + br_r, br_r, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.fill()

                # Lens triangle on right
                cr.move_to(bx0 + bw + 1, cy - 2)
                cr.line_to(bx0 + bw + 7, cy - 5.5)
                cr.line_to(bx0 + bw + 7, cy + 5.5)
                cr.line_to(bx0 + bw + 1, cy + 2)
                cr.close_path()
                cr.fill()

            elif self.mode == "4up":
                # 4-Grid Burst glyph (2x2 squares)
                cr.set_source_rgb(1.0, 1.0, 1.0)
                sq_s = 5.0
                gap = 2.0
                gx0 = cx - sq_s - gap / 2
                gy0 = cy - sq_s - gap / 2

                for row in range(2):
                    for col in range(2):
                        sx = gx0 + col * (sq_s + gap)
                        sy = gy0 + row * (sq_s + gap)
                        cr.new_sub_path()
                        cr.arc(sx + sq_s - 1.0, sy + 1.0, 1.0, -math.pi / 2, 0)
                        cr.arc(sx + sq_s - 1.0, sy + sq_s - 1.0, 1.0, 0, math.pi / 2)
                        cr.arc(sx + 1.0, sy + sq_s - 1.0, 1.0, math.pi / 2, math.pi)
                        cr.arc(sx + 1.0, sy + 1.0, 1.0, math.pi, 3 * math.pi / 2)
                        cr.close_path()
                        cr.fill()

            else:
                # Classic Still Camera glyph
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cw, ch = 16, 10.5
                cx0, cy0 = cx - cw / 2, cy - ch / 2 + 1
                cr_r = 2.0

                cr.new_sub_path()
                cr.arc(cx0 + cw - cr_r, cy0 + cr_r, cr_r, -math.pi / 2, 0)
                cr.arc(cx0 + cw - cr_r, cy0 + ch - cr_r, cr_r, 0, math.pi / 2)
                cr.arc(cx0 + cr_r, cy0 + ch - cr_r, cr_r, math.pi / 2, math.pi)
                cr.arc(cx0 + cr_r, cy0 + cr_r, cr_r, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.fill()

                # Top notch / flash
                cr.rectangle(cx - 3.0, cy0 - 2.0, 6, 2.0)
                cr.fill()

                # Lens cutout
                cr.set_source_rgb(0.92, 0.28, 0.21)
                cr.arc(cx, cy0 + ch / 2, 3.5, 0, 2 * math.pi)
                cr.fill()

                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.arc(cx, cy0 + ch / 2, 1.8, 0, 2 * math.pi)
                cr.fill()

        return False


class ViewfinderArea(Gtk.DrawingArea):
    """Main live camera preview canvas matching authentic macOS Photo Booth."""
    def __init__(self, vcam_mgr, on_recent_click=None, on_right_click=None, on_filter_selected=None):
        super().__init__()
        self.vcam_mgr = vcam_mgr
        self.on_recent_click = on_recent_click
        self.on_right_click = on_right_click
        self.on_filter_selected = on_filter_selected
        self.set_size_request(640, 480)
        self.connect("draw", self.on_draw)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self._on_button_press)
        self.connect("motion-notify-event", self._on_motion_notify)

        self.countdown_val = 0
        self.flash_alpha = 0.0
        self.burst_progress = ""
        self.video_time_str = ""
        self.toast_message = ""
        self.recent_pixbuf = None
        self.recent_filepath = None

        # Authentic macOS Photo Booth 3x3 Live Effects Grid state
        self.is_effects_grid = False
        self.grid_rects = []

        self._load_latest_recent_photo()

    def _load_latest_recent_photo(self):
        """Loads only actual photos/videos taken in ~/Pictures/Photo Booth. If none exist, no thumbnail!"""
        files = sorted(glob.glob(os.path.join(PHOTOS_DIR, "*.*")), key=os.path.getmtime, reverse=True)
        valid_files = [f for f in files if not os.path.basename(f).startswith(".") and not f.endswith("_thumb.png") and f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4'))]
        if valid_files:
            try:
                self.recent_filepath = valid_files[0]
                if self.recent_filepath.lower().endswith('.mp4'):
                    thumb = self.recent_filepath.rsplit('.', 1)[0] + "_thumb.png"
                    if os.path.exists(thumb):
                        self.recent_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb, 80, 60, True)
                    else:
                        self.recent_pixbuf = None
                else:
                    self.recent_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.recent_filepath, 80, 60, True)
            except Exception:
                self.recent_pixbuf = None
                self.recent_filepath = None
        else:
            self.recent_pixbuf = None
            self.recent_filepath = None

    def update_recent_photo(self, filepath: str):
        try:
            self.recent_filepath = filepath
            if filepath.lower().endswith(('.mp4', '.mov', '.webm')):
                thumb = filepath.rsplit('.', 1)[0] + "_thumb.png"
                if os.path.exists(thumb):
                    self.recent_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb, 80, 60, True)
                else:
                    pix = self.vcam_mgr.get_current_pixbuf()
                    if pix:
                        self.recent_pixbuf = pix.scale_simple(80, 60, GdkPixbuf.InterpType.BILINEAR)
            else:
                self.recent_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filepath, 80, 60, True)
            self.queue_draw()
        except Exception:
            pass

    def _on_button_press(self, widget, event):
        if event.button == 1:
            if self.is_effects_grid:
                # Check which tile was clicked in the 3x3 grid
                for col, row, f_key, tx, ty, tw, th in self.grid_rects:
                    if tx <= event.x <= tx + tw and ty <= event.y <= ty + th:
                        self.is_effects_grid = False
                        if self.on_filter_selected:
                            self.on_filter_selected(f_key)
                        else:
                            self.vcam_mgr.set_filter(f_key)
                        self.queue_draw()
                        return True
                return True

            if self.recent_pixbuf:
                w = widget.get_allocated_width()
                h = widget.get_allocated_height()
                tw, th = 80, 60
                tx = w - tw - 12
                ty = h - th - 10
                if tx <= event.x <= tx + tw and ty <= event.y <= ty + th:
                    if self.recent_filepath and self.on_recent_click:
                        self.on_recent_click(self.recent_filepath)
                    return True
        elif event.button == 3:
            if self.on_right_click:
                self.on_right_click(event)
                return True
        return False

    def _on_motion_notify(self, widget, event):
        window = widget.get_window()
        if not window:
            return False
        if self.is_effects_grid:
            for col, row, f_key, tx, ty, tw, th in self.grid_rects:
                if tx <= event.x <= tx + tw and ty <= event.y <= ty + th:
                    window.set_cursor(Gdk.Cursor.new_from_name(widget.get_display(), "pointer"))
                    return False
        elif self.recent_pixbuf:
            w = widget.get_allocated_width()
            h = widget.get_allocated_height()
            tw, th = 80, 60
            tx = w - tw - 12
            ty = h - th - 10
            if tx <= event.x <= tx + tw and ty <= event.y <= ty + th:
                window.set_cursor(Gdk.Cursor.new_from_name(widget.get_display(), "pointer"))
                return False
        window.set_cursor(None)
        return False

    def set_countdown(self, val):
        self.countdown_val = val
        self.queue_draw()

    def set_burst_progress(self, text):
        self.burst_progress = text
        self.queue_draw()

    def set_video_time(self, time_str):
        self.video_time_str = time_str
        self.queue_draw()

    def show_toast(self, msg: str):
        self.toast_message = msg
        self.queue_draw()
        GLib.timeout_add(3000, self._hide_toast)

    def _hide_toast(self):
        self.toast_message = ""
        self.queue_draw()
        return False

    def trigger_flash(self):
        self.flash_alpha = 1.0
        self.queue_draw()
        GLib.timeout_add(25, self._fade_flash)

    def _fade_flash(self):
        self.flash_alpha -= 0.15
        if self.flash_alpha <= 0.0:
            self.flash_alpha = 0.0
            self.queue_draw()
            return False
        self.queue_draw()
        return True

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Fill background
        cr.set_source_rgb(0.08, 0.08, 0.10)
        cr.paint()

        # If in 3x3 Live Effects Grid mode, render 9 interactive live preview tiles!
        if self.is_effects_grid:
            self.grid_rects = []
            pad_x = 12.0
            pad_y = 12.0
            gap = 8.0
            avail_w = width - pad_x * 2 - gap * 2
            avail_h = height - pad_y * 2 - gap * 2
            tile_w = max(10.0, avail_w / 3.0)
            tile_h = max(10.0, avail_h / 3.0)
            r_tile = 8.0

            raw_pixbuf = self.vcam_mgr.get_raw_pixbuf()
            active_filter = self.vcam_mgr.active_filter

            for idx, (f_key, f_name, _) in enumerate(AVAILABLE_FILTERS[:9]):
                col = idx % 3
                row = idx // 3
                tx = pad_x + col * (tile_w + gap)
                ty = pad_y + row * (tile_h + gap)
                self.grid_rects.append((col, row, f_key, tx, ty, tile_w, tile_h))

                # Draw tile background & clip to rounded rect
                cr.save()
                cr.new_sub_path()
                cr.arc(tx + tile_w - r_tile, ty + r_tile, r_tile, -math.pi / 2, 0)
                cr.arc(tx + tile_w - r_tile, ty + tile_h - r_tile, r_tile, 0, math.pi / 2)
                cr.arc(tx + r_tile, ty + tile_h - r_tile, r_tile, math.pi / 2, math.pi)
                cr.arc(tx + r_tile, ty + r_tile, r_tile, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.clip()

                # 1. Base tile background
                cr.set_source_rgb(0.04, 0.04, 0.06)
                cr.paint()

                # 2. Draw live camera frame into tile (aspect-fill)
                if raw_pixbuf:
                    pw = raw_pixbuf.get_width()
                    ph = raw_pixbuf.get_height()
                    scale = max(tile_w / pw, tile_h / ph)
                    dw = max(1, int(pw * scale))
                    dh = max(1, int(ph * scale))
                    dx = tx + (tile_w - dw) / 2.0
                    dy = ty + (tile_h - dh) / 2.0

                    scaled = raw_pixbuf.scale_simple(dw, dh, GdkPixbuf.InterpType.BILINEAR)
                    if scaled:
                        if f_key == FILTER_MIRROR:
                            cr.save()
                            cr.translate(tx + tile_w, ty)
                            cr.scale(-1, 1)
                            Gdk.cairo_set_source_pixbuf(cr, scaled, (tile_w - dw) / 2.0, (tile_h - dh) / 2.0)
                            cr.paint()
                            cr.restore()
                        else:
                            Gdk.cairo_set_source_pixbuf(cr, scaled, dx, dy)
                            cr.paint()
                            cr.save()
                            cr.translate(tx, ty)
                            self.vcam_mgr._apply_cairo_filter(cr, f_key, int(tile_w), int(tile_h))
                            cr.restore()

                # 3. Bottom label bar (Apple translucent dark bar)
                bar_h = 24.0
                bar_y = ty + tile_h - bar_h
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.72)
                cr.rectangle(tx, bar_y, tile_w, bar_h)
                cr.fill()

                # Filter name text (Localized)
                f_name_trans = t(f"photobooth_filter_{f_key}", f_name)
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(11)
                ext = cr.text_extents(f_name_trans)
                tx_text = tx + (tile_w - ext.width) / 2.0 - ext.x_bearing
                ty_text = bar_y + (bar_h / 2.0) - (ext.y_bearing + ext.height / 2.0)
                cr.move_to(tx_text, ty_text)
                cr.show_text(f_name_trans)

                cr.restore()

                # 4. Border / Highlight: active filter gets Apple blue border
                cr.save()
                cr.new_sub_path()
                cr.arc(tx + tile_w - r_tile, ty + r_tile, r_tile, -math.pi / 2, 0)
                cr.arc(tx + tile_w - r_tile, ty + tile_h - r_tile, r_tile, 0, math.pi / 2)
                cr.arc(tx + r_tile, ty + tile_h - r_tile, r_tile, math.pi / 2, math.pi)
                cr.arc(tx + r_tile, ty + r_tile, r_tile, math.pi, 3 * math.pi / 2)
                cr.close_path()

                if f_key == active_filter:
                    cr.set_source_rgba(0.0, 0.48, 1.0, 1.0) # Apple vibrant blue
                    cr.set_line_width(3.0)
                else:
                    cr.set_source_rgba(1.0, 1.0, 1.0, 0.15)
                    cr.set_line_width(1.0)
                cr.stroke()
                cr.restore()

            # If toast message exists, draw it over the grid
            if self.toast_message:
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(14)
                ext = cr.text_extents(self.toast_message)
                tw, th = ext.width + 36, 38
                tx, ty = (width - tw) / 2, height - 70
                tr = 19.0
                cr.new_sub_path()
                cr.arc(tx + tw - tr, ty + tr, tr, -math.pi / 2, 0)
                cr.arc(tx + tw - tr, ty + th - tr, tr, 0, math.pi / 2)
                cr.arc(tx + tr, ty + th - tr, tr, math.pi / 2, math.pi)
                cr.arc(tx + tr, ty + tr, tr, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.set_source_rgba(0.12, 0.12, 0.15, 0.94)
                cr.fill()
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
                cr.set_line_width(1.0)
                cr.stroke()
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.move_to(tx + 18, ty + 24)
                cr.show_text(self.toast_message)

            return False

        # Draw current camera frame (Aspect Fit - never distorted, never cropped or blown up)
        pixbuf = self.vcam_mgr.get_current_pixbuf()
        if pixbuf:
            pw = pixbuf.get_width()
            ph = pixbuf.get_height()
            
            # Natural aspect fit: preserves 100% of the phone camera field of view
            scale = min(width / pw, height / ph)
            dw = max(1, int(pw * scale))
            dh = max(1, int(ph * scale))
            dx = (width - dw) // 2
            dy = (height - dh) // 2

            scaled = pixbuf.scale_simple(dw, dh, GdkPixbuf.InterpType.BILINEAR)
            if scaled:
                # Rounded video card effect matching macOS
                r_cam = 10.0
                cr.save()
                cr.new_sub_path()
                cr.arc(dx + dw - r_cam, dy + r_cam, r_cam, -math.pi / 2, 0)
                cr.arc(dx + dw - r_cam, dy + dh - r_cam, r_cam, 0, math.pi / 2)
                cr.arc(dx + r_cam, dy + dh - r_cam, r_cam, math.pi / 2, math.pi)
                cr.arc(dx + r_cam, dy + r_cam, r_cam, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.clip()

                Gdk.cairo_set_source_pixbuf(cr, scaled, dx, dy)
                cr.paint()
                cr.restore()

                # Subtle elegant border around camera frame
                cr.new_sub_path()
                cr.arc(dx + dw - r_cam, dy + r_cam, r_cam, -math.pi / 2, 0)
                cr.arc(dx + dw - r_cam, dy + dh - r_cam, r_cam, 0, math.pi / 2)
                cr.arc(dx + r_cam, dy + dh - r_cam, r_cam, math.pi / 2, math.pi)
                cr.arc(dx + r_cam, dy + r_cam, r_cam, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
                cr.set_line_width(1.0)
                cr.stroke()

        # 4-Up Burst Badge
        if self.burst_progress:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.65)
            cr.arc(50, 40, 24, 0, 2 * math.pi)
            cr.fill()

            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(15)
            ext = cr.text_extents(self.burst_progress)
            cr.move_to(50 - ext.width / 2, 40 + ext.height / 2)
            cr.show_text(self.burst_progress)

        # Video Recording Timer Badge
        if self.video_time_str:
            badge_w, badge_h = 130, 32
            bx = (width - badge_w) / 2
            by = 16
            r_b = 16.0
            cr.new_sub_path()
            cr.arc(bx + badge_w - r_b, by + r_b, r_b, -math.pi / 2, 0)
            cr.arc(bx + badge_w - r_b, by + badge_h - r_b, r_b, 0, math.pi / 2)
            cr.arc(bx + r_b, by + badge_h - r_b, r_b, math.pi / 2, math.pi)
            cr.arc(bx + r_b, by + r_b, r_b, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.set_source_rgba(0.1, 0.1, 0.12, 0.85)
            cr.fill()

            # Pulsing red dot
            t = time.time()
            if int(t * 2) % 2 == 0:
                cr.set_source_rgb(0.95, 0.2, 0.2)
                cr.arc(bx + 18, by + 16, 5, 0, 2 * math.pi)
                cr.fill()

            # Timer text
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(13)
            cr.move_to(bx + 32, by + 21)
            cr.show_text(f"REC {self.video_time_str}")

        # Floating Recent Photo Thumbnail in lower right (matching Image 2)
        if self.recent_pixbuf:
            tw, th = 80, 60
            tx = width - tw - 12
            ty = height - th - 10
            cr_r = 5.0

            # Soft drop shadow
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.5)
            cr.new_sub_path()
            cr.arc(tx + tw - cr_r + 1.5, ty + cr_r + 1.5, cr_r, -math.pi / 2, 0)
            cr.arc(tx + tw - cr_r + 1.5, ty + th - cr_r + 1.5, cr_r, 0, math.pi / 2)
            cr.arc(tx + cr_r + 1.5, ty + th - cr_r + 1.5, cr_r, math.pi / 2, math.pi)
            cr.arc(tx + cr_r + 1.5, ty + cr_r + 1.5, cr_r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.fill()

            # White frame card with 2.5px white border
            cr.save()
            cr.new_sub_path()
            cr.arc(tx + tw - cr_r, ty + cr_r, cr_r, -math.pi / 2, 0)
            cr.arc(tx + tw - cr_r, ty + th - cr_r, cr_r, 0, math.pi / 2)
            cr.arc(tx + cr_r, ty + th - cr_r, cr_r, math.pi / 2, math.pi)
            cr.arc(tx + cr_r, ty + cr_r, cr_r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_line_width(2.5)
            cr.stroke_preserve()
            cr.clip()

            scaled_rec = self.recent_pixbuf.scale_simple(tw, th, GdkPixbuf.InterpType.BILINEAR)
            if scaled_rec:
                Gdk.cairo_set_source_pixbuf(cr, scaled_rec, tx, ty)
                cr.paint()
            cr.restore()

        # Toast Message
        if self.toast_message:
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(14)
            ext = cr.text_extents(self.toast_message)
            tw, th = ext.width + 36, 38
            tx, ty = (width - tw) / 2, height - 70
            tr = 19.0

            cr.new_sub_path()
            cr.arc(tx + tw - tr, ty + tr, tr, -math.pi / 2, 0)
            cr.arc(tx + tw - tr, ty + th - tr, tr, 0, math.pi / 2)
            cr.arc(tx + tr, ty + th - tr, tr, math.pi / 2, math.pi)
            cr.arc(tx + tr, ty + tr, tr, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.set_source_rgba(0.12, 0.12, 0.15, 0.94)
            cr.fill()

            cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
            cr.set_line_width(1.0)
            cr.stroke()

            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.move_to(tx + 18, ty + 24)
            cr.show_text(self.toast_message)

        # Countdown overlay (3, 2, 1)
        if self.countdown_val > 0:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.45)
            cr.paint()

            text = str(self.countdown_val)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(125)

            ext = cr.text_extents(text)
            tx = (width - ext.width) / 2 - ext.x_bearing
            ty = (height - ext.height) / 2 - ext.y_bearing

            # Drop shadow
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.7)
            cr.move_to(tx + 4, ty + 4)
            cr.show_text(text)

            # Crisp numeral
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.98)
            cr.move_to(tx, ty)
            cr.show_text(text)

        # White screen flash overlay
        if self.flash_alpha > 0.0:
            cr.set_source_rgba(1.0, 1.0, 1.0, self.flash_alpha)
            cr.paint()

        return False


class MacOSPhotoBoothWindow(Gtk.Window):
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MacOSPhotoBoothWindow()
        return cls._instance

    def show_and_present(self):
        """Unminimizes, shows, and focuses the window to the front."""
        self.deiconify()
        self.show_all()
        self.present_with_time(Gdk.CURRENT_TIME)
        try:
            subprocess.Popen(["wmctrl", "-a", "Photo Booth"])
        except Exception:
            pass

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        MacOSPhotoBoothWindow._instance = self

        GLib.set_prgname("macos-photobooth")
        if not GLib.get_application_name():
            GLib.set_application_name(t("photobooth_title", "Photo Booth"))
        self.set_title(t("photobooth_title", "Photo Booth"))
        self.set_wmclass("macos-photobooth", "Photo Booth")
        self.set_role("photobooth")
        self.set_default_size(718, 648)
        self.set_position(Gtk.WindowPosition.CENTER)

        self._is_iconified = False

        # Borderless window with custom rounded decoration
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_resizable(True)

        geom = Gdk.Geometry()
        geom.min_width = 580
        geom.min_height = 480
        self.set_geometry_hints(None, geom, Gdk.WindowHints.MIN_SIZE)

        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        self.vcam_mgr = VirtualCameraManager.get_instance()
        self.sound_mgr = SoundManager.get_instance()
        self.phone_server = PhoneCameraServer.get_instance()
        self.dark_mode = is_system_dark_mode()

        self.capture_mode = "single" # "4up", "single", "video"
        self._countdown_timer_id = None
        self._countdown_val = 0
        self._is_maximized = False

        # 4-Up Burst State
        self._burst_shots = []
        self._burst_step = 0

        # Video State
        self._is_recording = False
        self._recording_start_time = 0
        self._recording_timer_id = None

        # Start Continuity Camera server in background
        self.phone_server.on_photo_received_cb = self._on_phone_photo_received
        self.phone_server.on_frame_received_cb = self._on_phone_frame_received
        self.phone_server.on_phone_connected_cb = self._on_phone_connected
        self.phone_server.start()

        # Stylesheet
        self._apply_css()

        # Master Overlay for Resize Handles
        self.master_overlay = Gtk.Overlay()
        self.add(self.master_overlay)

        # Root Layout Box
        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root_box.get_style_context().add_class("photobooth-window")
        self.master_overlay.add(self.root_box)

        self._setup_resize_handles()

        # 1. macOS Titlebar (Traffic lights + Centered Title "Photo Booth" ONLY - matching Image 2)
        self._build_header_bar()

        # 2. Main Viewport & Overlay Container (fills window edge-to-edge)
        self.main_overlay = Gtk.Overlay()
        self.root_box.pack_start(self.main_overlay, True, True, 0)

        self.viewfinder = ViewfinderArea(
            self.vcam_mgr,
            on_recent_click=self._open_recent_photo,
            on_right_click=self._on_viewfinder_right_click,
            on_filter_selected=self._on_filter_selected
        )
        self.main_overlay.add(self.viewfinder)

        # Floating Phone Camera Badge in top-right of viewfinder
        self.btn_phone_cam = Gtk.Button()
        self.btn_phone_cam.get_style_context().add_class("pb-phone-badge")
        self.btn_phone_cam.set_halign(Gtk.Align.END)
        self.btn_phone_cam.set_valign(Gtk.Align.START)
        self.btn_phone_cam.set_margin_top(12)
        self.btn_phone_cam.set_margin_end(14)

        phone_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        phone_icon = get_pb_image("icon_iphone_pill", 16, 16)
        self.lbl_phone_status = Gtk.Label(label=t("photobooth_connect_phone", "Kết nối điện thoại"))
        self.lbl_phone_status.get_style_context().add_class("caption")
        phone_box.pack_start(phone_icon, False, False, 0)
        phone_box.pack_start(self.lbl_phone_status, False, False, 0)
        self.btn_phone_cam.add(phone_box)
        self.btn_phone_cam.connect("clicked", lambda w: self._toggle_continuity_sheet())
        self.main_overlay.add_overlay(self.btn_phone_cam)

        # Continuity Camera QR Popover Sheet (Modal Overlay)
        self._build_continuity_sheet()

        # 3. Bottom Controls Bar (Mode buttons on Left, Red Shutter in Center, Live-Preview on Right)
        self._build_controls_bar()

        # Register live frame callback for 30 FPS redraw
        self.vcam_mgr.register_frame_callback(self._on_frame_update)

        self.connect("draw", self._on_window_draw)
        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self._on_key_press)
        self.connect("window-state-event", self._on_window_state_event)
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

    def _apply_css(self):
        css = """
        .photobooth-window {
            background-color: #272a33;
            color: #ffffff;
            border-radius: 12px;
        }
        .pb-header {
            background-color: #2b2e37;
            border-bottom: none;
            padding: 7px 12px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        .pb-title {
            font-size: 13px;
            font-weight: 500;
            color: #e5e5ea;
        }
        
        /* Traffic Lights */
        .traffic-light {
            min-width: 12px;
            min-height: 12px;
            border-radius: 6px;
            border: none;
            padding: 0;
            margin: 0;
            background-color: transparent;
        }
        .tl-symbol {
            font-size: 8px;
            font-weight: 800;
            color: rgba(0, 0, 0, 0.6);
        }
        .tl-red { background-color: #ff5f56; }
        .tl-yellow { background-color: #ffbd2e; }
        .tl-green { background-color: #27c93f; }

        /* Segmented Mode Switcher (Bottom Left) */
        .pb-segmented {
            background-color: #1e2128;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 2px;
        }
        .pb-segmented button {
            background: transparent;
            border: none;
            border-radius: 4px;
            padding: 3px 6px;
            transition: all 0.12s;
        }
        .pb-segmented button:hover {
            background-color: rgba(255, 255, 255, 0.08);
        }
        .pb-segmented button.active {
            background-color: #555d6e;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        }

        /* Bottom Controls Bar */
        .pb-controls-bar {
            background-color: #252831;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            padding: 6px 14px;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        }

        .pb-live-pill {
            background-color: #444a56;
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #ffffff;
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .pb-live-pill:hover {
            background-color: #505765;
        }
        .pb-live-pill.active {
            background-color: #007aff;
            border-color: #007aff;
        }

        /* Floating Phone Badge in Viewfinder */
        .pb-phone-badge {
            background-color: rgba(24, 26, 32, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 14px;
            padding: 4px 10px;
            color: #ffffff;
            transition: all 0.15s;
        }
        .pb-phone-badge:hover {
            background-color: rgba(40, 44, 54, 0.90);
            border-color: rgba(255, 255, 255, 0.35);
        }
        .pb-phone-badge.connected {
            background-color: rgba(48, 209, 88, 0.22);
            border-color: #30d158;
            color: #30d158;
        }

        /* Continuity Modal Sheet */
        .continuity-sheet {
            background-color: rgba(28, 28, 30, 0.96);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 18px;
            padding: 24px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
        }
        .url-box {
            background-color: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 8px 14px;
            font-family: monospace;
            font-size: 13px;
        }

        /* 3x3 Effect Tiles */
        .effect-tile {
            background-color: rgba(32, 32, 36, 0.95);
            border: 2px solid rgba(255, 255, 255, 0.12);
            border-radius: 14px;
            padding: 10px;
            transition: all 0.15s;
        }
        .effect-tile:hover {
            border-color: #007aff;
            background-color: rgba(44, 44, 48, 0.98);
        }
        .effect-tile.active {
            border-color: #007aff;
            background-color: rgba(0, 122, 255, 0.25);
        }

        /* macOS Context Menu */
        .pb-context-menu {
            background-color: #23252b;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 10px;
            padding: 4px;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.65);
        }
        .pb-context-menu menuitem {
            border-radius: 6px;
            padding: 6px 10px;
            color: #ffffff;
            font-size: 13px;
            font-weight: 500;
        }
        .pb-context-menu menuitem:hover {
            background-color: #007aff;
            color: #ffffff;
        }
        .pb-context-menu separator {
            background-color: rgba(255, 255, 255, 0.1);
            margin: 4px 6px;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_header_bar(self):
        """macOS Titlebar matching Image 2 100%: Traffic lights on left, 'Photo Booth' in center."""
        self.header_event_box = Gtk.EventBox()
        self.header_event_box.set_visible_window(False)
        self.header_event_box.connect("button-press-event", self._on_header_button_press)
        self.root_box.pack_start(self.header_event_box, False, False, 0)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.get_style_context().add_class("pb-header")
        self.header_event_box.add(header)

        # 1. Traffic Lights (Left)
        tf_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tf_box.set_valign(Gtk.Align.CENTER)

        def make_traffic_light(color_class, symbol, cb):
            btn = Gtk.Button()
            btn.get_style_context().add_class("traffic-light")
            btn.get_style_context().add_class(color_class)
            lbl = Gtk.Label(label="")
            lbl.get_style_context().add_class("tl-symbol")
            btn.add(lbl)
            btn.connect("enter-notify-event", lambda b, e: [lbl.set_text(symbol), False][1])
            btn.connect("leave-notify-event", lambda b, e: [lbl.set_text(""), False][1])
            btn.connect("clicked", lambda w: cb())
            return btn

        btn_close = make_traffic_light("tl-red", "✕", lambda: self.destroy())
        btn_min = make_traffic_light("tl-yellow", "—", lambda: self.iconify())
        btn_max = make_traffic_light("tl-green", "⤢", self._toggle_maximize)

        tf_box.pack_start(btn_close, False, False, 0)
        tf_box.pack_start(btn_min, False, False, 0)
        tf_box.pack_start(btn_max, False, False, 0)
        header.pack_start(tf_box, False, False, 2)

        # 2. Centered Window Title: "Photo Booth" (matching Image 2)
        self.title_lbl = Gtk.Label(label=t("photobooth_title", "Photo Booth"))
        self.title_lbl.get_style_context().add_class("pb-title")
        header.set_center_widget(self.title_lbl)

    def _build_controls_bar(self):
        """
        Bottom Controls Bar matching Image 2 100%:
        - Left: 3 mode icons in a segmented pill ([4-Up] [Single Photo (Selected)] [Video])
        - Center: 50px Red Shutter button with white camera glyph
        - Right: 'Live-Preview' capsule pill button
        """
        ctrls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        ctrls.get_style_context().add_class("pb-controls-bar")
        self.root_box.pack_start(ctrls, False, False, 0)

        # 1. Bottom-Left: Mode Switcher ([4-Up] [Single] [Video])
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        mode_box.get_style_context().add_class("pb-segmented")
        mode_box.set_valign(Gtk.Align.CENTER)

        def make_mode_btn(img_name, tooltip_text, mode_val):
            btn = Gtk.Button()
            btn.set_tooltip_text(tooltip_text)
            btn.add(get_pb_image(img_name, 18, 18))
            btn.connect("clicked", lambda w: self._set_capture_mode(mode_val))
            return btn

        self.btn_mode_4up = make_mode_btn("mode_burst", t("photobooth_mode_4up", "Chụp 4 ô liên hoàn"), "4up")
        self.btn_mode_single = make_mode_btn("mode_single", t("photobooth_mode_single", "Chụp ảnh đơn"), "single")
        self.btn_mode_single.get_style_context().add_class("active")
        self.btn_mode_video = make_mode_btn("mode_video", t("photobooth_mode_video", "Quay video"), "video")

        # Order matching Image 2: [4-Up] [Single] [Video]
        mode_box.pack_start(self.btn_mode_4up, False, False, 0)
        mode_box.pack_start(self.btn_mode_single, False, False, 0)
        mode_box.pack_start(self.btn_mode_video, False, False, 0)
        ctrls.pack_start(mode_box, False, False, 0)

        # 2. Bottom-Center: Iconic Red Shutter Button with White Camera Glyph
        self.btn_shutter = ShutterButton(on_click=self._on_shutter_press)
        ctrls.set_center_widget(self.btn_shutter)

        # 3. Bottom-Right: 'Live-Preview' Pill Button (matching Image 2)
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_box.set_valign(Gtk.Align.CENTER)

        self.btn_live_preview = Gtk.Button(label=t("photobooth_effects", "Hiệu ứng"))
        self.btn_live_preview.get_style_context().add_class("pb-live-pill")
        self.btn_live_preview.connect("clicked", self._on_live_preview_clicked)
        right_box.pack_end(self.btn_live_preview, False, False, 0)

        ctrls.pack_end(right_box, False, False, 0)

    def _on_live_preview_clicked(self, widget):
        """Directly toggles the authentic 3x3 Live Effects Drawer (matching real Photo Booth)."""
        self._toggle_effects_drawer()

    def _on_viewfinder_right_click(self, event):
        """Right click brings up camera settings / virtual cam toggle with authentic macOS icons."""
        self._show_camera_menu(event=event)

    def _show_camera_menu(self, widget=None, event=None):
        """Display macOS styled context menu with crisp image icons."""
        menu = Gtk.Menu()
        menu.get_style_context().add_class("pb-context-menu")

        # 1. Phone Continuity Camera Item with clean image icon
        item_phone = Gtk.MenuItem()
        box_phone = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_phone.pack_start(get_pb_image("menu_phone", 18, 18), False, False, 0)
        lbl_phone = Gtk.Label(label=t("photobooth_phone_menu", "Quét mã kết nối điện thoại (Continuity)"))
        lbl_phone.set_halign(Gtk.Align.START)
        box_phone.pack_start(lbl_phone, True, True, 0)
        item_phone.add(box_phone)
        item_phone.connect("activate", lambda w: self._toggle_continuity_sheet(True))
        menu.append(item_phone)

        # Separator
        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        # 2. Virtual Camera Broadcast Item with clean image icon
        item_vcam = Gtk.MenuItem()
        box_vcam = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_vcam.pack_start(get_pb_image("menu_vcam", 18, 18), False, False, 0)
        lbl_vcam = Gtk.Label(label=t("photobooth_vcam_menu", "Phát Cam ảo (Virtual Camera)"))
        lbl_vcam.set_halign(Gtk.Align.START)
        box_vcam.pack_start(lbl_vcam, True, True, 0)

        if self.vcam_mgr.is_broadcasting:
            box_vcam.pack_end(get_pb_image("menu_check", 16, 16), False, False, 0)

        item_vcam.add(box_vcam)
        item_vcam.connect("activate", self._toggle_vcam_from_menu)
        menu.append(item_vcam)

        menu.show_all()
        if event is not None:
            try:
                menu.popup_at_pointer(event)
            except Exception:
                menu.popup(None, None, None, None, getattr(event, 'button', 3), getattr(event, 'time', 0))
        elif widget is not None:
            try:
                menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)
            except Exception:
                menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())
        else:
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def _toggle_vcam_from_menu(self, widget):
        if not self.vcam_mgr.is_broadcasting:
            ok = self.vcam_mgr.start_virtual_cam()
            if ok:
                self.viewfinder.show_toast(t("photobooth_vcam_started", "Cam ảo: Đang phát"))
            else:
                self.viewfinder.show_toast(t("photobooth_vcam_error", "Không thể bật Cam ảo"))
        else:
            self.vcam_mgr.stop_virtual_cam()
            self.viewfinder.show_toast(t("photobooth_vcam_stopped", "Cam ảo: Đã dừng"))

    def _open_recent_photo(self, filepath):
        subprocess.Popen(["xdg-open", filepath])

    def _build_continuity_sheet(self):
        """macOS Floating Sheet Modal for scanning QR code and connecting phone."""
        self.continuity_sheet = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.continuity_sheet.get_style_context().add_class("continuity-sheet")
        self.continuity_sheet.set_halign(Gtk.Align.CENTER)
        self.continuity_sheet.set_valign(Gtk.Align.CENTER)
        self.continuity_sheet.set_size_request(440, 480)

        # Header with Title and Close Button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.pack_start(get_pb_image("icon_continuity", 22, 22), False, False, 0)
        self.lbl_continuity_title = Gtk.Label(label=t("photobooth_continuity_title", "Continuity Camera"))
        self.lbl_continuity_title.get_style_context().add_class("title-2")
        title_box.pack_start(self.lbl_continuity_title, False, False, 0)
        top_row.pack_start(title_box, False, False, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("pb-live-pill")
        btn_close.connect("clicked", lambda w: self._toggle_continuity_sheet(False))
        top_row.pack_end(btn_close, False, False, 0)
        self.continuity_sheet.pack_start(top_row, False, False, 0)

        # Description
        self.desc_lbl = Gtk.Label(label=t("photobooth_continuity_desc"))
        self.desc_lbl.set_use_markup(True)
        self.desc_lbl.set_line_wrap(True)
        self.desc_lbl.set_max_width_chars(44)
        self.desc_lbl.set_halign(Gtk.Align.CENTER)
        self.continuity_sheet.pack_start(self.desc_lbl, False, False, 0)

        # QR Code Card
        qr_center = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        qr_center.set_halign(Gtk.Align.CENTER)
        self.qr_widget = QRCodeWidget(self.phone_server.get_url(), size=190)
        qr_center.pack_start(self.qr_widget, False, False, 0)
        self.continuity_sheet.pack_start(qr_center, False, False, 4)

        # Direct URL & Copy Button
        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        url_box.get_style_context().add_class("url-box")
        url_box.set_halign(Gtk.Align.CENTER)

        self.url_label = Gtk.Label(label=self.phone_server.get_url())
        url_box.pack_start(self.url_label, False, False, 0)

        self.btn_copy_url = Gtk.Button(label=t("photobooth_copy_url", "Sao chép"))
        self.btn_copy_url.get_style_context().add_class("pb-live-pill")
        self.btn_copy_url.connect("clicked", self._copy_url)
        url_box.pack_start(self.btn_copy_url, False, False, 0)
        self.continuity_sheet.pack_start(url_box, False, False, 0)

        # Connection Status
        self.sheet_status_lbl = Gtk.Label(label=t("photobooth_waiting_phone", "Đang chờ điện thoại quét mã..."))
        self.sheet_status_lbl.get_style_context().add_class("caption")
        self.continuity_sheet.pack_start(self.sheet_status_lbl, False, False, 0)

        self.continuity_sheet.set_no_show_all(True)
        self.continuity_sheet.hide()
        self.main_overlay.add_overlay(self.continuity_sheet)

    def _copy_url(self, widget):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.phone_server.get_url(), -1)
        self.viewfinder.show_toast(t("photobooth_copied", "Đã sao chép liên kết!"))

    def _toggle_continuity_sheet(self, visible=None):
        if visible is None:
            visible = not self.continuity_sheet.get_visible()
        if visible:
            if self.viewfinder.is_effects_grid:
                self._toggle_effects_drawer(False)
            self.qr_widget.update_url(self.phone_server.get_url())
            self.url_label.set_text(self.phone_server.get_url())
            self.continuity_sheet.set_no_show_all(False)
            self.continuity_sheet.show_all()
        else:
            self.continuity_sheet.hide()
            self.continuity_sheet.set_no_show_all(True)

    def _on_filter_selected(self, filter_key):
        """Called when user clicks any of the 9 tiles in the 3x3 Live Effects Grid."""
        self.vcam_mgr.set_filter(filter_key)
        self.btn_phone_cam.show()
        self.btn_live_preview.get_style_context().remove_class("active")

    def _toggle_effects_drawer(self, visible=None):
        """Toggles the authentic macOS Photo Booth 3x3 Live Effects Grid in the viewfinder."""
        if visible is None:
            visible = not self.viewfinder.is_effects_grid
        self.viewfinder.is_effects_grid = visible
        if visible:
            if self.continuity_sheet.get_visible():
                self._toggle_continuity_sheet(False)
            self.btn_phone_cam.hide()
            self.btn_live_preview.get_style_context().add_class("active")
        else:
            self.btn_phone_cam.show()
            self.btn_live_preview.get_style_context().remove_class("active")
        self.viewfinder.queue_draw()

    # --- Phone Camera Callbacks ---
    def _on_phone_connected(self):
        self.sheet_status_lbl.set_text("Đã kết nối iPhone! Sẵn sàng chụp ảnh.")
        self.lbl_phone_status.set_text("iPhone Camera")
        self.btn_phone_cam.get_style_context().add_class("connected")
        self.viewfinder.show_toast(t("photobooth_phone_connected_toast", "Đã kết nối iPhone!"))
        self._toggle_continuity_sheet(False)

    def _on_phone_photo_received(self, filepath):
        """Called when phone captures and uploads a photo."""
        self.viewfinder.trigger_flash()
        self.sound_mgr.play_screenshot()
        self.viewfinder.show_toast(t("photobooth_photo_received_toast", "Đã nhận ảnh từ iPhone!"))
        self.viewfinder.update_recent_photo(filepath)

    def _on_phone_frame_received(self, jpeg_bytes):
        """Called when phone is streaming live camera feed."""
        if self.vcam_mgr.set_phone_frame_bytes(jpeg_bytes):
            GLib.idle_add(self._update_phone_live_ui)

    def _update_phone_live_ui(self):
        if not getattr(self, "_phone_ui_connected", False):
            self._phone_ui_connected = True
            self.lbl_phone_status.set_text("iPhone Camera (Live)")
            self.btn_phone_cam.get_style_context().add_class("connected")
        if self.viewfinder:
            self.viewfinder.queue_draw()
        return False

    # --- Shutter & Capture Logic ---
    def _on_language_changed(self, lang_code: str):
        try:
            self._retranslate_ui()
        except Exception:
            GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("photobooth_title", "Photo Booth"))
            if hasattr(self, "title_lbl"):
                self.title_lbl.set_text(t("photobooth_title", "Photo Booth"))
            if hasattr(self, "lbl_phone_status"):
                is_conn = getattr(self.phone_server, "is_connected", False)
                self.lbl_phone_status.set_text(t("photobooth_phone_connected" if is_conn else "photobooth_connect_phone"))
            if hasattr(self, "btn_live_preview"):
                self.btn_live_preview.set_label(t("photobooth_effects", "Hiệu ứng"))
            if hasattr(self, "btn_mode_4up"):
                self.btn_mode_4up.set_tooltip_text(t("photobooth_mode_4up", "Chụp 4 ô liên hoàn"))
            if hasattr(self, "btn_mode_single"):
                self.btn_mode_single.set_tooltip_text(t("photobooth_mode_single", "Chụp ảnh đơn"))
            if hasattr(self, "btn_mode_video"):
                self.btn_mode_video.set_tooltip_text(t("photobooth_mode_video", "Quay video"))
            if hasattr(self, "lbl_continuity_title"):
                self.lbl_continuity_title.set_text(t("photobooth_continuity_title", "Continuity Camera"))
            if hasattr(self, "desc_lbl"):
                self.desc_lbl.set_markup(t("photobooth_continuity_desc"))
            if hasattr(self, "btn_copy_url"):
                self.btn_copy_url.set_label(t("photobooth_copy_url", "Sao chép"))
            if hasattr(self, "sheet_status_lbl"):
                self.sheet_status_lbl.set_text(t("photobooth_waiting_phone", "Đang chờ điện thoại quét mã..."))
            if hasattr(self, "viewfinder"):
                self.viewfinder.queue_draw()
        except Exception as e:
            print(f"[PhotoBooth] _retranslate_ui error: {e}")

    def _set_capture_mode(self, mode):
        self.capture_mode = mode
        self.btn_mode_single.get_style_context().remove_class("active")
        self.btn_mode_4up.get_style_context().remove_class("active")
        self.btn_mode_video.get_style_context().remove_class("active")

        if mode == "single":
            self.btn_mode_single.get_style_context().add_class("active")
            self.btn_shutter.set_mode("single")
            self.btn_shutter.set_recording(False)
            self.viewfinder.show_toast(t("photobooth_toast_mode_single", "Chế độ chụp ảnh đơn"))
        elif mode == "4up":
            self.btn_mode_4up.get_style_context().add_class("active")
            self.btn_shutter.set_mode("4up")
            self.btn_shutter.set_recording(False)
            self.viewfinder.show_toast(t("photobooth_toast_mode_4up", "Chế độ chụp 4 ô liên hoàn"))
        elif mode == "video":
            self.btn_mode_video.get_style_context().add_class("active")
            self.btn_shutter.set_mode("video")
            self.viewfinder.show_toast(t("photobooth_toast_mode_video", "Chế độ quay video"))

    def _on_shutter_press(self):
        if self.capture_mode == "video":
            self._toggle_video_recording()
        elif self.capture_mode == "4up":
            self._start_4up_burst()
        else:
            self._start_single_capture()

    def _start_single_capture(self):
        if self._countdown_timer_id:
            return
        self._countdown_val = 3
        self.viewfinder.set_countdown(3)
        self._countdown_timer_id = GLib.timeout_add(1000, self._single_countdown_tick)

    def _single_countdown_tick(self):
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self.viewfinder.set_countdown(self._countdown_val)
            return True
        else:
            self.viewfinder.set_countdown(0)
            self._countdown_timer_id = None
            self._do_single_snapshot()
            return False

    def _do_single_snapshot(self):
        self.viewfinder.trigger_flash()
        self.sound_mgr.play_screenshot()

        pixbuf = self.vcam_mgr.get_current_pixbuf()
        if pixbuf:
            ts = time.strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Photo_{ts}.png"
            out_path = os.path.join(PHOTOS_DIR, filename)
            pixbuf.savev(out_path, "png", [], [])
            print(f"[PhotoBooth] Saved photo to {out_path}")
            self.viewfinder.update_recent_photo(out_path)

    def _start_4up_burst(self):
        """Starts capturing 4 photos in sequence and stitches into a 2x2 strip."""
        if self._countdown_timer_id:
            return
        self._burst_shots = []
        self._burst_step = 1
        self._countdown_val = 3
        self.viewfinder.set_burst_progress("1/4")
        self.viewfinder.set_countdown(3)
        self._countdown_timer_id = GLib.timeout_add(1000, self._burst_countdown_tick)

    def _burst_countdown_tick(self):
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self.viewfinder.set_countdown(self._countdown_val)
            return True
        else:
            self.viewfinder.trigger_flash()
            self.sound_mgr.play_screenshot()

            pixbuf = self.vcam_mgr.get_current_pixbuf()
            if pixbuf:
                ts = time.strftime("%Y-%m-%d_%H-%M-%S")
                temp_path = os.path.join(PHOTOS_DIR, f".temp_burst_{self._burst_step}_{ts}.png")
                pixbuf.savev(temp_path, "png", [], [])
                self._burst_shots.append(temp_path)

            self._burst_step += 1
            if self._burst_step <= 4:
                self.viewfinder.set_burst_progress(f"{self._burst_step}/4")
                self._countdown_val = 2
                self.viewfinder.set_countdown(2)
                return True
            else:
                self.viewfinder.set_countdown(0)
                self.viewfinder.set_burst_progress("")
                self._countdown_timer_id = None
                self._stitch_4up_strip()
                return False

    def _stitch_4up_strip(self):
        """Stitches 4 burst shots into a classic 2x2 Photo Booth collage."""
        if len(self._burst_shots) < 4:
            return
        try:
            imgs = [Image.open(p) for p in self._burst_shots]
            w, h = imgs[0].size
            pad = 16
            strip_w = w * 2 + pad * 3
            strip_h = h * 2 + pad * 3

            canvas = Image.new("RGB", (strip_w, strip_h), (255, 255, 255))
            canvas.paste(imgs[0], (pad, pad))
            canvas.paste(imgs[1], (pad * 2 + w, pad))
            canvas.paste(imgs[2], (pad, pad * 2 + h))
            canvas.paste(imgs[3], (pad * 2 + w, pad * 2 + h))

            ts = time.strftime("%Y-%m-%d_%H-%M-%S")
            out_path = os.path.join(PHOTOS_DIR, f"Photo_Strip_{ts}.png")
            canvas.save(out_path)
            print(f"[PhotoBooth] Created 4-Up Photo Strip: {out_path}")

            for p in self._burst_shots:
                try:
                    os.remove(p)
                except Exception:
                    pass
            self._burst_shots = []
            self.viewfinder.show_toast(t("photobooth_burst_saved", "Đã tạo ảnh 4 ô liên hoàn!"))
            self.viewfinder.update_recent_photo(out_path)
        except Exception as e:
            print(f"[PhotoBooth] Error stitching 4-up strip: {e}")

    def _toggle_video_recording(self):
        if not self._is_recording:
            ts = time.strftime("%Y-%m-%d_%H-%M-%S")
            out_path = os.path.join(PHOTOS_DIR, f"Movie_{ts}.mp4")
            if not self.vcam_mgr.start_recording(out_path):
                self.viewfinder.show_toast(t("photobooth_video_error", "Không thể bắt đầu quay video!"))
                return
            self._is_recording = True
            self._recording_start_time = time.time()
            self.btn_shutter.set_recording(True)
            self.viewfinder.set_video_time("00:00")
            self._recording_timer_id = GLib.timeout_add(1000, self._video_record_tick)
            self.viewfinder.show_toast(t("photobooth_video_recording", "Đang quay video... 🎥"))
        else:
            self._is_recording = False
            self.btn_shutter.set_recording(False)
            if self._recording_timer_id:
                GLib.source_remove(self._recording_timer_id)
                self._recording_timer_id = None
            self.viewfinder.set_video_time("")
            self.sound_mgr.play_screenshot()

            # Stop recording and save thumbnail
            saved_path = self.vcam_mgr.stop_recording()
            if saved_path and os.path.exists(saved_path):
                pixbuf = self.vcam_mgr.get_current_pixbuf()
                if pixbuf:
                    thumb_path = saved_path.rsplit(".", 1)[0] + "_thumb.png"
                    try:
                        pixbuf.savev(thumb_path, "png", [], [])
                    except Exception:
                        pass
                self.viewfinder.update_recent_photo(saved_path)
                self.viewfinder.show_toast(t("photobooth_video_saved", "Đã lưu video vào Photo Booth! 🎥"))
            else:
                self.viewfinder.show_toast(t("photobooth_video_stopped", "Đã dừng quay video!"))

    def _video_record_tick(self):
        if not self._is_recording:
            return False
        elapsed = int(time.time() - self._recording_start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        self.viewfinder.set_video_time(f"{mins:02d}:{secs:02d}")
        return True

    def _on_frame_update(self, pixbuf):
        if getattr(self, "_is_iconified", False) or not self.get_visible():
            return False
        self.viewfinder.queue_draw()
        return False

    def _setup_resize_handles(self):
        """Add 8 edge and corner resize handles around the window overlay."""
        def make_handle(cursor_name, edge, width, height, halign, valign):
            eb = Gtk.EventBox()
            eb.set_visible_window(True)
            eb.set_opacity(0.0)
            eb.set_size_request(width, height)
            eb.set_halign(halign)
            eb.set_valign(valign)

            def on_realize(widget):
                win = widget.get_window()
                if win:
                    cursor = Gdk.Cursor.new_from_name(widget.get_display(), cursor_name)
                    win.set_cursor(cursor)

            def on_button_press(widget, event):
                if event.button == 1 and not getattr(self, "_is_maximized", False):
                    self.begin_resize_drag(
                        edge,
                        event.button,
                        int(event.x_root),
                        int(event.y_root),
                        event.time
                    )
                    return True
                return False

            eb.connect("realize", on_realize)
            eb.connect("button-press-event", on_button_press)
            self.master_overlay.add_overlay(eb)
            return eb

        # 4 Edges (thickness: 6px)
        make_handle("ns-resize", Gdk.WindowEdge.NORTH, -1, 6, Gtk.Align.FILL, Gtk.Align.START)
        make_handle("ns-resize", Gdk.WindowEdge.SOUTH, -1, 6, Gtk.Align.FILL, Gtk.Align.END)
        make_handle("ew-resize", Gdk.WindowEdge.WEST, 6, -1, Gtk.Align.START, Gtk.Align.FILL)
        make_handle("ew-resize", Gdk.WindowEdge.EAST, 6, -1, Gtk.Align.END, Gtk.Align.FILL)

        # 4 Corners (thickness: 14x14px)
        make_handle("nwse-resize", Gdk.WindowEdge.NORTH_WEST, 14, 14, Gtk.Align.START, Gtk.Align.START)
        make_handle("nesw-resize", Gdk.WindowEdge.NORTH_EAST, 14, 14, Gtk.Align.END, Gtk.Align.START)
        make_handle("nesw-resize", Gdk.WindowEdge.SOUTH_WEST, 14, 14, Gtk.Align.START, Gtk.Align.END)
        make_handle("nwse-resize", Gdk.WindowEdge.SOUTH_EAST, 16, 16, Gtk.Align.END, Gtk.Align.END)

    def _on_window_state_event(self, widget, event):
        is_max = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        is_icon = bool(event.new_window_state & Gdk.WindowState.ICONIFIED)
        was_icon = getattr(self, "_is_iconified", False)
        self._is_iconified = is_icon

        if is_icon:
            return False

        if was_icon and not is_icon:
            # Unminimized/restored: queue single redraw
            self.queue_draw()
        elif self._is_maximized != is_max:
            self._is_maximized = is_max
            self.queue_draw()
        return False

    def _on_header_button_press(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self._toggle_maximize()
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if not getattr(self, "_is_maximized", False):
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                return True
        return False

    def _toggle_maximize(self):
        if self._is_maximized:
            self.unmaximize()
            self._is_maximized = False
        else:
            self.maximize()
            self._is_maximized = True

    def _on_window_draw(self, widget, cr: cairo.Context):
        if getattr(self, "_is_iconified", False):
            return False

        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height
        r = 0.0 if getattr(self, "_is_maximized", False) else 12.0

        cr.save()
        if r > 0:
            cr.set_operator(cairo.Operator.CLEAR)
            cr.paint()
            cr.set_operator(cairo.Operator.OVER)
            cr.new_sub_path()
            cr.arc(w - r, r, r, -math.pi / 2, 0)
            cr.arc(w - r, h - r, r, 0, math.pi / 2)
            cr.arc(r, h - r, r, math.pi / 2, math.pi)
            cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.clip()

        # Window background fill matching macOS dark
        cr.set_source_rgb(0.17, 0.17, 0.18)
        cr.paint()

        # Subtle window outer border
        if r > 0:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.5)
            cr.set_line_width(1.0)
            cr.arc(w - r, r, r, -math.pi / 2, 0)
            cr.arc(w - r, h - r, r, 0, math.pi / 2)
            cr.arc(r, h - r, r, math.pi / 2, math.pi)
            cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.stroke()

        cr.restore()
        return False

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.continuity_sheet.get_visible():
                self._toggle_continuity_sheet(False)
                return True
            if self.viewfinder.is_effects_grid:
                self._toggle_effects_drawer(False)
                return True
        elif event.keyval == Gdk.KEY_space:
            self._on_shutter_press()
            return True
        return False

    def _on_destroy(self, widget):
        self.vcam_mgr.unregister_frame_callback(self._on_frame_update)
        MacOSPhotoBoothWindow._instance = None


def main():
    win = MacOSPhotoBoothWindow()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
