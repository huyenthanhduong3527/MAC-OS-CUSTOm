"""
macOS Sequoia AirDrop Window for Ubuntu Linux.
Authentic Apple AirDrop user experience featuring:
- Pulsing concentric radar rings animation (Cairo custom rendering)
- Local device discovery & display (iPhones, iPads, Macs, Linux PCs, Android)
- Drag-and-drop file transfer onto devices
- Mobile WebDrop integration: Native QR Code scanning for iPhone/iPad/Android
- Live transfer progress bar and incoming transfer authorization modal
- Full macOS Sequoia dark/light frosted glass aesthetic
- Dock integration with official Apple AirDrop icon
"""

import os
import sys
import math
import time
import subprocess
import threading
import urllib.parse
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, Gio

from src.modules.airdrop import AirDropManager, get_local_ip, get_machine_name, DOWNLOADS_DIR
from src.utils.theme import is_dark_mode
from src.utils.qrcodegen import QrCode
from src.utils.icons import get_image, get_pixbuf
from src.utils.i18n import t, add_language_listener

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AIRDROP_ICON_PATH = os.path.join(PROJECT_ROOT, "assets", "airdrop_icon.png")


class TrafficLightsWidget(Gtk.Box):
    """macOS Window Control Traffic Lights: 🔴 Red, 🟡 Yellow, 🟢 Green."""
    def __init__(self, on_close, on_minimize, on_maximize):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_start(4)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_valign(Gtk.Align.CENTER)

        def make_light(color_class, tooltip, symbol, cb):
            btn = Gtk.Button()
            btn.set_size_request(13, 13)
            btn.set_valign(Gtk.Align.CENTER)
            btn.set_halign(Gtk.Align.CENTER)
            btn.get_style_context().add_class("mac-traffic-light")
            btn.get_style_context().add_class(color_class)
            btn.set_tooltip_text(tooltip)
            lbl = Gtk.Label(label="")
            lbl.get_style_context().add_class("tl-symbol")
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_halign(Gtk.Align.CENTER)
            btn.add(lbl)

            btn.connect("enter-notify-event", lambda b, e: [lbl.set_text(symbol), False][1])
            btn.connect("leave-notify-event", lambda b, e: [lbl.set_text(""), False][1])
            btn.connect("clicked", lambda _: cb())
            return btn

        self.pack_start(make_light("tl-red", t("tl_close", "Đóng"), "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", t("tl_minimize", "Thu nhỏ"), "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", t("tl_zoom", "Phóng to"), "⤢", on_maximize), False, False, 0)


class QRCodeWidget(Gtk.DrawingArea):
    """
    Renders a high-resolution, pixel-crisp QR code on a rounded white card.
    Easily scannable by iPhone Camera in all lighting conditions.
    """
    def __init__(self, url: str, size: int = 220):
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

        # White rounded card background with soft shadow
        r = 16.0
        cr.save()
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi/2)
        cr.arc(r, h - r, r, math.pi/2, math.pi)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.fill_preserve()

        # Subtle border
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.08)
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
        cr.set_source_rgb(0.05, 0.05, 0.08) # Crisp dark charcoal modules
        for y in range(qr_size):
            for x in range(qr_size):
                if self.qr.get_module(x, y):
                    mx = offset_x + (x + quiet_zone) * module_scale
                    my = offset_y + (y + quiet_zone) * module_scale
                    cr.rectangle(mx, my, module_scale + 0.3, module_scale + 0.3)
        cr.fill()

        # Mini AirDrop badge in center
        center_x = w / 2.0
        center_y = h / 2.0
        badge_r = module_scale * 2.8

        # Badge white background
        cr.arc(center_x, center_y, badge_r + 2, 0, 2 * math.pi)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.fill()

        # Badge blue circle
        cr.arc(center_x, center_y, badge_r, 0, 2 * math.pi)
        cr.set_source_rgb(0.0, 0.48, 1.0)
        cr.fill()

        # Badge white arcs
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Center dot
        cr.arc(center_x, center_y + 1, 1.5, 0, 2 * math.pi)
        cr.fill()

        # Ring 1
        cr.set_line_width(1.2)
        cr.arc(center_x, center_y + 1, 4.0, 3*math.pi/4, 9*math.pi/4)
        cr.stroke()

        # Ring 2
        cr.set_line_width(1.2)
        cr.arc(center_x, center_y + 1, 7.0, 3*math.pi/4, 9*math.pi/4)
        cr.stroke()

        cr.restore()
        return False


