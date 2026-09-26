"""
Authentic Apple macOS Memoji & Profile Picture Chooser Modal Dialog.
Matches macOS Sonoma / Sequoia Memoji Picker specifications:
- Left sidebar: Memoji, Emoji, Monogram, Photos.
- Memoji View: Segmented [ 👤 Nhân vật ] | [ 📷 Cử chỉ ] toggle:
  * Characters: 20+ diverse Apple Memoji characters (Boy, Girl, Young, Old, Lion, Bear, Robot...).
  * Poses: 12 expressive facial poses (Smile, Wink, Tongue, Kiss, Laugh, Cool...).
- Emoji View: 46 Apple Color Emojis (humans of all ages, animals, symbols).
- Monogram View: Initials with rich Apple gradient colors.
- Photos View: Custom image file selector.
- Bottom bar: Live circular preview (with specular ring) + Zoom slider (0.6x - 2.2x) + Cancel / Save buttons.
"""

import os
import sys
import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo

from src.utils.theme import is_dark_mode


class CircularPreviewWidget(Gtk.DrawingArea):
    """Draws avatar inside a circular crop with smooth zoom scaling and specular ring."""
    def __init__(self, size=64):
        super().__init__()
        self.size = size
        self.set_size_request(size, size)
        self.pixbuf = None
        self.zoom = 1.0
        self.bg_color = (0.20, 0.20, 0.24)
        self.monogram_text = None
        self.connect("draw", self._on_draw)

    def set_avatar(self, pixbuf=None, zoom=1.0, bg_color=None, monogram_text=None):
        self.pixbuf = pixbuf
        self.zoom = max(0.5, min(3.0, float(zoom)))
        if bg_color is not None:
            self.bg_color = bg_color
        self.monogram_text = monogram_text
        self.queue_draw()

    def set_zoom(self, zoom):
        self.zoom = max(0.5, min(3.0, float(zoom)))
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0
        r = min(cx, cy) - 2.5

        cr.save()

        # 1. Circular Clip
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.clip()

        # 2. Background
        if self.bg_color:
            cr.set_source_rgb(*self.bg_color)
            cr.paint()
        else:
            cr.set_source_rgb(0.20, 0.20, 0.24)
            cr.paint()

        # 3. Draw Pixbuf with Zoom
        if self.pixbuf:
            cr.save()
            cr.translate(cx, cy)
            cr.scale(self.zoom, self.zoom)
            cr.translate(-cx, -cy)

            pw = self.pixbuf.get_width()
            ph = self.pixbuf.get_height()
            scale_fit = (r * 2.0) / max(pw, ph)
            scaled_w = pw * scale_fit
            scaled_h = ph * scale_fit
            draw_x = cx - scaled_w / 2.0
            draw_y = cy - scaled_h / 2.0

            scaled_pb = self.pixbuf.scale_simple(int(scaled_w), int(scaled_h), GdkPixbuf.InterpType.BILINEAR)
            if scaled_pb:
                Gdk.cairo_set_source_pixbuf(cr, scaled_pb, draw_x, draw_y)
                cr.paint()
            cr.restore()
        elif self.monogram_text:
            cr.save()
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.select_font_face("SF Pro Display, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(r * 0.9 * self.zoom)
            ext = cr.text_extents(self.monogram_text)
            tx = cx - (ext.width / 2.0 + ext.x_bearing)
            ty = cy - (ext.height / 2.0 + ext.y_bearing)
            cr.move_to(tx, ty)
            cr.show_text(self.monogram_text)
            cr.restore()

        cr.restore()

        # 4. Specular Highlight Outer Ring
        cr.save()
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.set_line_width(2.0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.30)
        cr.stroke()
        cr.restore()


class MacOSAvatarDialog(Gtk.Window):
    """Authentic Apple macOS Profile Picture Chooser Modal Dialog."""

    def __init__(self, parent=None, current_avatar=None, fullname="User", on_save=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.parent_window = parent
        self.current_avatar = current_avatar
        self.fullname = fullname or "User"
        self.on_save = on_save
        self.is_dark = is_dark_mode()

        self.set_title("Chọn ảnh đại diện")
        self.set_default_size(680, 520)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT if parent else Gtk.WindowPosition.CENTER)
        self.set_transient_for(parent)
        self.set_modal(True)

        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.memoji_dir = os.path.join(self.project_root, "assets", "avatars", "memoji")
        self.emoji_dir = os.path.join(self.project_root, "assets", "avatars")

        self.selected_type = "memoji"
        self.selected_path = None
        self.selected_pixbuf = None
        self.selected_bg = (0.18, 0.18, 0.22)
        self.current_zoom = 1.0

        self.character_buttons = {}
        self.pose_buttons = {}
        self.emoji_buttons = {}

        self._load_css()
        self._build_ui()
        self._select_default_memoji()

    def _load_css(self):
        css = b"""
        .avatar-dialog-root {
            background-color: #242428;
            color: #f5f5f7;
            border-radius: 14px;
        }
        .mac-light .avatar-dialog-root {
            background-color: #f2f2f7;
            color: #1c1c1e;
        }
        .avatar-sidebar {
            background-color: #1c1c1f;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            padding: 14px 10px;
        }
        .mac-light .avatar-sidebar {
            background-color: #e5e5ea;
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }
        .avatar-sidebar-row {
            background: transparent;
            border: none;
            box-shadow: none;
            border-radius: 8px;
            padding: 7px 12px;
            margin-bottom: 3px;
            color: #d1d1d6;
            font-size: 13px;
            font-weight: 500;
        }
        .avatar-sidebar-row:hover {
            background: rgba(255, 255, 255, 0.07);
        }
        .mac-light .avatar-sidebar-row {
            color: #3a3a3c;
        }
        .mac-light .avatar-sidebar-row:hover {
            background: rgba(0, 0, 0, 0.05);
        }
        .avatar-sidebar-row.selected {
            background: rgba(255, 255, 255, 0.16);
            color: #ffffff;
            font-weight: 600;
        }
        .mac-light .avatar-sidebar-row.selected {
            background: rgba(0, 0, 0, 0.10);
            color: #000000;
        }
        .avatar-content-area {
            background-color: #2a2a2e;
            padding: 14px 18px 8px 18px;
        }
        .mac-light .avatar-content-area {
            background-color: #ffffff;
        }
        .avatar-title-label {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.2px;
        }
        .mac-light .avatar-title-label {
            color: #1c1c1e;
        }
        button.avatar-card-cell {
            background: rgba(255, 255, 255, 0.05);
            border: 1.5px solid rgba(255, 255, 255, 0.08);
            box-shadow: none;
            outline: none;
            border-radius: 12px;
            padding: 6px 4px;
            transition: all 120ms ease;
        }
        button.avatar-card-cell:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.22);
        }
        button.avatar-card-cell.selected {
            background: rgba(0, 122, 255, 0.18);
            border: 2px solid #007aff;
            box-shadow: 0 0 10px rgba(0, 122, 255, 0.35);
        }
        .mac-light button.avatar-card-cell {
            background: #fbfbfd;
            border: 1.5px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }
        .mac-light button.avatar-card-cell:hover {
            background: #ffffff;
            border-color: rgba(0, 0, 0, 0.18);
        }
        .mac-light button.avatar-card-cell.selected {
            border: 2px solid #007aff;
            background: #edf5ff;
        }
        .avatar-card-title {
            font-size: 10.5px;
            font-weight: 500;
            color: #a1a1a6;
            margin-top: 3px;
        }
        .mac-light .avatar-card-title {
            color: #6e6e73;
        }
        button.avatar-card-cell.selected .avatar-card-title {
            color: #38bdf8;
            font-weight: 600;
        }
        .mac-light button.avatar-card-cell.selected .avatar-card-title {
            color: #007aff;
            font-weight: 600;
        }
        .seg-pill-box {
            background-color: rgba(0, 0, 0, 0.30);
            border-radius: 8px;
            padding: 2px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .mac-light .seg-pill-box {
            background-color: rgba(0, 0, 0, 0.07);
            border: 1px solid rgba(0, 0, 0, 0.08);
        }
        .seg-pill-btn {
            background: transparent;
            border: none;
            box-shadow: none;
            outline: none;
            border-radius: 6px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 500;
            color: #aeaeb2;
            transition: all 120ms ease;
        }
        .seg-pill-btn.active {
            background: #007aff;
            color: #ffffff;
            font-weight: 600;
        }
        .avatar-zoom-scale trough {
            background-color: rgba(255, 255, 255, 0.18);
            border-radius: 3px;
            min-height: 4px;
            border: none;
        }
        .mac-light .avatar-zoom-scale trough {
            background-color: rgba(0, 0, 0, 0.15);
        }
        .avatar-zoom-scale highlight {
            background-color: #007aff;
            border-radius: 3px;
            min-height: 4px;
            border: none;
        }
        .avatar-zoom-scale slider {
            background: #ffffff;
            border-radius: 50%;
            min-width: 13px;
            min-height: 13px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
            border: none;
        }
        .mac-bottom-bar {
            background-color: #1f1f23;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            padding: 10px 18px;
        }
        .mac-light .mac-bottom-bar {
            background-color: #ececee;
            border-top: 1px solid rgba(0, 0, 0, 0.08);
        }
        .mac-dialog-btn {
            border-radius: 7px;
            padding: 6px 16px;
            font-size: 12.5px;
            font-weight: 500;
            background: rgba(255, 255, 255, 0.10);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.10);
        }
        .mac-dialog-btn:hover {
            background: rgba(255, 255, 255, 0.16);
        }
        .mac-light .mac-dialog-btn {
            background: #ffffff;
            color: #1c1c1e;
            border: 1px solid rgba(0, 0, 0, 0.15);
        }
        .mac-light .mac-dialog-btn:hover {
            background: #f7f7f9;
        }
        .mac-dialog-btn.save {
            background: #007aff;
            color: #ffffff;
            border: none;
            font-weight: 600;
        }
        .mac-dialog-btn.save:hover {
            background: #0a84ff;
        }
        .zoom-label-text {
            font-size: 11.5px;
            color: #8e8e93;
            font-weight: 500;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 30
        )

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("avatar-dialog-root")
        if self.is_dark:
            root.get_style_context().add_class("mac-dark")
        else:
            root.get_style_context().add_class("mac-light")
        self.add(root)

        # Upper Area: Sidebar + Content Stack
        upper_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        root.pack_start(upper_box, True, True, 0)

        # 1. Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sidebar.get_style_context().add_class("avatar-sidebar")
        sidebar.set_size_request(136, -1)
        upper_box.pack_start(sidebar, False, False, 0)

        self.sidebar_buttons = {}
        sidebar_items = [
            ("memoji", "avatar-default-symbolic", "Memoji"),
            ("emoji", "face-smile-symbolic", "Emoji"),
            ("monogram", "font-select-symbolic", "Monogram"),
            ("photos", "image-x-generic-symbolic", "Photos"),
        ]

        for sid, icon_nm, label in sidebar_items:
            btn = Gtk.Button()
            btn.get_style_context().add_class("avatar-sidebar-row")
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            img_icon = Gtk.Image.new_from_icon_name(icon_nm, Gtk.IconSize.MENU)
            lbl_text = Gtk.Label(label=label)
            lbl_text.set_xalign(0.0)
            hbox.pack_start(img_icon, False, False, 0)
            hbox.pack_start(lbl_text, True, True, 0)
            btn.add(hbox)
            btn.connect("clicked", lambda b, s=sid: self._on_sidebar_select(s))
            sidebar.pack_start(btn, False, False, 0)
            self.sidebar_buttons[sid] = btn

        # 2. Content Stack Area
        self.stack = Gtk.Stack()
        self.stack.get_style_context().add_class("avatar-content-area")
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        upper_box.pack_start(self.stack, True, True, 0)

        self._build_memoji_page()
        self._build_emoji_page()
        self._build_monogram_page()
        self._build_photos_page()

        # 3. Bottom Action & Preview Bar
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        bottom_box.get_style_context().add_class("mac-bottom-bar")
        root.pack_start(bottom_box, False, False, 0)

        # Left: Circular Preview (62px)
        self.preview_widget = CircularPreviewWidget(size=56)
        bottom_box.pack_start(self.preview_widget, False, False, 0)

        # Middle: Integrated Zoom Controller
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        zoom_box.set_valign(Gtk.Align.CENTER)

        zoom_icon = Gtk.Image.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.MENU)
        zoom_box.pack_start(zoom_icon, False, False, 0)

        self.zoom_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.6, 2.2, 0.05)
        self.zoom_slider.get_style_context().add_class("avatar-zoom-scale")
        self.zoom_slider.set_value(1.0)
        self.zoom_slider.set_size_request(130, -1)
        self.zoom_slider.set_draw_value(False)
        self.zoom_slider.connect("value-changed", self._on_zoom_changed)
        zoom_box.pack_start(self.zoom_slider, False, False, 0)

        self.zoom_val_lbl = Gtk.Label(label="1.0x")
        self.zoom_val_lbl.get_style_context().add_class("zoom-label-text")
        zoom_box.pack_start(self.zoom_val_lbl, False, False, 0)

        bottom_box.pack_start(zoom_box, False, False, 0)

        # Right: Clean Modal Action Buttons (Cancel / Save)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_valign(Gtk.Align.CENTER)

        btn_cancel = Gtk.Button(label="Hủy")
        btn_cancel.get_style_context().add_class("mac-dialog-btn")
        btn_cancel.connect("clicked", lambda _: self.destroy())
        btn_box.pack_start(btn_cancel, False, False, 0)

        btn_save = Gtk.Button(label="Lưu làm Avatar")
        btn_save.get_style_context().add_class("mac-dialog-btn")
        btn_save.get_style_context().add_class("save")
        btn_save.connect("clicked", lambda _: self._on_save_clicked())
        btn_box.pack_start(btn_save, False, False, 0)

        bottom_box.pack_end(btn_box, False, False, 0)

    def _build_memoji_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Top bar: Clean Title + Segmented [ 👤 Nhân vật ] | [ 📷 Cử chỉ ]
        hbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label="Memoji")
        lbl.get_style_context().add_class("avatar-title-label")
        hbar.pack_start(lbl, False, False, 0)

        seg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        seg_box.get_style_context().add_class("seg-pill-box")
        seg_box.set_halign(Gtk.Align.END)

        self.btn_chars = Gtk.Button(label="Nhân vật")
        self.btn_chars.get_style_context().add_class("seg-pill-btn")
        self.btn_chars.get_style_context().add_class("active")

        self.btn_poses = Gtk.Button(label="Cử chỉ")
        self.btn_poses.get_style_context().add_class("seg-pill-btn")

        self.btn_chars.connect("clicked", lambda _: self._on_memoji_subtab_toggle(True))
        self.btn_poses.connect("clicked", lambda _: self._on_memoji_subtab_toggle(False))

        seg_box.pack_start(self.btn_chars, False, False, 0)
        seg_box.pack_start(self.btn_poses, False, False, 0)
        hbar.pack_end(seg_box, False, False, 0)
        container.pack_start(hbar, False, False, 0)

        # Sub-stack for Characters vs Poses
        self.memoji_substack = Gtk.Stack()
        self.memoji_substack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.memoji_substack.set_transition_duration(100)

        # --- Sub-page 1: Diverse Characters (20+ Apple Characters) ---
        chars_scroll = Gtk.ScrolledWindow()
        chars_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        chars_grid = Gtk.Grid()
        chars_grid.set_column_spacing(10)
        chars_grid.set_row_spacing(10)
        chars_grid.set_halign(Gtk.Align.FILL)
        chars_scroll.add(chars_grid)

        characters = [
            ("emoji_boy.png", "Bé trai"),
            ("emoji_girl.png", "Bé gái"),
            ("emoji_baby.png", "Em bé"),
            ("emoji_young_man.png", "Thanh niên"),
            ("emoji_young_woman.png", "Nữ thanh niên"),
            ("emoji_tech_man.png", "Lập trình viên"),
            ("emoji_student.png", "Cử nhân"),
            ("emoji_man.png", "Nam trung niên"),
            ("emoji_woman.png", "Nữ trung niên"),
            ("emoji_businessman.png", "Doanh nhân nam"),
            ("emoji_businesswoman.png", "Doanh nhân nữ"),
            ("emoji_beard.png", "Quý ông râu"),
            ("emoji_old_man.png", "Cụ ông"),
            ("emoji_old_woman.png", "Cụ bà"),
            ("emoji_lion.png", "Sư tử"),
            ("emoji_bear.png", "Gấu xám"),
            ("emoji_fox.png", "Cáo lửa"),
            ("emoji_panda.png", "Gấu trúc"),
            ("emoji_cat.png", "Mèo con"),
            ("emoji_dog.png", "Cún cưng"),
            ("emoji_robot.png", "Robot 3D"),
            ("emoji_alien.png", "Alien"),
        ]

        col = 0
        row = 0
        for fname, title in characters:
            fpath = os.path.join(self.emoji_dir, fname)
            btn = Gtk.Button()
            btn.get_style_context().add_class("avatar-card-cell")
            btn.set_size_request(88, 92)
            btn.set_tooltip_text(title)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_halign(Gtk.Align.CENTER)
            vbox.set_valign(Gtk.Align.CENTER)

            if os.path.exists(fpath):
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, 58, 58, True)
                img = Gtk.Image.new_from_pixbuf(pb)
                vbox.pack_start(img, False, False, 0)

            lbl_t = Gtk.Label(label=title)
            lbl_t.get_style_context().add_class("avatar-card-title")
            vbox.pack_start(lbl_t, False, False, 0)
            btn.add(vbox)

            btn.connect("clicked", lambda b, p=fpath: self._on_select_character(p, b))
            chars_grid.attach(btn, col, row, 1, 1)
            self.character_buttons[fpath] = btn

            col += 1
            if col >= 5:
                col = 0
                row += 1

        self.memoji_substack.add_named(chars_scroll, "characters")

        # --- Sub-page 2: Poses (12 Apple Cap Poses) ---
        poses_scroll = Gtk.ScrolledWindow()
        poses_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        poses_grid = Gtk.Grid()
        poses_grid.set_column_spacing(10)
        poses_grid.set_row_spacing(10)
        poses_grid.set_halign(Gtk.Align.FILL)
        poses_scroll.add(poses_grid)

        poses = [
            ("memoji_cap_smile.png", "Mỉm cười"),
            ("memoji_cap_wink.png", "Nháy mắt"),
            ("memoji_cap_tongue.png", "Lè lưỡi"),
            ("memoji_cap_whistle.png", "Hôn gió / Huýt sáo"),
            ("memoji_cap_laugh.png", "Cười lớn"),
            ("memoji_cap_cool.png", "Đeo kính ngầu"),
            ("memoji_cap_smirk.png", "Cười nhếch mép"),
            ("memoji_cap_happy.png", "Rạng rỡ"),
            ("memoji_cap_surprised.png", "Bất ngờ"),
            ("memoji_cap_pout.png", "Phồng má"),
            ("memoji_cap_neutral.png", "Điềm tĩnh"),
            ("memoji_cap_look_side.png", "Liếc nhìn"),
        ]

        col = 0
        row = 0
        for fname, title in poses:
            fpath = os.path.join(self.memoji_dir, fname)
            btn = Gtk.Button()
            btn.get_style_context().add_class("avatar-card-cell")
            btn.set_size_request(98, 96)
            btn.set_tooltip_text(title)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_halign(Gtk.Align.CENTER)
            vbox.set_valign(Gtk.Align.CENTER)

            if os.path.exists(fpath):
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, 64, 64, True)
                img = Gtk.Image.new_from_pixbuf(pb)
                vbox.pack_start(img, False, False, 0)

            lbl_t = Gtk.Label(label=title)
            lbl_t.get_style_context().add_class("avatar-card-title")
            vbox.pack_start(lbl_t, False, False, 0)
            btn.add(vbox)

            btn.connect("clicked", lambda b, p=fpath: self._on_select_pose(p, b))
            poses_grid.attach(btn, col, row, 1, 1)
            self.pose_buttons[fpath] = btn

            col += 1
            if col >= 4:
                col = 0
                row += 1

        self.memoji_substack.add_named(poses_scroll, "poses")

        container.pack_start(self.memoji_substack, True, True, 0)
        self.stack.add_named(container, "memoji")

    def _build_emoji_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        lbl = Gtk.Label(label="Biểu tượng Apple Emoji")
        lbl.get_style_context().add_class("avatar-title-label")
        lbl.set_xalign(0.0)
        container.pack_start(lbl, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_halign(Gtk.Align.FILL)
        scroll.add(grid)

        emojis = sorted([f for f in os.listdir(self.emoji_dir) if f.startswith("emoji_") and f.endswith(".png")])
        col = 0
        row = 0
        for fname in emojis:
            fpath = os.path.join(self.emoji_dir, fname)
            btn = Gtk.Button()
            btn.get_style_context().add_class("avatar-card-cell")
            btn.set_size_request(68, 68)

            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, 50, 50, True)
            img = Gtk.Image.new_from_pixbuf(pb)
            btn.add(img)

            btn.connect("clicked", lambda b, p=fpath: self._on_select_emoji(p, b))
            grid.attach(btn, col, row, 1, 1)
            self.emoji_buttons[fpath] = btn

            col += 1
            if col >= 6:
                col = 0
                row += 1

        container.pack_start(scroll, True, True, 0)
        self.stack.add_named(container, "emoji")

    def _build_monogram_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(16)

        lbl = Gtk.Label(label="Ký tự viết tắt (Monogram)")
        lbl.get_style_context().add_class("avatar-title-label")
        lbl.set_xalign(0.0)
        container.pack_start(lbl, False, False, 0)

        # Monogram Initials Entry
        r_entry = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_in = Gtk.Label(label="Chữ cái viết tắt:")
        self.mono_entry = Gtk.Entry()
        initials = "".join([part[0].upper() for part in self.fullname.split()[:2]]) or "TT"
        self.mono_entry.set_text(initials)
        self.mono_entry.set_max_length(3)
        self.mono_entry.connect("changed", self._on_monogram_text_changed)
        r_entry.pack_start(lbl_in, False, False, 0)
        r_entry.pack_start(self.mono_entry, False, False, 0)
        container.pack_start(r_entry, False, False, 0)

        # Color Swatches
        lbl_c = Gtk.Label(label="Chọn màu nền Apple Gradient:")
        lbl_c.set_xalign(0.0)
        container.pack_start(lbl_c, False, False, 0)

        colors_grid = Gtk.Grid()
        colors_grid.set_column_spacing(12)
        colors_grid.set_row_spacing(12)

        palettes = [
            ("Xanh Lam Apple", (0.0, 0.48, 1.0)),
            ("Tím Indigo", (0.35, 0.34, 0.84)),
            ("Hồng Apple", (0.88, 0.19, 0.47)),
            ("Đỏ San Hô", (0.95, 0.28, 0.25)),
            ("Cam Hoàng Hôn", (0.98, 0.55, 0.10)),
            ("Vàng Nắng", (0.98, 0.78, 0.15)),
            ("Xanh Lá", (0.20, 0.78, 0.35)),
            ("Xanh Ngọc", (0.15, 0.75, 0.70)),
            ("Tím Mận", (0.68, 0.32, 0.87)),
            ("Xám Thép", (0.35, 0.35, 0.38)),
        ]

        for i, (cname, rgb) in enumerate(palettes):
            btn = Gtk.Button()
            btn.set_size_request(42, 42)
            btn.set_tooltip_text(cname)
            da = Gtk.DrawingArea()
            da.set_size_request(32, 32)
            def _draw_swatch(w, cr, color=rgb):
                cr.arc(16, 16, 15, 0, 2*math.pi)
                cr.set_source_rgb(*color)
                cr.fill_preserve()
                cr.set_source_rgba(1, 1, 1, 0.35)
                cr.set_line_width(1.5)
                cr.stroke()
            da.connect("draw", _draw_swatch)
            btn.add(da)
            btn.connect("clicked", lambda b, c=rgb: self._on_monogram_color_selected(c))
            colors_grid.attach(btn, i % 5, i // 5, 1, 1)

        container.pack_start(colors_grid, False, False, 0)
        self.stack.add_named(container, "monogram")

    def _build_photos_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(16)

        lbl = Gtk.Label(label="Chọn ảnh từ ứng dụng Ảnh (macOS Photos)")
        lbl.get_style_context().add_class("avatar-title-label")
        lbl.set_xalign(0.0)
        container.pack_start(lbl, False, False, 0)

        desc = Gtk.Label(label="Duyệt và chọn ảnh trực tiếp từ thư viện Photos hoặc duyệt tệp tin trên máy tính. Sử dụng thanh trượt bên dưới để phóng to/thu nhỏ ảnh vừa vặn khuôn hình tròn.")
        desc.set_xalign(0.0)
        desc.set_line_wrap(True)
        container.pack_start(desc, False, False, 0)

        btn_pick = Gtk.Button(label="Mở ứng dụng Ảnh để chọn…")
        btn_pick.get_style_context().add_class("mac-dialog-btn")
        btn_pick.set_halign(Gtk.Align.START)
        btn_pick.connect("clicked", lambda _: self._on_pick_file())
        container.pack_start(btn_pick, False, False, 0)

        self.stack.add_named(container, "photos")

    def _on_sidebar_select(self, sid):
        for k, btn in self.sidebar_buttons.items():
            if k == sid:
                btn.get_style_context().add_class("selected")
            else:
                btn.get_style_context().remove_class("selected")
        self.stack.set_visible_child_name(sid)

    def _on_memoji_subtab_toggle(self, is_chars):
        if is_chars:
            self.btn_chars.get_style_context().add_class("active")
            self.btn_poses.get_style_context().remove_class("active")
            self.memoji_substack.set_visible_child_name("characters")
        else:
            self.btn_poses.get_style_context().add_class("active")
            self.btn_chars.get_style_context().remove_class("active")
            self.memoji_substack.set_visible_child_name("poses")

    def _select_default_memoji(self):
        self._on_sidebar_select("memoji")
        # Select first character (boy or young man) by default
        default_char = os.path.join(self.emoji_dir, "emoji_boy.png")
        if not os.path.exists(default_char):
            default_char = os.path.join(self.emoji_dir, "emoji_young_man.png")
        if os.path.exists(default_char) and default_char in self.character_buttons:
            self._on_select_character(default_char, self.character_buttons[default_char])
        elif self.pose_buttons:
            first_pose = list(self.pose_buttons.keys())[0]
            self._on_select_pose(first_pose, self.pose_buttons[first_pose])

    def _clear_all_card_selections(self):
        for b in self.character_buttons.values():
            b.get_style_context().remove_class("selected")
        for b in self.pose_buttons.values():
            b.get_style_context().remove_class("selected")
        for b in self.emoji_buttons.values():
            b.get_style_context().remove_class("selected")

    def _on_select_character(self, fpath, btn_widget):
        self._clear_all_card_selections()
        btn_widget.get_style_context().add_class("selected")

        self.selected_type = "memoji"
        self.selected_path = fpath
        self.selected_pixbuf = GdkPixbuf.Pixbuf.new_from_file(fpath)
        self.preview_widget.set_avatar(pixbuf=self.selected_pixbuf, zoom=self.current_zoom, bg_color=(0.18, 0.18, 0.22))

    def _on_select_pose(self, fpath, btn_widget):
        self._clear_all_card_selections()
        btn_widget.get_style_context().add_class("selected")

        self.selected_type = "memoji"
        self.selected_path = fpath
        self.selected_pixbuf = GdkPixbuf.Pixbuf.new_from_file(fpath)
        self.preview_widget.set_avatar(pixbuf=self.selected_pixbuf, zoom=self.current_zoom, bg_color=(0.18, 0.18, 0.22))

    def _on_select_emoji(self, fpath, btn_widget):
        self._clear_all_card_selections()
        btn_widget.get_style_context().add_class("selected")

        self.selected_type = "emoji"
        self.selected_path = fpath
        self.selected_pixbuf = GdkPixbuf.Pixbuf.new_from_file(fpath)
        self.preview_widget.set_avatar(pixbuf=self.selected_pixbuf, zoom=self.current_zoom, bg_color=(0.18, 0.18, 0.22))

    def _on_monogram_text_changed(self, entry):
        text = entry.get_text().strip().upper()
        self.selected_type = "monogram"
        self.preview_widget.set_avatar(pixbuf=None, zoom=self.current_zoom, bg_color=self.selected_bg, monogram_text=text)

    def _on_monogram_color_selected(self, color_rgb):
        self.selected_bg = color_rgb
        text = self.mono_entry.get_text().strip().upper()
        self.selected_type = "monogram"
        self.preview_widget.set_avatar(pixbuf=None, zoom=self.current_zoom, bg_color=self.selected_bg, monogram_text=text)

    def _on_zoom_changed(self, scale):
        self.current_zoom = scale.get_value()
        self.zoom_val_lbl.set_text(f"{self.current_zoom:.1f}x")
        self.preview_widget.set_zoom(self.current_zoom)

    def _on_pick_file(self):
        try:
            from src.ui.macos_photos_window import MacOSPhotosWindow
            def on_selected(chosen):
                try:
                    self.selected_type = "photos"
                    self.selected_path = chosen
                    self.selected_pixbuf = GdkPixbuf.Pixbuf.new_from_file(chosen)
                    self.preview_widget.set_avatar(pixbuf=self.selected_pixbuf, zoom=self.current_zoom, bg_color=(0.18, 0.18, 0.22))
                except Exception as e:
                    print(f"[AvatarDialog] Error loading chosen photo: {e}")

            MacOSPhotosWindow.open_picker(
                title="Chọn ảnh đại diện",
                parent=self,
                on_photo_selected=on_selected
            )
        except Exception as e:
            print(f"[AvatarDialog] Fallback to file chooser: {e}")
            dialog = Gtk.FileChooserDialog(
                title="Chọn tệp tin ảnh",
                parent=self,
                action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
            filt = Gtk.FileFilter()
            filt.set_name("Hình ảnh")
            filt.add_mime_type("image/png")
            filt.add_mime_type("image/jpeg")
            filt.add_mime_type("image/webp")
            dialog.add_filter(filt)

            res = dialog.run()
            if res == Gtk.ResponseType.OK:
                chosen = dialog.get_filename()
                dialog.destroy()
                try:
                    self.selected_type = "photos"
                    self.selected_path = chosen
                    self.selected_pixbuf = GdkPixbuf.Pixbuf.new_from_file(chosen)
                    self.preview_widget.set_avatar(pixbuf=self.selected_pixbuf, zoom=self.current_zoom, bg_color=(0.18, 0.18, 0.22))
                except Exception as e:
                    print(f"[AvatarDialog] Error loading chosen photo: {e}")
            else:
                dialog.destroy()

    def _on_save_clicked(self):
        out_path = os.path.expanduser("~/.face")
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
        cr = cairo.Context(surf)

        # Clip circle
        cr.arc(128, 128, 128, 0, 2*math.pi)
        cr.clip()

        # Background
        if self.selected_bg:
            cr.set_source_rgb(*self.selected_bg)
            cr.paint()

        if self.selected_pixbuf:
            cr.save()
            cr.translate(128, 128)
            cr.scale(self.current_zoom, self.current_zoom)
            cr.translate(-128, -128)

            pw = self.selected_pixbuf.get_width()
            ph = self.selected_pixbuf.get_height()
            scale_fit = 256.0 / max(pw, ph)
            sw = pw * scale_fit
            sh = ph * scale_fit
            draw_x = 128 - sw / 2.0
            draw_y = 128 - sh / 2.0
            scaled_pb = self.selected_pixbuf.scale_simple(int(sw), int(sh), GdkPixbuf.InterpType.BILINEAR)
            if scaled_pb:
                Gdk.cairo_set_source_pixbuf(cr, scaled_pb, draw_x, draw_y)
                cr.paint()
            cr.restore()
        elif self.selected_type == "monogram":
            text = self.mono_entry.get_text().strip().upper()
            cr.save()
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.select_font_face("SF Pro Display, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(110 * self.current_zoom)
            ext = cr.text_extents(text)
            tx = 128 - (ext.width / 2.0 + ext.x_bearing)
            ty = 128 - (ext.height / 2.0 + ext.y_bearing)
            cr.move_to(tx, ty)
            cr.show_text(text)
            cr.restore()

        surf.write_to_png(out_path)

        # Also copy to ~/.face.icon
        try:
            import shutil
            shutil.copyfile(out_path, os.path.expanduser("~/.face.icon"))
        except Exception:
            pass

        # Update AccountsService
        try:
            from src.ui.macos_settings_window import set_user_avatar, get_user_profile
            u, _, _ = get_user_profile()
            set_user_avatar(u, out_path)
        except Exception as e:
            print(f"[AvatarDialog] Error updating AccountsService: {e}")

        if callable(self.on_save):
            self.on_save(out_path)

        self.destroy()
