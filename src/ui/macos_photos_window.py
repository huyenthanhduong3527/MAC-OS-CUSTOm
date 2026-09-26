"""
macOS Photos (Ảnh) for Ubuntu Linux.
Authentic Apple macOS Sequoia Photos app experience:
- Supports both high-resolution Photos and Videos (.mp4, .mov, .mkv, .webm, .avi, etc.).
- Window: Frosted glass aesthetics, rounded squircle corners, macOS traffic lights.
- Sidebar: Thư viện (Tất cả ảnh & video, Video, Gần đây, Yêu thích, Ảnh chụp màn hình, Tải về),
  Thư mục trên máy (với nút + thêm thư mục), Phân loại định dạng, Thùng rác.
- Gallery: Lưới FlowBox cuộn mượt, nạp lười (lazy loading), zoom slider chỉnh kích thước thumbnail,
  nhóm theo thời gian, thẻ ảnh/video bo góc tinh tế, huy hiệu thời lượng video, hover thả tim ❤️.
- Lightbox Viewer: Trình xem ảnh toàn màn hình với thu phóng con lăn chuột mượt mà, kéo rê ảnh,
  tích hợp trình phát video GStreamer (Play/Pause, Scrubber timeline seeking, Volume, Loop),
  thanh công cụ nổi dạng viên thuốc (Glass Floating Pill), tự động trình chiếu (Slideshow).
- Inspector Panel: Bảng thông số chi tiết EXIF máy ảnh, thông số video (codec, audio, thời lượng),
  kích thước, dung lượng, đường dẫn.
- Tích hợp hệ thống: Đặt ảnh làm hình nền Desktop GNOME, xóa vào Thùng rác, hiện trong Nautilus.
"""

import os
import sys
import time
import math
import subprocess
from datetime import datetime
from typing import List, Optional, Tuple

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, GdkPixbuf, Gst
import cairo

Gst.init(None)

from src.utils.theme import is_system_dark_mode
from src.utils.icons import get_pixbuf, get_image
from src.utils.i18n import t, add_language_listener
from src.modules.photos_scanner import PhotoLibraryManager, PhotoItem, format_file_size
from src.ui.photo_editor import PhotoEditorEngine, PhotoEditorHeader, PhotoEditorInspector

_photos_window_instance = None


class TrafficLightsWidget(Gtk.Box):
    """Authentic Apple macOS Traffic Lights: 🔴 Red, 🟡 Yellow, 🟢 Green."""
    def __init__(self, on_close, on_minimize, on_maximize):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_start(16)
        self.set_valign(Gtk.Align.CENTER)

        def make_light(color_class, tooltip, symbol, cb):
            btn = Gtk.Button()
            btn.set_size_request(12, 12)
            btn.set_valign(Gtk.Align.CENTER)
            btn.set_halign(Gtk.Align.CENTER)
            btn.get_style_context().add_class("mac-traffic-light")
            btn.get_style_context().add_class(color_class)
            btn.set_tooltip_text(tooltip)
            lbl = Gtk.Label(label="")
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.get_style_context().add_class("tl-symbol")
            btn.add(lbl)

            btn.connect("enter-notify-event", lambda b, e: [lbl.set_text(symbol), False][1])
            btn.connect("leave-notify-event", lambda b, e: [lbl.set_text(""), False][1])
            btn.connect("clicked", lambda _: cb())
            return btn

        self.pack_start(make_light("tl-red", "Đóng (Close)", "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", "Thu nhỏ (Minimize)", "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", "Phóng to (Zoom)", "⤢", on_maximize), False, False, 0)


class RoundedThumbnailDrawingArea(Gtk.DrawingArea):
    """
    Cairo-powered thumbnail renderer that guarantees pixel-perfect anti-aliased
    rounded squircle corners, aspect-ratio crop/fill, subtle glass rim highlight,
    and selection state indicators.
    """
    def __init__(self, radius=12):
        super().__init__()
        self.radius = radius
        self.pixbuf: Optional[GdkPixbuf.Pixbuf] = None
        self.is_selected = False
        self.connect("draw", self.on_draw)

    def set_pixbuf(self, pb: GdkPixbuf.Pixbuf):
        self.pixbuf = pb
        self.queue_draw()

    def set_selected(self, selected: bool):
        if self.is_selected != selected:
            self.is_selected = selected
            self.queue_draw()

    def on_draw(self, widget, cr: cairo.Context):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = min(self.radius, w / 2.0, h / 2.0)

        # 1. Rounded rectangle clip path
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        # Save state for drawing inside clip
        cr.save()
        cr.clip()

        # 2. Draw placeholder or pixbuf
        if self.pixbuf:
            pb_w = self.pixbuf.get_width()
            pb_h = self.pixbuf.get_height()

            # Center-crop / aspect fill
            scale = max(w / float(pb_w), h / float(pb_h))
            draw_w = pb_w * scale
            draw_h = pb_h * scale
            draw_x = (w - draw_w) / 2.0
            draw_y = (h - draw_h) / 2.0

            cr.translate(draw_x, draw_y)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
            cr.paint()
        else:
            # Subtle dark placeholder
            cr.set_source_rgba(0.16, 0.16, 0.18, 1.0)
            cr.paint()

        cr.restore()

        # 3. Border & Selection Styling
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        if self.is_selected:
            # Vibrant Apple blue selection border
            cr.set_source_rgba(0.0, 0.48, 1.0, 1.0) # #007aff
            cr.set_line_width(3.0)
            cr.stroke()
        else:
            # Subtle glass rim border
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
            cr.set_line_width(1.0)
            cr.stroke()

        return False


class SelectionBadge(Gtk.DrawingArea):
    """Circular selection checkmark indicator for Photos multi-select mode."""
    def __init__(self):
        super().__init__()
        self.set_size_request(24, 24)
        self.is_selected = False
        self.connect("draw", self.on_draw)

    def set_selected(self, selected: bool):
        if self.is_selected != selected:
            self.is_selected = selected
            self.queue_draw()

    def on_draw(self, widget, cr: cairo.Context):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0
        r = min(cx, cy) - 2.5

        if self.is_selected:
            # Filled Apple Blue circle with white checkmark
            cr.set_source_rgba(0.0, 0.48, 1.0, 1.0) # #007aff
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.fill()

            # White outer ring
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.set_line_width(1.8)
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()

            # Checkmark ✓
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.set_line_width(2.2)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.move_to(cx - 4.5, cy + 0.2)
            cr.line_to(cx - 1.0, cy + 3.8)
            cr.line_to(cx + 4.8, cy - 3.5)
            cr.stroke()
        else:
            # Translucent glass circle with white border
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.45)
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.fill()

            cr.set_source_rgba(1.0, 1.0, 1.0, 0.85)
            cr.set_line_width(1.8)
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()

        return False


class PhotoCardWidget(Gtk.Button):
    """Individual Photo or Video Card in the macOS Photos gallery grid with rounded corners & multi-select."""
    def __init__(self, photo_item: PhotoItem, target_size: int, on_open_lightbox, on_toggle_fav, on_context_menu, on_toggle_select=None, is_select_mode=False, is_selected=False, on_picker_select=None, on_picker_confirm=None, is_picker_mode=False):
        super().__init__()
        self.photo_item = photo_item
        self.target_size = target_size
        self.on_open_lightbox = on_open_lightbox
        self.on_toggle_fav = on_toggle_fav
        self.on_context_menu = on_context_menu
        self.on_toggle_select = on_toggle_select
        self.is_select_mode = is_select_mode
        self.is_selected = is_selected
        self.on_picker_select = on_picker_select
        self.on_picker_confirm = on_picker_confirm
        self.is_picker_mode = is_picker_mode

        self.get_style_context().add_class("mac-photo-card")
        if self.is_selected:
            self.get_style_context().add_class("is-selected")
        self.set_size_request(target_size, target_size)
        self.set_relief(Gtk.ReliefStyle.NONE)

        # Overlay allows badge & favorite heart on top of thumbnail
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        # Thumbnail Image Container with Anti-Aliased Cairo Rounded Corners
        self.img_box = Gtk.Box()
        self.img_box.set_size_request(target_size, target_size)
        self.img_box.get_style_context().add_class("photo-thumb-container")

        self.thumb_draw = RoundedThumbnailDrawingArea(radius=12)
        self.thumb_draw.set_size_request(target_size, target_size)
        self.thumb_draw.set_selected(self.is_selected)
        self.img_box.pack_start(self.thumb_draw, True, True, 0)
        self.overlay.add(self.img_box)

        # Top Bar Overlays: Selection Badge (Left), Format Badge (Center), Favorite Heart (Right)
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top_bar.set_valign(Gtk.Align.START)
        top_bar.set_margin_top(6)
        top_bar.set_margin_end(6)
        top_bar.set_margin_start(6)

        # Selection Checkmark Badge (Left)
        self.select_badge = SelectionBadge()
        self.select_badge.set_no_show_all(True)
        self.select_badge.set_selected(self.is_selected)
        top_bar.pack_start(self.select_badge, False, False, 0)
        if not self.is_select_mode:
            self.select_badge.hide()
        else:
            self.select_badge.show()

        # Badge (Format or Video)
        if photo_item.is_video or photo_item.ext in (".gif", ".webp", ".svg"):
            badge = Gtk.Label(label=photo_item.format_name)
            badge.get_style_context().add_class("photo-format-badge")
            top_bar.pack_start(badge, False, False, 0)

        # Favorite Heart Button (Right)
        self.fav_btn = Gtk.Button()
        self.fav_btn.set_no_show_all(True)
        self.fav_btn.get_style_context().add_class("photo-card-heart-btn")
        self.fav_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.fav_btn.set_halign(Gtk.Align.END)
        self.fav_icon = Gtk.Image()
        self._update_fav_icon()
        self.fav_btn.add(self.fav_icon)
        self.fav_btn.connect("clicked", self._on_fav_clicked)
        self.fav_btn.connect("button-press-event", lambda _w, _e: True)
        top_bar.pack_end(self.fav_btn, False, False, 0)
        if self.is_select_mode:
            self.fav_btn.hide()
        else:
            self.fav_btn.show()

        self.overlay.add_overlay(top_bar)

        # Video Specific Overlays: Sleek Duration Pill with Play Icon in Bottom Right
        if photo_item.is_video:
            dur_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            dur_box.set_valign(Gtk.Align.END)
            dur_box.set_halign(Gtk.Align.END)
            dur_box.set_margin_bottom(6)
            dur_box.set_margin_end(6)
            dur_box.get_style_context().add_class("photo-video-duration-badge")

            play_icon = get_image("play", 11, "#ffffff")
            dur_box.pack_start(play_icon, False, False, 0)

            self.duration_lbl = Gtk.Label(label=photo_item.duration_str or "00:00")
            dur_box.pack_start(self.duration_lbl, False, False, 0)
            self.overlay.add_overlay(dur_box)

        # Connect signals
        self.connect("clicked", self._on_clicked)
        self.connect("button-press-event", self._on_button_press)
        tip_text = f"{photo_item.filename}\n{photo_item.formatted_size} • {photo_item.date_str}"
        if photo_item.is_video and photo_item.duration_str:
            tip_text += f"\nThời lượng: {photo_item.duration_str}"
        self.set_tooltip_text(tip_text)

        # Asynchronously load thumbnail
        PhotoLibraryManager.get_instance().request_thumbnail(
            photo_item, target_size * 2, self._on_thumb_ready
        )

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.thumb_draw.set_selected(selected)
        self.select_badge.set_selected(selected)
        if selected:
            self.get_style_context().add_class("is-selected")
        else:
            self.get_style_context().remove_class("is-selected")

    def set_select_mode(self, mode: bool):
        self.is_select_mode = mode
        if mode:
            self.select_badge.show()
            self.fav_btn.hide()
        else:
            self.select_badge.hide()
            self.fav_btn.show()
            self.set_selected(False)

    def set_picker_mode(self, mode: bool):
        self.is_picker_mode = mode

    def _update_fav_icon(self):
        if self.photo_item.is_favorite:
            pb = get_pixbuf("heart_filled", 14, "#ff3b30")
            self.fav_btn.get_style_context().add_class("is-favorited")
        else:
            pb = get_pixbuf("heart", 14, "#ffffff")
            self.fav_btn.get_style_context().remove_class("is-favorited")
        if pb:
            self.fav_icon.set_from_pixbuf(pb)

    def _on_fav_clicked(self, btn):
        if self.on_toggle_fav:
            self.on_toggle_fav(self.photo_item)
            self._update_fav_icon()

    def update_favorite_state(self):
        self._update_fav_icon()

    def _on_thumb_ready(self, item: PhotoItem, thumb_path: str):
        if item.path != self.photo_item.path:
            return
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                thumb_path, self.target_size, self.target_size, True
            )
            self.thumb_draw.set_pixbuf(pb)
        except Exception:
            pass

        if self.photo_item.is_video and hasattr(self, 'duration_lbl'):
            if self.photo_item.duration_str:
                self.duration_lbl.set_text(self.photo_item.duration_str)

    def _on_clicked(self, btn):
        if self.is_select_mode:
            if self.on_toggle_select:
                self.on_toggle_select(self.photo_item)
        elif self.is_picker_mode:
            if self.on_picker_select:
                self.on_picker_select(self.photo_item)
        else:
            if self.on_open_lightbox:
                self.on_open_lightbox(self.photo_item)

    def _on_button_press(self, widget, event):
        if event.button == 1:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                if self.is_picker_mode:
                    if self.on_picker_confirm:
                        self.on_picker_confirm(self.photo_item)
                        return True
                elif not self.is_select_mode and self.on_open_lightbox:
                    self.on_open_lightbox(self.photo_item)
                return True
            return False
        elif event.button == 3:  # Right Click
            if self.on_context_menu:
                self.on_context_menu(self.photo_item, event)
            return True
        return False


