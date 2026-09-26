#!/usr/bin/env python3
"""
Patch script for src/ui/macos_photobooth_window.py to support dynamic multilingual translation.
"""

TARGET = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/src/ui/macos_photobooth_window.py"

def patch_photobooth():
    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Imports
    old_imp = "from src.utils.theme import is_system_dark_mode"
    new_imp = "from src.utils.theme import is_system_dark_mode\nfrom src.utils.i18n import t, get_current_language, add_language_listener"
    if old_imp in content:
        content = content.replace(old_imp, new_imp, 1)
        print("Added i18n imports to macos_photobooth_window.py")

    # 2. ViewfinderArea filter name translation
    old_filter_text = """                # Filter name text
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(11)
                ext = cr.text_extents(f_name)
                tx_text = tx + (tile_w - ext.width) / 2.0 - ext.x_bearing
                ty_text = bar_y + (bar_h / 2.0) - (ext.y_bearing + ext.height / 2.0)
                cr.move_to(tx_text, ty_text)
                cr.show_text(f_name)"""

    new_filter_text = """                # Filter name text (Localized)
                f_name_trans = t(f"photobooth_filter_{f_key}", f_name)
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(11)
                ext = cr.text_extents(f_name_trans)
                tx_text = tx + (tile_w - ext.width) / 2.0 - ext.x_bearing
                ty_text = bar_y + (bar_h / 2.0) - (ext.y_bearing + ext.height / 2.0)
                cr.move_to(tx_text, ty_text)
                cr.show_text(f_name_trans)"""

    if old_filter_text in content:
        content = content.replace(old_filter_text, new_filter_text, 1)
        print("Updated filter text rendering in ViewfinderArea")

    # 3. MacOSPhotoBoothWindow.__init__ language listener and initial title
    old_init = """        self.set_title("Photo Booth")
        self.set_wmclass("Photo Booth", "Photo Booth")"""
    new_init = """        self.set_title(t("photobooth_title", "Photo Booth"))
        self.set_wmclass("Photo Booth", "Photo Booth")"""
    if old_init in content:
        content = content.replace(old_init, new_init, 1)
        print("Updated initial window title")

    # Add language listener in __init__
    old_init_end = """        self.connect("window-state-event", self._on_window_state_event)"""
    new_init_end = """        self.connect("window-state-event", self._on_window_state_event)
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass"""
    if old_init_end in content:
        content = content.replace(old_init_end, new_init_end, 1)
        print("Added language listener in MacOSPhotoBoothWindow.__init__")

    # 4. Header title label
    old_header = """        # 2. Centered Window Title: "Photo Booth" (matching Image 2)
        title_lbl = Gtk.Label(label="Photo Booth")
        title_lbl.get_style_context().add_class("pb-title")
        header.set_center_widget(title_lbl)"""

    new_header = """        # 2. Centered Window Title: "Photo Booth" (matching Image 2)
        self.title_lbl = Gtk.Label(label=t("photobooth_title", "Photo Booth"))
        self.title_lbl.get_style_context().add_class("pb-title")
        header.set_center_widget(self.title_lbl)"""

    if old_header in content:
        content = content.replace(old_header, new_header, 1)
        print("Updated header title label in MacOSPhotoBoothWindow")

    # 5. Phone status label
    old_phone_status = 'self.lbl_phone_status = Gtk.Label(label="Kết nối điện thoại")'
    new_phone_status = 'self.lbl_phone_status = Gtk.Label(label=t("photobooth_connect_phone", "Kết nối điện thoại"))'
    if old_phone_status in content:
        content = content.replace(old_phone_status, new_phone_status, 1)
        print("Updated phone status label")

    # 6. Controls bar: tooltips and effects button label
    old_controls = """        self.btn_mode_4up = make_mode_btn("mode_burst", "Chụp 4 ô liên hoàn", "4up")
        self.btn_mode_single = make_mode_btn("mode_single", "Chụp ảnh đơn", "single")
        self.btn_mode_single.get_style_context().add_class("active")
        self.btn_mode_video = make_mode_btn("mode_video", "Quay video", "video")"""

    new_controls = """        self.btn_mode_4up = make_mode_btn("mode_burst", t("photobooth_mode_4up", "Chụp 4 ô liên hoàn"), "4up")
        self.btn_mode_single = make_mode_btn("mode_single", t("photobooth_mode_single", "Chụp ảnh đơn"), "single")
        self.btn_mode_single.get_style_context().add_class("active")
        self.btn_mode_video = make_mode_btn("mode_video", t("photobooth_mode_video", "Quay video"), "video")"""

    if old_controls in content:
        content = content.replace(old_controls, new_controls, 1)
        print("Updated mode button tooltips")

    old_live_btn = 'self.btn_live_preview = Gtk.Button(label="Live-Preview")'
    new_live_btn = 'self.btn_live_preview = Gtk.Button(label=t("photobooth_effects", "Hiệu ứng"))'
    if old_live_btn in content:
        content = content.replace(old_live_btn, new_live_btn, 1)
        print("Updated effects button label")

    # 7. Continuity Sheet
    old_sheet = """        title_box.pack_start(get_pb_image("icon_continuity", 22, 22), False, False, 0)
        lbl_title = Gtk.Label(label="Continuity Camera")
        lbl_title.get_style_context().add_class("title-2")
        title_box.pack_start(lbl_title, False, False, 0)
        top_row.pack_start(title_box, False, False, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("pb-live-pill")
        btn_close.connect("clicked", lambda w: self._toggle_continuity_sheet(False))
        top_row.pack_end(btn_close, False, False, 0)
        self.continuity_sheet.pack_start(top_row, False, False, 0)

        # Description
        desc_lbl = Gtk.Label(
            label="1. Dùng <b>Camera iPhone / Android</b> quét mã QR bên dưới.\\n"
                  "2. Khi mở web: Bấm <i>Nâng cao</i> ➔ <i>Tiếp tục truy cập</i> (chấp nhận SSL).\\n"
                  "3. Bấm <b>Cho phép</b> Camera ➔ Khung hình truyền trực tiếp (Live Stream) tức thì!"
        )
        desc_lbl.set_use_markup(True)
        desc_lbl.set_line_wrap(True)
        desc_lbl.set_max_width_chars(44)
        desc_lbl.set_halign(Gtk.Align.CENTER)
        self.continuity_sheet.pack_start(desc_lbl, False, False, 0)

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

        btn_copy = Gtk.Button(label="Sao chép")
        btn_copy.get_style_context().add_class("pb-live-pill")
        btn_copy.connect("clicked", self._copy_url)
        url_box.pack_start(btn_copy, False, False, 0)
        self.continuity_sheet.pack_start(url_box, False, False, 0)

        # Connection Status
        self.sheet_status_lbl = Gtk.Label(label="Đang chờ điện thoại quét mã...")"""

    new_sheet = """        title_box.pack_start(get_pb_image("icon_continuity", 22, 22), False, False, 0)
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
        self.sheet_status_lbl = Gtk.Label(label=t("photobooth_waiting_phone", "Đang chờ điện thoại quét mã..."))"""

    if old_sheet in content:
        content = content.replace(old_sheet, new_sheet, 1)
        print("Updated continuity sheet in MacOSPhotoBoothWindow")

    # 8. Menu labels
    old_menu = """        lbl_phone = Gtk.Label(label="Quét mã kết nối điện thoại (Continuity)")
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
        lbl_vcam = Gtk.Label(label="Phát Cam ảo (Virtual Camera)")"""

    new_menu = """        lbl_phone = Gtk.Label(label=t("photobooth_phone_menu", "Quét mã kết nối điện thoại (Continuity)"))
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
        lbl_vcam = Gtk.Label(label=t("photobooth_vcam_menu", "Phát Cam ảo (Virtual Camera)"))"""

    if old_menu in content:
        content = content.replace(old_menu, new_menu, 1)
        print("Updated camera menu in MacOSPhotoBoothWindow")

    # 9. Toasts
    toasts = [
        ('self.viewfinder.show_toast("Cam ảo: Đang phát")', 'self.viewfinder.show_toast(t("photobooth_vcam_started", "Cam ảo: Đang phát"))'),
        ('self.viewfinder.show_toast("Không thể bật Cam ảo")', 'self.viewfinder.show_toast(t("photobooth_vcam_error", "Không thể bật Cam ảo"))'),
        ('self.viewfinder.show_toast("Cam ảo: Đã dừng")', 'self.viewfinder.show_toast(t("photobooth_vcam_stopped", "Cam ảo: Đã dừng"))'),
        ('self.viewfinder.show_toast("Đã sao chép liên kết!")', 'self.viewfinder.show_toast(t("photobooth_copied", "Đã sao chép liên kết!"))'),
        ('self.viewfinder.show_toast("Đã kết nối iPhone!")', 'self.viewfinder.show_toast(t("photobooth_phone_connected_toast", "Đã kết nối iPhone!"))'),
        ('self.viewfinder.show_toast("Đã nhận ảnh từ iPhone!")', 'self.viewfinder.show_toast(t("photobooth_photo_received_toast", "Đã nhận ảnh từ iPhone!"))'),
        ('self.viewfinder.show_toast("Chế độ chụp ảnh đơn")', 'self.viewfinder.show_toast(t("photobooth_toast_mode_single", "Chế độ chụp ảnh đơn"))'),
        ('self.viewfinder.show_toast("Chế độ chụp 4 ô liên hoàn")', 'self.viewfinder.show_toast(t("photobooth_toast_mode_4up", "Chế độ chụp 4 ô liên hoàn"))'),
        ('self.viewfinder.show_toast("Chế độ quay video")', 'self.viewfinder.show_toast(t("photobooth_toast_mode_video", "Chế độ quay video"))'),
        ('self.viewfinder.show_toast("Đã tạo ảnh 4 ô liên hoàn!")', 'self.viewfinder.show_toast(t("photobooth_burst_saved", "Đã tạo ảnh 4 ô liên hoàn!"))'),
        ('self.viewfinder.show_toast("Không thể bắt đầu quay video!")', 'self.viewfinder.show_toast(t("photobooth_video_error", "Không thể bắt đầu quay video!"))'),
        ('self.viewfinder.show_toast("Đang quay video... 🎥")', 'self.viewfinder.show_toast(t("photobooth_video_recording", "Đang quay video... 🎥"))'),
        ('self.viewfinder.show_toast("Đã lưu video vào Photo Booth! 🎥")', 'self.viewfinder.show_toast(t("photobooth_video_saved", "Đã lưu video vào Photo Booth! 🎥"))'),
        ('self.viewfinder.show_toast("Đã dừng quay video!")', 'self.viewfinder.show_toast(t("photobooth_video_stopped", "Đã dừng quay video!"))'),
        ('self.lbl_phone_status.set_text("iPhone đã kết nối")', 'self.lbl_phone_status.set_text(t("photobooth_phone_connected", "iPhone đã kết nối"))'),
        ('self.lbl_phone_status.set_text("Kết nối điện thoại")', 'self.lbl_phone_status.set_text(t("photobooth_connect_phone", "Kết nối điện thoại"))'),
    ]
    for old_t, new_t in toasts:
        if old_t in content:
            content = content.replace(old_t, new_t)

    print("Updated toasts in MacOSPhotoBoothWindow")

    # 10. Add _on_language_changed and _retranslate_ui
    retrans_methods = """    def _on_language_changed(self, lang_code: str):
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

"""
    pos_pb = content.find("    def _set_capture_mode(self, mode):")
    if pos_pb != -1 and "_retranslate_ui" not in content:
        content = content[:pos_pb] + retrans_methods + content[pos_pb:]
        print("Added _retranslate_ui method to MacOSPhotoBoothWindow")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched macos_photobooth_window.py!")

if __name__ == "__main__":
    patch_photobooth()
