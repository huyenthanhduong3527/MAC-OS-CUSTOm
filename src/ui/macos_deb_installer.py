"""
Authentic Apple macOS Package Installer (.pkg / .deb) for Ubuntu Linux.
Provides an elegant, step-by-step installation wizard matching macOS Installer:
- Left sidebar: 1. Giới thiệu  2. Chi tiết gói  3. Cài đặt  4. Hoàn tất
- Right content area with package metadata, dependency resolution, and real-time installation.
- Real APT/DPKG backend with automatic dependency resolution via `pkexec apt install -y ./<file.deb>`.
- One-click launch button upon successful installation.
"""

import os
import sys
import math
import shutil
import subprocess
import threading
from typing import Dict, Any, Optional

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo

from src.utils.theme import is_dark_mode
from src.utils.i18n import t


def parse_deb_info(deb_path: str) -> Dict[str, Any]:
    """Parse metadata from a Debian package (.deb) using dpkg-deb."""
    info = {
        "path": deb_path,
        "filename": os.path.basename(deb_path),
        "package": os.path.basename(deb_path).split("_")[0],
        "version": "1.0",
        "maintainer": "Nhà phát triển phần mềm",
        "size": "Unknown",
        "installed_size": "Unknown",
        "desc": "Gói cài đặt phần mềm Linux Debian/Ubuntu (.deb).",
        "depends": "",
        "homepage": "",
        "section": "Chung",
    }
    if not os.path.exists(deb_path):
        return info

    try:
        fsize = os.path.getsize(deb_path)
        info["size"] = f"{round(fsize / (1024 * 1024), 2)} MB"
    except Exception:
        pass

    try:
        res = subprocess.run(["dpkg-deb", "-I", deb_path], capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            current_field = None
            desc_lines = []
            for line in lines:
                if line.startswith(" ") and current_field == "description":
                    desc_lines.append(line.strip())
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    current_field = key
                    if key == "package":
                        info["package"] = val
                    elif key == "version":
                        info["version"] = val
                    elif key == "maintainer":
                        info["maintainer"] = val
                    elif key == "installed-size":
                        try:
                            info["installed_size"] = f"{round(int(val) / 1024, 1)} MB"
                        except Exception:
                            info["installed_size"] = f"{val} KB"
                    elif key == "depends":
                        info["depends"] = val
                    elif key == "homepage":
                        info["homepage"] = val
                    elif key == "section":
                        info["section"] = val.title()
                    elif key == "description":
                        desc_lines.append(val)
            if desc_lines:
                info["desc"] = "\n".join(desc_lines)
    except Exception:
        pass

    return info


class MacOSPackageIcon(Gtk.DrawingArea):
    """Draws an authentic Apple macOS Package squircle icon with golden tape seal."""
    def __init__(self, size=64):
        super().__init__()
        self.size = size
        self.set_size_request(size, size)
        self.connect("draw", self._on_draw)

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        s = min(w, h)
        pad = s * 0.08
        bw = s - 2 * pad
        bh = s - 2 * pad
        r = s * 0.22

        cr.save()
        # Squircle Path
        cr.new_sub_path()
        cr.arc(pad + bw - r, pad + r, r, -math.pi / 2, 0)
        cr.arc(pad + bw - r, pad + bh - r, r, 0, math.pi / 2)
        cr.arc(pad + r, pad + bh - r, r, math.pi / 2, math.pi)
        cr.arc(pad + r, pad + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        # Warm Cardboard Gradient
        pat = cairo.LinearGradient(pad, pad, pad, pad + bh)
        pat.add_color_stop_rgb(0.0, 0.90, 0.72, 0.52)  # #e6b885
        pat.add_color_stop_rgb(1.0, 0.72, 0.50, 0.32)  # #b88052
        cr.set_source(pat)
        cr.fill_preserve()

        # Inner shadow / stroke
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.15)
        cr.set_line_width(1.5)
        cr.stroke()

        # Cardboard Fold Flaps (Box seams)
        cr.set_source_rgba(0.45, 0.28, 0.15, 0.35)
        cr.set_line_width(1.2)
        # Horizontal fold
        cr.move_to(pad + r * 0.5, pad + bh * 0.45)
        cr.line_to(pad + bw - r * 0.5, pad + bh * 0.45)
        cr.stroke()

        # Golden Packing Tape
        cr.set_source_rgba(0.98, 0.85, 0.45, 0.85)
        tape_w = bw * 0.28
        tape_x = pad + (bw - tape_w) / 2
        cr.rectangle(tape_x, pad + 2, tape_w, bh - 4)
        cr.fill()

        # Tape outline
        cr.set_source_rgba(0.85, 0.65, 0.25, 0.6)
        cr.set_line_width(1.0)
        cr.rectangle(tape_x, pad + 2, tape_w, bh - 4)
        cr.stroke()

        # Center Golden Seal
        cx = pad + bw / 2
        cy = pad + bh / 2
        seal_r = s * 0.15
        cr.arc(cx, cy, seal_r, 0, 2 * math.pi)
        cr.set_source_rgba(0.95, 0.75, 0.15, 0.95)
        cr.fill_preserve()
        cr.set_source_rgba(0.65, 0.45, 0.05, 0.5)
        cr.stroke()

        cr.restore()
        return False


class MacOSDebInstallerDialog(Gtk.Window):
    """Authentic Apple macOS Package Installer (.pkg / .deb) Window."""

    def __init__(self, deb_path: str, parent: Optional[Gtk.Window] = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.deb_path = os.path.abspath(deb_path)
        self.parent_window = parent
        self.is_dark = is_dark_mode()
        self.deb_info = parse_deb_info(self.deb_path)
        self.current_step = 1
        self.install_success = False
        self.installed_desktop_file = None

        pkg_title = self.deb_info.get("package", "Gói phần mềm").replace("-", " ").title()
        self.set_title(f"Trình cài đặt {pkg_title}")
        self.set_default_size(680, 520)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_wmclass("macos-deb-installer", "MacOSDebInstaller")

        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        if parent:
            self.set_transient_for(parent)

        self._load_css()
        self._build_ui()
        self.connect("key-press-event", self._on_key_press)
        self.connect("button-press-event", self._on_window_button_press)
        self.connect("draw", self._on_draw_window)

    def _on_window_button_press(self, widget, event):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            # Allow dragging anywhere on sidebar or top header
            if event.y < 70 or event.x < 190:
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                return True
        return False

    def _on_draw_window(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 14.0

        cr.save()
        # Rounded clipping path
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        if self.is_dark:
            cr.set_source_rgba(0.14, 0.14, 0.16, 0.98)
        else:
            cr.set_source_rgba(0.95, 0.95, 0.97, 0.98)
        cr.fill_preserve()

        # Border outline
        if self.is_dark:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        else:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        cr.restore()
        return False

    def _load_css(self):
        css = b"""
        .installer-root {
            background-color: #242428;
            color: #f5f5f7;
            border-radius: 14px;
        }
        .mac-light .installer-root {
            background-color: #f2f2f7;
            color: #1c1c1e;
        }
        .installer-sidebar {
            background-color: #1c1c1f;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            padding: 20px 14px;
        }
        .mac-light .installer-sidebar {
            background-color: #e5e5ea;
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }
        .step-label {
            font-size: 13px;
            font-weight: 500;
            color: #8e8e93;
            padding: 6px 10px;
            border-radius: 6px;
        }
        .step-label.active {
            font-weight: 700;
            color: #007aff;
            background-color: rgba(0, 122, 255, 0.12);
        }
        .step-label.done {
            color: #34c759;
        }
        .installer-content {
            padding: 24px 32px;
            background: transparent;
        }
        .installer-title {
            font-size: 22px;
            font-weight: 700;
            color: #f5f5f7;
        }
        .mac-light .installer-title {
            color: #1c1c1e;
        }
        .installer-sub {
            font-size: 13px;
            color: #8e8e93;
            margin-top: 4px;
        }
        .info-card {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 14px 18px;
        }
        .mac-light .info-card {
            background-color: #ffffff;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }
        .info-key {
            font-size: 12px;
            font-weight: 600;
            color: #8e8e93;
        }
        .info-val {
            font-size: 13px;
            font-weight: 500;
            color: #f5f5f7;
        }
        .mac-light .info-val {
            color: #1c1c1e;
        }
        .desc-view {
            background-color: rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 10px;
            font-size: 12px;
            color: #d1d1d6;
        }
        .mac-light .desc-view {
            background-color: #f9f9fb;
            border: 1px solid rgba(0, 0, 0, 0.06);
            color: #3a3a3c;
        }
        .security-badge {
            background-color: rgba(52, 199, 89, 0.12);
            border: 1px solid rgba(52, 199, 89, 0.3);
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 600;
            color: #34c759;
        }
        .btn-cancel {
            background-color: rgba(255, 255, 255, 0.08);
            color: #f5f5f7;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            padding: 7px 18px;
        }
        .mac-light .btn-cancel {
            background-color: #e5e5ea;
            color: #1c1c1e;
            border: 1px solid rgba(0, 0, 0, 0.1);
        }
        .btn-cancel:hover {
            background-color: rgba(255, 255, 255, 0.14);
        }
        .btn-primary {
            background-color: #007aff;
            color: #ffffff;
            font-weight: 700;
            border-radius: 18px;
            padding: 7px 22px;
            border: none;
        }
        .btn-primary:hover {
            background-color: #0062cc;
        }
        .btn-success {
            background-color: #34c759;
            color: #ffffff;
            font-weight: 700;
            border-radius: 18px;
            padding: 7px 22px;
            border: none;
        }
        .tl-red {
            background-color: #ff5f56;
            border: 0.5px solid #e0443e;
            border-radius: 50%;
            min-width: 12px;
            min-height: 12px;
            padding: 0;
        }
        .tl-red:hover {
            background-color: #ff3b30;
        }
        .tl-yellow {
            background-color: #ffbd2e;
            border: 0.5px solid #dea123;
            border-radius: 50%;
            min-width: 12px;
            min-height: 12px;
            padding: 0;
        }
        .tl-yellow:hover {
            background-color: #ff9500;
        }
        .tl-green {
            background-color: #27c93f;
            border: 0.5px solid #1aab29;
            border-radius: 50%;
            min-width: 12px;
            min-height: 12px;
            padding: 0;
        }
        .tl-green:hover {
            background-color: #28cd41;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        root.get_style_context().add_class("installer-root")
        if not self.is_dark:
            root.get_style_context().add_class("mac-light")
        self.add(root)

        # -------------------------------------------------------------
        # 1. LEFT SIDEBAR: STEPS WIZARD (MAC STYLE)
        # -------------------------------------------------------------
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.set_size_request(190, -1)
        sidebar.get_style_context().add_class("installer-sidebar")
        root.pack_start(sidebar, False, False, 0)

        # macOS Window Traffic Lights (🔴 🟡 🟢)
        tl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tl_box.set_margin_bottom(18)

        def make_light(color_class, callback):
            b = Gtk.Button()
            b.set_size_request(12, 12)
            b.get_style_context().add_class(color_class)
            b.connect("clicked", lambda _: callback())
            return b

        tl_box.pack_start(make_light("tl-red", self.close), False, False, 0)
        tl_box.pack_start(make_light("tl-yellow", self.iconify), False, False, 0)
        tl_box.pack_start(make_light("tl-green", lambda: None), False, False, 0)
        sidebar.pack_start(tl_box, False, False, 0)

        # Steps List
        self.step_labels = []
        steps_data = [
            (1, "1. Giới thiệu"),
            (2, "2. Thông tin gói"),
            (3, "3. Cài đặt"),
            (4, "4. Hoàn tất")
        ]
        for step_num, step_name in steps_data:
            lbl = Gtk.Label(label=step_name)
            lbl.set_xalign(0.0)
            lbl.get_style_context().add_class("step-label")
            sidebar.pack_start(lbl, False, False, 2)
            self.step_labels.append(lbl)

        # Bottom Package Icon
        sidebar.pack_end(MacOSPackageIcon(size=56), False, False, 10)

        # -------------------------------------------------------------
        # 2. RIGHT MAIN AREA: STACK OF PAGES + BOTTOM BUTTONS
        # -------------------------------------------------------------
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(main_box, True, True, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(250)
        main_box.pack_start(self.stack, True, True, 0)

        # Build each page
        self._build_intro_page()
        self._build_details_page()
        self._build_install_page()
        self._build_finish_page()

        # -------------------------------------------------------------
        # 3. BOTTOM CONTROL BAR
        # -------------------------------------------------------------
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        bottom_bar.set_margin_start(32)
        bottom_bar.set_margin_end(32)
        bottom_bar.set_margin_top(12)
        bottom_bar.set_margin_bottom(20)
        main_box.pack_end(bottom_bar, False, False, 0)

        self.btn_cancel = Gtk.Button(label=t("installer_cancel", "Cancel"))
        self.btn_cancel.get_style_context().add_class("btn-cancel")
        self.btn_cancel.connect("clicked", lambda _: self.close())
        bottom_bar.pack_start(self.btn_cancel, False, False, 0)

        self.btn_back = Gtk.Button(label=t("installer_back", "‹ Back"))
        self.btn_back.get_style_context().add_class("btn-cancel")
        self.btn_back.connect("clicked", self._on_back_clicked)
        bottom_bar.pack_end(self.btn_back, False, False, 0)

        self.btn_next = Gtk.Button(label=t("installer_next", "Continue ›"))
        self.btn_next.get_style_context().add_class("btn-primary")
        self.btn_next.connect("clicked", self._on_next_clicked)
        bottom_bar.pack_end(self.btn_next, False, False, 0)

        self._update_step_ui()

    def _build_intro_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.get_style_context().add_class("installer-content")

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        header_row.pack_start(MacOSPackageIcon(size=64), False, False, 0)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_box.set_valign(Gtk.Align.CENTER)
        pkg_name = self.deb_info.get("package", "Gói cài đặt").title()
        lbl_t = Gtk.Label(label=f"Cài đặt {pkg_name}")
        lbl_t.get_style_context().add_class("installer-title")
        lbl_t.set_xalign(0.0)
        title_box.pack_start(lbl_t, False, False, 0)

        lbl_sub = Gtk.Label(label=f"Gói cài đặt phần mềm Debian (.deb) • Phiên bản {self.deb_info.get('version')}")
        lbl_sub.get_style_context().add_class("installer-sub")
        lbl_sub.set_xalign(0.0)
        title_box.pack_start(lbl_sub, False, False, 0)
        header_row.pack_start(title_box, True, True, 0)

        page.pack_start(header_row, False, False, 4)

        # Welcome Text
        welcome_lbl = Gtk.Label(
            label=f"Chào mừng bạn đến với Trình cài đặt {pkg_name}.\n\n"
                  f"Trình hướng dẫn này sẽ giúp bạn cài đặt phần mềm {pkg_name} vào hệ điều hành Ubuntu Linux của bạn một cách an toàn và chuẩn xác.\n\n"
                  f"Các thư viện phụ thuộc (dependencies) cần thiết sẽ được hệ thống tự động kiểm tra và giải quyết hoàn toàn thông qua APT."
        )
        welcome_lbl.set_line_wrap(True)
        welcome_lbl.set_xalign(0.0)
        page.pack_start(welcome_lbl, False, False, 8)

        # Security Badge
        sec_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sec_box.get_style_context().add_class("security-badge")
        sec_icon = Gtk.Label(label="🛡️")
        sec_box.pack_start(sec_icon, False, False, 0)
        sec_text = Gtk.Label(label=f"Tệp cài đặt cục bộ an toàn: {self.deb_info.get('filename')} ({self.deb_info.get('size')})")
        sec_text.set_xalign(0.0)
        sec_box.pack_start(sec_text, True, True, 0)
        page.pack_start(sec_box, False, False, 6)

        self.stack.add_named(page, "step1")

    def _build_details_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.get_style_context().add_class("installer-content")

        lbl_t = Gtk.Label(label=t("installer_package_info", "Package Installation Details"))
        lbl_t.get_style_context().add_class("installer-title")
        lbl_t.set_xalign(0.0)
        page.pack_start(lbl_t, False, False, 0)

        # Info Card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("info-card")

        def add_row(k, v):
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lk = Gtk.Label(label=k)
            lk.get_style_context().add_class("info-key")
            lk.set_size_request(130, -1)
            lk.set_xalign(0.0)
            lv = Gtk.Label(label=v)
            lv.get_style_context().add_class("info-val")
            lv.set_xalign(0.0)
            lv.set_line_wrap(True)
            r.pack_start(lk, False, False, 0)
            r.pack_start(lv, True, True, 0)
            card.pack_start(r, False, False, 0)

        add_row("Tên gói (Package):", self.deb_info.get("package", "—"))
        add_row("Phiên bản (Version):", self.deb_info.get("version", "—"))
        add_row("Kích thước tệp tải về:", self.deb_info.get("size", "—"))
        add_row("Dung lượng sau khi cài:", self.deb_info.get("installed_size", "—"))
        add_row("Nhà phát triển / Maintainer:", self.deb_info.get("maintainer", "—"))
        if self.deb_info.get("homepage"):
            add_row("Trang chủ (Homepage):", self.deb_info.get("homepage", "—"))
        page.pack_start(card, False, False, 0)

        # Description textview
        lbl_desc_title = Gtk.Label(label=t("installer_description", "Application description:"))
        lbl_desc_title.get_style_context().add_class("info-key")
        lbl_desc_title.set_xalign(0.0)
        page.pack_start(lbl_desc_title, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(-1, 110)
        scrolled.get_style_context().add_class("desc-view")
        desc_lbl = Gtk.Label(label=self.deb_info.get("desc", ""))
        desc_lbl.set_line_wrap(True)
        desc_lbl.set_xalign(0.0)
        desc_lbl.set_yalign(0.0)
        scrolled.add(desc_lbl)
        page.pack_start(scrolled, True, True, 0)

        self.stack.add_named(page, "step2")

    def _build_install_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.get_style_context().add_class("installer-content")
        page.set_valign(Gtk.Align.CENTER)

        pkg_name = self.deb_info.get("package", "phần mềm").title()
        self.lbl_install_title = Gtk.Label(label=f"Đang cài đặt {pkg_name}...")
        self.lbl_install_title.get_style_context().add_class("installer-title")
        self.lbl_install_title.set_xalign(0.5)
        page.pack_start(self.lbl_install_title, False, False, 0)

        self.lbl_install_sub = Gtk.Label(label=t("installer_extracting", "The system is extracting and configuring files..."))
        self.lbl_install_sub.get_style_context().add_class("installer-sub")
        self.lbl_install_sub.set_xalign(0.5)
        page.pack_start(self.lbl_install_sub, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_size_request(380, 8)
        self.progress_bar.set_halign(Gtk.Align.CENTER)
        page.pack_start(self.progress_bar, False, False, 10)

        self.lbl_install_status = Gtk.Label(label=t("installer_authenticating", "Authenticating administrator..."))
        self.lbl_install_status.set_xalign(0.5)
        self.lbl_install_status.get_style_context().add_class("info-key")
        page.pack_start(self.lbl_install_status, False, False, 0)

        self.stack.add_named(page, "step3")

    def _build_finish_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.get_style_context().add_class("installer-content")
        page.set_valign(Gtk.Align.CENTER)

        self.finish_icon = Gtk.Label(label="🎉")
        self.finish_icon.set_markup("<span font='48'>✓</span>")
        self.finish_icon.get_style_context().add_class("step-label done")
        page.pack_start(self.finish_icon, False, False, 0)

        pkg_name = self.deb_info.get("package", "phần mềm").title()
        self.finish_title = Gtk.Label(label=f"Cài đặt {pkg_name} thành công!")
        self.finish_title.get_style_context().add_class("installer-title")
        self.finish_title.set_xalign(0.5)
        page.pack_start(self.finish_title, False, False, 0)

        self.finish_sub = Gtk.Label(
            label=f"Phần mềm đã được cài đặt vào hệ thống và sẵn sàng sử dụng.\n"
                  f"Biểu tượng ứng dụng đã được tạo trên thanh Dock và Menu tìm kiếm."
        )
        self.finish_sub.get_style_context().add_class("installer-sub")
        self.finish_sub.set_justify(Gtk.Justification.CENTER)
        self.finish_sub.set_xalign(0.5)
        page.pack_start(self.finish_sub, False, False, 6)

        self.stack.add_named(page, "step4")

    def _update_step_ui(self):
        # Update sidebar active states
        for i, lbl in enumerate(self.step_labels, 1):
            ctx = lbl.get_style_context()
            ctx.remove_class("active")
            ctx.remove_class("done")
            if i == self.current_step:
                ctx.add_class("active")
            elif i < self.current_step:
                ctx.add_class("done")

        # Update buttons
        if self.current_step == 1:
            self.btn_back.hide()
            self.btn_next.set_label("Tiếp tục ›")
            self.btn_next.get_style_context().remove_class("btn-success")
            self.btn_next.get_style_context().add_class("btn-primary")
            self.btn_cancel.set_sensitive(True)
            self.stack.set_visible_child_name("step1")
        elif self.current_step == 2:
            self.btn_back.show()
            self.btn_next.set_label("Cài đặt gói .deb")
            self.btn_next.get_style_context().remove_class("btn-success")
            self.btn_next.get_style_context().add_class("btn-primary")
            self.btn_cancel.set_sensitive(True)
            self.stack.set_visible_child_name("step2")
        elif self.current_step == 3:
            self.btn_back.hide()
            self.btn_next.hide()
            self.btn_cancel.set_sensitive(False)
            self.stack.set_visible_child_name("step3")
        elif self.current_step == 4:
            self.btn_back.hide()
            self.btn_cancel.hide()
            self.btn_next.show()
            if self.install_success:
                self.btn_next.set_label("Mở ứng dụng")
                self.btn_next.get_style_context().remove_class("btn-primary")
                self.btn_next.get_style_context().add_class("btn-success")
            else:
                self.btn_next.set_label("Đóng")
                self.btn_next.get_style_context().remove_class("btn-success")
                self.btn_next.get_style_context().add_class("btn-primary")
            self.stack.set_visible_child_name("step4")

    def _on_next_clicked(self, btn):
        if self.current_step == 1:
            self.current_step = 2
            self._update_step_ui()
        elif self.current_step == 2:
            self.current_step = 3
            self._update_step_ui()
            self._start_installation()
        elif self.current_step == 4:
            if self.install_success:
                self._launch_installed_deb()
            self.close()

    def _on_back_clicked(self, btn):
        if self.current_step == 2:
            self.current_step = 1
            self._update_step_ui()

    def _start_installation(self):
        """Perform real APT/DPKG installation with dependency resolution in background."""
        self._pulse_active = True

        def _pulse():
            if self._pulse_active:
                self.progress_bar.pulse()
                return True
            return False

        GLib.timeout_add(100, _pulse)

        def _install_worker():
            success = False
            err_msg = ""
            pkg_name = self.deb_info.get("package", "")

            # Use one non-interactive APT transaction.  pkexec is only needed
            # for an unprivileged process, avoiding repeated auth prompts and
            # the apt progress UI waiting forever for terminal input.
            env = os.environ.copy()
            env.update({"DEBIAN_FRONTEND": "noninteractive",
                        "APT_LISTCHANGES_FRONTEND": "none",
                        "NEEDRESTART_MODE": "a"})
            prefix = [] if os.geteuid() == 0 else ["pkexec"]
            cmd = prefix + ["apt-get", "install", "-y", self.deb_path]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
                if res.returncode == 0:
                    success = True
                else:
                    # Fallback to dpkg -i + apt install -f
                    res_dpkg = subprocess.run(prefix + ["dpkg", "-i", self.deb_path], capture_output=True, text=True, env=env, timeout=300)
                    if res_dpkg.returncode == 0:
                        success = True
                    else:
                        res_fix = subprocess.run(prefix + ["apt-get", "-f", "install", "-y"], capture_output=True, text=True, env=env, timeout=600)
                        if res_fix.returncode == 0:
                            success = True
                        else:
                            err_msg = res.stderr or res_dpkg.stderr or "Lỗi cài đặt gói."
            except Exception as e:
                err_msg = str(e)

            # Update desktop database
            subprocess.run(["update-desktop-database", os.path.expanduser("~/.local/share/applications/")], capture_output=True)

            self._pulse_active = False
            GLib.idle_add(self._on_installation_finished, success, err_msg)

        threading.Thread(target=_install_worker, daemon=True).start()

    def _on_installation_finished(self, success: bool, err_msg: str):
        self.install_success = success
        self.current_step = 4
        pkg_name = self.deb_info.get("package", "phần mềm").title()

        if success:
            self.finish_icon.set_markup("<span font='48' color='#34c759'>✓</span>")
            self.finish_title.set_text(f"Cài đặt {pkg_name} thành công!")
            self.finish_sub.set_text(
                f"Phần mềm {pkg_name} đã được cài đặt vào hệ thống và sẵn sàng sử dụng.\n"
                f"Bạn có thể mở ứng dụng ngay hoặc tìm trong Menu ứng dụng."
            )
        else:
            self.finish_icon.set_markup("<span font='48' color='#ff3b30'>✕</span>")
            self.finish_title.set_text(f"Không thể cài đặt {pkg_name}")
            self.finish_sub.set_text(f"Đã xảy ra lỗi trong quá trình cài đặt:\n{err_msg[:250]}")

        self._update_step_ui()

    def _launch_installed_deb(self):
        """Launch the newly installed application."""
        pkg = self.deb_info.get("package", "")
        if not pkg:
            return

        pkg_l = pkg.lower()

        # 1. Try binary directly
        for bin_name in [pkg, pkg_l, pkg_l.replace("-", ""), pkg_l.split("-")[0]]:
            if shutil.which(bin_name):
                try:
                    subprocess.Popen([bin_name], start_new_session=True)
                    return
                except Exception:
                    pass

        # 2. Try desktop files
        search_dirs = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/snapd/desktop/applications",
        ]

        # Exact match first
        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for name in [f"{pkg}.desktop", f"{pkg_l}.desktop"]:
                cand = os.path.join(d, name)
                if os.path.exists(cand):
                    try:
                        subprocess.Popen(["gtk-launch", name], start_new_session=True)
                        return
                    except Exception:
                        pass

        # Fuzzy / prefix search
        for d in search_dirs:
            if not os.path.exists(d):
                continue
            try:
                for fname in os.listdir(d):
                    if not fname.endswith(".desktop"):
                        continue
                    fname_l = fname.lower()
                    if pkg_l in fname_l:
                        try:
                            subprocess.Popen(["gtk-launch", fname], start_new_session=True)
                            return
                        except Exception:
                            pass
            except Exception:
                pass

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False