class LightboxViewer(Gtk.Overlay):
    """
    macOS Photos cinematic Lightbox full-resolution image and video viewer
    with hardware-accelerated video playback, zoom, pan, floating glass toolbar and slideshow.
    """
    def __init__(self, on_close, on_toggle_fav, on_set_wallpaper, on_trash, on_rotate, on_reveal, on_select_picker=None, on_airdrop=None, on_photo_edited=None):
        super().__init__()
        self.set_no_show_all(True)
        self.on_close = on_close
        self.on_toggle_fav = on_toggle_fav
        self.on_set_wallpaper = on_set_wallpaper
        self.on_trash = on_trash
        self.on_rotate = on_rotate
        self.on_reveal = on_reveal
        self.on_select_picker = on_select_picker
        self.on_airdrop = on_airdrop
        self.on_photo_edited = on_photo_edited

        self.current_photo: Optional[PhotoItem] = None
        self.photos_list: List[PhotoItem] = []
        self.current_index = 0

        # Photo Editing State (macOS Sequoia Photos Suite)
        self.is_editing: bool = False
        self.editor_engine: Optional[PhotoEditorEngine] = None
        self.editor_active_tab: str = "adjust"
        self._crop_dragging: Optional[str] = None
        self._crop_drag_start = (0, 0)
        self._crop_initial_box = (0.0, 0.0, 1.0, 1.0)
        self._markup_drawing: bool = False
        self._markup_start_pt: Optional[Tuple[float, float]] = None
        self._markup_current_stroke: Optional[dict] = None

        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False

        self._slideshow_active = False
        self._slideshow_timer_id = None

        # Video Player Engine state (GStreamer playbin + appsink)
        self._gst_pipeline = None
        self._video_sink = None
        self._video_is_playing = False
        self._video_loop = False
        self._video_muted = False
        self._video_pos_timer = None
        self._is_seeking = False
        self._opened_timestamp = 0.0

        self.get_style_context().add_class("mac-lightbox-overlay")

        # Dark Glass Background EventBox
        self.bg_box = Gtk.EventBox()
        self.bg_box.get_style_context().add_class("lightbox-backdrop")
        self.add(self.bg_box)

        # Drawing area for smooth Cairo hardware-accelerated image scaling and panning
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.connect("draw", self._on_draw)
        self.draw_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK
        )
        self.draw_area.connect("button-press-event", self._on_draw_button_press)
        self.draw_area.connect("button-release-event", self._on_draw_button_release)
        self.draw_area.connect("motion-notify-event", self._on_draw_motion)
        self.draw_area.connect("scroll-event", self._on_draw_scroll)
        self.bg_box.add(self.draw_area)

        self._pixbuf_cache = None
        self._pixbuf_cache_path = None

        # Floating Navigation Chevrons (Left & Right)
        self.btn_prev = self._create_nav_chevron("left", self.prev_photo)
        self.btn_prev.set_halign(Gtk.Align.START)
        self.btn_prev.set_valign(Gtk.Align.CENTER)
        self.btn_prev.set_margin_start(16)
        self.add_overlay(self.btn_prev)

        self.btn_next = self._create_nav_chevron("right", self.next_photo)
        self.btn_next.set_halign(Gtk.Align.END)
        self.btn_next.set_valign(Gtk.Align.CENTER)
        self.btn_next.set_margin_end(16)
        self.add_overlay(self.btn_next)

        # Top Header Bar: Close Button, Filename, Index Counter
        self.top_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.top_header.set_valign(Gtk.Align.START)
        self.top_header.set_margin_top(16)
        self.top_header.set_margin_start(20)
        self.top_header.set_margin_end(20)
        self.top_header.get_style_context().add_class("lightbox-top-bar")

        close_btn = Gtk.Button()
        close_btn.get_style_context().add_class("lightbox-close-btn")
        close_icon = get_image("chevron_left", 16, "#ffffff")
        close_box = Gtk.Box(spacing=6)
        close_box.pack_start(close_icon, False, False, 0)
        close_lbl = Gtk.Label(label="Thư viện")
        close_lbl.get_style_context().add_class("lightbox-back-lbl")
        close_box.pack_start(close_lbl, False, False, 0)
        close_btn.add(close_box)
        close_btn.connect("clicked", lambda _: self.close_lightbox())
        self.top_header.pack_start(close_btn, False, False, 0)

        self.title_lbl = Gtk.Label(label="")
        self.title_lbl.get_style_context().add_class("lightbox-title-lbl")
        self.top_header.pack_start(self.title_lbl, True, True, 0)

        self.counter_lbl = Gtk.Label(label="0 / 0")
        self.counter_lbl.get_style_context().add_class("lightbox-counter-lbl")
        self.top_header.pack_end(self.counter_lbl, False, False, 0)

        # macOS Photos "Sửa" (Edit) Top Action Button
        self.btn_edit_top = Gtk.Button()
        self.btn_edit_top.get_style_context().add_class("lightbox-edit-btn")
        edit_box = Gtk.Box(spacing=6)
        edit_box.pack_start(get_image("sliders", 14, "#ffffff"), False, False, 0)
        edit_lbl = Gtk.Label(label="Sửa")
        edit_box.pack_start(edit_lbl, False, False, 0)
        self.btn_edit_top.add(edit_box)
        self.btn_edit_top.set_tooltip_text("Chỉnh sửa ảnh chuyên nghiệp như macOS (Phím E)")
        self.btn_edit_top.connect("clicked", lambda _: self.enter_edit_mode())
        self.top_header.pack_end(self.btn_edit_top, False, False, 6)

        self.add_overlay(self.top_header)

        # Bottom Floating Glass Pill Action Bar
        self.bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.bottom_bar.set_halign(Gtk.Align.CENTER)
        self.bottom_bar.set_valign(Gtk.Align.END)
        self.bottom_bar.set_margin_bottom(24)
        self.bottom_bar.get_style_context().add_class("mac-glass-pill-bar")

        # --- Sub-bar 1: Photo Controls ---
        self.photo_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.photo_actions_box.set_no_show_all(True)
        self.bottom_bar.pack_start(self.photo_actions_box, False, False, 0)

        def add_photo_action(icon_name, tooltip, callback):
            b = Gtk.Button()
            b.get_style_context().add_class("pill-action-btn")
            b.set_tooltip_text(tooltip)
            img = get_image(icon_name, 17, "#ffffff")
            b.add(img)
            b.connect("clicked", lambda _: callback())
            self.photo_actions_box.pack_start(b, False, False, 0)
            return b

        self.fav_pill_btn = add_photo_action("heart", "Yêu thích", self._on_toggle_fav_clicked)
        self.fav_pill_icon = self.fav_pill_btn.get_child()

        self.btn_edit_pill = add_photo_action("sliders", "Chỉnh sửa ảnh (Phím E)", self.enter_edit_mode)
        add_photo_action("rotate", "Xoay ảnh 90°", self._on_rotate_clicked)
        add_photo_action("wallpaper", "Đặt làm hình nền Desktop", self._on_wallpaper_clicked)
        if self.on_airdrop:
            add_photo_action("share", "Chia sẻ qua AirDrop", lambda: self.on_airdrop(self.current_photo) if self.current_photo else None)
        add_photo_action("slideshow", "Trình chiếu ảnh (Slideshow)", self.toggle_slideshow)
        add_photo_action("folder", "Hiện trong Trình quản lý tệp", self._on_reveal_clicked)
        add_photo_action("trash", "Chuyển vào Thùng rác", self._on_trash_clicked)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(4)
        sep.set_margin_end(4)
        self.photo_actions_box.pack_start(sep, False, False, 0)

        self.zoom_lbl = Gtk.Label(label="100%")
        self.zoom_lbl.get_style_context().add_class("pill-zoom-lbl")

        add_photo_action("zoom_out", "Thu nhỏ", self._zoom_out)
        self.photo_actions_box.pack_start(self.zoom_lbl, False, False, 4)
        add_photo_action("zoom_in", "Phóng to", self._zoom_in)

        fit_btn = Gtk.Button(label="Vừa khung")
        fit_btn.get_style_context().add_class("pill-fit-btn")
        fit_btn.connect("clicked", lambda _: self.reset_zoom())
        self.photo_actions_box.pack_start(fit_btn, False, False, 0)

        if self.on_select_picker:
            self.btn_picker_use = Gtk.Button(label="✓ Sử dụng ảnh này")
            self.btn_picker_use.get_style_context().add_class("pill-fit-btn")
            self.btn_picker_use.get_style_context().add_class("pill-picker-confirm-btn")
            self.btn_picker_use.connect("clicked", lambda _: self.on_select_picker(self.current_photo) if (self.on_select_picker and self.current_photo) else None)
            self.btn_picker_use.set_no_show_all(True)
            self.btn_picker_use.hide()
            self.photo_actions_box.pack_start(self.btn_picker_use, False, False, 0)

        # --- Sub-bar 2: Video Playback Controls ---
        self.video_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.video_actions_box.set_no_show_all(True)
        self.bottom_bar.pack_start(self.video_actions_box, False, False, 0)

        # Play / Pause button
        self.btn_video_play = Gtk.Button()
        self.btn_video_play.get_style_context().add_class("pill-action-btn")
        self.btn_video_play.set_tooltip_text("Phát / Tạm dừng (Phím Space)")
        self.btn_video_play_icon = get_image("play", 17, "#ffffff")
        self.btn_video_play.add(self.btn_video_play_icon)
        self.btn_video_play.connect("clicked", lambda _: self.toggle_video_play_pause())
        self.video_actions_box.pack_start(self.btn_video_play, False, False, 0)

        # Time label
        self.video_time_lbl = Gtk.Label(label="00:00 / 00:00")
        self.video_time_lbl.get_style_context().add_class("pill-time-lbl")
        self.video_actions_box.pack_start(self.video_time_lbl, False, False, 4)

        # Scrubber seek slider
        self.video_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.video_slider.get_style_context().add_class("video-scrubber-slider")
        self.video_slider.set_size_request(220, 20)
        self.video_slider.set_draw_value(False)
        self.video_slider.connect("value-changed", self._on_video_seek)
        self.video_actions_box.pack_start(self.video_slider, False, False, 0)

        # Loop button
        self.btn_video_loop = Gtk.Button()
        self.btn_video_loop.get_style_context().add_class("pill-action-btn")
        self.btn_video_loop.set_tooltip_text("Lặp lại video")
        self.btn_video_loop.add(get_image("loop", 16, "#8e8e93"))
        self.btn_video_loop.connect("clicked", lambda _: self._toggle_video_loop())
        self.video_actions_box.pack_start(self.btn_video_loop, False, False, 0)

        # Mute / Volume button
        self.btn_video_mute = Gtk.Button()
        self.btn_video_mute.get_style_context().add_class("pill-action-btn")
        self.btn_video_mute.set_tooltip_text("Bật / Tắt âm thanh")
        self.btn_video_mute_icon = get_image("volume_high", 16, "#ffffff")
        self.btn_video_mute.add(self.btn_video_mute_icon)
        self.btn_video_mute.connect("clicked", lambda _: self._toggle_video_mute())
        self.video_actions_box.pack_start(self.btn_video_mute, False, False, 0)

        # Common actions for video too: Fav, Reveal, Trash
        b_fav_v = Gtk.Button()
        b_fav_v.get_style_context().add_class("pill-action-btn")
        b_fav_v.set_tooltip_text("Yêu thích")
        b_fav_v.add(get_image("heart", 16, "#ffffff"))
        b_fav_v.connect("clicked", lambda _: self._on_toggle_fav_clicked())
        self.video_actions_box.pack_start(b_fav_v, False, False, 0)

        b_rev_v = Gtk.Button()
        b_rev_v.get_style_context().add_class("pill-action-btn")
        b_rev_v.set_tooltip_text("Hiện trong Thư mục")
        b_rev_v.add(get_image("folder", 16, "#ffffff"))
        b_rev_v.connect("clicked", lambda _: self._on_reveal_clicked())
        self.video_actions_box.pack_start(b_rev_v, False, False, 0)

        b_del_v = Gtk.Button()
        b_del_v.get_style_context().add_class("pill-action-btn")
        b_del_v.set_tooltip_text("Chuyển vào Thùng rác")
        b_del_v.add(get_image("trash", 16, "#ffffff"))
        b_del_v.connect("clicked", lambda _: self._on_trash_clicked())
        self.video_actions_box.pack_start(b_del_v, False, False, 0)

        self.photo_actions_box.hide()
        self.video_actions_box.hide()
        self.add_overlay(self.bottom_bar)

        # Editor Overlays (Apple Photos Top Header & Right Inspector Panel)
        self.editor_header = PhotoEditorHeader(
            on_cancel=lambda: self.exit_edit_mode(save=False),
            on_tab_switch=self._on_editor_tab_switched,
            on_auto_enhance=self._on_auto_enhance,
            on_revert=self._on_revert_original,
            on_done=self._on_save_done,
        )
        self.editor_header.set_no_show_all(True)
        self.editor_header.hide()
        self.add_overlay(self.editor_header)

        self.editor_inspector_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.editor_inspector_box.set_halign(Gtk.Align.END)
        self.editor_inspector_box.set_valign(Gtk.Align.FILL)
        self.editor_inspector_box.set_no_show_all(True)
        self.editor_inspector_box.hide()
        self.add_overlay(self.editor_inspector_box)
        self.editor_inspector: Optional[PhotoEditorInspector] = None

    def _create_nav_chevron(self, direction: str, callback):
        b = Gtk.Button()
        b.get_style_context().add_class("lightbox-nav-chevron")
        icon_name = "chevron_left" if direction == "left" else "chevron_right"
        b.add(get_image(icon_name, 22, "#ffffff"))
        b.connect("clicked", lambda _: callback())
        return b

    def set_picker_mode(self, enabled: bool):
        if hasattr(self, "btn_picker_use"):
            if enabled:
                self.btn_picker_use.show()
            else:
                self.btn_picker_use.hide()

    def open_photo(self, photo_item: PhotoItem, photos_list: List[PhotoItem]):
        if self.is_editing:
            self.exit_edit_mode(save=False)

        if self.get_visible() and self.current_photo and self.current_photo.path == photo_item.path:
            return

        self._opened_timestamp = time.time()
        self.photos_list = photos_list
        self.current_photo = photo_item
        try:
            self.current_index = [p.path for p in photos_list].index(photo_item.path)
        except ValueError:
            self.current_index = 0

        self.reset_zoom()
        self._update_header_and_actions()

        # Show Lightbox overlay container and all interior widgets
        self.set_no_show_all(False)
        self.show_all()
        self.set_no_show_all(True)

        if photo_item.is_video:
            # Hide photo editor top button for videos
            if hasattr(self, "btn_edit_top"):
                self.btn_edit_top.hide()
            # Show ONLY video controls, strictly hide photo controls
            self.photo_actions_box.hide()
            self.video_actions_box.set_no_show_all(False)
            self.video_actions_box.show_all()
            self.video_actions_box.set_no_show_all(True)
            self._start_video_playback(photo_item.path)
        else:
            # Show photo editor top button for photos
            if hasattr(self, "btn_edit_top"):
                self.btn_edit_top.show()
            # Show ONLY photo controls, strictly hide video controls
            self._stop_video_playback()
            self.video_actions_box.hide()
            self.photo_actions_box.set_no_show_all(False)
            self.photo_actions_box.show_all()
            self.photo_actions_box.set_no_show_all(True)
            self._load_current_pixbuf()

    def _load_current_pixbuf(self):
        if not self.current_photo:
            return
        if self._pixbuf_cache_path == self.current_photo.path and self._pixbuf_cache:
            self.draw_area.queue_draw()
            return

        try:
            self._pixbuf_cache = GdkPixbuf.Pixbuf.new_from_file(self.current_photo.path)
            self._pixbuf_cache_path = self.current_photo.path
            self.current_photo.width = self._pixbuf_cache.get_width()
            self.current_photo.height = self._pixbuf_cache.get_height()
        except Exception as e:
            print(f"[Lightbox] Error loading image with GdkPixbuf: {e}")
            if HAS_PIL:
                try:
                    im = Image.open(self.current_photo.path)
                    im.thumbnail((3840, 2160), Image.Resampling.LANCZOS)
                    if im.mode != "RGBA":
                        im = im.convert("RGBA")
                    data = GLib.Bytes.new(im.tobytes())
                    self._pixbuf_cache = GdkPixbuf.Pixbuf.new_from_bytes(
                        data, GdkPixbuf.Colorspace.RGB, True, 8, im.width, im.height, im.width * 4
                    )
                    self._pixbuf_cache_path = self.current_photo.path
                    self.current_photo.width = im.width
                    self.current_photo.height = im.height
                except Exception as ex2:
                    print(f"[Lightbox] PIL fallback failed: {ex2}")
                    self._pixbuf_cache = None
            else:
                self._pixbuf_cache = None

        self.draw_area.queue_draw()

    def _update_header_and_actions(self):
        if not self.current_photo:
            return
        self.title_lbl.set_text(self.current_photo.filename)
        total = len(self.photos_list)
        idx_str = f"{self.current_index + 1} / {total}"
        self.counter_lbl.set_text(idx_str)

        # Update favorite button
        if self.current_photo.is_favorite:
            pb = get_pixbuf("heart_filled", 17, "#ff3b30")
        else:
            pb = get_pixbuf("heart", 17, "#ffffff")
        if pb:
            self.fav_pill_icon.set_from_pixbuf(pb)

        self.zoom_lbl.set_text(f"{int(self.zoom_factor * 100)}%")

    # -------------------------------------------------------------------------
    # VIDEO PLAYBACK ENGINE (GStreamer)
    # -------------------------------------------------------------------------
    def _start_video_playback(self, path: str):
        self._stop_video_playback()
        try:
            self._gst_pipeline = Gst.ElementFactory.make('playbin', 'video_player')
            uri = f"file://{os.path.abspath(path)}"
            self._gst_pipeline.set_property('uri', uri)

            vbin = Gst.parse_bin_from_description(
                'videoconvert ! video/x-raw,format=RGB ! appsink name=sink emit-signals=true max-buffers=2 drop=true',
                True
            )
            self._gst_pipeline.set_property('video-sink', vbin)
            self._video_sink = vbin.get_by_name('sink')
            self._video_sink.connect('new-sample', self._on_video_sample)

            bus = self._gst_pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect('message::eos', self._on_video_eos)
            bus.connect('message::error', self._on_video_error)

            if self._video_muted:
                self._gst_pipeline.set_property('volume', 0.0)

            self._gst_pipeline.set_state(Gst.State.PLAYING)
            self._video_is_playing = True
            self._update_video_play_btn()

            # Set slider range
            dur_sec = self.current_photo.duration_sec if self.current_photo.duration_sec > 0 else 100
            self.video_slider.set_range(0, dur_sec)

            self._video_pos_timer = GLib.timeout_add(250, self._update_video_progress)
        except Exception as e:
            print(f"[Lightbox] Video playback init error: {e}")

    def _stop_video_playback(self):
        if self._video_pos_timer:
            GLib.source_remove(self._video_pos_timer)
            self._video_pos_timer = None
        if self._gst_pipeline:
            try:
                self._gst_pipeline.set_state(Gst.State.NULL)
            except Exception:
                pass
            self._gst_pipeline = None
            self._video_sink = None
        self._video_is_playing = False

    def toggle_video_play_pause(self):
        if not self._gst_pipeline:
            if self.current_photo and self.current_photo.is_video:
                self._start_video_playback(self.current_photo.path)
            return

        if self._video_is_playing:
            self._gst_pipeline.set_state(Gst.State.PAUSED)
            self._video_is_playing = False
        else:
            self._gst_pipeline.set_state(Gst.State.PLAYING)
            self._video_is_playing = True
        self._update_video_play_btn()

    def _update_video_play_btn(self):
        icon_name = "pause" if self._video_is_playing else "play"
        pb = get_pixbuf(icon_name, 17, "#ffffff")
        if pb:
            self.btn_video_play_icon.set_from_pixbuf(pb)

    def _update_video_progress(self):
        if not self._gst_pipeline or not self._video_is_playing:
            return True
        try:
            ok, pos = self._gst_pipeline.query_position(Gst.Format.TIME)
            ok_dur, dur = self._gst_pipeline.query_duration(Gst.Format.TIME)
            if ok and ok_dur and dur > 0:
                pos_sec = pos / Gst.SECOND
                dur_sec = dur / Gst.SECOND
                self._is_seeking = True
                self.video_slider.set_range(0, dur_sec)
                self.video_slider.set_value(pos_sec)
                self._is_seeking = False

                cur_str = f"{int(pos_sec//60):02d}:{int(pos_sec%60):02d}"
                tot_str = f"{int(dur_sec//60):02d}:{int(dur_sec%60):02d}"
                self.video_time_lbl.set_text(f"{cur_str} / {tot_str}")
        except Exception:
            pass
        return True

    def _on_video_sample(self, appsink):
        sample = appsink.emit('pull-sample')
        if not sample:
            return Gst.FlowReturn.OK
        buf = sample.get_buffer()
        caps = sample.get_caps()
        s = caps.get_structure(0)
        w = s.get_value('width')
        h = s.get_value('height')
        success, map_info = buf.map(Gst.MapFlags.READ)
        if success:
            try:
                b = GLib.Bytes.new(map_info.data)
                pb = GdkPixbuf.Pixbuf.new_from_bytes(b, GdkPixbuf.Colorspace.RGB, False, 8, w, h, w * 3)
                self._pixbuf_cache = pb
                GLib.idle_add(self.draw_area.queue_draw)
            finally:
                buf.unmap(map_info)
        return Gst.FlowReturn.OK

    def _on_video_seek(self, scale):
        if not self._gst_pipeline or self._is_seeking:
            return
        target_sec = scale.get_value()
        self._gst_pipeline.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(target_sec * Gst.SECOND)
        )

    def _toggle_video_mute(self):
        self._video_muted = not self._video_muted
        if self._gst_pipeline:
            self._gst_pipeline.set_property('volume', 0.0 if self._video_muted else 1.0)
        icon_name = "volume_mute" if self._video_muted else "volume_high"
        pb = get_pixbuf(icon_name, 16, "#ffffff")
        if pb:
            self.btn_video_mute_icon.set_from_pixbuf(pb)

    def _toggle_video_loop(self):
        self._video_loop = not self._video_loop
        color = "#007aff" if self._video_loop else "#86868b"
        pb = get_pixbuf("loop", 16, color)
        if pb:
            self.btn_video_loop.get_child().set_from_pixbuf(pb)

    def _on_video_eos(self, bus, msg):
        if self._video_loop and self._gst_pipeline:
            self._gst_pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        else:
            if self._gst_pipeline:
                self._gst_pipeline.set_state(Gst.State.PAUSED)
                self._gst_pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
            self._video_is_playing = False
            self.video_slider.set_value(0)
            self._update_video_play_btn()

    def _on_video_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"[Lightbox] Video playback error: {err}, {debug}")
        self._stop_video_playback()

    def prev_photo(self):
        if not self.photos_list:
            return
        self._stop_video_playback()
        self.current_index = (self.current_index - 1) % len(self.photos_list)
        self.open_photo(self.photos_list[self.current_index], self.photos_list)

    def next_photo(self):
        if not self.photos_list:
            return
        self._stop_video_playback()
        self.current_index = (self.current_index + 1) % len(self.photos_list)
        self.open_photo(self.photos_list[self.current_index], self.photos_list)

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.zoom_lbl.set_text("100%")
        self.draw_area.queue_draw()

    def _zoom_in(self):
        self.zoom_factor = min(5.0, self.zoom_factor * 1.25)
        self.zoom_lbl.set_text(f"{int(self.zoom_factor * 100)}%")
        self.draw_area.queue_draw()

    def _zoom_out(self):
        self.zoom_factor = max(0.2, self.zoom_factor / 1.25)
        self.zoom_lbl.set_text(f"{int(self.zoom_factor * 100)}%")
        self.draw_area.queue_draw()

    def toggle_slideshow(self):
        self._slideshow_active = not self._slideshow_active
        if self._slideshow_active:
            self._slideshow_timer_id = GLib.timeout_add(3200, self._on_slideshow_tick)
        else:
            if self._slideshow_timer_id:
                GLib.source_remove(self._slideshow_timer_id)
                self._slideshow_timer_id = None

    def _on_slideshow_tick(self):
        if not self._slideshow_active or not self.get_visible():
            self._slideshow_active = False
            return False
        self.next_photo()
        return True

    def close_lightbox(self):
        if self.is_editing:
            self.exit_edit_mode(save=False)
        self._stop_video_playback()
        if self._slideshow_active:
            self.toggle_slideshow()
        self.photo_actions_box.hide()
        self.video_actions_box.hide()
        self.hide()
        if self.on_close:
            self.on_close()

    def _on_toggle_fav_clicked(self):
        if self.current_photo and self.on_toggle_fav:
            self.on_toggle_fav(self.current_photo)
            self._update_header_and_actions()

    def _on_wallpaper_clicked(self):
        if self.current_photo and self.on_set_wallpaper:
            self.on_set_wallpaper(self.current_photo)

    def _on_rotate_clicked(self):
        if self.current_photo and self.on_rotate:
            self.on_rotate(self.current_photo)
            self._pixbuf_cache = None
            self._load_current_pixbuf()

    def _on_reveal_clicked(self):
        if self.current_photo and self.on_reveal:
            self.on_reveal(self.current_photo)

    def _on_trash_clicked(self):
        if self.current_photo and self.on_trash:
            photo = self.current_photo
            self.on_trash(photo)
            if photo in self.photos_list:
                self.photos_list.remove(photo)
            if self.photos_list:
                self.next_photo()
            else:
                self.close_lightbox()

    # -------------------------------------------------------------------------
    # PHOTO EDITING WORKFLOW (macOS Sequoia Photos Suite)
    # -------------------------------------------------------------------------
    def enter_edit_mode(self):
        if not self.current_photo or self.current_photo.is_video:
            return
        self.is_editing = True
        self.reset_zoom()
        self.pan_x = 0
        self.pan_y = 0

        # Hide normal lightbox controls
        self.top_header.hide()
        self.btn_prev.hide()
        self.btn_next.hide()
        self.bottom_bar.hide()

        # Initialize editing engine
        self.editor_engine = PhotoEditorEngine(self.current_photo.path)
        self.editor_active_tab = "adjust"
        self.editor_header._highlight_tab("adjust")
        self.editor_header.revert_btn.set_sensitive(self.editor_engine.has_backup())

        # Construct and mount right inspector panel
        for child in self.editor_inspector_box.get_children():
            self.editor_inspector_box.remove(child)
        self.editor_inspector = PhotoEditorInspector(self.editor_engine, self._on_editor_changed)
        self.editor_inspector.set_active_tab("adjust")
        self.editor_inspector_box.pack_start(self.editor_inspector, True, True, 0)

        # Show editor controls
        self.editor_header.set_no_show_all(False)
        self.editor_header.show_all()
        self.editor_header.set_no_show_all(True)

        self.editor_inspector_box.set_no_show_all(False)
        self.editor_inspector_box.show_all()
        self.editor_inspector_box.set_no_show_all(True)

        self._refresh_editor_preview()

    def exit_edit_mode(self, save=False):
        if not self.is_editing:
            return
        self.is_editing = False
        self._crop_dragging = None
        self._markup_drawing = False
        self._markup_current_stroke = None

        self.editor_header.hide()
        self.editor_inspector_box.hide()

        self.top_header.show()
        self.btn_prev.show()
        self.btn_next.show()
        self.bottom_bar.show()

        if not save:
            self.editor_engine = None
            self._pixbuf_cache = None
            self._load_current_pixbuf()
        else:
            self.editor_engine = None

        self.draw_area.queue_draw()

    def _on_editor_tab_switched(self, tab_id: str):
        self.editor_active_tab = tab_id
        if self.editor_inspector:
            self.editor_inspector.set_active_tab(tab_id)
        self.draw_area.queue_draw()

    def _on_editor_changed(self, re_crop=False):
        if not self.editor_engine:
            return
        self._refresh_editor_preview()

    def _refresh_editor_preview(self):
        if not self.editor_engine:
            return
        pb = self.editor_engine.render_preview_pixbuf()
        if pb:
            self._pixbuf_cache = pb
            self.draw_area.queue_draw()

    def _on_auto_enhance(self):
        if not self.editor_engine:
            return
        self.editor_engine.auto_enhance()
        if self.editor_inspector:
            self.editor_inspector.sync_sliders_from_engine()
        self._refresh_editor_preview()

    def _on_revert_original(self):
        if not self.editor_engine:
            return
        ok = self.editor_engine.revert_to_original()
        if ok:
            if self.editor_inspector:
                self.editor_inspector.sync_sliders_from_engine()
                self.editor_inspector._on_reset_crop()
            self.editor_header.revert_btn.set_sensitive(False)
            self._refresh_editor_preview()
            if self.on_photo_edited and self.current_photo:
                self.on_photo_edited(self.current_photo)

    def _on_save_done(self):
        if not self.editor_engine or not self.current_photo:
            self.exit_edit_mode(save=False)
            return
        ok = self.editor_engine.save_full()
        if ok:
            try:
                stat = os.stat(self.current_photo.path)
                self.current_photo.mtime = stat.st_mtime
                self.current_photo.size_bytes = stat.st_size
                if self.editor_engine.original_im:
                    self.current_photo.width, self.current_photo.height = self.editor_engine.original_im.size
            except Exception as e:
                print(f"[Lightbox] Stat update failed after save: {e}")
            if self.on_photo_edited:
                self.on_photo_edited(self.current_photo)
            self.exit_edit_mode(save=True)
            self._pixbuf_cache = None
            self._load_current_pixbuf()
        else:
            self.exit_edit_mode(save=False)

    def _get_image_geometry(self, w: int, h: int):
        if not self._pixbuf_cache:
            return 0.0, 0.0, 0.0, 0.0
        img_w = self._pixbuf_cache.get_width()
        img_h = self._pixbuf_cache.get_height()
        if img_w <= 0 or img_h <= 0:
            return 0.0, 0.0, 0.0, 0.0

        view_w = max(100, w - 310) if self.is_editing else w
        view_h = h

        scale_fit = min(view_w / img_w, view_h / img_h)
        final_scale = scale_fit * self.zoom_factor

        draw_w = img_w * final_scale
        draw_h = img_h * final_scale

        draw_x = (view_w - draw_w) / 2.0 + self.pan_x
        draw_y = (view_h - draw_h) / 2.0 + self.pan_y
        return draw_x, draw_y, draw_w, draw_h

    def _get_crop_handle_at(self, mx: float, my: float, csx1: float, csy1: float, csx2: float, csy2: float, hit_radius: float = 18.0) -> Optional[str]:
        if math.hypot(mx - csx1, my - csy1) <= hit_radius:
            return "nw"
        if math.hypot(mx - csx2, my - csy1) <= hit_radius:
            return "ne"
        if math.hypot(mx - csx2, my - csy2) <= hit_radius:
            return "se"
        if math.hypot(mx - csx1, my - csy2) <= hit_radius:
            return "sw"

        mid_x = (csx1 + csx2) / 2.0
        mid_y = (csy1 + csy2) / 2.0
        if math.hypot(mx - mid_x, my - csy1) <= hit_radius:
            return "n"
        if math.hypot(mx - mid_x, my - csy2) <= hit_radius:
            return "s"
        if math.hypot(mx - csx1, my - mid_y) <= hit_radius:
            return "w"
        if math.hypot(mx - csx2, my - mid_y) <= hit_radius:
            return "e"

        if csx1 < mx < csx2 and csy1 < my < csy2:
            return "move"
        return None

    # Cairo Drawing & Gestures
    def _on_draw(self, widget, cr: cairo.Context):
        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height

        cr.set_source_rgba(0.06, 0.06, 0.08, 0.98)
        cr.paint()

        if not self._pixbuf_cache:
            if self.current_photo and not self.current_photo.is_video:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.5)
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(15.0)
                msg = f"Đang tải {self.current_photo.filename}..."
                extents = cr.text_extents(msg)
                cr.move_to((w - extents.width) / 2.0, h / 2.0)
                cr.show_text(msg)
            return

        draw_x, draw_y, draw_w, draw_h = self._get_image_geometry(w, h)
        if draw_w <= 0 or draw_h <= 0:
            return

        img_w = self._pixbuf_cache.get_width()
        final_scale = draw_w / img_w

        cr.save()
        cr.translate(draw_x, draw_y)
        cr.scale(final_scale, final_scale)
        Gdk.cairo_set_source_pixbuf(cr, self._pixbuf_cache, 0, 0)
        cr.paint()
        cr.restore()

        # If in edit mode and on Crop tab: draw Apple Photos crop grid & handles
        if self.is_editing and self.editor_active_tab == "crop" and self.editor_engine:
            crop_box = self.editor_engine.crop_box or (0.0, 0.0, 1.0, 1.0)
            x1, y1, x2, y2 = crop_box
            csx1 = draw_x + x1 * draw_w
            csy1 = draw_y + y1 * draw_h
            csx2 = draw_x + x2 * draw_w
            csy2 = draw_y + y2 * draw_h
            csw = max(10.0, csx2 - csx1)
            csh = max(10.0, csy2 - csy1)

            # 1. Dark mask outside crop box
            cr.save()
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.rectangle(draw_x, draw_y, draw_w, draw_h)
            cr.rectangle(csx1, csy1, csw, csh)
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.52)
            cr.fill()
            cr.restore()

            # 2. Rule of thirds 3x3 grid lines
            cr.save()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.35)
            cr.set_line_width(1.0)
            cr.move_to(csx1 + csw / 3.0, csy1)
            cr.line_to(csx1 + csw / 3.0, csy2)
            cr.move_to(csx1 + 2.0 * csw / 3.0, csy1)
            cr.line_to(csx1 + 2.0 * csw / 3.0, csy2)
            cr.move_to(csx1, csy1 + csh / 3.0)
            cr.line_to(csx2, csy1 + csh / 3.0)
            cr.move_to(csx1, csy1 + 2.0 * csh / 3.0)
            cr.line_to(csx2, csy1 + 2.0 * csh / 3.0)
            cr.stroke()

            # 3. Outer boundary line
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.set_line_width(1.5)
            cr.rectangle(csx1, csy1, csw, csh)
            cr.stroke()

            # 4. Corner L brackets (Apple macOS Photos signature style)
            cr.set_line_width(3.5)
            cr.set_line_cap(cairo.LINE_CAP_SQUARE)
            arm = min(22.0, min(csw, csh) / 4.0)

            # NW
            cr.move_to(csx1, csy1 + arm)
            cr.line_to(csx1, csy1)
            cr.line_to(csx1 + arm, csy1)
            # NE
            cr.move_to(csx2 - arm, csy1)
            cr.line_to(csx2, csy1)
            cr.line_to(csx2, csy1 + arm)
            # SE
            cr.move_to(csx2, csy2 - arm)
            cr.line_to(csx2, csy2)
            cr.line_to(csx2 - arm, csy2)
            # SW
            cr.move_to(csx1 + arm, csy2)
            cr.line_to(csx1, csy2)
            cr.line_to(csx1, csy2 - arm)
            cr.stroke()

            # 5. Edge midpoints
            marm = 14.0
            cr.move_to(csx1 + csw / 2.0 - marm / 2.0, csy1)
            cr.line_to(csx1 + csw / 2.0 + marm / 2.0, csy1)
            cr.move_to(csx1 + csw / 2.0 - marm / 2.0, csy2)
            cr.line_to(csx1 + csw / 2.0 + marm / 2.0, csy2)
            cr.move_to(csx1, csy1 + csh / 2.0 - marm / 2.0)
            cr.line_to(csx1, csy1 + csh / 2.0 + marm / 2.0)
            cr.move_to(csx2, csy1 + csh / 2.0 - marm / 2.0)
            cr.line_to(csx2, csy1 + csh / 2.0 + marm / 2.0)
            cr.stroke()
            cr.restore()

        # If in edit mode and drawing live markup in Cairo:
        if self.is_editing and self.editor_active_tab == "markup" and self._markup_drawing and self._markup_current_stroke:
            cr.save()
            st = self._markup_current_stroke
            st_type = st.get("type")
            rgba = st.get("color", (255, 59, 48, 255))
            r = rgba[0] / 255.0
            g = rgba[1] / 255.0
            b = rgba[2] / 255.0
            a = (rgba[3] if len(rgba) > 3 else 255) / 255.0
            cr.set_source_rgba(r, g, b, a)
            cr.set_line_width(st.get("width", 5))
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)

            if st_type == "pen":
                pts = st.get("points", [])
                if len(pts) > 1:
                    cr.move_to(draw_x + pts[0][0] * draw_w, draw_y + pts[0][1] * draw_h)
                    for px, py in pts[1:]:
                        cr.line_to(draw_x + px * draw_w, draw_y + py * draw_h)
                    cr.stroke()
            elif st_type == "arrow":
                p1 = st.get("p1")
                p2 = st.get("p2")
                if p1 and p2:
                    ax1, ay1 = draw_x + p1[0] * draw_w, draw_y + p1[1] * draw_h
                    ax2, ay2 = draw_x + p2[0] * draw_w, draw_y + p2[1] * draw_h
                    cr.move_to(ax1, ay1)
                    cr.line_to(ax2, ay2)
                    cr.stroke()
                    ang = math.atan2(ay2 - ay1, ax2 - ax1)
                    hlen = max(14.0, st.get("width", 5) * 3.0)
                    a_ang = math.pi / 6.0
                    cr.move_to(ax2, ay2)
                    cr.line_to(ax2 - hlen * math.cos(ang - a_ang), ay2 - hlen * math.sin(ang - a_ang))
                    cr.line_to(ax2 - hlen * math.cos(ang + a_ang), ay2 - hlen * math.sin(ang + a_ang))
                    cr.close_path()
                    cr.fill()
            elif st_type == "rect":
                box = st.get("box")
                if box:
                    rx1, ry1, rx2, ry2 = box
                    cr.rectangle(draw_x + rx1 * draw_w, draw_y + ry1 * draw_h, (rx2 - rx1) * draw_w, (ry2 - ry1) * draw_h)
                    cr.stroke()
            elif st_type == "circle":
                center = st.get("center")
                radius = st.get("radius", 0.05)
                if center:
                    cr.save()
                    cr.translate(draw_x + center[0] * draw_w, draw_y + center[1] * draw_h)
                    cr.scale(draw_w, draw_h)
                    cr.arc(0, 0, radius, 0, 2 * math.pi)
                    cr.restore()
                    cr.stroke()
            cr.restore()

    def _on_draw_button_press(self, widget, event):
        if event.button == 1:
            if self.is_editing:
                alloc = widget.get_allocation()
                draw_x, draw_y, draw_w, draw_h = self._get_image_geometry(alloc.width, alloc.height)
                if draw_w <= 0 or draw_h <= 0:
                    return True

                if self.editor_active_tab == "crop" and self.editor_engine:
                    crop_box = self.editor_engine.crop_box or (0.0, 0.0, 1.0, 1.0)
                    x1, y1, x2, y2 = crop_box
                    csx1 = draw_x + x1 * draw_w
                    csy1 = draw_y + y1 * draw_h
                    csx2 = draw_x + x2 * draw_w
                    csy2 = draw_y + y2 * draw_h

                    handle = self._get_crop_handle_at(event.x, event.y, csx1, csy1, csx2, csy2)
                    if handle:
                        self._crop_dragging = handle
                        self._crop_drag_start = (event.x, event.y)
                        self._crop_initial_box = crop_box
                    return True

                elif self.editor_active_tab == "markup" and self.editor_inspector:
                    if draw_x <= event.x <= draw_x + draw_w and draw_y <= event.y <= draw_y + draw_h:
                        nx = (event.x - draw_x) / draw_w
                        ny = (event.y - draw_y) / draw_h
                        tool = self.editor_inspector.active_markup_tool
                        color = self.editor_inspector.active_color
                        width = self.editor_inspector.active_stroke_width

                        if tool == "text":
                            txt = self.editor_inspector.text_entry.get_text() or "Ghi chú"
                            self.editor_engine.add_markup({
                                "type": "text",
                                "pos": (nx, ny),
                                "text": txt,
                                "color": color,
                            })
                            self._refresh_editor_preview()
                        else:
                            self._markup_drawing = True
                            self._markup_start_pt = (nx, ny)
                            self._markup_current_stroke = {
                                "type": tool,
                                "color": color,
                                "width": width,
                            }
                            if tool == "pen":
                                self._markup_current_stroke["points"] = [(nx, ny)]
                            elif tool == "arrow":
                                self._markup_current_stroke["p1"] = (nx, ny)
                                self._markup_current_stroke["p2"] = (nx, ny)
                            elif tool == "rect":
                                self._markup_current_stroke["box"] = (nx, ny, nx, ny)
                            elif tool == "circle":
                                self._markup_current_stroke["center"] = (nx, ny)
                                self._markup_current_stroke["radius"] = 0.001
                        return True
                return True

            # Video click toggles Play/Pause (ignore double-click from card activation)
            if self.current_photo and self.current_photo.is_video:
                if time.time() - getattr(self, '_opened_timestamp', 0) >= 0.35:
                    self.toggle_video_play_pause()
                return True
            self._is_dragging = True
            self._drag_start_x = event.x - self.pan_x
            self._drag_start_y = event.y - self.pan_y
            return True
        return False

    def _on_draw_button_release(self, widget, event):
        if event.button == 1:
            if self.is_editing:
                if self._crop_dragging:
                    self._crop_dragging = None
                    return True
                elif self._markup_drawing:
                    self._markup_drawing = False
                    if self._markup_current_stroke:
                        self.editor_engine.add_markup(self._markup_current_stroke)
                        self._markup_current_stroke = None
                        self._refresh_editor_preview()
                    return True
                return True
            self._is_dragging = False
            return True
        return False

    def _on_draw_motion(self, widget, event):
        if self.is_editing:
            alloc = widget.get_allocation()
            draw_x, draw_y, draw_w, draw_h = self._get_image_geometry(alloc.width, alloc.height)
            if draw_w <= 0 or draw_h <= 0:
                return False

            if self.editor_active_tab == "crop" and self._crop_dragging and self.editor_engine:
                dx = (event.x - self._crop_drag_start[0]) / draw_w
                dy = (event.y - self._crop_drag_start[1]) / draw_h
                x1, y1, x2, y2 = self._crop_initial_box

                h_type = self._crop_dragging
                if h_type == "move":
                    bw = x2 - x1
                    bh = y2 - y1
                    nx1 = max(0.0, min(1.0 - bw, x1 + dx))
                    ny1 = max(0.0, min(1.0 - bh, y1 + dy))
                    new_box = (nx1, ny1, nx1 + bw, ny1 + bh)
                elif h_type == "nw":
                    nx1 = max(0.0, min(x2 - 0.05, x1 + dx))
                    ny1 = max(0.0, min(y2 - 0.05, y1 + dy))
                    new_box = (nx1, ny1, x2, y2)
                elif h_type == "ne":
                    nx2 = min(1.0, max(x1 + 0.05, x2 + dx))
                    ny1 = max(0.0, min(y2 - 0.05, y1 + dy))
                    new_box = (x1, ny1, nx2, y2)
                elif h_type == "se":
                    nx2 = min(1.0, max(x1 + 0.05, x2 + dx))
                    ny2 = min(1.0, max(y1 + 0.05, y2 + dy))
                    new_box = (x1, y1, nx2, ny2)
                elif h_type == "sw":
                    nx1 = max(0.0, min(x2 - 0.05, x1 + dx))
                    ny2 = min(1.0, max(y1 + 0.05, y2 + dy))
                    new_box = (nx1, y1, x2, ny2)
                elif h_type == "n":
                    ny1 = max(0.0, min(y2 - 0.05, y1 + dy))
                    new_box = (x1, ny1, x2, y2)
                elif h_type == "s":
                    ny2 = min(1.0, max(y1 + 0.05, y2 + dy))
                    new_box = (x1, y1, x2, ny2)
                elif h_type == "w":
                    nx1 = max(0.0, min(x2 - 0.05, x1 + dx))
                    new_box = (nx1, y1, x2, y2)
                elif h_type == "e":
                    nx2 = min(1.0, max(x1 + 0.05, x2 + dx))
                    new_box = (x1, y1, nx2, y2)
                else:
                    new_box = (x1, y1, x2, y2)

                self.editor_engine.set_crop_box(new_box)
                widget.queue_draw()
                return True

            elif self.editor_active_tab == "markup" and self._markup_drawing and self._markup_current_stroke:
                nx = max(0.0, min(1.0, (event.x - draw_x) / draw_w))
                ny = max(0.0, min(1.0, (event.y - draw_y) / draw_h))
                tool = self._markup_current_stroke.get("type")

                if tool == "pen":
                    self._markup_current_stroke["points"].append((nx, ny))
                elif tool == "arrow":
                    self._markup_current_stroke["p2"] = (nx, ny)
                elif tool == "rect":
                    sx, sy = self._markup_start_pt
                    self._markup_current_stroke["box"] = (min(sx, nx), min(sy, ny), max(sx, nx), max(sy, ny))
                elif tool == "circle":
                    sx, sy = self._markup_start_pt
                    cx = (sx + nx) / 2.0
                    cy = (sy + ny) / 2.0
                    r = math.hypot(nx - sx, ny - sy) / 2.0
                    self._markup_current_stroke["center"] = (cx, cy)
                    self._markup_current_stroke["radius"] = r

                widget.queue_draw()
                return True
            return False

        if self._is_dragging and self.zoom_factor > 1.01:
            self.pan_x = event.x - self._drag_start_x
            self.pan_y = event.y - self._drag_start_y
            widget.queue_draw()
            return True
        return False

    def _on_draw_scroll(self, widget, event):
        if self.is_editing:
            return True
        if event.direction == Gdk.ScrollDirection.UP:
            self._zoom_in()
            return True
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self._zoom_out()
            return True
        return False


