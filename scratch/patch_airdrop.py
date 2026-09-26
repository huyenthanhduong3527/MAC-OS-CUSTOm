#!/usr/bin/env python3
import sys

with open("src/ui/macos_airdrop_window.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Imports
import_target = "from src.utils.icons import get_image, get_pixbuf"
import_replacement = """from src.utils.icons import get_image, get_pixbuf
from src.utils.i18n import t, add_language_listener"""
if import_target in text:
    text = text.replace(import_target, import_replacement, 1)

# 2. TrafficLightsWidget
tl_target = """        self.pack_start(make_light("tl-red", "Đóng (Close)", "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", "Thu nhỏ (Minimize)", "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", "Phóng to (Zoom)", "⤢", on_maximize), False, False, 0)"""
tl_replacement = """        self.pack_start(make_light("tl-red", t("tl_close", "Đóng"), "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", t("tl_minimize", "Thu nhỏ"), "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", t("tl_zoom", "Phóng to"), "⤢", on_maximize), False, False, 0)"""
if tl_target in text:
    text = text.replace(tl_target, tl_replacement, 1)

# 3. AirDropQRDialog
qr_dlg_target = """        super().__init__(
            title="Quét mã QR để kết nối iPhone & iPad",
            parent=parent,
            modal=True,
            destroy_with_parent=True
        )"""
qr_dlg_replacement = """        super().__init__(
            title=t("airdrop_qr_dialog_title", "Quét mã QR để kết nối iPhone & iPad"),
            parent=parent,
            modal=True,
            destroy_with_parent=True
        )"""
if qr_dlg_target in text:
    text = text.replace(qr_dlg_target, qr_dlg_replacement, 1)

qr_scan_title_target = """        title = Gtk.Label()
        title.set_markup("<span font='14.5' weight='bold' color='#ffffff'>📱 Quét mã bằng iPhone để kết nối</span>")
        title_box.pack_start(title, False, False, 0)

        desc = Gtk.Label()
        desc.set_markup(
            "<span font='10' color='#a1a1a6'>Mở ứng dụng <b>Camera</b> trên iPhone / iPad\\n"
            "và quét mã QR bên dưới để mở AirDrop Web ngay lập tức.</span>"
        )"""
qr_scan_title_replacement = """        title = Gtk.Label()
        title.set_markup(f"<span font='14.5' weight='bold' color='#ffffff'>{t('airdrop_qr_scan_title', '📱 Quét mã bằng iPhone để kết nối')}</span>")
        title_box.pack_start(title, False, False, 0)

        desc = Gtk.Label()
        desc_text = t("airdrop_qr_scan_desc", "Mở ứng dụng <b>Camera</b> trên iPhone / iPad\\nvà quét mã QR bên dưới để mở AirDrop Web ngay lập tức.")
        desc.set_markup(f"<span font='10' color='#a1a1a6'>{desc_text}</span>")"""
if qr_scan_title_target in text:
    text = text.replace(qr_scan_title_target, qr_scan_title_replacement, 1)

qr_actions_target = """        btn_copy = Gtk.Button(label="📋 Sao chép")
        btn_copy.get_style_context().add_class("mac-btn-secondary")
        def _copy(_):
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.set_text(self.url, -1)
            btn_copy.set_label("✓ Đã chép!")
            GLib.timeout_add(2000, lambda: [btn_copy.set_label("📋 Sao chép"), False][1])
        btn_copy.connect("clicked", _copy)
        url_row.pack_start(btn_copy, False, False, 0)

        url_card.pack_start(url_row, False, False, 0)

        status_lbl = Gtk.Label()
        status_lbl.set_markup("<span font='9.5' color='#34c759'>● Máy chủ AirDrop đang hoạt động trên Wi-Fi</span>")
        url_card.pack_start(status_lbl, False, False, 0)
        content.pack_start(url_card, False, False, 0)

        # Shortcut Tip Card
        tip_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tip_card.get_style_context().add_class("mac-qr-url-card")
        tip_card.set_halign(Gtk.Align.FILL)

        tip_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        tip_vbox.set_hexpand(True)
        tip_title = Gtk.Label()
        tip_title.set_markup("<span font='10' weight='bold' color='#ffffff'>⚡ Gửi ảnh 1 chạm (Không cần vào link)</span>")
        tip_title.set_halign(Gtk.Align.START)
        tip_vbox.pack_start(tip_title, False, False, 0)

        tip_desc = Gtk.Label()
        tip_desc.set_markup("<span font='9' color='#a1a1a6'>Dùng Phím tắt iOS để gửi ảnh trực tiếp từ nút Chia sẻ 📤</span>")
        tip_desc.set_halign(Gtk.Align.START)
        tip_vbox.pack_start(tip_desc, False, False, 0)
        tip_card.pack_start(tip_vbox, True, True, 0)

        btn_guide = Gtk.Button(label="📖 Xem cách cài")
        btn_guide.get_style_context().add_class("mac-btn-secondary")
        btn_guide.connect("clicked", lambda _: self._show_shortcut_guide())
        tip_card.pack_start(btn_guide, False, False, 0)

        content.pack_start(tip_card, False, False, 0)

        # Action Area Buttons (bottom)
        btn_open = Gtk.Button(label="🌐 Mở trên máy")
        btn_open.get_style_context().add_class("mac-btn-secondary")
        btn_open.connect("clicked", lambda _: subprocess.Popen(["xdg-open", self.url]))
        self.add_action_widget(btn_open, Gtk.ResponseType.NONE)

        btn_close = Gtk.Button(label="Đóng")"""

qr_actions_replacement = """        btn_copy = Gtk.Button(label=t("copy", "📋 Sao chép"))
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

        btn_close = Gtk.Button(label=t("tl_close", "Đóng"))"""
if qr_actions_target in text:
    text = text.replace(qr_actions_target, qr_actions_replacement, 1)

# 4. Radar labels
radar_this_dev_target = """        # Sub-label ("• Thiết bị này")
        sub_layout = Pango.Layout(pctx)
        sub_layout.set_text("• Thiết bị này", -1)"""
radar_this_dev_replacement = """        # Sub-label ("• Thiết bị này")
        sub_layout = Pango.Layout(pctx)
        sub_layout.set_text(t("airdrop_this_device", "• Thiết bị này"), -1)"""
if radar_this_dev_target in text:
    text = text.replace(radar_this_dev_target, radar_this_dev_replacement, 1)

radar_tap_target = """            r_layout = Pango.Layout(pctx)
            r_layout.set_text("Chạm để gửi tệp", -1)"""
radar_tap_replacement = """            r_layout = Pango.Layout(pctx)
            r_layout.set_text(t("airdrop_tap_to_send", "Chạm để gửi tệp"), -1)"""
if radar_tap_target in text:
    text = text.replace(radar_tap_target, radar_tap_replacement, 1)

radar_scanning_target = """            hint_layout = Pango.Layout(pctx)
            hint_layout.set_text("Đang quét các thiết bị lân cận qua Wi-Fi & Mạng nội bộ...", -1)"""
radar_scanning_replacement = """            hint_layout = Pango.Layout(pctx)
            hint_layout.set_text(t("airdrop_scanning_hint", "Đang quét các thiết bị lân cận qua Wi-Fi & Mạng nội bộ…"), -1)"""
if radar_scanning_target in text:
    text = text.replace(radar_scanning_target, radar_scanning_replacement, 1)

# 5. AirDrop Window init and UI
win_init_target = """        self._setup_ui()
        self._load_css()"""
win_init_replacement = """        self._setup_ui()
        self._load_css()
        self.set_title(t("airdrop_title", "AirDrop"))
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass"""
assert win_init_target in text, "win_init_target not found"
text = text.replace(win_init_target, win_init_replacement, 1)

# 6. UI labels & buttons in _setup_ui
ui_target = """        # Column 1: Title (Strictly centered at 50% width)
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        title_lbl = Gtk.Label(label="AirDrop")
        title_lbl.get_style_context().add_class("mac-airdrop-title")
        center_box.pack_start(title_lbl, False, False, 0)
        header_grid.attach(center_box, 1, 0, 1, 1)

        # Column 2: Right-aligned quick action (Expands equally to match Left box)
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_box.set_hexpand(True)
        right_box.set_halign(Gtk.Align.END)
        right_box.set_valign(Gtk.Align.CENTER)

        btn_header_qr = Gtk.Button(label="📷 Mã QR iPhone")
        btn_header_qr.get_style_context().add_class("mac-btn-header-qr")
        btn_header_qr.set_tooltip_text("Mở mã QR để kết nối nhanh iPhone / iPad")
        btn_header_qr.connect("clicked", self._show_webdrop_dialog)
        right_box.pack_end(btn_header_qr, False, False, 0)
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
        disc_lbl = Gtk.Label(label="Cho phép phát hiện:")
        disc_lbl.get_style_context().add_class("mac-disc-label")
        disc_box.pack_start(disc_lbl, False, False, 0)

        self.disc_combo = Gtk.ComboBoxText()
        self.disc_combo.append("everyone", "Mọi người")
        self.disc_combo.append("contacts", "Chỉ danh bạ")
        self.disc_combo.append("off", "Không ai cả")
        self.disc_combo.set_active_id("everyone")
        self.disc_combo.connect("changed", self._on_disc_changed)
        self.disc_combo.get_style_context().add_class("mac-disc-combo")
        disc_box.pack_start(self.disc_combo, False, False, 0)
        toolbar_row.pack_start(disc_box, False, False, 0)

        # Center: Prominent QR Scan Button (iPhone / Android)
        center_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        center_actions.set_halign(Gtk.Align.CENTER)
        self.btn_webdrop = Gtk.Button(label="📷 Quét mã QR kết nối iPhone / iPad")
        self.btn_webdrop.get_style_context().add_class("mac-btn-webdrop")
        self.btn_webdrop.set_tooltip_text("Mở mã QR lớn để quét bằng camera điện thoại")
        self.btn_webdrop.connect("clicked", self._show_webdrop_dialog)
        center_actions.pack_start(self.btn_webdrop, False, False, 0)
        toolbar_row.pack_start(center_actions, True, True, 0)

        # Right: Primary Send File & Send Photo Buttons
        self.btn_send_file = Gtk.Button(label="Chọn tệp để gửi...")
        self.btn_send_file.get_style_context().add_class("mac-btn-primary")
        self.btn_send_file.connect("clicked", self._on_pick_file_and_send)
        toolbar_row.pack_end(self.btn_send_file, False, False, 0)

        self.btn_send_photo = Gtk.Button(label="📸 Gửi ảnh từ Photos…")
        self.btn_send_photo.get_style_context().add_class("mac-btn-webdrop")
        self.btn_send_photo.connect("clicked", self._on_pick_photo_and_send)
        toolbar_row.pack_end(self.btn_send_photo, False, False, 0)

        # Row 2: Status Line
        self.status_lbl = Gtk.Label(label=f"🟢 Sẵn sàng chia sẻ • http://{get_local_ip()}:8765")"""

ui_replacement = """        # Column 1: Title (Strictly centered at 50% width)
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
        self.status_lbl = Gtk.Label(label=f"{t('airdrop_ready_to_share', '🟢 Sẵn sàng chia sẻ')} • http://{get_local_ip()}:8765")"""
assert ui_target in text, "ui_target not found"
text = text.replace(ui_target, ui_replacement, 1)

# 7. Add _on_language_changed method
airdrop_methods = """    def _refresh_disc_combo(self):
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
"""

hook_target = "    def _show_received_notification(self, filename: str, file_path: str):"
assert hook_target in text, "hook_target not found"
text = text.replace(hook_target, airdrop_methods + "\n" + hook_target, 1)

with open("src/ui/macos_airdrop_window.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched src/ui/macos_airdrop_window.py")