class iOSShortcutGuideDialog(Gtk.Dialog):
    """
    Step-by-step Apple Shortcuts guide for 1-tap iPhone photo sharing
    directly to Linux Downloads without opening a browser or URL.
    """
    def __init__(self, parent, api_url: str):
        super().__init__(
            title="Hướng dẫn phím tắt iPhone (Gửi ảnh 1 chạm)",
            parent=parent,
            modal=True,
            destroy_with_parent=True
        )
        self.set_default_size(480, 520)
        self.api_url = api_url

        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(12)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label()
        title.set_markup("<span font='14' weight='bold' color='#ffffff'>📲 Gửi ảnh từ iPhone không cần vào link</span>")
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label()
        subtitle.set_markup("<span font='10' color='#a1a1a6'>Chỉ cần cài 1 lần trong ứng dụng <b>Phím tắt (Shortcuts)</b> trên iPhone</span>")
        header.pack_start(subtitle, False, False, 0)
        content.pack_start(header, False, False, 0)

        # Steps container
        steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        steps_box.get_style_context().add_class("mac-qr-url-card")

        steps = [
            ("1. Tạo phím tắt mới", "Mở ứng dụng <b>Phím tắt</b> trên iPhone > Bấm dấu <b>[+]</b> > Đổi tên thành <b>\"Gửi sang Máy tính\"</b>."),
            ("2. Bật bảng chia sẻ", "Bấm chữ <b>(i)</b> ở thanh dưới > Bật <b>\"Hiển thị trong bảng chia sẻ\"</b> (Show in Share Sheet)."),
            ("3. Thêm tác vụ gửi file", "Thêm tác vụ <b>\"Lấy nội dung từ URL\"</b> (Get Contents of URL):\n"
                                        "• <b>URL:</b> <tt>" + api_url + "</tt>\n"
                                        "• <b>Phương thức:</b> POST\n"
                                        "• <b>Tiêu đề (Header):</b> Thêm <tt>X-Filename</tt> = [Đầu vào phím tắt > Tên]\n"
                                        "• <b>Phần thân:</b> Chọn [Tệp] = [Đầu vào phím tắt]"),
            ("4. Sử dụng mọi lúc", "Mở <b>Ảnh</b> > Chọn các ảnh cần gửi > Bấm <b>Chia sẻ 📤</b> > Chọn <b>\"Gửi sang Máy tính\"</b>. Ảnh sẽ bay thẳng về thư mục Tải về!")
        ]

        for step_title, step_desc in steps:
            s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl_title = Gtk.Label()
            lbl_title.set_markup(f"<span font='10.5' weight='bold' color='#0a84ff'>{step_title}</span>")
            lbl_title.set_halign(Gtk.Align.START)
            s_box.pack_start(lbl_title, False, False, 0)

            lbl_desc = Gtk.Label()
            lbl_desc.set_markup(f"<span font='9.5' color='#e5e5ea'>{step_desc}</span>")
            lbl_desc.set_halign(Gtk.Align.START)
            lbl_desc.set_line_wrap(True)
            s_box.pack_start(lbl_desc, False, False, 0)
            steps_box.pack_start(s_box, False, False, 0)

        content.pack_start(steps_box, False, False, 0)

        # Copy API URL button
        btn_copy_api = Gtk.Button(label="📋 Sao chép URL API (" + api_url + ")")
        btn_copy_api.get_style_context().add_class("mac-btn-secondary")
        def _copy_api(_):
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.set_text(self.api_url, -1)
            btn_copy_api.set_label("✓ Đã chép URL API!")
            GLib.timeout_add(2000, lambda: [btn_copy_api.set_label("📋 Sao chép URL API (" + self.api_url + ")"), False][1])
        btn_copy_api.connect("clicked", _copy_api)
        content.pack_start(btn_copy_api, False, False, 0)

        # Close
        btn_close = Gtk.Button(label="Đóng")
        btn_close.get_style_context().add_class("mac-btn-primary")
        btn_close.connect("clicked", lambda _: self.destroy())
        self.add_action_widget(btn_close, Gtk.ResponseType.CLOSE)

        self.connect("key-press-event", lambda w, e: self.destroy() if e.keyval == Gdk.KEY_Escape else False)
        self.show_all()


class AirDropQRDialog(Gtk.Dialog):
    """
    Dedicated macOS-styled Modal Dialog showcasing the live QR Code
    for instant iPhone & iPad connectivity without typing any URL.
    """
    def __init__(self, parent, url: str):
        super().__init__(
            title=t("airdrop_qr_dialog_title", "Quét mã QR để kết nối iPhone & iPad"),
            parent=parent,
            modal=True,
            destroy_with_parent=True
        )
        self.set_default_size(440, 560)
        self.url = url
        self.api_url = f"{url}/api/upload"

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(14)
        content.set_margin_bottom(8)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title = Gtk.Label()
        title.set_markup(f"<span font='14.5' weight='bold' color='#ffffff'>{t('airdrop_qr_scan_title', '📱 Quét mã bằng iPhone để kết nối')}</span>")
        title_box.pack_start(title, False, False, 0)

        desc = Gtk.Label()
        desc_text = t("airdrop_qr_scan_desc", "Mở ứng dụng <b>Camera</b> trên iPhone / iPad\nvà quét mã QR bên dưới để mở AirDrop Web ngay lập tức.")
        desc.set_markup(f"<span font='10' color='#a1a1a6'>{desc_text}</span>")
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_line_wrap(True)
        title_box.pack_start(desc, False, False, 0)
        content.pack_start(title_box, False, False, 0)

        # Centered QR Code Widget
        qr_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        qr_container.set_halign(Gtk.Align.CENTER)
        self.qr_widget = QRCodeWidget(url, size=180)
        qr_container.pack_start(self.qr_widget, False, False, 0)
        content.pack_start(qr_container, False, False, 0)

        # URL Card (URL + Copy Button + Status)
        url_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        url_card.get_style_context().add_class("mac-qr-url-card")
        url_card.set_halign(Gtk.Align.FILL)

        url_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        url_row.set_halign(Gtk.Align.CENTER)

        url_lbl = Gtk.Label()
        url_lbl.set_markup(f"<span font='11' font_family='monospace' weight='bold' color='#0a84ff'>{url}</span>")
        url_lbl.set_selectable(True)
        url_row.pack_start(url_lbl, False, False, 0)

        btn_copy = Gtk.Button(label=t("copy", "📋 Sao chép"))
        btn_copy.get_style_context().add_class("mac-btn-secondary")
        def _copy(_):
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.set_text(self.url, -1)
            btn_copy.set_label(t("copied", "✓ Đã chép!"))
            GLib.timeout_add(2000, lambda: [btn_copy.set_label(t("copy", "📋 Sao chép")), False][1])
        btn_copy.connect("clicked", _copy)
        url_row.pack_start(btn_copy, False, False, 0)

        url_card.pack_start(url_row, False, False, 0)

        status_lbl = Gtk.Label()
        status_lbl.set_markup(f"<span font='9.5' color='#34c759'>{t('airdrop_server_active', '● Máy chủ AirDrop đang hoạt động trên Wi-Fi')}</span>")
        url_card.pack_start(status_lbl, False, False, 0)
        content.pack_start(url_card, False, False, 0)

        # Shortcut Tip Card
        tip_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tip_card.get_style_context().add_class("mac-qr-url-card")
        tip_card.set_halign(Gtk.Align.FILL)

        tip_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        tip_vbox.set_hexpand(True)
        tip_title = Gtk.Label()
        tip_title.set_markup(f"<span font='10' weight='bold' color='#ffffff'>{t('airdrop_shortcut_title', '⚡ Gửi ảnh 1 chạm (Không cần vào link)')}</span>")
        tip_title.set_halign(Gtk.Align.START)
        tip_vbox.pack_start(tip_title, False, False, 0)

        tip_desc = Gtk.Label()
        tip_desc.set_markup(f"<span font='9' color='#a1a1a6'>{t('airdrop_shortcut_desc', 'Dùng Phím tắt iOS để gửi ảnh trực tiếp từ nút Chia sẻ 📤')}</span>")
        tip_desc.set_halign(Gtk.Align.START)
        tip_vbox.pack_start(tip_desc, False, False, 0)
        tip_card.pack_start(tip_vbox, True, True, 0)

        btn_guide = Gtk.Button(label=t("airdrop_shortcut_btn", "📖 Xem cách cài"))
        btn_guide.get_style_context().add_class("mac-btn-secondary")
        btn_guide.connect("clicked", lambda _: self._show_shortcut_guide())
        tip_card.pack_start(btn_guide, False, False, 0)

        content.pack_start(tip_card, False, False, 0)

        # Action Area Buttons (bottom)
        btn_open = Gtk.Button(label=t("airdrop_open_browser", "🌐 Mở trên máy"))
        btn_open.get_style_context().add_class("mac-btn-secondary")
        btn_open.connect("clicked", lambda _: subprocess.Popen(["xdg-open", self.url]))
        self.add_action_widget(btn_open, Gtk.ResponseType.NONE)

        btn_close = Gtk.Button(label=t("tl_close", "Đóng"))
        btn_close.get_style_context().add_class("mac-btn-primary")
        btn_close.connect("clicked", lambda _: self.destroy())
        self.add_action_widget(btn_close, Gtk.ResponseType.CLOSE)

        self.connect("key-press-event", lambda w, e: self.destroy() if e.keyval == Gdk.KEY_Escape else False)
        self.show_all()

    def _show_shortcut_guide(self):
        guide = iOSShortcutGuideDialog(self, self.api_url)
        guide.run()
        guide.destroy()