class InspectorPanel(Gtk.Box):
    """
    macOS Photos Inspector Panel (Bảng Thông tin - "i")
    Displays full photo/video specs, EXIF camera details, dimensions and quick actions.
    """
    def __init__(self, on_set_wallpaper, on_reveal, on_close):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_no_show_all(True)
        self.on_set_wallpaper = on_set_wallpaper
        self.on_reveal = on_reveal
        self.on_close = on_close
        self.current_photo: Optional[PhotoItem] = None

        self.set_size_request(290, -1)
        self.get_style_context().add_class("mac-inspector-panel")

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class("inspector-header")

        title = Gtk.Label(label="Thông tin (Info)")
        title.get_style_context().add_class("inspector-title")
        header.pack_start(title, True, True, 0)

        close_btn = Gtk.Button()
        close_btn.get_style_context().add_class("inspector-close-btn")
        close_lbl = Gtk.Label(label="✕")
        close_lbl.get_style_context().add_class("inspector-x")
        close_btn.add(close_lbl)
        close_btn.connect("clicked", lambda _: self.on_close())
        header.pack_end(close_btn, False, False, 0)
        self.pack_start(header, False, False, 0)

        # Scrolled content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.pack_start(scroll, True, True, 0)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.content_box.set_margin_start(16)
        self.content_box.set_margin_end(16)
        self.content_box.set_margin_top(12)
        self.content_box.set_margin_bottom(16)
        scroll.add(self.content_box)

        # Mini preview
        self.preview_img = Gtk.Image()
        self.preview_img.set_size_request(250, 160)
        self.preview_img.get_style_context().add_class("inspector-thumb")
        self.content_box.pack_start(self.preview_img, False, False, 0)

        # Filename
        self.filename_lbl = Gtk.Label(label="")
        self.filename_lbl.get_style_context().add_class("inspector-filename")
        self.filename_lbl.set_line_wrap(True)
        self.filename_lbl.set_line_wrap_mode(Pango.WrapMode.CHAR)
        self.filename_lbl.set_xalign(0.0)
        self.content_box.pack_start(self.filename_lbl, False, False, 0)

        # Primary Stats Card
        self.stats_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.stats_card.get_style_context().add_class("inspector-card")

        self.row_date = self._create_info_row("Ngày chụp / tạo", "")
        self.row_dims = self._create_info_row("Kích thước", "")
        self.row_size = self._create_info_row("Dung lượng", "")
        self.row_format = self._create_info_row("Định dạng", "")
        self.row_folder = self._create_info_row("Thư mục", "")

        self.stats_card.pack_start(self.row_date[0], False, False, 0)
        self.stats_card.pack_start(self.row_dims[0], False, False, 0)
        self.stats_card.pack_start(self.row_size[0], False, False, 0)
        self.stats_card.pack_start(self.row_format[0], False, False, 0)
        self.stats_card.pack_start(self.row_folder[0], False, False, 0)
        self.content_box.pack_start(self.stats_card, False, False, 0)

        # EXIF / Video Specs Card
        self.exif_header = Gtk.Label(label="MÁY ẢNH & THÔNG SỐ (EXIF)")
        self.exif_header.get_style_context().add_class("inspector-section-hdr")
        self.exif_header.set_xalign(0.0)
        self.content_box.pack_start(self.exif_header, False, False, 0)

        self.exif_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.exif_card.get_style_context().add_class("inspector-card")

        self.row_camera = self._create_info_row("Thiết bị", "—")
        self.row_lens = self._create_info_row("Ống kính", "—")
        self.row_iso = self._create_info_row("ISO / Khẩu độ", "—")
        self.row_focal = self._create_info_row("Tiêu cự", "—")

        self.exif_card.pack_start(self.row_camera[0], False, False, 0)
        self.exif_card.pack_start(self.row_lens[0], False, False, 0)
        self.exif_card.pack_start(self.row_iso[0], False, False, 0)
        self.exif_card.pack_start(self.row_focal[0], False, False, 0)
        self.content_box.pack_start(self.exif_card, False, False, 0)

        # Quick Actions
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        actions_box.set_margin_top(8)

        self.btn_wall = Gtk.Button(label="Đặt làm hình nền Desktop")
        self.btn_wall.get_style_context().add_class("inspector-action-btn")
        self.btn_wall.connect("clicked", lambda _: self.on_set_wallpaper(self.current_photo))
        actions_box.pack_start(self.btn_wall, False, False, 0)

        btn_reveal = Gtk.Button(label="Mở trong Thư mục (Files)")
        btn_reveal.get_style_context().add_class("inspector-action-btn")
        btn_reveal.connect("clicked", lambda _: self.on_reveal(self.current_photo))
        actions_box.pack_start(btn_reveal, False, False, 0)

        self.content_box.pack_start(actions_box, False, False, 0)

    def _create_info_row(self, title: str, default_val: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_t = Gtk.Label(label=title)
        lbl_t.get_style_context().add_class("inspector-row-title")
        lbl_t.set_xalign(0.0)

        lbl_v = Gtk.Label(label=default_val)
        lbl_v.get_style_context().add_class("inspector-row-value")
        lbl_v.set_xalign(1.0)
        lbl_v.set_ellipsize(Pango.EllipsizeMode.MIDDLE)

        row.pack_start(lbl_t, False, False, 0)
        row.pack_end(lbl_v, True, True, 0)
        return row, lbl_v

    def set_photo(self, photo: Optional[PhotoItem]):
        self.current_photo = photo
        if not photo:
            return

        photo.load_dimensions_and_exif()

        self.filename_lbl.set_text(photo.filename)
        self.row_date[1].set_text(photo.date_str)
        self.row_dims[1].set_text(photo.dimensions_str)
        self.row_size[1].set_text(photo.formatted_size)
        self.row_format[1].set_text(photo.format_name)
        self.row_folder[1].set_text(photo.folder_name)

        if photo.is_video:
            self.exif_header.set_text("THÔNG SỐ VIDEO (SPECS)")
            self.row_camera[0].get_children()[0].set_text("Thời lượng")
            self.row_camera[1].set_text(photo.duration_str or "—")

            self.row_lens[0].get_children()[0].set_text("Codec Video")
            self.row_lens[1].set_text(photo.video_codec or photo.format_name)

            self.row_iso[0].get_children()[0].set_text("Codec Audio")
            self.row_iso[1].set_text(photo.audio_codec or "—")

            self.row_focal[0].get_children()[0].set_text("Loại tập tin")
            self.row_focal[1].set_text("Video đa phương tiện")

            self.btn_wall.hide()
        else:
            self.exif_header.set_text("MÁY ẢNH & THÔNG SỐ (EXIF)")
            self.row_camera[0].get_children()[0].set_text("Thiết bị")
            self.row_lens[0].get_children()[0].set_text("Ống kính")
            self.row_iso[0].get_children()[0].set_text("ISO / Khẩu độ")
            self.row_focal[0].get_children()[0].set_text("Tiêu cự")
            self.btn_wall.show()

            exif = photo.exif_data or {}
            cam_make = exif.get("Make", "")
            cam_model = exif.get("Model", "")
            camera_str = f"{cam_make} {cam_model}".strip() or "Không có EXIF"
            self.row_camera[1].set_text(camera_str)

            lens = exif.get("LensModel", exif.get("LensMake", "—"))
            self.row_lens[1].set_text(lens)

            f_num = exif.get("FNumber", "")
            iso = exif.get("ISOSpeedRatings", exif.get("ISO", ""))
            speed = exif.get("ExposureTime", "")
            iso_str = f"ISO {iso}" if iso else ""
            if f_num:
                iso_str += f" • f/{f_num}"
            if speed:
                iso_str += f" • {speed}s"
            self.row_iso[1].set_text(iso_str or "—")

            focal = exif.get("FocalLength", "—")
            self.row_focal[1].set_text(f"{focal} mm" if focal != "—" else "—")

        # Load preview thumbnail
        PhotoLibraryManager.get_instance().request_thumbnail(
            photo, 300, self._on_preview_ready
        )

    def _on_preview_ready(self, item: PhotoItem, thumb_path: str):
        if self.current_photo and item.path == self.current_photo.path:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb_path, 250, 160, True)
                self.preview_img.set_from_pixbuf(pb)
            except Exception:
                pass


class MacOSPhotosWindow(Gtk.Window):
    """
    Main macOS Photos Application Window for Ubuntu Linux.
    Supports Photos & Videos management and viewing.
    """
    _instance = None
    _css_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MacOSPhotosWindow()
        else:
            try:
                # If destroyed or invalid GObject, recreate
                if not hasattr(cls._instance, "props") or cls._instance.__grefcount__ <= 0:
                    cls._instance = MacOSPhotosWindow()
            except Exception:
                cls._instance = MacOSPhotosWindow()
        return cls._instance

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        GLib.set_prgname("macos-photos")
        if not GLib.get_application_name():
            GLib.set_application_name(t("photos_title", "Ảnh"))
        self.set_title("Ảnh (macOS Photos)")
        self.set_wmclass("macos-photos", "MacOSPhotos")
        self.set_role("photos")
        self._is_iconified = False

        # App Icon (Authentic Apple Photos rainbow flower icon)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "photos_icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "photos_icon.svg")
        try:
            if os.path.exists(icon_path):
                self.set_icon_from_file(icon_path)
            else:
                self.set_icon_name("multimedia-photo-viewer")
        except Exception as e:
            print(f"[Photos] Error setting icon: {e}")

        self.set_default_size(1180, 780)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_resizable(True)

        geom = Gdk.Geometry()
        geom.min_width = 840
        geom.min_height = 560
        self.set_geometry_hints(None, geom, Gdk.WindowHints.MIN_SIZE)

        self._is_maximized = False
        self._is_sidebar_visible = True
        self._is_inspector_visible = False
        self.is_dark = is_system_dark_mode()

        self.library_mgr = PhotoLibraryManager.get_instance()
        self.current_category = "all"
        self.current_folder_filter: Optional[str] = None
        self.current_format_filter: Optional[str] = None
        self.search_query = ""

        self.displayed_photos: List[PhotoItem] = []
        self._loaded_batch_count = 0
        self._batch_size = 45
        self.selected_photo: Optional[PhotoItem] = None
        self._is_select_mode = False
        self.selected_photos = set() # Set of photo.path

        self.picker_mode = False
        self.picker_callback = None
        self.picker_title = "Chọn ảnh"

        # RGBA Visual
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        self._load_css()
        self._setup_ui()

        # Connect window events
        self.connect("draw", self._on_window_draw)
        self.connect("delete-event", self._on_delete_event)
        self.connect("destroy", self._on_destroy_cleanup)
        self.connect("key-press-event", self._on_key_press)
        self.connect("window-state-event", self._on_window_state_event)

        # Dynamic System Theme Listener
        try:
            self._gnome_settings = Gio.Settings.new("org.gnome.desktop.interface")
            self._gnome_settings.connect("changed::color-scheme", lambda *_: GLib.idle_add(self.apply_theme))
            self._gnome_settings.connect("changed::gtk-theme", lambda *_: GLib.idle_add(self.apply_theme))
        except Exception:
            pass

        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

        # Subscribe to library changes
        self.library_mgr.subscribe(self._on_library_event)

        # Initial Scan
        self.library_mgr.start_scan()
        self.apply_theme()

    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self._rebuild_sidebar_and_refresh)

    def _rebuild_sidebar_and_refresh(self):
        try:
            if hasattr(self, "sidebar_nav_box"):
                for ch in self.sidebar_nav_box.get_children():
                    self.sidebar_nav_box.remove(ch)
                self._sidebar_buttons = {}
                # Section 1: Library
                self._add_sidebar_section_header(t("photos_library").upper())
                self._add_sidebar_nav_item("all", t("photos_all"), "photos")
                self._add_sidebar_nav_item("videos", t("photos_videos"), "film")
                self._add_sidebar_nav_item("recent", t("photos_recents"), "clock")
                self._add_sidebar_nav_item("favorites", t("photos_favorites"), "heart")
                self._add_sidebar_nav_item("screenshots", t("photos_screenshots"), "screenshot")
                self._add_sidebar_nav_item("downloads", t("photos_downloads"), "download")

                # Section 2: Local Folders
                sec_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                sec_header.set_margin_top(14)
                sec_header.set_margin_bottom(4)
                sec_header.set_margin_start(8)
                lbl = Gtk.Label(label=t("photos_local_folders").upper())
                lbl.get_style_context().add_class("sidebar-section-hdr")
                sec_header.pack_start(lbl, True, True, 0)
                btn_add_folder = Gtk.Button()
                btn_add_folder.get_style_context().add_class("sidebar-add-folder-btn")
                btn_add_folder.set_tooltip_text(t("photos_add_folder_tooltip"))
                btn_add_folder.add(get_image("plus", 12, "#86868b"))
                btn_add_folder.connect("clicked", lambda _: self._open_add_folder_dialog())
                sec_header.pack_end(btn_add_folder, False, False, 4)
                self.sidebar_nav_box.pack_start(sec_header, False, False, 0)
                self.folders_nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                self.sidebar_nav_box.pack_start(self.folders_nav_box, False, False, 0)
                self._populate_folders_sidebar()

                # Section 3: Formats
                self._add_sidebar_section_header(t("photos_media_types").upper())
                self.formats_nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                self.sidebar_nav_box.pack_start(self.formats_nav_box, False, False, 0)
                self._populate_formats_sidebar()

                # Section 4: Utilities
                self._add_sidebar_section_header(t("photos_utilities").upper())
                self._add_sidebar_nav_item("trash", t("photos_trash"), "trash")
                self.sidebar_nav_box.show_all()
                self._highlight_sidebar_item(self.current_category)

            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("photos_search_placeholder"))
            if hasattr(self, "btn_select"):
                self.btn_select.set_label(t("photos_select"))
            if hasattr(self, "btn_slideshow"):
                self.btn_slideshow.set_tooltip_text(t("photos_slideshow"))
            self._render_current_category()
        except Exception as e:
            print(f"[Photos] _rebuild_sidebar_and_refresh error: {e}")

    def _setup_ui(self):
        # Master Stack / Overlay Root
        self.master_overlay = Gtk.Overlay()
        self.add(self.master_overlay)

        # Main App Window Card
        self.root_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root_card.get_style_context().add_class("mac-photos-window")
        self.master_overlay.add(self.root_card)

        self._setup_resize_handles()

        # -------------------------------------------------------------
        # 1. TOP TOOLBAR & HEADER
        # -------------------------------------------------------------
        self.toolbar_event_box = Gtk.EventBox()
        self.toolbar_event_box.set_visible_window(False)
        self.toolbar_event_box.connect("button-press-event", self._on_header_button_press)
        self.root_card.pack_start(self.toolbar_event_box, False, False, 0)

        # -------------------------------------------------------------
        # 1.1 PHOTO PICKER MODE TOP BANNER
        # -------------------------------------------------------------
        self.picker_banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.picker_banner.get_style_context().add_class("mac-photos-picker-banner")
        self.picker_banner.set_no_show_all(True)

        picker_icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        picker_icon_box.set_valign(Gtk.Align.CENTER)
        picker_icon_box.pack_start(get_image("photos", 20, "#007aff"), False, False, 0)
        self.picker_banner.pack_start(picker_icon_box, False, False, 0)

        picker_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        picker_text_box.set_valign(Gtk.Align.CENTER)
        self.picker_title_lbl = Gtk.Label(label="Chọn hình ảnh")
        self.picker_title_lbl.get_style_context().add_class("picker-banner-title")
        self.picker_title_lbl.set_xalign(0.0)
        picker_text_box.pack_start(self.picker_title_lbl, False, False, 0)

        self.picker_sub_lbl = Gtk.Label(label="Nhấp chọn một ảnh rồi bấm 'Sử dụng ảnh này', hoặc nhấp đúp để chọn ngay.")
        self.picker_sub_lbl.get_style_context().add_class("picker-banner-subtitle")
        self.picker_sub_lbl.set_xalign(0.0)
        picker_text_box.pack_start(self.picker_sub_lbl, False, False, 0)
        self.picker_banner.pack_start(picker_text_box, True, True, 0)

        picker_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        picker_actions.set_valign(Gtk.Align.CENTER)

        self.btn_picker_browse = Gtk.Button(label="📁 Duyệt tệp khác…")
        self.btn_picker_browse.get_style_context().add_class("mac-tool-btn")
        self.btn_picker_browse.connect("clicked", lambda _: self._browse_fallback_file())
        picker_actions.pack_start(self.btn_picker_browse, False, False, 0)

        self.btn_picker_cancel = Gtk.Button(label="Hủy")
        self.btn_picker_cancel.get_style_context().add_class("mac-tool-btn")
        self.btn_picker_cancel.connect("clicked", lambda _: self._cancel_picker_mode())
        picker_actions.pack_start(self.btn_picker_cancel, False, False, 0)

        self.btn_picker_confirm = Gtk.Button(label="✓ Sử dụng ảnh này")
        self.btn_picker_confirm.get_style_context().add_class("mac-btn-primary")
        self.btn_picker_confirm.set_sensitive(False)
        self.btn_picker_confirm.connect("clicked", lambda _: self._confirm_picker_selection())
        picker_actions.pack_start(self.btn_picker_confirm, False, False, 0)

        self.picker_banner.pack_end(picker_actions, False, False, 0)
        self.root_card.pack_start(self.picker_banner, False, False, 0)

        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.toolbar.get_style_context().add_class("mac-photos-toolbar")
        self.toolbar_event_box.add(self.toolbar)

        # Traffic Lights
        tl = TrafficLightsWidget(
            on_close=self.close_window,
            on_minimize=self.iconify,
            on_maximize=self.toggle_maximize
        )
        self.toolbar.pack_start(tl, False, False, 0)

        # Sidebar Toggle Button
        self.btn_sidebar_toggle = Gtk.Button()
        self.btn_sidebar_toggle.set_valign(Gtk.Align.CENTER)
        self.btn_sidebar_toggle.set_size_request(32, 32)
        self.btn_sidebar_toggle.get_style_context().add_class("mac-tool-btn")
        self.btn_sidebar_toggle.set_tooltip_text("Ẩn / Hiện thanh bên (Sidebar)")
        self.btn_sidebar_toggle.add(get_image("sidebar", 16, "#6e6e73"))
        self.btn_sidebar_toggle.connect("clicked", lambda _: self.toggle_sidebar())
        self.toolbar.pack_start(self.btn_sidebar_toggle, False, False, 0)

        # Category Title & Count (Center)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_box.set_valign(Gtk.Align.CENTER)
        self.title_lbl = Gtk.Label(label=t("photos_all"))
        self.title_lbl.get_style_context().add_class("mac-toolbar-title")
        self.title_lbl.set_xalign(0.0)

        self.subtitle_lbl = Gtk.Label(label="Đang quét ảnh & video...")
        self.subtitle_lbl.get_style_context().add_class("mac-toolbar-subtitle")
        self.subtitle_lbl.set_xalign(0.0)

        title_box.pack_start(self.title_lbl, False, False, 0)
        title_box.pack_start(self.subtitle_lbl, False, False, 0)
        self.toolbar.pack_start(title_box, False, False, 8)

        # Right Controls: Zoom Slider, Search Entry, Slideshow, Info
        right_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        right_controls.set_valign(Gtk.Align.CENTER)

        # Zoom Slider Box
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        zoom_box.get_style_context().add_class("mac-zoom-control")
        zoom_box.pack_start(get_image("zoom_out", 12, "#86868b"), False, False, 2)

        self.zoom_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 110, 280, 10)
        self.zoom_slider.set_value(self.library_mgr.zoom_size)
        self.zoom_slider.set_size_request(90, 20)
        self.zoom_slider.set_draw_value(False)
        self.zoom_slider.connect("value-changed", self._on_zoom_changed)
        zoom_box.pack_start(self.zoom_slider, False, False, 0)
        zoom_box.pack_start(get_image("zoom_in", 12, "#86868b"), False, False, 2)
        right_controls.pack_start(zoom_box, False, False, 0)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(t("photos_search_placeholder"))
        self.search_entry.set_size_request(210, -1)
        self.search_entry.get_style_context().add_class("mac-search-entry")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("changed", self._on_search_changed)
        right_controls.pack_start(self.search_entry, False, False, 0)

        # Slideshow Button
        self.btn_slideshow = Gtk.Button()
        self.btn_slideshow.set_valign(Gtk.Align.CENTER)
        self.btn_slideshow.set_size_request(32, 32)
        self.btn_slideshow.get_style_context().add_class("mac-tool-btn")
        self.btn_slideshow.set_tooltip_text(t("photos_slideshow"))
        self.btn_slideshow.add(get_image("slideshow", 16, "#6e6e73"))
        self.btn_slideshow.connect("clicked", lambda _: self._start_slideshow_from_first())
        right_controls.pack_start(self.btn_slideshow, False, False, 0)

        # Select Mode Button ("Chọn")
        self.btn_select = Gtk.Button(label=t("photos_select"))
        self.btn_select.get_style_context().add_class("mac-select-mode-btn")
        self.btn_select.set_tooltip_text("Chọn nhiều ảnh để thao tác hoặc xóa (Multi-Select)")
        self.btn_select.connect("clicked", lambda _: self.toggle_select_mode())
        right_controls.pack_start(self.btn_select, False, False, 0)

        # Refresh / Rescan Button
        self.btn_refresh = Gtk.Button()
        self.btn_refresh.set_valign(Gtk.Align.CENTER)
        self.btn_refresh.set_size_request(32, 32)
        self.btn_refresh.get_style_context().add_class("mac-tool-btn")
        self.btn_refresh.set_tooltip_text("Làm mới & quét lại thư viện")
        self.btn_refresh.add(get_image("refresh", 15, "#6e6e73"))
        self.btn_refresh.connect("clicked", lambda _: self.library_mgr.start_scan(force=True))
        right_controls.pack_start(self.btn_refresh, False, False, 0)

        # Info Inspector Toggle Button
        self.btn_inspector = Gtk.Button()
        self.btn_inspector.set_valign(Gtk.Align.CENTER)
        self.btn_inspector.set_size_request(32, 32)
        self.btn_inspector.get_style_context().add_class("mac-tool-btn")
        self.btn_inspector.set_tooltip_text("Thông tin chi tiết (EXIF / Video Specs)")
        self.btn_inspector.add(get_image("info", 16, "#6e6e73"))
        self.btn_inspector.connect("clicked", lambda _: self.toggle_inspector())
        right_controls.pack_start(self.btn_inspector, False, False, 4)

        self.toolbar.pack_end(right_controls, False, False, 16)

        # -------------------------------------------------------------
        # 2. MAIN BODY (SIDEBAR + GALLERY + INSPECTOR)
        # -------------------------------------------------------------
        self.body_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.root_card.pack_start(self.body_box, True, True, 0)

        # Sidebar (Left)
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_box.set_size_request(230, -1)
        self.sidebar_box.get_style_context().add_class("mac-photos-sidebar")
        self.body_box.pack_start(self.sidebar_box, False, False, 0)
        self._build_sidebar_content()

        # Center Gallery Pane
        self.gallery_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.gallery_container.get_style_context().add_class("mac-gallery-container")
        self.body_box.pack_start(self.gallery_container, True, True, 0)

        # Scrolled FlowBox inside an Overlay for floating action bar
        self.gallery_overlay = Gtk.Overlay()
        self.gallery_container.pack_start(self.gallery_overlay, True, True, 0)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.get_vadjustment().connect("value-changed", self._on_scroll_value_changed)
        self.gallery_overlay.add(self.scrolled_window)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(30)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_column_spacing(12)
        self.flowbox.set_row_spacing(12)
        self.flowbox.set_margin_start(20)
        self.flowbox.set_margin_end(20)
        self.flowbox.set_margin_top(16)
        self.flowbox.set_margin_bottom(24)
        self.flowbox.get_style_context().add_class("mac-photo-flowbox")
        self.flowbox.connect("child-activated", self._on_flowbox_child_activated)
        self.scrolled_window.add(self.flowbox)

        # Floating Selection Action Bar (macOS style glass pill)
        self.select_action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.select_action_bar.get_style_context().add_class("mac-select-action-bar")
        self.select_action_bar.set_halign(Gtk.Align.CENTER)
        self.select_action_bar.set_valign(Gtk.Align.END)
        self.select_action_bar.set_margin_bottom(22)
        self.select_action_bar.set_no_show_all(True)

        self.selected_count_lbl = Gtk.Label(label="Chưa chọn mục nào")
        self.selected_count_lbl.get_style_context().add_class("selected-count-label")
        self.select_action_bar.pack_start(self.selected_count_lbl, False, False, 4)

        # Select All Button with Vector Check Icon
        self.btn_select_all = Gtk.Button()
        self.btn_select_all.get_style_context().add_class("mac-action-pill-btn")
        box_sel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.icon_select_all = get_image("check", 14, "#007aff")
        box_sel.pack_start(self.icon_select_all, False, False, 0)
        self.lbl_select_all = Gtk.Label(label="Chọn tất cả")
        box_sel.pack_start(self.lbl_select_all, False, False, 0)
        self.btn_select_all.add(box_sel)
        self.btn_select_all.connect("clicked", lambda _: self.select_all_photos())
        self.select_action_bar.pack_start(self.btn_select_all, False, False, 0)

        # Favorite Selected Button with Vector Heart Icon
        self.btn_fav_selected = Gtk.Button()
        self.btn_fav_selected.get_style_context().add_class("mac-action-pill-btn")
        box_fav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.icon_fav_selected = get_image("heart_filled", 14, "#ff2d55")
        box_fav.pack_start(self.icon_fav_selected, False, False, 0)
        self.lbl_fav_selected = Gtk.Label(label="Yêu thích")
        box_fav.pack_start(self.lbl_fav_selected, False, False, 0)
        self.btn_fav_selected.add(box_fav)
        self.btn_fav_selected.connect("clicked", lambda _: self.favorite_selected_photos())
        self.select_action_bar.pack_start(self.btn_fav_selected, False, False, 0)

        # Share Selected via AirDrop Button
        self.btn_airdrop_selected = Gtk.Button()
        self.btn_airdrop_selected.get_style_context().add_class("mac-action-pill-btn")
        box_air = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box_air.pack_start(get_image("share", 14, "#007aff"), False, False, 0)
        lbl_air = Gtk.Label(label="Gửi qua AirDrop")
        box_air.pack_start(lbl_air, False, False, 0)
        self.btn_airdrop_selected.add(box_air)
        self.btn_airdrop_selected.connect("clicked", lambda _: self._share_via_airdrop(list(self.selected_photos)))
        self.select_action_bar.pack_start(self.btn_airdrop_selected, False, False, 0)

        # Delete Selected Button with Vector Trash Can Icon
        self.btn_delete_selected = Gtk.Button()
        self.btn_delete_selected.get_style_context().add_class("mac-btn-danger")
        box_del = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.icon_delete_selected = get_image("trash", 14, "#ffffff")
        box_del.pack_start(self.icon_delete_selected, False, False, 0)
        self.lbl_delete_selected = Gtk.Label(label="Xóa đã chọn")
        box_del.pack_start(self.lbl_delete_selected, False, False, 0)
        self.btn_delete_selected.add(box_del)
        self.btn_delete_selected.connect("clicked", lambda _: self.delete_selected_photos())
        self.select_action_bar.pack_start(self.btn_delete_selected, False, False, 0)

        self.gallery_overlay.add_overlay(self.select_action_bar)
        self.select_action_bar.show_all()
        self.select_action_bar.hide()

        # Inspector Panel (Right)
        self.inspector_panel = InspectorPanel(
            on_set_wallpaper=self._set_wallpaper_action,
            on_reveal=self._reveal_action,
            on_close=self.toggle_inspector
        )
        self.inspector_panel.set_no_show_all(True)
        self.body_box.pack_start(self.inspector_panel, False, False, 0)
        self.inspector_panel.hide()

        # -------------------------------------------------------------
        # 3. FULLSCREEN LIGHTBOX OVERLAY
        # -------------------------------------------------------------
        self.lightbox = LightboxViewer(
            on_close=self._on_lightbox_closed,
            on_toggle_fav=self._toggle_favorite_action,
            on_set_wallpaper=self._set_wallpaper_action,
            on_trash=self._trash_action,
            on_rotate=self._rotate_action,
            on_reveal=self._reveal_action,
            on_select_picker=lambda photo: self._confirm_picker_selection(photo.path if photo else None),
            on_airdrop=self._share_via_airdrop,
            on_photo_edited=self._on_photo_edited_action,
        )
        self.lightbox.set_no_show_all(True)
        self.master_overlay.add_overlay(self.lightbox)
        self.lightbox.hide()

    def _build_sidebar_content(self):
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar_box.pack_start(sidebar_scroll, True, True, 0)

        self.sidebar_nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.sidebar_nav_box.set_margin_start(10)
        self.sidebar_nav_box.set_margin_end(10)
        self.sidebar_nav_box.set_margin_top(8)
        self.sidebar_nav_box.set_margin_bottom(12)
        sidebar_scroll.add(self.sidebar_nav_box)

        self._sidebar_buttons = {}

        # Section 1: Thư viện (Library)
        self._add_sidebar_section_header(t("photos_library").upper())
        self._add_sidebar_nav_item("all", t("photos_all"), "photos")
        self._add_sidebar_nav_item("videos", t("photos_videos"), "film")
        self._add_sidebar_nav_item("recent", t("photos_recents"), "clock")
        self._add_sidebar_nav_item("favorites", t("photos_favorites"), "heart")
        self._add_sidebar_nav_item("screenshots", t("photos_screenshots"), "screenshot")
        self._add_sidebar_nav_item("downloads", t("photos_downloads"), "download")

        # Section 2: Thư mục trên máy
        sec_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sec_header.set_margin_top(14)
        sec_header.set_margin_bottom(4)
        sec_header.set_margin_start(8)

        lbl = Gtk.Label(label=t("photos_local_folders").upper())
        lbl.get_style_context().add_class("sidebar-section-hdr")
        sec_header.pack_start(lbl, True, True, 0)

        btn_add_folder = Gtk.Button()
        btn_add_folder.get_style_context().add_class("sidebar-add-folder-btn")
        btn_add_folder.set_tooltip_text(t("photos_add_folder_tooltip"))
        btn_add_folder.add(get_image("plus", 12, "#86868b"))
        btn_add_folder.connect("clicked", lambda _: self._open_add_folder_dialog())
        sec_header.pack_end(btn_add_folder, False, False, 4)
        self.sidebar_nav_box.pack_start(sec_header, False, False, 0)

        self.folders_nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.sidebar_nav_box.pack_start(self.folders_nav_box, False, False, 0)

        # Section 3: Định dạng
        self._add_sidebar_section_header(t("photos_media_types").upper())
        self.formats_nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.sidebar_nav_box.pack_start(self.formats_nav_box, False, False, 0)

        # Section 4: Thùng rác
        self._add_sidebar_section_header(t("photos_utilities").upper())
        self._add_sidebar_nav_item("trash", t("photos_trash"), "trash")

        # Sidebar Bottom Status Bar
        self.sidebar_status_bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.sidebar_status_bar.get_style_context().add_class("sidebar-status-bar")
        self.sidebar_status_bar.set_margin_start(12)
        self.sidebar_status_bar.set_margin_end(12)
        self.sidebar_status_bar.set_margin_bottom(10)

        self.stat_count_lbl = Gtk.Label(label="0 mục")
        self.stat_count_lbl.get_style_context().add_class("sidebar-stat-count")
        self.stat_count_lbl.set_xalign(0.0)

        self.stat_size_lbl = Gtk.Label(label="0 MB")
        self.stat_size_lbl.get_style_context().add_class("sidebar-stat-size")
        self.stat_size_lbl.set_xalign(0.0)

        self.sidebar_status_bar.pack_start(self.stat_count_lbl, False, False, 0)
        self.sidebar_status_bar.pack_start(self.stat_size_lbl, False, False, 0)
        self.sidebar_box.pack_end(self.sidebar_status_bar, False, False, 0)

        # Highlight default category
        self._highlight_sidebar_item("all")

    def _add_sidebar_section_header(self, text: str):
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class("sidebar-section-hdr")
        lbl.set_xalign(0.0)
        lbl.set_margin_top(14)
        lbl.set_margin_bottom(4)
        lbl.set_margin_start(8)
        self.sidebar_nav_box.pack_start(lbl, False, False, 0)

    def _add_sidebar_nav_item(self, key: str, title: str, icon_name: str):
        btn = Gtk.Button()
        btn.get_style_context().add_class("mac-sidebar-item")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(6)
        row.set_margin_end(6)
        row.set_margin_top(5)
        row.set_margin_bottom(5)

        icon = get_image(icon_name, 16, "#007aff" if key == "all" else "#6e6e73")
        row.pack_start(icon, False, False, 0)

        lbl = Gtk.Label(label=title)
        lbl.get_style_context().add_class("sidebar-item-label")
        lbl.set_xalign(0.0)
        row.pack_start(lbl, True, True, 0)

        badge = Gtk.Label(label="")
        badge.get_style_context().add_class("sidebar-item-badge")
        row.pack_end(badge, False, False, 0)

        btn.add(row)
        btn.connect("clicked", lambda _: self.select_category(key))
        self.sidebar_nav_box.pack_start(btn, False, False, 0)

        self._sidebar_buttons[key] = (btn, badge, icon, key)

    def _highlight_sidebar_item(self, target_key: str):
        for k, (btn, badge, icon, _) in self._sidebar_buttons.items():
            if k == target_key:
                btn.get_style_context().add_class("active")
            else:
                btn.get_style_context().remove_class("active")

    # -------------------------------------------------------------------------
    # FILTERING & GALLERY POPULATION
    # -------------------------------------------------------------------------
    def select_category(self, category_key: str, folder_path: Optional[str] = None, format_name: Optional[str] = None):
        self.current_category = category_key
        self.current_folder_filter = folder_path
        self.current_format_filter = format_name
        self._highlight_sidebar_item(category_key)
        self.refresh_gallery(reset_scroll=True)

    def refresh_gallery(self, reset_scroll: bool = True):
        all_photos = self.library_mgr.photos
        filtered = []

        q = self.search_query.strip().lower()

        for p in all_photos:
            # Search filter
            if q and (q not in p.filename.lower() and q not in p.folder_name.lower() and q not in p.format_name.lower() and q not in p.date_str.lower()):
                continue

            # Category filter
            if self.current_category == "all":
                filtered.append(p)
            elif self.current_category == "videos":
                if p.is_video:
                    filtered.append(p)
            elif self.current_category == "recent":
                # Last 14 days
                if (datetime.now() - p.date_obj).days <= 14:
                    filtered.append(p)
            elif self.current_category == "favorites":
                if p.is_favorite:
                    filtered.append(p)
            elif self.current_category == "screenshots":
                if p.is_screenshot:
                    filtered.append(p)
            elif self.current_category == "downloads":
                if "download" in p.folder.lower():
                    filtered.append(p)
            elif self.current_category.startswith("folder:"):
                if p.folder == self.current_folder_filter:
                    filtered.append(p)
            elif self.current_category.startswith("format:"):
                if p.format_name == self.current_format_filter:
                    filtered.append(p)

        self.displayed_photos = filtered
        self._loaded_batch_count = 0

        # Update headers
        title_map = {
            "all": t("photos_all"),
            "videos": t("photos_videos"),
            "recent": t("photos_recents"),
            "favorites": t("photos_favorites"),
            "screenshots": t("photos_screenshots"),
            "downloads": t("photos_downloads"),
            "trash": t("photos_trash"),
        }
        if self.current_folder_filter:
            disp_title = os.path.basename(self.current_folder_filter)
        elif self.current_format_filter:
            disp_title = f"{t('photos_media_types')}: {self.current_format_filter}"
        else:
            disp_title = title_map.get(self.current_category, t("photos_library"))

        self.title_lbl.set_text(disp_title)

        v_count = sum(1 for p in filtered if p.is_video)
        img_count = len(filtered) - v_count
        if v_count > 0 and img_count > 0:
            count_info = f"{len(filtered)} mục ({img_count} ảnh, {v_count} video)"
        elif v_count > 0:
            count_info = f"{v_count} video"
        else:
            count_info = f"{img_count} ảnh"
        self.subtitle_lbl.set_text(f"{count_info} • Phong cách macOS Sequoia")

        # Clear FlowBox
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)

        # Load first batch
        self._load_next_batch()

        if reset_scroll:
            adj = self.scrolled_window.get_vadjustment()
            adj.set_value(adj.get_lower())

    def _load_next_batch(self):
        start = self._loaded_batch_count
        end = min(len(self.displayed_photos), start + self._batch_size)
        if start >= end:
            return

        target_size = int(self.zoom_slider.get_value())

        for idx in range(start, end):
            photo = self.displayed_photos[idx]
            card = PhotoCardWidget(
                photo_item=photo,
                target_size=target_size,
                on_open_lightbox=self._open_lightbox_action,
                on_toggle_fav=self._toggle_favorite_action,
                on_context_menu=self._show_context_menu,
                on_toggle_select=self._on_toggle_select,
                is_select_mode=self._is_select_mode,
                is_selected=(photo.path in self.selected_photos),
                on_picker_select=self._on_picker_select_photo,
                on_picker_confirm=self._on_picker_confirm_photo,
                is_picker_mode=self.picker_mode
            )
            self.flowbox.add(card)

        self._loaded_batch_count = end
        self.flowbox.show_all()

    def _on_scroll_value_changed(self, adj: Gtk.Adjustment):
        if adj.get_value() + adj.get_page_size() >= adj.get_upper() * 0.75:
            if self._loaded_batch_count < len(self.displayed_photos):
                self._load_next_batch()

    def _on_flowbox_child_activated(self, flowbox, child):
        card = child.get_child()
        if isinstance(card, PhotoCardWidget):
            if self._is_select_mode:
                self._on_toggle_select(card.photo_item)
            else:
                self.selected_photo = card.photo_item
                if self._is_inspector_visible:
                    self.inspector_panel.set_photo(self.selected_photo)
                self._open_lightbox_action(card.photo_item)

    def _on_zoom_changed(self, scale):
        new_size = int(scale.get_value())
        self.library_mgr.zoom_size = new_size
        self.library_mgr.save_config()

        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget):
                card.set_size_request(new_size, new_size)
                card.img_box.set_size_request(new_size, new_size)
                card.thumb_draw.set_size_request(new_size, new_size)

    def toggle_select_mode(self, force_off=False):
        if force_off or self._is_select_mode:
            self._is_select_mode = False
            self.selected_photos.clear()
            self.btn_select.set_label("Chọn")
            self.btn_select.get_style_context().remove_class("active")
            self.select_action_bar.hide()
            self.select_action_bar.set_no_show_all(True)
        else:
            self._is_select_mode = True
            self.btn_select.set_label("Xong")
            self.btn_select.get_style_context().add_class("active")
            self.select_action_bar.set_no_show_all(False)
            self.select_action_bar.show_all()
            self._update_select_action_bar()

        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget):
                card.set_select_mode(self._is_select_mode)
                card.set_selected(card.photo_item.path in self.selected_photos)

    def _on_toggle_select(self, photo: PhotoItem):
        if photo.path in self.selected_photos:
            self.selected_photos.remove(photo.path)
        else:
            self.selected_photos.add(photo.path)

        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget) and card.photo_item.path == photo.path:
                card.set_selected(photo.path in self.selected_photos)
                break

        self._update_select_action_bar()

    def _update_select_action_bar(self):
        count = len(self.selected_photos)
        if count == 0:
            self.selected_count_lbl.set_text("Chưa chọn mục nào")
            self.btn_delete_selected.set_sensitive(False)
            self.btn_fav_selected.set_sensitive(False)
            self.lbl_select_all.set_text("Chọn tất cả")
            self.lbl_delete_selected.set_text("Xóa đã chọn")
            self.lbl_fav_selected.set_text("Yêu thích")
            pb_fav = get_pixbuf("heart_filled", 14, "#ff2d55")
            if pb_fav:
                self.icon_fav_selected.set_from_pixbuf(pb_fav)
        else:
            self.selected_count_lbl.set_text(f"Đã chọn {count} mục")
            self.btn_delete_selected.set_sensitive(True)
            self.btn_fav_selected.set_sensitive(True)
            self.lbl_delete_selected.set_text(f"Xóa {count} mục")

            fav_items = [self.library_mgr.photos_by_path.get(p) for p in self.selected_photos if self.library_mgr.photos_by_path.get(p)]
            all_fav = len(fav_items) > 0 and all(item.is_favorite for item in fav_items)

            if all_fav:
                self.lbl_fav_selected.set_text("Bỏ thích")
                pb_fav = get_pixbuf("heart", 14, "#8e8e93")
                if pb_fav:
                    self.icon_fav_selected.set_from_pixbuf(pb_fav)
            else:
                self.lbl_fav_selected.set_text("Yêu thích")
                pb_fav = get_pixbuf("heart_filled", 14, "#ff2d55")
                if pb_fav:
                    self.icon_fav_selected.set_from_pixbuf(pb_fav)

            if count == len(self.displayed_photos) and len(self.displayed_photos) > 0:
                self.lbl_select_all.set_text("Bỏ chọn tất cả")
            else:
                self.lbl_select_all.set_text("Chọn tất cả")

    def select_all_photos(self):
        if len(self.selected_photos) == len(self.displayed_photos) and len(self.displayed_photos) > 0:
            self.selected_photos.clear()
        else:
            self.selected_photos = {p.path for p in self.displayed_photos}

        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget):
                card.set_selected(card.photo_item.path in self.selected_photos)

        self._update_select_action_bar()

    def favorite_selected_photos(self):
        if not self.selected_photos:
            return
        fav_count = 0
        for p in self.selected_photos:
            item = self.library_mgr.photos_by_path.get(p)
            if item and not item.is_favorite:
                self.library_mgr.toggle_favorite(p)
                fav_count += 1
        self._show_toast(f"Đã thêm {fav_count} mục vào Yêu thích")
        self.toggle_select_mode(force_off=True)
        self.refresh_gallery(reset_scroll=False)

    def delete_selected_photos(self):
        if not self.selected_photos:
            self._show_toast("Vui lòng chọn ít nhất 1 ảnh để xóa")
            return

        count = len(self.selected_photos)
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Xóa các mục đã chọn?"
        )
        dialog.format_secondary_text(
            f"Bạn có chắc chắn muốn chuyển {count} ảnh/video đã chọn vào Thùng rác không?\n"
            "Các tệp này có thể được khôi phục từ Thùng rác hệ thống."
        )
        dialog.add_button("Hủy", Gtk.ResponseType.CANCEL)
        del_btn = dialog.add_button(f"Xóa {count} mục", Gtk.ResponseType.OK)
        del_btn.get_style_context().add_class("destructive-action")

        res = dialog.run()
        dialog.destroy()

        if res == Gtk.ResponseType.OK:
            paths = list(self.selected_photos)
            deleted_count = 0
            for p in paths:
                if self.library_mgr.move_to_trash(p):
                    deleted_count += 1

            try:
                from src.modules.sound import SoundManager
                SoundManager.get_instance().play_trash()
            except Exception:
                pass

            self.selected_photos.clear()
            self.toggle_select_mode(force_off=True)
            self.refresh_gallery(reset_scroll=False)
            self._show_toast(f"Đã chuyển {deleted_count} mục vào Thùng rác")

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text()
        self.refresh_gallery(reset_scroll=True)

    # -------------------------------------------------------------------------
    # LIBRARY & SCANNER EVENT LISTENER
    # -------------------------------------------------------------------------
    def _on_library_event(self, event_type: str, *args):
        if event_type in ("scan_started", "photos_batch_added"):
            self._update_sidebar_counts()
            if self.current_category == "all" and self._loaded_batch_count < 30:
                self.refresh_gallery(reset_scroll=False)
        elif event_type == "scan_finished":
            self._update_sidebar_counts()
            self._rebuild_folders_and_formats_sidebar()
            self.refresh_gallery(reset_scroll=False)
        elif event_type in ("photo_deleted", "photo_rotated", "favorite_changed"):
            self._update_sidebar_counts()
            self.refresh_gallery(reset_scroll=False)

    def _update_sidebar_counts(self):
        photos = self.library_mgr.photos
        total_count = len(photos)
        video_count = sum(1 for p in photos if p.is_video)
        photo_count = total_count - video_count
        total_bytes = sum(p.size_bytes for p in photos)

        self.stat_count_lbl.set_text(f"{total_count} mục ({photo_count} ảnh, {video_count} video)")
        self.stat_size_lbl.set_text(format_file_size(total_bytes))

        # Library section badges
        recent_count = sum(1 for p in photos if (datetime.now() - p.date_obj).days <= 14)
        fav_count = len(self.library_mgr.favorites)
        ss_count = sum(1 for p in photos if p.is_screenshot)
        dl_count = sum(1 for p in photos if "download" in p.folder.lower())

        badges_map = {
            "all": total_count,
            "videos": video_count,
            "recent": recent_count,
            "favorites": fav_count,
            "screenshots": ss_count,
            "downloads": dl_count,
        }
        for k, count in badges_map.items():
            if k in self._sidebar_buttons:
                _, badge, _, _ = self._sidebar_buttons[k]
                badge.set_text(str(count) if count > 0 else "")

    def _rebuild_folders_and_formats_sidebar(self):
        # 1. Folders
        for c in self.folders_nav_box.get_children():
            self.folders_nav_box.remove(c)

        folder_counts = {}
        for p in self.library_mgr.photos:
            folder_counts[p.folder] = folder_counts.get(p.folder, 0) + 1

        for fpath, cnt in sorted(folder_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            fname = os.path.basename(fpath) or fpath
            key = f"folder:{fpath}"
            self._add_folder_sidebar_item(key, fname, fpath, cnt)

        # 2. Formats
        for c in self.formats_nav_box.get_children():
            self.formats_nav_box.remove(c)

        format_counts = {}
        for p in self.library_mgr.photos:
            format_counts[p.format_name] = format_counts.get(p.format_name, 0) + 1

        for fmt, cnt in sorted(format_counts.items(), key=lambda x: x[1], reverse=True):
            key = f"format:{fmt}"
            self._add_format_sidebar_item(key, fmt, cnt)

        self.sidebar_nav_box.show_all()

    def _add_folder_sidebar_item(self, key: str, label_text: str, folder_path: str, count: int):
        btn = Gtk.Button()
        btn.get_style_context().add_class("mac-sidebar-item")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(6)
        row.set_margin_end(6)
        row.set_margin_top(5)
        row.set_margin_bottom(5)

        icon = get_image("folder", 15, "#007aff")
        row.pack_start(icon, False, False, 0)

        lbl = Gtk.Label(label=label_text)
        lbl.get_style_context().add_class("sidebar-item-label")
        lbl.set_xalign(0.0)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        row.pack_start(lbl, True, True, 0)

        badge = Gtk.Label(label=str(count))
        badge.get_style_context().add_class("sidebar-item-badge")
        row.pack_end(badge, False, False, 0)

        btn.add(row)
        btn.connect("clicked", lambda _: self.select_category(key, folder_path=folder_path))
        self.folders_nav_box.pack_start(btn, False, False, 0)
        self._sidebar_buttons[key] = (btn, badge, icon, key)

    def _add_format_sidebar_item(self, key: str, format_name: str, count: int):
        btn = Gtk.Button()
        btn.get_style_context().add_class("mac-sidebar-item")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(6)
        row.set_margin_end(6)
        row.set_margin_top(5)
        row.set_margin_bottom(5)

        # Different icon color for video formats
        is_vid = format_name in ("MP4", "MOV", "MKV", "WEBM", "AVI", "M4V", "FLV")
        icon_name = "film" if is_vid else "photos"
        icon_col = "#007aff" if is_vid else "#a855f7"

        icon = get_image(icon_name, 15, icon_col)
        row.pack_start(icon, False, False, 0)

        lbl = Gtk.Label(label=format_name)
        lbl.get_style_context().add_class("sidebar-item-label")
        lbl.set_xalign(0.0)
        row.pack_start(lbl, True, True, 0)

        badge = Gtk.Label(label=str(count))
        badge.get_style_context().add_class("sidebar-item-badge")
        row.pack_end(badge, False, False, 0)

        btn.add(row)
        btn.connect("clicked", lambda _: self.select_category(key, format_name=format_name))
        self.formats_nav_box.pack_start(btn, False, False, 0)
        self._sidebar_buttons[key] = (btn, badge, icon, key)

    def _open_add_folder_dialog(self):
        dlg = Gtk.FileChooserDialog(
            title="Chọn thư mục ảnh & video để quét",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dlg.add_button("Hủy", Gtk.ResponseType.CANCEL)
        dlg.add_button("Thêm thư mục", Gtk.ResponseType.OK)

        res = dlg.run()
        if res == Gtk.ResponseType.OK:
            chosen = dlg.get_filename()
            if chosen:
                self.library_mgr.add_custom_folder(chosen)
        dlg.destroy()

    # -------------------------------------------------------------------------
    # ACTIONS: LIGHTBOX, INSPECTOR, WALLPAPER, TRASH
    # -------------------------------------------------------------------------
    def _open_lightbox_action(self, photo_item: PhotoItem):
        self.selected_photo = photo_item
        self.lightbox.open_photo(photo_item, self.displayed_photos)

    def _start_slideshow_from_first(self):
        if self.displayed_photos:
            photo = self.selected_photo or self.displayed_photos[0]
            self.lightbox.open_photo(photo, self.displayed_photos)
            self.lightbox.toggle_slideshow()

    def _on_lightbox_closed(self):
        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget):
                card.update_favorite_state()

    def toggle_sidebar(self):
        self._is_sidebar_visible = not self._is_sidebar_visible
        if self._is_sidebar_visible:
            self.sidebar_box.show()
        else:
            self.sidebar_box.hide()

    def toggle_inspector(self):
        self._is_inspector_visible = not self._is_inspector_visible
        if self._is_inspector_visible:
            if self.selected_photo or self.displayed_photos:
                photo = self.selected_photo or self.displayed_photos[0]
                self.inspector_panel.set_photo(photo)
            self.inspector_panel.set_no_show_all(False)
            self.inspector_panel.show_all()
            self.inspector_panel.set_no_show_all(True)
            self.btn_inspector.get_style_context().add_class("active")
        else:
            self.inspector_panel.hide()
            self.btn_inspector.get_style_context().remove_class("active")

    def _toggle_favorite_action(self, photo: PhotoItem):
        self.library_mgr.toggle_favorite(photo.path)
        self._update_sidebar_counts()

    def _set_wallpaper_action(self, photo: PhotoItem):
        if photo.is_video:
            self._show_toast("Không thể đặt video làm hình nền Desktop tĩnh")
            return
        ok = self.library_mgr.set_as_desktop_wallpaper(photo.path)
        self._show_toast("Đã đặt làm hình nền Desktop!" if ok else "Không thể đặt hình nền")

    def _trash_action(self, photo: PhotoItem):
        self.library_mgr.move_to_trash(photo.path)
        self.refresh_gallery(reset_scroll=False)
        self._show_toast(f"Đã chuyển '{photo.filename}' vào Thùng rác")

    def _rotate_action(self, photo: PhotoItem):
        if photo.is_video:
            self._show_toast("Chưa hỗ trợ xoay video trực tiếp")
            return
        self.library_mgr.rotate_photo(photo.path, 90)
        self.refresh_gallery(reset_scroll=False)
        self._show_toast("Đã xoay ảnh 90°")

    def _open_photo_editor_action(self, photo: PhotoItem):
        self._open_lightbox_action(photo)
        self.lightbox.enter_edit_mode()

    def _on_photo_edited_action(self, photo: PhotoItem):
        try:
            stat = os.stat(photo.path)
            photo.mtime = stat.st_mtime
            photo.size_bytes = stat.st_size
        except Exception as e:
            print(f"[Photos] Error updating photo stat after edit: {e}")
        self.refresh_gallery(reset_scroll=False)
        self._show_toast(f"Đã cập nhật chỉnh sửa cho '{photo.filename}'")

    def _reveal_action(self, photo: PhotoItem):
        self.library_mgr.reveal_in_file_manager(photo.path)

    def _show_context_menu(self, photo: PhotoItem, event):
        menu = Gtk.Menu()
        menu.get_style_context().add_class("mac-context-menu")

        def add_item(label_text, cb):
            item = Gtk.MenuItem(label=label_text)
            item.connect("activate", lambda _: cb())
            menu.append(item)

        if getattr(self, "picker_mode", False):
            add_item("✓ Sử dụng ảnh này", lambda: self._confirm_picker_selection(photo.path))
            menu.append(Gtk.SeparatorMenuItem())

        view_label = "Phát video (Lightbox)" if photo.is_video else "Xem chi tiết (Lightbox)"
        add_item(view_label, lambda: self._open_lightbox_action(photo))

        if not photo.is_video:
            add_item("Sửa ảnh như macOS (Edit)...", lambda: self._open_photo_editor_action(photo))

        add_item("Chia sẻ qua AirDrop…", lambda: self._share_via_airdrop(photo))

        if not photo.is_video:
            add_item("Đặt làm hình nền Desktop", lambda: self._set_wallpaper_action(photo))

        fav_label = "Xóa khỏi Mục yêu thích" if photo.is_favorite else "Thêm vào Mục yêu thích"
        add_item(fav_label, lambda: self._toggle_favorite_action(photo))

        if not photo.is_video:
            add_item("Xoay 90° sang phải", lambda: self._rotate_action(photo))

        info_lbl = "Xem thông số video" if photo.is_video else "Xem thông số kỹ thuật (EXIF)"
        add_item(info_lbl, lambda: [self.inspector_panel.set_photo(photo), self.toggle_inspector() if not self._is_inspector_visible else None])

        menu.append(Gtk.SeparatorMenuItem())
        add_item("Hiện trong Thư mục (Files)", lambda: self._reveal_action(photo))
        add_item("Mở bằng Trình xem mặc định", lambda: self.library_mgr.open_with_default_viewer(photo.path))

        def copy_path():
            clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clip.set_text(photo.path, -1)
            self._show_toast("Đã sao chép đường dẫn")

        add_item("Sao chép đường dẫn", copy_path)

        menu.append(Gtk.SeparatorMenuItem())
        add_item("Chuyển vào Thùng rác", lambda: self._trash_action(photo))

        menu.show_all()
        menu.popup_at_pointer(event)

    def _show_toast(self, message: str):
        self.subtitle_lbl.set_text(message)
        GLib.timeout_add(3000, lambda: self.subtitle_lbl.set_text(f"{len(self.displayed_photos)} mục • Phong cách macOS Sequoia"))

    # -------------------------------------------------------------------------
    # PHOTO PICKER MODE & AIRDROP INTEGRATION
    # -------------------------------------------------------------------------
    @classmethod
    def open_picker(cls, title="Chọn ảnh", on_photo_selected=None, parent=None):
        w = cls.get_instance()
        w.set_picker_mode(True, title=title, callback=on_photo_selected)
        if parent and isinstance(parent, Gtk.Window):
            try:
                w.set_transient_for(parent)
            except Exception:
                pass
        w.show_all()
        w.lightbox.hide()
        w.inspector_panel.hide()
        w.select_action_bar.hide()
        w.present()
        return w

    def set_picker_mode(self, enabled: bool, title: str = "Chọn ảnh", callback=None):
        self.picker_mode = enabled
        self.picker_callback = callback
        self.picker_title = title

        if enabled:
            self.picker_title_lbl.set_text(title)
            self.picker_sub_lbl.set_text("Nhấp chọn một ảnh rồi bấm 'Sử dụng ảnh này', hoặc nhấp đúp để chọn ngay.")
            self.btn_picker_confirm.set_sensitive(bool(self.selected_photo))
            self.picker_banner.show_all()
            self.lightbox.set_picker_mode(True)
            self.title_lbl.set_text(f"Bộ chọn ảnh: {title}")
        else:
            self.picker_banner.hide()
            self.lightbox.set_picker_mode(False)
            self.picker_callback = None
            self.title_lbl.set_text("Tất cả ảnh & video")

        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget):
                card.set_picker_mode(enabled)
                if not enabled:
                    card.set_selected(False)

    def _on_picker_select_photo(self, photo: PhotoItem):
        self.selected_photo = photo
        for child in self.flowbox.get_children():
            card = child.get_child()
            if isinstance(card, PhotoCardWidget):
                card.set_selected(card.photo_item.path == photo.path)
        self.btn_picker_confirm.set_sensitive(True)
        self.picker_sub_lbl.set_text(f"Đã chọn: {photo.filename} ({photo.formatted_size}) • Bấm 'Sử dụng ảnh này' hoặc nhấp đúp để xác nhận.")

    def _on_picker_confirm_photo(self, photo: PhotoItem):
        self._confirm_picker_selection(photo.path)

    def _confirm_picker_selection(self, chosen_path=None):
        path = chosen_path or (self.selected_photo.path if self.selected_photo else None)
        if not path:
            return
        cb = self.picker_callback
        self.set_picker_mode(False)
        self.close_window()
        if cb:
            cb(path)

    def _cancel_picker_mode(self):
        self.set_picker_mode(False)
        self.close_window()

    def _browse_fallback_file(self):
        dialog = Gtk.FileChooserDialog(
            title=getattr(self, "picker_title", "Chọn tệp ảnh"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        filt = Gtk.FileFilter()
        filt.set_name("Tất cả định dạng ảnh (*.png, *.jpg, *.jpeg, *.webp, *.svg)")
        filt.add_mime_type("image/png")
        filt.add_mime_type("image/jpeg")
        filt.add_mime_type("image/webp")
        filt.add_mime_type("image/svg+xml")
        filt.add_pattern("*.png")
        filt.add_pattern("*.jpg")
        filt.add_pattern("*.jpeg")
        filt.add_pattern("*.webp")
        filt.add_pattern("*.svg")
        dialog.add_filter(filt)

        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            chosen = dialog.get_filename()
            dialog.destroy()
            if chosen and os.path.exists(chosen):
                self._confirm_picker_selection(chosen)
        else:
            dialog.destroy()

    def _share_via_airdrop(self, photo_or_photos):
        try:
            from src.ui.macos_airdrop_window import MacOSAirDropWindow
            win = MacOSAirDropWindow.get_instance()
            if isinstance(photo_or_photos, PhotoItem):
                win.prepare_send_file(photo_or_photos.path)
            elif isinstance(photo_or_photos, str):
                win.prepare_send_file(photo_or_photos)
            elif isinstance(photo_or_photos, (list, set)):
                paths = [p if isinstance(p, str) else p.path for p in photo_or_photos]
                if paths:
                    win.prepare_send_file(paths[0])
            win.show_window()
        except Exception as e:
            print(f"[Photos] Error launching AirDrop: {e}")
            self._show_toast("Không thể mở AirDrop")

    # -------------------------------------------------------------------------
    # WINDOW CONTROLS & EVENTS
    # -------------------------------------------------------------------------
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
            self.queue_draw()
        elif self._is_maximized != is_max:
            self._is_maximized = is_max
            self.queue_draw()
        return False

    def _on_header_button_press(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self.toggle_maximize()
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    def toggle_maximize(self):
        if self._is_maximized:
            self.unmaximize()
            self._is_maximized = False
        else:
            self.maximize()
            self._is_maximized = True

    def close_window(self):
        self.lightbox.close_lightbox()
        self.hide()
        if getattr(self, "is_standalone", False):
            Gtk.main_quit()

    def _on_delete_event(self, *args):
        self.close_window()
        return True

    def _on_destroy_cleanup(self, *args):
        if MacOSPhotosWindow._instance is self:
            MacOSPhotosWindow._instance = None

    def _on_key_press(self, widget, event):
        keyval = event.keyval
        # Escape closes Lightbox, exits Edit Mode, Inspector or Select Mode
        if keyval == Gdk.KEY_Escape:
            if self.lightbox.get_visible():
                if self.lightbox.is_editing:
                    self.lightbox.exit_edit_mode(save=False)
                    return True
                self.lightbox.close_lightbox()
                return True
            elif self._is_select_mode:
                self.toggle_select_mode(force_off=True)
                return True
            elif self._is_inspector_visible:
                self.toggle_inspector()
                return True
        # Delete or Backspace in select mode deletes selected photos
        elif keyval in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
            if self._is_select_mode and self.selected_photos:
                self.delete_selected_photos()
                return True
        # Space or Enter
        elif keyval in (Gdk.KEY_space, Gdk.KEY_Return):
            if self.lightbox.get_visible():
                if self.lightbox.is_editing:
                    if keyval == Gdk.KEY_Return:
                        self.lightbox._on_save_done()
                        return True
                elif self.lightbox.current_photo and self.lightbox.current_photo.is_video:
                    self.lightbox.toggle_video_play_pause()
                    return True
            elif not self.lightbox.get_visible() and (self.selected_photo or self.displayed_photos):
                photo = self.selected_photo or self.displayed_photos[0]
                self._open_lightbox_action(photo)
                return True
        # Left / Right arrows (only when not editing)
        elif keyval == Gdk.KEY_Left:
            if self.lightbox.get_visible() and not self.lightbox.is_editing:
                self.lightbox.prev_photo()
                return True
        elif keyval == Gdk.KEY_Right:
            if self.lightbox.get_visible() and not self.lightbox.is_editing:
                self.lightbox.next_photo()
                return True
        # 'E' edits photo in Lightbox
        elif keyval in (Gdk.KEY_e, Gdk.KEY_E):
            if not self.search_entry.has_focus() and self.lightbox.get_visible():
                if not self.lightbox.is_editing:
                    self.lightbox.enter_edit_mode()
                    return True
        # 'I' toggles Inspector
        elif keyval in (Gdk.KEY_i, Gdk.KEY_I):
            if not self.search_entry.has_focus() and not self.lightbox.is_editing:
                self.toggle_inspector()
                return True
        # 'F' toggles Favorite
        elif keyval in (Gdk.KEY_f, Gdk.KEY_F):
            if not self.search_entry.has_focus():
                target = self.lightbox.current_photo if self.lightbox.get_visible() else self.selected_photo
                if target:
                    self._toggle_favorite_action(target)
                    return True
        # Delete moves to trash
        elif keyval in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
            if not self.search_entry.has_focus():
                target = self.lightbox.current_photo if self.lightbox.get_visible() else self.selected_photo
                if target:
                    self._trash_action(target)
                    return True
        # Ctrl+F focuses search
        if (event.state & Gdk.ModifierType.CONTROL_MASK) and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.search_entry.grab_focus()
            return True

        return False

    def _on_window_draw(self, widget, cr: cairo.Context):
        if getattr(self, "_is_iconified", False):
            return False
        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height
        r = 0.0 if getattr(self, "_is_maximized", False) else 16.0

        cr.save()
        if r > 0:
            cr.set_operator(cairo.Operator.CLEAR)
            cr.paint()
            cr.set_operator(cairo.Operator.OVER)
            cr.new_sub_path()
            cr.arc(w - r, r, r, -math.pi/2, 0)
            cr.arc(w - r, h - r, r, 0, math.pi/2)
            cr.arc(r, h - r, r, math.pi/2, math.pi)
            cr.arc(r, r, r, math.pi, 3*math.pi/2)
            cr.close_path()
            cr.clip()

        if self.is_dark:
            cr.set_source_rgb(0.12, 0.12, 0.13)
        else:
            cr.set_source_rgb(0.96, 0.96, 0.97)
        cr.paint()
        cr.restore()
        return False

    def apply_theme(self):
        self.is_dark = is_system_dark_mode()
        ctx = self.root_card.get_style_context()
        if self.is_dark:
            ctx.add_class("mac-dark")
            ctx.remove_class("mac-light")
        else:
            ctx.add_class("mac-light")
            ctx.remove_class("mac-dark")
        self.queue_draw()

    # -------------------------------------------------------------------------
    # STYLESHEET CSS
    # -------------------------------------------------------------------------
    def _load_css(self):
        if MacOSPhotosWindow._css_loaded:
            return
        MacOSPhotosWindow._css_loaded = True

        css = b"""
        /* ========================================================= */
        /* ROOT WINDOW & BACKGROUND                                  */
        /* ========================================================= */
        window {
            background-color: transparent;
        }
        .mac-photos-window {
            border-radius: 16px;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Ubuntu", sans-serif;
        }
        .mac-dark.mac-photos-window {
            background-color: #1e1e20;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
        }
        .mac-light.mac-photos-window {
            background-color: #f6f6f8;
            border: 1px solid rgba(0, 0, 0, 0.14);
            box-shadow: 0 24px 64px rgba(0, 0, 0, 0.22);
        }

        /* ========================================================= */
        /* PHOTO PICKER BANNER                                       */
        /* ========================================================= */
        .mac-photos-picker-banner {
            padding: 10px 18px;
            background: linear-gradient(135deg, rgba(0, 122, 255, 0.15), rgba(88, 86, 214, 0.10));
            border-bottom: 1px solid rgba(0, 122, 255, 0.25);
        }
        .mac-dark .mac-photos-picker-banner {
            background: linear-gradient(135deg, rgba(0, 122, 255, 0.22), rgba(30, 30, 40, 0.85));
            border-bottom: 1px solid rgba(0, 122, 255, 0.35);
        }
        .picker-banner-title {
            font-size: 14px;
            font-weight: 700;
            color: #007aff;
        }
        .mac-dark .picker-banner-title {
            color: #0a84ff;
        }
        .picker-banner-subtitle {
            font-size: 11px;
            color: #555558;
        }
        .mac-dark .picker-banner-subtitle {
            color: #a1a1a6;
        }
        .pill-picker-confirm-btn {
            background-color: #007aff;
            color: #ffffff;
            font-weight: 700;
        }

        /* ========================================================= */
        /* TOOLBAR                                                   */
        /* ========================================================= */
        .mac-photos-toolbar {
            padding: 8px 14px;
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        }
        .mac-dark .mac-photos-toolbar {
            background-color: #262629;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .mac-light .mac-photos-toolbar {
            background-color: #ededf0;
            border-bottom: 1px solid rgba(0, 0, 0, 0.08);
        }

        .mac-toolbar-title {
            font-size: 15px;
            font-weight: 700;
        }
        .mac-dark .mac-toolbar-title { color: #f5f5f7; }
        .mac-light .mac-toolbar-title { color: #1d1d1f; }

        .mac-toolbar-subtitle {
            font-size: 11px;
            font-weight: 500;
        }
        .mac-dark .mac-toolbar-subtitle { color: #86868b; }
        .mac-light .mac-toolbar-subtitle { color: #6e6e73; }

        .mac-tool-btn {
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 9999px;
            min-height: 32px;
            min-width: 32px;
            padding: 0;
            margin: 0;
            transition: all 150ms ease;
        }
        .mac-dark .mac-tool-btn {
            background-color: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.1);
        }
        .mac-dark .mac-tool-btn:hover {
            background-color: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .mac-light .mac-tool-btn {
            background-color: rgba(0, 0, 0, 0.04);
            border-color: rgba(0, 0, 0, 0.07);
        }
        .mac-light .mac-tool-btn:hover {
            background-color: rgba(0, 0, 0, 0.08);
            border-color: rgba(0, 0, 0, 0.12);
        }
        .mac-tool-btn.active {
            background-color: #007aff;
            border-color: #007aff;
            color: #ffffff;
        }

        .mac-zoom-control {
            padding: 2px 10px;
            border-radius: 9999px;
            border: 1px solid transparent;
        }
        .mac-dark .mac-zoom-control {
            background-color: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.08);
        }
        .mac-light .mac-zoom-control {
            background-color: rgba(0, 0, 0, 0.04);
            border-color: rgba(0, 0, 0, 0.06);
        }

        .mac-search-entry {
            border-radius: 9999px;
            padding: 4px 12px;
            font-size: 12px;
            border: none;
        }
        .mac-dark .mac-search-entry {
            background-color: #323236;
            color: #f5f5f7;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .mac-light .mac-search-entry {
            background-color: #ffffff;
            color: #1d1d1f;
            border: 1px solid rgba(0, 0, 0, 0.1);
        }

        /* Traffic Lights */
        .mac-traffic-light {
            border-radius: 9999px;
            min-width: 12px;
            min-height: 12px;
            padding: 0;
            margin: 0;
            border: none;
            box-shadow: none;
            outline: none;
        }
        .mac-traffic-light.tl-red { background-color: #ff5f56; border: 0.5px solid #e0443e; }
        .mac-traffic-light.tl-yellow { background-color: #ffbd2e; border: 0.5px solid #dea123; }
        .mac-traffic-light.tl-green { background-color: #27c93f; border: 0.5px solid #1aab29; }
        .tl-symbol {
            font-size: 7px;
            font-weight: 900;
            color: rgba(0, 0, 0, 0.65);
            padding: 0;
            margin: 0;
        }

        /* ========================================================= */
        /* SIDEBAR                                                   */
        /* ========================================================= */
        .mac-photos-sidebar {
            border-bottom-left-radius: 16px;
        }
        .mac-dark .mac-photos-sidebar {
            background-color: #232326;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        .mac-light .mac-photos-sidebar {
            background-color: #e8e8ed;
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }

        .sidebar-section-hdr {
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .mac-dark .sidebar-section-hdr { color: #86868b; }
        .mac-light .sidebar-section-hdr { color: #86868b; }

        .mac-sidebar-item {
            background: transparent;
            border: none;
            border-radius: 8px;
            padding: 2px 4px;
        }
        .mac-dark .mac-sidebar-item:hover { background-color: rgba(255, 255, 255, 0.07); }
        .mac-light .mac-sidebar-item:hover { background-color: rgba(0, 0, 0, 0.05); }

        .mac-sidebar-item.active {
            background-color: #007aff;
        }
        .mac-sidebar-item.active .sidebar-item-label,
        .mac-sidebar-item.active .sidebar-item-badge {
            color: #ffffff;
        }

        .sidebar-item-label {
            font-size: 13px;
            font-weight: 500;
        }
        .mac-dark .sidebar-item-label { color: #e2e8f0; }
        .mac-light .sidebar-item-label { color: #1d1d1f; }

        .sidebar-item-badge {
            font-size: 11px;
            font-weight: 600;
        }
        .mac-dark .sidebar-item-badge { color: #86868b; }
        .mac-light .sidebar-item-badge { color: #86868b; }

        .sidebar-add-folder-btn {
            background: transparent;
            border: none;
            border-radius: 4px;
            padding: 2px;
        }
        .sidebar-add-folder-btn:hover { background-color: rgba(255, 255, 255, 0.1); }

        .sidebar-status-bar {
            padding-top: 8px;
            border-top: 1px solid rgba(128, 128, 128, 0.15);
        }
        .sidebar-stat-count {
            font-size: 12px;
            font-weight: 700;
        }
        .mac-dark .sidebar-stat-count { color: #f5f5f7; }
        .mac-light .sidebar-stat-count { color: #1d1d1f; }
        .sidebar-stat-size {
            font-size: 10px;
            color: #86868b;
        }

        /* ========================================================= */
        /* GALLERY GRID & PHOTO / VIDEO CARDS                        */
        /* ========================================================= */
        .mac-gallery-container {
            border-bottom-right-radius: 16px;
        }
        .mac-dark .mac-gallery-container { background-color: #1a1a1c; }
        .mac-light .mac-gallery-container { background-color: #ffffff; }

        .mac-photo-card {
            border-radius: 12px;
            padding: 0;
            border: 2px solid transparent;
            transition: all 160ms ease;
        }
        .mac-dark .mac-photo-card {
            background-color: #262629;
            border: 2px solid rgba(255, 255, 255, 0.05);
        }
        .mac-light .mac-photo-card {
            background-color: #f5f5f7;
            border: 2px solid rgba(0, 0, 0, 0.06);
        }
        .mac-photo-card:hover {
            border-color: #007aff;
            box-shadow: 0 6px 18px rgba(0, 122, 255, 0.3);
        }
        .mac-photo-card.is-selected {
            border-color: #007aff;
            box-shadow: 0 0 0 2px #007aff, 0 6px 20px rgba(0, 122, 255, 0.35);
        }
        .mac-photo-card:focus, .mac-photo-card:active {
            border-color: #007aff;
        }

        .photo-thumb-container {
            border-radius: 12px;
        }

        /* Select Mode Button & Floating Action Bar */
        .mac-select-mode-btn {
            background-color: rgba(0, 0, 0, 0.06);
            color: #1d1d1f;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 14px;
            border-radius: 9999px;
            border: 1px solid rgba(0, 0, 0, 0.12);
            transition: all 150ms ease;
        }
        .mac-dark .mac-select-mode-btn {
            background-color: rgba(255, 255, 255, 0.12);
            color: #f5f5f7;
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        .mac-select-mode-btn:hover {
            background-color: rgba(0, 122, 255, 0.15);
            color: #007aff;
            border-color: rgba(0, 122, 255, 0.4);
        }
        .mac-select-mode-btn.active {
            background-color: #007aff;
            color: #ffffff;
            border-color: #007aff;
            box-shadow: 0 2px 8px rgba(0, 122, 255, 0.4);
        }

        .mac-dark .mac-select-action-bar {
            background-color: rgba(30, 30, 36, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 9999px;
            padding: 8px 18px;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.65);
        }
        .mac-light .mac-select-action-bar {
            background-color: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(0, 0, 0, 0.14);
            border-radius: 9999px;
            padding: 8px 18px;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.18);
        }

        .mac-select-action-bar .selected-count-label {
            font-size: 13px;
            font-weight: 600;
            padding: 0 6px;
        }
        .mac-dark .mac-select-action-bar .selected-count-label {
            color: #f5f5f7;
        }
        .mac-light .mac-select-action-bar .selected-count-label {
            color: #1d1d1f;
        }

        .mac-action-pill-btn {
            border-radius: 9999px;
            padding: 6px 14px;
            border: 1px solid transparent;
            transition: all 150ms ease;
        }
        .mac-dark .mac-action-pill-btn {
            background-color: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.14);
        }
        .mac-dark .mac-action-pill-btn label {
            color: #f5f5f7;
            font-size: 13px;
            font-weight: 500;
        }
        .mac-dark .mac-action-pill-btn:hover {
            background-color: rgba(255, 255, 255, 0.20);
            border-color: rgba(255, 255, 255, 0.25);
        }

        .mac-light .mac-action-pill-btn {
            background-color: rgba(0, 0, 0, 0.06);
            border-color: rgba(0, 0, 0, 0.08);
        }
        .mac-light .mac-action-pill-btn label {
            color: #1d1d1f;
            font-size: 13px;
            font-weight: 500;
        }
        .mac-light .mac-action-pill-btn:hover {
            background-color: rgba(0, 0, 0, 0.12);
            border-color: rgba(0, 0, 0, 0.15);
        }

        .mac-btn-danger {
            background-color: #ff3b30;
            border-radius: 9999px;
            padding: 6px 16px;
            border: none;
            transition: all 150ms ease;
        }
        .mac-btn-danger label {
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
        }
        .mac-btn-danger:hover {
            background-color: #e02d23;
            box-shadow: 0 3px 12px rgba(255, 59, 48, 0.45);
        }
        .mac-btn-danger:disabled,
        .mac-action-pill-btn:disabled {
            opacity: 0.40;
        }

        .photo-format-badge {
            background-color: rgba(0, 0, 0, 0.65);
            color: #ffffff;
            font-size: 9px;
            font-weight: 700;
            padding: 2px 5px;
            border-radius: 4px;
        }

        .photo-video-duration-badge {
            background-color: rgba(0, 0, 0, 0.78);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 9999px;
            letter-spacing: 0.3px;
        }

        .photo-card-heart-btn {
            background-color: rgba(0, 0, 0, 0.45);
            border-radius: 9999px;
            padding: 4px;
            border: none;
            min-height: 22px;
            min-width: 22px;
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .mac-photo-card:hover .photo-card-heart-btn {
            opacity: 1;
        }
        .photo-card-heart-btn:hover {
            background-color: rgba(0, 0, 0, 0.75);
        }
        .photo-card-heart-btn.is-favorited {
            opacity: 1;
            background-color: rgba(255, 255, 255, 0.95);
        }

        /* ========================================================= */
        /* LIGHTBOX OVERLAY                                          */
        /* ========================================================= */
        .mac-lightbox-overlay {
            background-color: #0d0d0f;
        }
        .lightbox-backdrop {
            background-color: #0d0d0f;
        }
        .lightbox-top-bar {
            background-color: rgba(20, 20, 24, 0.75);
            border-radius: 9999px;
            padding: 6px 14px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
        }
        .lightbox-close-btn {
            background: transparent;
            border: none;
            padding: 4px 8px;
            border-radius: 9999px;
        }
        .lightbox-close-btn:hover {
            background-color: rgba(255, 255, 255, 0.15);
        }
        .lightbox-back-lbl {
            font-size: 13px;
            font-weight: 600;
            color: #ffffff;
        }
        .lightbox-title-lbl {
            font-size: 13px;
            font-weight: 700;
            color: #ffffff;
        }
        .lightbox-counter-lbl {
            font-size: 12px;
            font-weight: 600;
            color: #8e8e93;
        }

        .lightbox-nav-chevron {
            background-color: rgba(30, 30, 34, 0.6);
            border-radius: 9999px;
            padding: 8px;
            border: none;
            min-height: 44px;
            min-width: 44px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        }
        .lightbox-nav-chevron:hover {
            background-color: rgba(50, 50, 56, 0.85);
        }

        /* Floating Pill Bar */
        .mac-glass-pill-bar {
            background-color: rgba(30, 30, 35, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 9999px;
            padding: 6px 16px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
        }
        .pill-action-btn {
            background: transparent;
            border: none;
            border-radius: 9999px;
            padding: 6px 10px;
            min-height: 32px;
            min-width: 32px;
        }
        .pill-action-btn:hover {
            background-color: rgba(255, 255, 255, 0.18);
        }
        .pill-zoom-lbl {
            font-size: 11px;
            font-weight: 600;
            color: #8e8e93;
        }
        .pill-fit-btn {
            background: transparent;
            border: none;
            font-size: 11px;
            font-weight: 600;
            color: #007aff;
            padding: 4px 8px;
        }
        .pill-fit-btn:hover {
            color: #389dff;
        }

        .pill-time-lbl {
            font-size: 11px;
            font-weight: 600;
            color: #ffffff;
        }

        .video-scrubber-slider {
            min-width: 220px;
            padding: 0;
        }
        .video-scrubber-slider trough {
            background-color: rgba(255, 255, 255, 0.25);
            border-radius: 9999px;
            min-height: 4px;
        }
        .video-scrubber-slider highlight {
            background-color: #007aff;
            border-radius: 9999px;
            min-height: 4px;
        }
        .video-scrubber-slider slider {
            background-color: #ffffff;
            border-radius: 9999px;
            min-width: 12px;
            min-height: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
        }

        /* ========================================================= */
        /* INSPECTOR PANEL                                           */
        /* ========================================================= */
        .mac-inspector-panel {
            border-bottom-right-radius: 16px;
        }
        .mac-dark .mac-inspector-panel {
            background-color: #212124;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }
        .mac-light .mac-inspector-panel {
            background-color: #f2f2f5;
            border-left: 1px solid rgba(0, 0, 0, 0.08);
        }

        .inspector-header {
            padding: 12px 16px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.15);
        }
        .inspector-title {
            font-size: 13.5px;
            font-weight: 700;
        }
        .mac-dark .inspector-title { color: #f5f5f7; }
        .mac-light .inspector-title { color: #1d1d1f; }

        .inspector-close-btn {
            background: transparent;
            border: none;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .inspector-close-btn:hover { background-color: rgba(255, 255, 255, 0.1); }
        .inspector-x { font-size: 11px; color: #86868b; }

        .inspector-thumb {
            border-radius: 8px;
            background-color: rgba(0, 0, 0, 0.2);
        }

        .inspector-filename {
            font-size: 13px;
            font-weight: 700;
        }
        .mac-dark .inspector-filename { color: #f5f5f7; }
        .mac-light .inspector-filename { color: #1d1d1f; }

        .inspector-card {
            border-radius: 10px;
            padding: 10px 12px;
        }
        .mac-dark .inspector-card {
            background-color: #2a2a2e;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .mac-light .inspector-card {
            background-color: #ffffff;
            border: 1px solid rgba(0, 0, 0, 0.06);
        }

        .inspector-row-title {
            font-size: 11.5px;
            color: #86868b;
        }
        .inspector-row-value {
            font-size: 11.5px;
            font-weight: 600;
        }
        .mac-dark .inspector-row-value { color: #e2e8f0; }
        .mac-light .inspector-row-value { color: #1d1d1f; }

        .inspector-section-hdr {
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #86868b;
        }

        .inspector-action-btn {
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            padding: 6px 12px;
            border: none;
        }
        .mac-dark .inspector-action-btn {
            background-color: #2d2d31;
            color: #f5f5f7;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .mac-light .inspector-action-btn {
            background-color: #ffffff;
            color: #1d1d1f;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }
        .inspector-action-btn:hover {
            background-color: #007aff;
            color: #ffffff;
        }

        /* Context Menu */
        .mac-context-menu {
            border-radius: 10px;
            padding: 6px;
        }
        .mac-dark .mac-context-menu {
            background-color: #28282c;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .mac-light .mac-context-menu {
            background-color: #fdfdfd;
            border: 1px solid rgba(0, 0, 0, 0.12);
        }

        /* ========================================================= */
        /* MACOS PHOTO EDITOR (SEQUOIA PHOTOS SUITE)                 */
        /* ========================================================= */
        .lightbox-edit-btn {
            background-color: rgba(255, 255, 255, 0.15);
            border: none;
            border-radius: 9999px;
            padding: 4px 14px;
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
        }
        .lightbox-edit-btn:hover {
            background-color: rgba(255, 255, 255, 0.28);
        }

        .editor-top-bar {
            background-color: rgba(24, 24, 28, 0.88);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 9999px;
            padding: 6px 14px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
        }

        .editor-btn-cancel {
            background-color: rgba(255, 255, 255, 0.12);
            border: none;
            border-radius: 9999px;
            padding: 6px 16px;
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
        }
        .editor-btn-cancel:hover {
            background-color: rgba(255, 255, 255, 0.22);
        }

        .editor-btn-done {
            background-color: #ffd60a;
            border: none;
            border-radius: 9999px;
            padding: 6px 18px;
            color: #000000;
            font-size: 13px;
            font-weight: 700;
        }
        .editor-btn-done:hover {
            background-color: #ffdf33;
        }

        .editor-btn-secondary {
            background-color: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 9999px;
            padding: 6px 14px;
            color: #ffffff;
            font-size: 12.5px;
            font-weight: 600;
        }
        .editor-btn-secondary:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        .editor-btn-secondary:disabled {
            opacity: 0.4;
        }

        .editor-segmented-group {
            background-color: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 9999px;
            padding: 3px;
        }

        .editor-segmented-btn {
            background: transparent;
            border: none;
            border-radius: 9999px;
            padding: 5px 14px;
            color: #a1a1a6;
            font-size: 12.5px;
            font-weight: 600;
        }
        .editor-segmented-btn:hover {
            color: #ffffff;
        }
        .editor-segmented-btn.active {
            background-color: rgba(255, 255, 255, 0.22);
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        .editor-inspector-panel {
            background-color: rgba(26, 26, 30, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 14px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
        }

        .editor-section-header {
            color: #8e8e93;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.8px;
        }

        .editor-slider-label {
            color: #e5e5ea;
            font-size: 12px;
            font-weight: 500;
        }

        .editor-slider-val {
            color: #ffd60a;
            font-size: 12px;
            font-weight: 700;
        }

        .editor-slider {
            min-width: 180px;
            padding: 0;
        }
        .editor-slider trough {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 9999px;
            min-height: 4px;
        }
        .editor-slider highlight {
            background-color: #ffd60a;
            border-radius: 9999px;
            min-height: 4px;
        }
        .editor-slider slider {
            background-color: #ffffff;
            border-radius: 9999px;
            min-width: 14px;
            min-height: 14px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        }

        .editor-ratio-pill {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            color: #d1d1d6;
            font-size: 12px;
            padding: 6px 12px;
            font-weight: 500;
        }
        .editor-ratio-pill:hover {
            background-color: rgba(255, 255, 255, 0.16);
            color: #ffffff;
        }
        .editor-ratio-pill.active {
            background-color: #007aff;
            border-color: #007aff;
            color: #ffffff;
            font-weight: 600;
        }

        .editor-tool-btn {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 7px;
            min-width: 36px;
            min-height: 36px;
        }
        .editor-tool-btn:hover {
            background-color: rgba(255, 255, 255, 0.18);
        }
        .editor-tool-btn.active {
            background-color: rgba(0, 122, 255, 0.35);
            border-color: #007aff;
        }

        .editor-filter-card {
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 8px 12px;
        }
        .editor-filter-card:hover {
            background-color: rgba(255, 255, 255, 0.14);
        }
        .editor-filter-card.active {
            background-color: rgba(0, 122, 255, 0.25);
            border-color: #007aff;
        }

        .editor-filter-lbl {
            color: #ffffff;
            font-size: 12.5px;
            font-weight: 600;
        }

        .editor-text-entry {
            background-color: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 12px;
        }
        """

        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(css)
            screen = Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception as e:
            print(f"[Photos] Error loading CSS: {e}")


def launch_photos_app():
    """Launch macOS Photos app standalone."""
    app = MacOSPhotosWindow.get_instance()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    app.lightbox.hide()
    app.inspector_panel.hide()
    Gtk.main()


if __name__ == "__main__":
    launch_photos_app()