class AirDropRadarWidget(Gtk.DrawingArea):
    """
    Renders the iconic Apple AirDrop animated concentric radar rings
    and interactive nearby devices with pixel-perfect balance.
    """
    def __init__(self, airdrop_mgr: AirDropManager, on_device_selected=None):
        super().__init__()
        self.airdrop_mgr = airdrop_mgr
        self.on_device_selected = on_device_selected

        self.pulse_phase = 0.0
        self.hovered_device_id = None
        self.devices = []

        self.set_size_request(600, 380)
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("button-press-event", self._on_click)
        self.connect("leave-notify-event", self._on_leave)

        # Smooth 30 FPS pulse animation
        self._anim_timer = GLib.timeout_add(33, self._on_anim_tick)

    def destroy(self):
        if self._anim_timer:
            GLib.source_remove(self._anim_timer)
            self._anim_timer = None

    def update_devices(self):
        self.devices = self.airdrop_mgr.get_discovered_devices()
        self.queue_draw()

    def _on_anim_tick(self):
        self.pulse_phase = (self.pulse_phase + 0.015) % 1.0
        self.queue_draw()
        return True

    def _on_leave(self, widget, event):
        if self.hovered_device_id is not None:
            self.hovered_device_id = None
            self.queue_draw()
        return False

    def _get_device_positions(self, cx, cy, radius):
        """Calculate balanced circular layout positions for discovered peers."""
        count = len(self.devices)
        if count == 0:
            return []

        positions = []
        angle_step = (2 * math.pi) / max(1, count)
        for i, dev in enumerate(self.devices):
            angle = i * angle_step - (math.pi / 2) # Start from top
            dist = radius * 0.70
            dx = cx + dist * math.cos(angle)
            dy = cy + dist * math.sin(angle)
            positions.append((dev, dx, dy, 34)) # (device, x, y, hit_radius)
        return positions

    def _on_motion(self, widget, event):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0 - 14 # Balanced vertical anchor
        max_r = min(cx, cy + 14) * 0.88

        old_hover = self.hovered_device_id
        self.hovered_device_id = None

        for dev, dx, dy, hit_r in self._get_device_positions(cx, cy, max_r):
            dist = math.hypot(event.x - dx, event.y - dy)
            if dist <= hit_r:
                self.hovered_device_id = dev.get("id") or dev.get("ip")
                break

        if old_hover != self.hovered_device_id:
            self.queue_draw()
        return False

    def _on_click(self, widget, event):
        if event.button == 1:
            w = widget.get_allocated_width()
            h = widget.get_allocated_height()
            cx = w / 2.0
            cy = h / 2.0 - 14
            max_r = min(cx, cy + 14) * 0.88

            for dev, dx, dy, hit_r in self._get_device_positions(cx, cy, max_r):
                dist = math.hypot(event.x - dx, event.y - dy)
                if dist <= hit_r:
                    if self.on_device_selected:
                        self.on_device_selected(dev)
                    return True
        return False

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Strictly centered anchor accounting for text labels below the center badge
        cx = w / 2.0
        cy = h / 2.0 - 14
        max_r = min(cx, cy + 14) * 0.88

        is_dark = is_dark_mode()

        # 1. Background concentric radar rings
        cr.save()
        num_rings = 4
        for i in range(1, num_rings + 1):
            r = (max_r / num_rings) * i
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            if is_dark:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.06)
            else:
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.06)
            cr.set_line_width(1.0)
            cr.stroke()

        # 2. Pulsing wave animation radiating outward
        pulse_r = max_r * self.pulse_phase
        pulse_alpha = (1.0 - self.pulse_phase) * 0.28
        cr.arc(cx, cy, pulse_r, 0, 2 * math.pi)
        cr.set_source_rgba(0.04, 0.52, 1.0, pulse_alpha) # Apple blue wave
        cr.set_line_width(2.2)
        cr.stroke()
        cr.restore()

        # 3. Center Host Mac Avatar / Badge
        cr.save()
        center_r = 34

        # Outer soft glow
        cr.arc(cx, cy, center_r + 6, 0, 2 * math.pi)
        cr.set_source_rgba(0.0, 0.48, 1.0, 0.22)
        cr.fill()

        # Inner circular gradient badge
        pat = cairo.LinearGradient(cx, cy - center_r, cx, cy + center_r)
        pat.add_color_stop_rgba(0.0, 0.08, 0.54, 1.0, 1.0) # #148aff
        pat.add_color_stop_rgba(1.0, 0.0, 0.40, 0.88, 1.0) # #0066e0
        cr.arc(cx, cy, center_r, 0, 2 * math.pi)
        cr.set_source(pat)
        cr.fill_preserve()

        # Crisp border
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.4)
        cr.set_line_width(1.5)
        cr.stroke()

        # Center device icon: High-contrast Apple Mac Laptop
        self._draw_macbook_icon(cr, cx, cy - 2, 28)

        # Center label (Device name)
        pctx = self.get_pango_context()
        layout = Pango.Layout(pctx)
        layout.set_text(get_machine_name(), -1)
        desc = Pango.FontDescription("SF Pro Text Bold 10.5")
        layout.set_font_description(desc)
        ink, log = layout.get_pixel_extents()
        cr.move_to(cx - log.width / 2.0, cy + center_r + 8)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        PangoCairo.show_layout(cr, layout)

        # Sub-label ("• Thiết bị này")
        sub_layout = Pango.Layout(pctx)
        sub_layout.set_text(t("airdrop_this_device", "• Thiết bị này"), -1)
        sub_desc = Pango.FontDescription("SF Pro Text 8.5")
        sub_layout.set_font_description(sub_desc)
        s_ink, s_log = sub_layout.get_pixel_extents()
        cr.move_to(cx - s_log.width / 2.0, cy + center_r + 24)
        cr.set_source_rgba(0.2, 0.75, 1.0, 0.9)
        PangoCairo.show_layout(cr, sub_layout)
        cr.restore()

        # 4. Discovered Nearby Devices
        positions = self._get_device_positions(cx, cy, max_r)
        for dev, dx, dy, hit_r in positions:
            dev_id = dev.get("id") or dev.get("ip")
            is_hover = (dev_id == self.hovered_device_id)

            cr.save()
            # Device circle
            cr.arc(dx, dy, hit_r, 0, 2 * math.pi)
            if is_hover:
                cr.set_source_rgba(0.0, 0.48, 1.0, 0.35)
                cr.fill_preserve()
                cr.set_source_rgba(0.0, 0.48, 1.0, 0.95)
                cr.set_line_width(2.5)
                cr.stroke()
            else:
                cr.set_source_rgba(0.20, 0.20, 0.24, 0.95)
                cr.fill_preserve()
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
                cr.set_line_width(1.2)
                cr.stroke()

            # Device icon
            dev_type = dev.get("type", "iphone").lower()
            if "iphone" in dev_type or "phone" in dev_type:
                self._draw_phone_icon(cr, dx, dy, 26)
            elif "ipad" in dev_type or "tablet" in dev_type:
                self._draw_tablet_icon(cr, dx, dy, 26)
            else:
                self._draw_macbook_icon(cr, dx, dy, 26)

            # Device name label
            dev_name = dev.get("name") or dev.get("ip")
            d_layout = Pango.Layout(pctx)
            d_layout.set_text(dev_name, -1)
            d_layout.set_font_description(Pango.FontDescription("SF Pro Text Medium 10"))
            d_ink, d_log = d_layout.get_pixel_extents()
            cr.move_to(dx - d_log.width / 2.0, dy + hit_r + 6)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95 if is_hover else 0.85)
            PangoCairo.show_layout(cr, d_layout)

            # Ready to share sub-label
            r_layout = Pango.Layout(pctx)
            r_layout.set_text(t("airdrop_tap_to_send", "Chạm để gửi tệp"), -1)
            r_layout.set_font_description(Pango.FontDescription("SF Pro Text 8.5"))
            r_ink, r_log = r_layout.get_pixel_extents()
            cr.move_to(dx - r_log.width / 2.0, dy + hit_r + 22)
            cr.set_source_rgba(0.0, 0.55, 1.0, 0.95 if is_hover else 0.7)
            PangoCairo.show_layout(cr, r_layout)

            cr.restore()

        # 5. Bottom Radar Status Hint (when scanning)
        if len(self.devices) == 0:
            cr.save()
            hint_layout = Pango.Layout(pctx)
            hint_layout.set_text(t("airdrop_scanning_hint", "Đang quét các thiết bị lân cận qua Wi-Fi & Mạng nội bộ…"), -1)
            hint_layout.set_font_description(Pango.FontDescription("SF Pro Text 10"))
            h_ink, h_log = hint_layout.get_pixel_extents()
            cr.move_to(cx - h_log.width / 2.0, h - 28)
            cr.set_source_rgba(0.65, 0.65, 0.70, 0.85)
            PangoCairo.show_layout(cr, hint_layout)
            cr.restore()

        return False

    def _draw_macbook_icon(self, cr, x, y, size):
        """Draw crisp Apple MacBook silhouette with screen and base."""
        cr.save()
        w = size * 0.82
        h = size * 0.54

        # Laptop Screen (rounded rect)
        sx = x - w/2
        sy = y - h/2 - 2
        r = 2.0

        cr.new_sub_path()
        cr.arc(sx + w - r, sy + r, r, -math.pi/2, 0)
        cr.arc(sx + w - r, sy + h - r, r, 0, math.pi/2)
        cr.arc(sx + r, sy + h - r, r, math.pi/2, math.pi)
        cr.arc(sx + r, sy + r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        # Screen fill & stroke
        cr.set_source_rgba(0.08, 0.12, 0.20, 0.95)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        cr.set_line_width(1.6)
        cr.stroke()

        # Screen inner glow / display
        cr.rectangle(sx + 3, sy + 3, w - 6, h - 6)
        cr.set_source_rgba(0.3, 0.7, 1.0, 0.35)
        cr.fill()

        # Laptop Base
        bw = size * 0.98
        by = sy + h + 1
        cr.move_to(x - bw/2, by)
        cr.line_to(x + bw/2, by)
        cr.line_to(x + bw/2 - 2, by + 3.0)
        cr.line_to(x - bw/2 + 2, by + 3.0)
        cr.close_path()
        cr.set_source_rgba(0.9, 0.92, 0.96, 0.95)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.8)
        cr.set_line_width(1.2)
        cr.stroke()

        # Trackpad notch
        cr.move_to(x - 4, by)
        cr.line_to(x + 4, by)
        cr.set_source_rgba(0.2, 0.2, 0.25, 0.9)
        cr.set_line_width(1.2)
        cr.stroke()

        cr.restore()

    def _draw_phone_icon(self, cr, x, y, size):
        """Draw crisp iPhone silhouette with Dynamic Island notch."""
        cr.save()
        w = size * 0.52
        h = size * 0.92
        r = 4.0

        sx = x - w/2
        sy = y - h/2

        cr.new_sub_path()
        cr.arc(sx + w - r, sy + r, r, -math.pi/2, 0)
        cr.arc(sx + w - r, sy + h - r, r, 0, math.pi/2)
        cr.arc(sx + r, sy + h - r, r, math.pi/2, math.pi)
        cr.arc(sx + r, sy + r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        # Body fill
        cr.set_source_rgba(0.12, 0.12, 0.16, 0.95)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        cr.set_line_width(1.6)
        cr.stroke()

        # Screen glass
        cr.rectangle(sx + 2.5, sy + 3.5, w - 5, h - 7)
        cr.set_source_rgba(0.0, 0.48, 1.0, 0.25)
        cr.fill()

        # Dynamic Island pill
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.9)
        pill_w = 7.0
        pill_h = 2.4
        cr.new_sub_path()
        cr.arc(x + pill_w/2 - 1.2, sy + 4.5, 1.2, -math.pi/2, math.pi/2)
        cr.arc(x - pill_w/2 + 1.2, sy + 4.5, 1.2, math.pi/2, 3*math.pi/2)
        cr.close_path()
        cr.fill()
        cr.restore()

        cr.restore()

    def _draw_tablet_icon(self, cr, x, y, size):
        """Draw crisp iPad silhouette."""
        cr.save()
        w = size * 0.72
        h = size * 0.92
        r = 4.0
        sx = x - w/2
        sy = y - h/2

        cr.new_sub_path()
        cr.arc(sx + w - r, sy + r, r, -math.pi/2, 0)
        cr.arc(sx + w - r, sy + h - r, r, 0, math.pi/2)
        cr.arc(sx + r, sy + h - r, r, math.pi/2, math.pi)
        cr.arc(sx + r, sy + r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        cr.set_source_rgba(0.12, 0.12, 0.16, 0.95)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        cr.set_line_width(1.6)
        cr.stroke()

        # Screen glass
        cr.rectangle(sx + 3, sy + 3.5, w - 6, h - 7)
        cr.set_source_rgba(0.0, 0.48, 1.0, 0.25)
        cr.fill()

        cr.restore()


class MacOSAirDropWindow(Gtk.Window):
    """
    Authentic macOS Sequoia AirDrop Window with dock integration and QR Code support.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MacOSAirDropWindow()
        return cls._instance

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        GLib.set_prgname("macos-airdrop")
        if not GLib.get_application_name():
            GLib.set_application_name("AirDrop")
        self.set_title("AirDrop")
        self.set_wmclass("macos-airdrop", "MacOSAirDrop")
        self.set_role("airdrop")
        self._is_iconified = False

        # Window & Dock Icon
        if os.path.exists(AIRDROP_ICON_PATH):
            try:
                self.set_icon_from_file(AIRDROP_ICON_PATH)
            except Exception as e:
                print(f"[AirDrop] Error loading icon from file: {e}")
        self.set_icon_name("macos-airdrop")

        self.set_default_size(780, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_resizable(True)

        geom = Gdk.Geometry()
        geom.min_width = 640
        geom.min_height = 480
        self.set_geometry_hints(None, geom, Gdk.WindowHints.MIN_SIZE)

        self._is_maximized = False
        self.airdrop_mgr = AirDropManager.get_instance()
        self.airdrop_mgr.on_device_list_changed = self._on_device_list_changed
        self.airdrop_mgr.on_transfer_event = self._on_transfer_event

        # RGBA Visual for smooth rounded window corners
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        self._setup_ui()
        self._load_css()
        self.set_title(t("airdrop_title", "AirDrop"))
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

        self.connect("draw", self._on_window_draw)
        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_key_press)
        self.connect("window-state-event", self._on_window_state_event)

        # Setup Drag and Drop reception on the window
        self.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [],
            Gdk.DragAction.COPY
        )
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self._on_drag_data_received)

    def _setup_ui(self):
        self.master_overlay = Gtk.Overlay()
        self.add(self.master_overlay)

        self.root_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root_card.get_style_context().add_class("mac-airdrop-window")
        self.master_overlay.add(self.root_card)

        self._setup_resize_handles()

        # ==================== TOP HEADER (3-Column Grid for Exact Center) ====================
        header_event_box = Gtk.EventBox()
        header_event_box.set_visible_window(False)
        header_event_box.connect("button-press-event", self._on_header_button_press)
        self.root_card.pack_start(header_event_box, False, False, 0)

        header_grid = Gtk.Grid()
        header_grid.set_column_homogeneous(False)
        header_grid.set_margin_start(16)
        header_grid.set_margin_end(16)
        header_grid.set_margin_top(12)
        header_grid.set_margin_bottom(8)
        header_event_box.add(header_grid)

        # Column 0: Traffic Lights (Left-aligned, expands to push center)
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left_box.set_hexpand(True)
        left_box.set_halign(Gtk.Align.START)
        left_box.set_valign(Gtk.Align.CENTER)
        tl = TrafficLightsWidget(
            on_close=self.hide_window,
            on_minimize=self.iconify,
            on_maximize=self.toggle_maximize
        )
        left_box.pack_start(tl, False, False, 0)
        header_grid.attach(left_box, 0, 0, 1, 1)

        # Column 1: Title (Strictly centered at 50% width)
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        self.title_lbl = Gtk.Label(label=t("airdrop_title", "AirDrop"))
        self.title_lbl.get_style_context().add_class("mac-airdrop-title")
        center_box.pack_start(self.title_lbl, False, False, 0)
        header_grid.attach(center_box, 1, 0, 1, 1)

        # Column 2: Right-aligned quick action (Expands equally to match Left box)
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_box.set_hexpand(True)
        right_box.set_halign(Gtk.Align.END)
        right_box.set_valign(Gtk.Align.CENTER)

        self.btn_header_qr = Gtk.Button(label=t("airdrop_header_qr", "📷 Mã QR iPhone"))
        self.btn_header_qr.get_style_context().add_class("mac-btn-header-qr")
        self.btn_header_qr.set_tooltip_text(t("airdrop_header_qr_tooltip", "Mở mã QR để kết nối nhanh iPhone / iPad"))
        self.btn_header_qr.connect("clicked", self._show_webdrop_dialog)
        right_box.pack_end(self.btn_header_qr, False, False, 0)
        header_grid.attach(right_box, 2, 0, 1, 1)

        # ==================== CENTRAL RADAR AREA ====================
        self.radar_widget = AirDropRadarWidget(
            self.airdrop_mgr,
            on_device_selected=self._on_device_clicked
        )
        self.root_card.pack_start(self.radar_widget, True, True, 0)

        # ==================== BOTTOM TOOLBAR (Balanced 3-Section) ====================
        bottom_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bottom_container.set_margin_start(20)
        bottom_container.set_margin_end(20)
        bottom_container.set_margin_top(8)
        bottom_container.set_margin_bottom(16)
        self.root_card.pack_end(bottom_container, False, False, 0)

        # Row 1: Actions & Discoverability
        toolbar_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bottom_container.pack_start(toolbar_row, False, False, 0)

        # Left: Discoverability Dropdown
        disc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.disc_lbl = Gtk.Label(label=t("airdrop_discoverable_label", "Cho phép phát hiện:"))
        self.disc_lbl.get_style_context().add_class("mac-disc-label")
        disc_box.pack_start(self.disc_lbl, False, False, 0)

        self.disc_combo = Gtk.ComboBoxText()
        self.disc_combo.append("everyone", t("airdrop_everyone", "Mọi người"))
        self.disc_combo.append("contacts", t("airdrop_contacts", "Chỉ danh bạ"))
        self.disc_combo.append("off", t("airdrop_no_one", "Không ai cả"))
        self.disc_combo.set_active_id("everyone")
        self.disc_combo.connect("changed", self._on_disc_changed)
        self.disc_combo.get_style_context().add_class("mac-disc-combo")
        disc_box.pack_start(self.disc_combo, False, False, 0)
        toolbar_row.pack_start(disc_box, False, False, 0)

        # Center: Prominent QR Scan Button (iPhone / Android)
        center_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        center_actions.set_halign(Gtk.Align.CENTER)
        self.btn_webdrop = Gtk.Button(label=t("airdrop_btn_qr", "📷 Quét mã QR kết nối iPhone / iPad"))
        self.btn_webdrop.get_style_context().add_class("mac-btn-webdrop")
        self.btn_webdrop.set_tooltip_text(t("airdrop_btn_qr_tooltip", "Mở mã QR lớn để quét bằng camera điện thoại"))
        self.btn_webdrop.connect("clicked", self._show_webdrop_dialog)
        center_actions.pack_start(self.btn_webdrop, False, False, 0)
        toolbar_row.pack_start(center_actions, True, True, 0)

        # Right: Primary Send File & Send Photo Buttons
        self.btn_send_file = Gtk.Button(label=t("airdrop_btn_send_file", "Chọn tệp để gửi…"))
        self.btn_send_file.get_style_context().add_class("mac-btn-primary")
        self.btn_send_file.connect("clicked", self._on_pick_file_and_send)
        toolbar_row.pack_end(self.btn_send_file, False, False, 0)

        self.btn_send_photo = Gtk.Button(label=t("airdrop_btn_send_photo", "📸 Gửi ảnh từ Photos…"))
        self.btn_send_photo.get_style_context().add_class("mac-btn-webdrop")
        self.btn_send_photo.connect("clicked", self._on_pick_photo_and_send)
        toolbar_row.pack_end(self.btn_send_photo, False, False, 0)

        # Row 2: Status Line
        self.status_lbl = Gtk.Label(label=f"{t('airdrop_ready_to_share', '🟢 Sẵn sàng chia sẻ')} • http://{get_local_ip()}:8765")
        self.status_lbl.get_style_context().add_class("mac-airdrop-status")
        self.status_lbl.set_halign(Gtk.Align.CENTER)
        bottom_container.pack_start(self.status_lbl, False, False, 0)

        # Row 3: Modern Non-Modal Floating Toast Card
        self.toast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.toast_box.get_style_context().add_class("mac-airdrop-toast")
        self.toast_box.set_halign(Gtk.Align.CENTER)
        self.toast_box.set_no_show_all(True)
        bottom_container.pack_start(self.toast_box, False, False, 0)

    def _load_css(self):
        css_data = b"""
        .mac-airdrop-window {
            background-color: rgba(28, 28, 32, 0.94);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.14);
        }
        .mac-airdrop-title {
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 0.2px;
        }
        .mac-disc-label {
            font-size: 12px;
            color: #98989d;
        }
        .mac-disc-combo {
            background: rgba(255, 255, 255, 0.10);
            border-radius: 8px;
            color: #0a84ff;
            font-size: 12px;
            font-weight: 500;
            padding: 2px 6px;
        }
        .mac-btn-header-qr {
            background: rgba(10, 132, 255, 0.15);
            border: 1px solid rgba(10, 132, 255, 0.35);
            border-radius: 10px;
            color: #0a84ff;
            padding: 5px 12px;
            font-weight: 600;
            font-size: 12px;
        }
        .mac-btn-header-qr:hover {
            background: rgba(10, 132, 255, 0.25);
            border-color: #0a84ff;
        }
        .mac-btn-webdrop {
            background: rgba(10, 132, 255, 0.16);
            border: 1px solid rgba(10, 132, 255, 0.45);
            border-radius: 12px;
            color: #38a2ff;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 13px;
        }
        .mac-btn-webdrop:hover {
            background: rgba(10, 132, 255, 0.30);
            border-color: #0a84ff;
            color: #ffffff;
        }
        .mac-btn-primary {
            background: #007aff;
            color: #ffffff;
            border-radius: 12px;
            border: none;
            padding: 8px 20px;
            font-weight: 600;
            font-size: 13px;
        }
        .mac-btn-primary:hover {
            background: #0066d6;
        }
        .mac-btn-secondary {
            background: rgba(255, 255, 255, 0.12);
            color: #ffffff;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            padding: 7px 16px;
            font-weight: 500;
            font-size: 12.5px;
        }
        .mac-btn-secondary:hover {
            background: rgba(255, 255, 255, 0.20);
        }
        .mac-qr-url-card {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 8px 20px;
        }
        .mac-airdrop-status {
            font-size: 11.5px;
            color: #98989d;
        }
        .mac-airdrop-toast {
            background-color: rgba(45, 45, 52, 0.96);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.20);
            padding: 5px 14px;
            margin-top: 6px;
        }
        .mac-airdrop-toast-btn {
            background: rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            border: none;
            color: #ffffff;
            font-size: 11.5px;
            font-weight: 500;
            padding: 4px 10px;
        }
        .mac-airdrop-toast-btn:hover {
            background: rgba(255, 255, 255, 0.22);
        }
        .mac-airdrop-toast-btn.primary {
            background: #007aff;
        }
        .mac-airdrop-toast-btn.primary:hover {
            background: #0a84ff;
        }
        .mac-traffic-light {
            border-radius: 50%;
            min-width: 13px;
            min-height: 13px;
            padding: 0;
            margin: 0;
            border: none;
        }
        .mac-traffic-light .tl-symbol {
            font-size: 7.5px;
            color: rgba(0, 0, 0, 0.65);
            font-weight: 700;
            margin: 0;
            padding: 0;
        }
        .tl-red { background: #ff5f56; }
        .tl-yellow { background: #ffbd2e; }
        .tl-green { background: #27c93f; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css_data)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_window_draw(self, widget, cr):
        if getattr(self, "_is_iconified", False):
            return False
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 0.0 if getattr(self, "_is_maximized", False) else 20.0

        if r > 0:
            cr.set_operator(cairo.Operator.CLEAR)
            cr.paint()
            cr.set_operator(cairo.Operator.OVER)

        # Rounded window mask
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi/2)
        cr.arc(r, h - r, r, math.pi/2, math.pi)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        # Frosted glass background
        cr.set_source_rgba(0.11, 0.11, 0.13, 0.95)
        cr.fill_preserve()

        # Border
        if r > 0:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.14)
            cr.set_line_width(1.0)
            cr.stroke()
        else:
            cr.new_path()
        return False

    def _on_disc_changed(self, combo):
        mode = combo.get_active_id() or "everyone"
        self.airdrop_mgr.set_discoverable_mode(mode)

    def _on_device_list_changed(self):
        self.radar_widget.update_devices()

    def _on_device_clicked(self, device):
        """User clicked a discovered device circle -> prompt to send file or send pending file."""
        if getattr(self, "_pending_send_path", None) and os.path.exists(self._pending_send_path):
            file_path = self._pending_send_path
            self._pending_send_path = None
            self._send_file(device.get("ip"), file_path, device.get("name") or device.get("ip"))
        else:
            self._prompt_send_file_to_device(device)

    def _prompt_send_file_to_device(self, device):
        dev_name = device.get("name") or device.get("ip")
        dev_ip = device.get("ip")

        # Apple-styled prompt dialog offering Photos or Other File
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Gửi tệp tới {dev_name}"
        )
        dialog.format_secondary_text("Bạn muốn chọn ảnh từ ứng dụng Ảnh (macOS Photos) hay duyệt tệp tin khác?")
        dialog.add_button("Hủy", Gtk.ResponseType.CANCEL)
        dialog.add_button("📁 Duyệt tệp khác…", Gtk.ResponseType.APPLY)
        dialog.add_button("📸 Chọn từ Photos", Gtk.ResponseType.OK)

        res = dialog.run()
        dialog.destroy()

        if res == Gtk.ResponseType.OK:
            try:
                from src.ui.macos_photos_window import MacOSPhotosWindow
                MacOSPhotosWindow.open_picker(
                    title=f"Chọn ảnh gửi qua AirDrop tới {dev_name}",
                    parent=self,
                    on_photo_selected=lambda p: self._send_file(dev_ip, p, dev_name)
                )
            except Exception as e:
                print(f"[AirDrop] Error opening photos picker: {e}")
                self._open_file_dialog_for_device(dev_ip, dev_name)
        elif res == Gtk.ResponseType.APPLY:
            self._open_file_dialog_for_device(dev_ip, dev_name)

    def _open_file_dialog_for_device(self, dev_ip, dev_name):
        dialog = Gtk.FileChooserDialog(
            title=f"Gửi tệp qua AirDrop tới {dev_name}",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "Hủy", Gtk.ResponseType.CANCEL,
            "Gửi", Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(False)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            dialog.destroy()
            if file_path:
                self._send_file(dev_ip, file_path, dev_name)
        else:
            dialog.destroy()

    def _on_pick_file_and_send(self, button):
        """Open file chooser to send file."""
        devices = self.airdrop_mgr.get_discovered_devices()
        if not devices:
            self._show_webdrop_dialog(None)
            return

        target = devices[0]
        self._prompt_send_file_to_device(target)

    def _on_pick_photo_and_send(self, button):
        """Open macOS Photos picker to choose and send photos."""
        devices = self.airdrop_mgr.get_discovered_devices()
        target = devices[0] if devices else None
        dev_name = (target.get("name") or target.get("ip")) if target else "thiết bị"

        def on_selected(photo_path):
            if target:
                self._send_file(target.get("ip"), photo_path, dev_name)
            else:
                self.prepare_send_file(photo_path)

        try:
            from src.ui.macos_photos_window import MacOSPhotosWindow
            MacOSPhotosWindow.open_picker(
                title=f"Chọn ảnh gửi qua AirDrop tới {dev_name}",
                parent=self,
                on_photo_selected=on_selected
            )
        except Exception as e:
            print(f"[AirDrop] Error opening photos picker: {e}")
            if target:
                self._prompt_send_file_to_device(target)

    def prepare_send_file(self, file_path: str):
        """Prepares a file to be sent when a device is clicked or connected."""
        self._pending_send_path = file_path
        self.show_window()
        devices = self.airdrop_mgr.get_discovered_devices()
        if devices:
            self.status_lbl.set_text(f"Đã chọn {os.path.basename(file_path)}. Nhấp vào thiết bị trên Radar để gửi.")
        else:
            self.status_lbl.set_text(f"Đã chọn {os.path.basename(file_path)}. Hãy kết nối thiết bị trên Radar để gửi.")

    def _send_file(self, target_ip: str, file_path: str, target_name: str):
        self.status_lbl.set_text(f"Đang gửi {os.path.basename(file_path)} tới {target_name}...")
        self.btn_send_file.set_sensitive(False)

        def on_done(success, err):
            self.btn_send_file.set_sensitive(True)
            if success:
                self.status_lbl.set_text(f"✓ Đã gửi tệp tới {target_name} thành công!")
            else:
                self.status_lbl.set_text(f"Gửi tệp thất bại: {err}")

        self.airdrop_mgr.send_file_async(
            target_ip=target_ip,
            file_path=file_path,
            on_done=on_done
        )

    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        """Handle Drag & Drop files from Nautilus/Desktop directly onto AirDrop window."""
        uris = data.get_uris()
        if uris:
            for uri in uris:
                if uri.startswith("file://"):
                    path = urllib.parse.unquote(uri[7:]).strip('\r\n')
                    devices = self.airdrop_mgr.get_discovered_devices()
                    if devices:
                        self._send_file(devices[0]["ip"], path, devices[0].get("name", "Thiết bị"))
                    else:
                        self.status_lbl.set_text(f"Đã nhận tệp {os.path.basename(path)}. Hãy kết nối thiết bị để gửi.")
        context.finish(True, False, time)

    def _on_transfer_event(self, event_type: str, data: dict):
        """Handle incoming and outgoing file transfer updates."""
        filename = data.get("filename", "Tệp tin")
        is_incoming = data.get("is_incoming", False)

        if event_type == "start":
            if is_incoming:
                self.status_lbl.set_text(f"Đang nhận {filename}...")
        elif event_type == "progress":
            pct = int(data.get("percent", 0))
            action = "Đang nhận" if is_incoming else "Đang gửi"
            self.status_lbl.set_text(f"{action} {filename}: {pct}%")
        elif event_type == "complete":
            if is_incoming:
                saved_path = data.get("file_path", "")
                self.status_lbl.set_text(f"✓ Đã nhận {filename} (Đã lưu vào Downloads)")
                self._show_received_notification(filename, saved_path)

    def _refresh_disc_combo(self):
        curr_id = self.disc_combo.get_active_id() or "everyone"
        self.disc_combo.remove_all()
        self.disc_combo.append("everyone", t("airdrop_everyone", "Mọi người"))
        self.disc_combo.append("contacts", t("airdrop_contacts", "Chỉ danh bạ"))
        self.disc_combo.append("off", t("airdrop_no_one", "Không ai cả"))
        self.disc_combo.set_active_id(curr_id)

    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("airdrop_title", "AirDrop"))
            if hasattr(self, "title_lbl"):
                self.title_lbl.set_text(t("airdrop_title", "AirDrop"))
            if hasattr(self, "btn_header_qr"):
                self.btn_header_qr.set_label(t("airdrop_header_qr", "📷 Mã QR iPhone"))
                self.btn_header_qr.set_tooltip_text(t("airdrop_header_qr_tooltip", "Mở mã QR để kết nối nhanh iPhone / iPad"))
            if hasattr(self, "disc_lbl"):
                self.disc_lbl.set_text(t("airdrop_discoverable_label", "Cho phép phát hiện:"))
            if hasattr(self, "disc_combo"):
                self._refresh_disc_combo()
            if hasattr(self, "btn_webdrop"):
                self.btn_webdrop.set_label(t("airdrop_btn_qr", "📷 Quét mã QR kết nối iPhone / iPad"))
                self.btn_webdrop.set_tooltip_text(t("airdrop_btn_qr_tooltip", "Mở mã QR lớn để quét bằng camera điện thoại"))
            if hasattr(self, "btn_send_file"):
                self.btn_send_file.set_label(t("airdrop_btn_send_file", "Chọn tệp để gửi…"))
            if hasattr(self, "btn_send_photo"):
                self.btn_send_photo.set_label(t("airdrop_btn_send_photo", "📸 Gửi ảnh từ Photos…"))
            if hasattr(self, "status_lbl"):
                from src.modules.airdrop import get_local_ip
                self.status_lbl.set_text(f"{t('airdrop_ready_to_share', '🟢 Sẵn sàng chia sẻ')} • http://{get_local_ip()}:8765")
            if hasattr(self, "radar_widget"):
                self.radar_widget.queue_draw()
        except Exception as e:
            print(f"[AirDrop] Error retranslating UI: {e}")

    def _show_received_notification(self, filename: str, file_path: str):
        """Send Dynamic Island notification and show non-modal toast in AirDrop window."""
        # 1. Forward notification directly to Dynamic Island!
        try:
            from src.ipc import send_command
            send_command(f'airdrop-received "{filename}" "{file_path}"')
        except Exception as e:
            print(f"[AirDrop] IPC notify notice: {e}")

        # 2. Display sleek non-modal floating toast inside AirDrop window
        if hasattr(self, "toast_box"):
            for ch in self.toast_box.get_children():
                self.toast_box.remove(ch)

            icon = get_image("airdrop", 18, "#007aff")
            self.toast_box.pack_start(icon, False, False, 0)

            lbl = Gtk.Label(label=f"Đã nhận '{filename}'")
            lbl.get_style_context().add_class("mac-airdrop-status")
            lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            lbl.set_max_width_chars(28)
            self.toast_box.pack_start(lbl, False, False, 0)

            btn_open = Gtk.Button(label="Mở tệp")
            btn_open.get_style_context().add_class("mac-airdrop-toast-btn")
            btn_open.get_style_context().add_class("primary")
            btn_open.connect("clicked", lambda _: subprocess.Popen(["xdg-open", file_path]))
            self.toast_box.pack_start(btn_open, False, False, 0)

            btn_folder = Gtk.Button(label="Downloads")
            btn_folder.get_style_context().add_class("mac-airdrop-toast-btn")
            btn_folder.connect("clicked", lambda _: subprocess.Popen(["nautilus", DOWNLOADS_DIR]))
            self.toast_box.pack_start(btn_folder, False, False, 0)

            btn_close = Gtk.Button(label="✕")
            btn_close.get_style_context().add_class("mac-traffic-light")
            btn_close.connect("clicked", lambda _: self.toast_box.hide())
            self.toast_box.pack_start(btn_close, False, False, 0)

            self.toast_box.show_all()
            GLib.timeout_add_seconds(8, self.toast_box.hide)

    def _show_webdrop_dialog(self, button):
        """Display dedicated large QR Code modal for instant iPhone / iPad camera scanning."""
        url = self.airdrop_mgr.get_local_url()
        dlg = AirDropQRDialog(self, url)
        dlg.run()
        dlg.destroy()

    def hide_window(self):
        self.hide()

    def show_window(self):
        self.show_all()
        self.present()
        self.radar_widget.update_devices()

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

    def _on_header_button_press(self, widget, event):
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.toggle_maximize()
            return True
        elif event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            if not getattr(self, "_is_maximized", False):
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                return True
        return False

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

    def toggle_maximize(self):
        if self._is_maximized:
            self.unmaximize()
            self._is_maximized = False
        else:
            self.maximize()
            self._is_maximized = True

    def _on_delete_event(self, widget, event):
        self.hide()
        return True

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False
