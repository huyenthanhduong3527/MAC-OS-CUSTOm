#!/usr/bin/env python3
import sys

with open("src/ui/macos_appstore_window.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Imports
import_target = "from src.utils.icons import get_image, get_pixbuf"
import_replacement = """from src.utils.icons import get_image, get_pixbuf
from src.utils.i18n import t, add_language_listener"""
assert import_target in text, "import_target not found"
text = text.replace(import_target, import_replacement, 1)

# 2. TrafficLightsWidget
tl_target = """        self.pack_start(make_light("tl-red", "Close", "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", "Minimize", "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", "Zoom", "⤢", on_maximize), False, False, 0)"""
tl_replacement = """        self.pack_start(make_light("tl-red", t("tl_close", "Close"), "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", t("tl_minimize", "Minimize"), "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", t("tl_zoom", "Zoom"), "⤢", on_maximize), False, False, 0)"""
assert tl_target in text, "tl_target not found"
text = text.replace(tl_target, tl_replacement, 1)

# 3. AppCardWidget labels
card_iap_target = """        if self.app.get("in_app_purchases", False):
            self.lbl_iap = Gtk.Label(label="Mua trong ứng dụng")"""
card_iap_replacement = """        if self.app.get("in_app_purchases", False):
            self.lbl_iap = Gtk.Label(label=t("appstore_iap", "Mua trong ứng dụng"))"""
assert card_iap_target in text, "card_iap_target not found"
text = text.replace(card_iap_target, card_iap_replacement, 1)

card_installing_target = """        if is_installing:
            self.btn_action.set_label("Đang cài đặt...")
            self.btn_action.set_sensitive(False)
            ctx.remove_class("pill-get")
            ctx.remove_class("pill-open")
            ctx.add_class("pill-installing")
            self.progress_bar.show()
            self.lbl_card_status.set_text("Đang cài...")"""

card_installing_replacement = """        if is_installing:
            self.btn_action.set_label(t("appstore_installing", "Đang cài đặt…"))
            self.btn_action.set_sensitive(False)
            ctx.remove_class("pill-get")
            ctx.remove_class("pill-open")
            ctx.add_class("pill-installing")
            self.progress_bar.show()
            self.lbl_card_status.set_text(t("appstore_installing", "Đang cài…"))"""
assert card_installing_target in text, "card_installing_target not found"
text = text.replace(card_installing_target, card_installing_replacement, 1)

card_installed_target = """            if success or is_app_installed(self.app):
                self.progress_bar.set_fraction(1.0)
                self.btn_action.set_label("Mở")
                ctx.remove_class("pill-get")
                ctx.add_class("pill-open")
                self.lbl_card_status.set_text("✓ Đã cài đặt")
                self.lbl_card_status.get_style_context().remove_class("mac-update-status-err")
                self.lbl_card_status.get_style_context().add_class("mac-update-status-ok")
                self.lbl_card_status.show()
                GLib.timeout_add(2500, lambda: [self.progress_bar.hide(), self.lbl_card_status.hide()] if hasattr(self, 'progress_bar') else None)
            else:
                self.progress_bar.hide()
                self.btn_action.set_label("Nhận")
                ctx.remove_class("pill-open")
                ctx.add_class("pill-get")
                self.lbl_card_status.set_text("⚠ Lỗi cài đặt")"""

card_installed_replacement = """            if success or is_app_installed(self.app):
                self.progress_bar.set_fraction(1.0)
                self.btn_action.set_label(t("appstore_open", "Mở"))
                ctx.remove_class("pill-get")
                ctx.add_class("pill-open")
                self.lbl_card_status.set_text(t("appstore_installed", "✓ Đã cài đặt"))
                self.lbl_card_status.get_style_context().remove_class("mac-update-status-err")
                self.lbl_card_status.get_style_context().add_class("mac-update-status-ok")
                self.lbl_card_status.show()
                GLib.timeout_add(2500, lambda: [self.progress_bar.hide(), self.lbl_card_status.hide()] if hasattr(self, 'progress_bar') else None)
            else:
                self.progress_bar.hide()
                self.btn_action.set_label(t("appstore_get", "Nhận"))
                ctx.remove_class("pill-open")
                ctx.add_class("pill-get")
                self.lbl_card_status.set_text(t("appstore_install_err", "⚠ Lỗi cài đặt"))"""
assert card_installed_target in text, "card_installed_target not found"
text = text.replace(card_installed_target, card_installed_replacement, 1)

card_update_state_target = """        if installed:
            self.btn_action.set_label("Mở")
            ctx.remove_class("pill-get")
            ctx.remove_class("pill-installing")
            ctx.add_class("pill-open")
        else:
            self.btn_action.set_label("Nhận")
            ctx.remove_class("pill-open")
            ctx.remove_class("pill-installing")
            ctx.add_class("pill-get")"""

card_update_state_replacement = """        if installed:
            self.btn_action.set_label(t("appstore_open", "Mở"))
            ctx.remove_class("pill-get")
            ctx.remove_class("pill-installing")
            ctx.add_class("pill-open")
        else:
            self.btn_action.set_label(t("appstore_get", "Nhận"))
            ctx.remove_class("pill-open")
            ctx.remove_class("pill-installing")
            ctx.add_class("pill-get")
        if hasattr(self, "lbl_iap") and self.app.get("in_app_purchases", False):
            self.lbl_iap.set_text(t("appstore_iap", "Mua trong ứng dụng"))"""
assert card_update_state_target in text, "card_update_state_target not found"
text = text.replace(card_update_state_target, card_update_state_replacement, 1)

# 4. Window init
win_init_target = """        self.apply_theme()"""
win_init_replacement = """        self.apply_theme()
        self.set_title(t("appstore_title", "App Store"))
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass"""
assert win_init_target in text, "win_init_target not found"
text = text.replace(win_init_target, win_init_replacement, 1)

# 5. Search entry and Sidebar nav items
search_nav_target = """        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Tìm kiếm")
        self.search_entry.get_style_context().add_class("mac-store-search-input")
        self.search_entry.connect("changed", self._on_search_text_changed)
        self.search_entry.connect("activate", self._on_search_enter)
        search_wrap.pack_start(self.search_entry, True, True, 0)
        self.sidebar_box.pack_start(search_wrap, False, False, 0)

        # Navigation Scroll
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar_box.pack_start(nav_scroll, True, True, 0)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.nav_box.set_margin_start(10)
        self.nav_box.set_margin_end(10)
        nav_scroll.add(self.nav_box)

        # 8 Authentic macOS App Store items in exact order
        self._nav_buttons = {}
        self._add_nav_item("discover", "Khám phá", "star")
        self._add_nav_item("arcade", "Arcade", "gamepad")
        self._add_nav_item("create", "Sáng tạo", "palette")
        self._add_nav_item("work", "Làm việc", "paperplane")
        self._add_nav_item("play", "Chơi", "rocket")
        self._add_nav_item("develop", "Phát triển", "hammer")
        self._add_nav_item("categories", "Danh mục", "grid")
        self._add_nav_item("updates", "Cập nhật", "tray_down")"""

search_nav_replacement = """        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(t("appstore_search_placeholder", "Tìm kiếm"))
        self.search_entry.get_style_context().add_class("mac-store-search-input")
        self.search_entry.connect("changed", self._on_search_text_changed)
        self.search_entry.connect("activate", self._on_search_enter)
        search_wrap.pack_start(self.search_entry, True, True, 0)
        self.sidebar_box.pack_start(search_wrap, False, False, 0)

        # Navigation Scroll
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar_box.pack_start(nav_scroll, True, True, 0)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.nav_box.set_margin_start(10)
        self.nav_box.set_margin_end(10)
        nav_scroll.add(self.nav_box)

        # 8 Authentic macOS App Store items in exact order
        self._nav_buttons = {}
        self._add_nav_item("discover", t("appstore_discover", "Khám phá"), "star")
        self._add_nav_item("arcade", t("appstore_arcade", "Arcade"), "gamepad")
        self._add_nav_item("create", t("appstore_create", "Sáng tạo"), "palette")
        self._add_nav_item("work", t("appstore_work", "Làm việc"), "paperplane")
        self._add_nav_item("play", t("appstore_play", "Chơi"), "rocket")
        self._add_nav_item("develop", t("appstore_develop", "Phát triển"), "hammer")
        self._add_nav_item("categories", t("appstore_categories", "Danh mục"), "grid")
        self._add_nav_item("updates", t("appstore_updates", "Cập nhật"), "tray_down")"""
assert search_nav_target in text, "search_nav_target not found"
text = text.replace(search_nav_target, search_nav_replacement, 1)

# 6. Back button tooltip & Categories page title
back_btn_target = """        # Back button
        self.btn_back = Gtk.Button()
        self.btn_back.get_style_context().add_class("mac-header-nav-btn")
        self.btn_back.add(Gtk.Label(label="‹"))
        self.btn_back.set_tooltip_text("Quay lại")
        self.btn_back.connect("clicked", lambda _: self._navigate_back())
        self.top_header.pack_start(self.btn_back, False, False, 0)

        # Page Title
        self.header_title = Gtk.Label(label="Danh mục")"""

back_btn_replacement = """        # Back button
        self.btn_back = Gtk.Button()
        self.btn_back.get_style_context().add_class("mac-header-nav-btn")
        self.btn_back.add(Gtk.Label(label="‹"))
        self.btn_back.set_tooltip_text(t("back", "Quay lại"))
        self.btn_back.connect("clicked", lambda _: self._navigate_back())
        self.top_header.pack_start(self.btn_back, False, False, 0)

        # Page Title
        self.header_title = Gtk.Label(label=t("appstore_categories", "Danh mục"))"""
assert back_btn_target in text, "back_btn_target not found"
text = text.replace(back_btn_target, back_btn_replacement, 1)

# 7. Categories overview page
cat_page_target = """        # Centered "Categories" Header
        header_lbl = Gtk.Label(label="Danh mục")
        header_lbl.get_style_context().add_class("mac-categories-page-title")
        header_lbl.set_halign(Gtk.Align.CENTER)
        header_lbl.set_margin_top(14)
        header_lbl.set_margin_bottom(12)
        main_box.pack_start(header_lbl, False, False, 0)

        # 3-Column Categories Grid / Columns
        cols_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        cols_container.set_homogeneous(True)

        for col_items in CATEGORY_COLUMNS:
            col_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for cat_id, cat_name, icon_filename in col_items:
                row_eb = Gtk.EventBox()
                row_eb.get_style_context().add_class("mac-cat-item-row")
                row_eb.connect("button-press-event", lambda _w, _e, cid=cat_id, cname=cat_name: self._on_category_clicked(cid, cname))

                row_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

                row_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_hbox.set_margin_top(7)
                row_hbox.set_margin_bottom(7)
                row_hbox.set_margin_start(6)
                row_hbox.set_margin_end(6)

                # Icon
                icon_path = os.path.join(CAT_ICONS_DIR, icon_filename)
                icon_img = Gtk.Image()
                if os.path.exists(icon_path):
                    try:
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 22, 22, True)
                        icon_img.set_from_pixbuf(pb)
                    except Exception:
                        icon_img.set_from_icon_name("folder", Gtk.IconSize.MENU)
                else:
                    icon_img.set_from_icon_name("folder", Gtk.IconSize.MENU)
                row_hbox.pack_start(icon_img, False, False, 0)

                # Name
                name_lbl = Gtk.Label(label=cat_name)"""

cat_page_replacement = """        # Centered "Categories" Header
        header_lbl = Gtk.Label(label=t("appstore_categories", "Danh mục"))
        header_lbl.get_style_context().add_class("mac-categories-page-title")
        header_lbl.set_halign(Gtk.Align.CENTER)
        header_lbl.set_margin_top(14)
        header_lbl.set_margin_bottom(12)
        main_box.pack_start(header_lbl, False, False, 0)

        # 3-Column Categories Grid / Columns
        cols_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        cols_container.set_homogeneous(True)

        for col_items in CATEGORY_COLUMNS:
            col_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for cat_id, cat_name, icon_filename in col_items:
                cat_display = t(f"cat_{cat_id}", cat_name)
                row_eb = Gtk.EventBox()
                row_eb.get_style_context().add_class("mac-cat-item-row")
                row_eb.connect("button-press-event", lambda _w, _e, cid=cat_id, cname=cat_display: self._on_category_clicked(cid, cname))

                row_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

                row_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_hbox.set_margin_top(7)
                row_hbox.set_margin_bottom(7)
                row_hbox.set_margin_start(6)
                row_hbox.set_margin_end(6)

                # Icon
                icon_path = os.path.join(CAT_ICONS_DIR, icon_filename)
                icon_img = Gtk.Image()
                if os.path.exists(icon_path):
                    try:
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 22, 22, True)
                        icon_img.set_from_pixbuf(pb)
                    except Exception:
                        icon_img.set_from_icon_name("folder", Gtk.IconSize.MENU)
                else:
                    icon_img.set_from_icon_name("folder", Gtk.IconSize.MENU)
                row_hbox.pack_start(icon_img, False, False, 0)

                # Name
                name_lbl = Gtk.Label(label=cat_display)"""
assert cat_page_target in text, "cat_page_target not found"
text = text.replace(cat_page_target, cat_page_replacement, 1)

# 8. Category subpage back button
cat_sub_back_target = """        btn_back_cat = Gtk.Button(label="‹ Danh mục")"""
cat_sub_back_replacement = """        btn_back_cat = Gtk.Button(label=t("appstore_back_categories", "‹ Danh mục"))"""
assert cat_sub_back_target in text, "cat_sub_back_target not found"
text = text.replace(cat_sub_back_target, cat_sub_back_replacement, 1)

# 9. Discover page sections
disc_sec_target = """        # 2. Essential Mac Apps (8 apps)
        essential_ids = ["code", "google-chrome", "telegram-desktop", "spotify", "discord", "vlc", "obsidian", "postman"]
        essential_apps = [app_map[aid] for aid in essential_ids if aid in app_map]
        if essential_apps:
            box.pack_start(self._create_app_grid_section("Ứng dụng Mac thiết yếu", "Các ứng dụng cần thiết cho quy trình làm việc hàng ngày của bạn", essential_apps), False, False, 0)

        # 3. Trending & Popular (8 apps)
        trending_ids = ["blender", "gimp", "steam", "inkscape", "kdenlive", "audacity", "brave", "beekeeper-studio"]
        trending_apps = [app_map[aid] for aid in trending_ids if aid in app_map]
        if trending_apps:
            box.pack_start(self._create_app_grid_section("Thịnh hành & Phổ biến", "Các ứng dụng tuyệt vời được người dùng toàn cầu yêu thích", trending_apps), False, False, 0)

        # 4. Creative Studio & Design (6 apps)
        creative_ids = ["blender", "krita", "inkscape", "darktable", "shotcut", "freecad"]
        creative_apps = [app_map[aid] for aid in creative_ids if aid in app_map]
        if creative_apps:
            box.pack_start(self._create_app_grid_section("Xưởng sáng tạo & Thiết kế", "Công cụ chuyên nghiệp cho nghệ thuật số, mô hình 3D và dựng video", creative_apps), False, False, 0)

        # 5. Developer Power Tools (6 apps)
        dev_ids = ["cursor", "pycharm-community", "docker", "android-studio", "sublime-text", "dbeaver-ce"]
        dev_apps = [app_map[aid] for aid in dev_ids if aid in app_map]
        if dev_apps:
            box.pack_start(self._create_app_grid_section("Công cụ phát triển", "Viết mã nhanh hơn, gỡ lỗi thông minh hơn với các IDE hàng đầu", dev_apps), False, False, 0)

        # 6. Productivity & Collaboration (6 apps)
        prod_ids = ["libreoffice", "notion-snap-reborn", "slack", "zoom-client", "bitwarden", "keepassxc"]
        prod_apps = [app_map[aid] for aid in prod_ids if aid in app_map]
        if prod_apps:
            box.pack_start(self._create_app_grid_section("Năng suất & Cộng tác", "Tổ chức công việc khoa học, tập trung và cộng tác cùng đội ngũ", prod_apps), False, False, 0)

        # 7. Games & Entertainment (6 apps)
        game_ids = ["steam", "0ad", "supertuxkart", "retroarch", "clementine", "vlc"]
        game_apps = [app_map[aid] for aid in game_ids if aid in app_map]
        if game_apps:
            box.pack_start(self._create_app_grid_section("Trò chơi & Giải trí", "Thư giãn cùng các tựa game tốc độ cao, chiến thuật hoặc tận hưởng âm nhạc", game_apps), False, False, 0)"""

disc_sec_replacement = """        # 2. Essential Mac Apps (8 apps)
        essential_ids = ["code", "google-chrome", "telegram-desktop", "spotify", "discord", "vlc", "obsidian", "postman"]
        essential_apps = [app_map[aid] for aid in essential_ids if aid in app_map]
        if essential_apps:
            box.pack_start(self._create_app_grid_section(t("appstore_essential_apps", "Ứng dụng Mac thiết yếu"), t("appstore_essential_apps_sub", "Các ứng dụng cần thiết cho quy trình làm việc hàng ngày của bạn"), essential_apps), False, False, 0)

        # 3. Trending & Popular (8 apps)
        trending_ids = ["blender", "gimp", "steam", "inkscape", "kdenlive", "audacity", "brave", "beekeeper-studio"]
        trending_apps = [app_map[aid] for aid in trending_ids if aid in app_map]
        if trending_apps:
            box.pack_start(self._create_app_grid_section(t("appstore_trending", "Thịnh hành & Phổ biến"), t("appstore_trending_sub", "Các ứng dụng tuyệt vời được người dùng toàn cầu yêu thích"), trending_apps), False, False, 0)

        # 4. Creative Studio & Design (6 apps)
        creative_ids = ["blender", "krita", "inkscape", "darktable", "shotcut", "freecad"]
        creative_apps = [app_map[aid] for aid in creative_ids if aid in app_map]
        if creative_apps:
            box.pack_start(self._create_app_grid_section(t("appstore_creative_studio", "Xưởng sáng tạo & Thiết kế"), t("appstore_creative_studio_sub", "Công cụ chuyên nghiệp cho nghệ thuật số, mô hình 3D và dựng video"), creative_apps), False, False, 0)

        # 5. Developer Power Tools (6 apps)
        dev_ids = ["cursor", "pycharm-community", "docker", "android-studio", "sublime-text", "dbeaver-ce"]
        dev_apps = [app_map[aid] for aid in dev_ids if aid in app_map]
        if dev_apps:
            box.pack_start(self._create_app_grid_section(t("appstore_dev_tools", "Công cụ phát triển"), t("appstore_dev_tools_sub", "Viết mã nhanh hơn, gỡ lỗi thông minh hơn với các IDE hàng đầu"), dev_apps), False, False, 0)

        # 6. Productivity & Collaboration (6 apps)
        prod_ids = ["libreoffice", "notion-snap-reborn", "slack", "zoom-client", "bitwarden", "keepassxc"]
        prod_apps = [app_map[aid] for aid in prod_ids if aid in app_map]
        if prod_apps:
            box.pack_start(self._create_app_grid_section(t("appstore_productivity", "Năng suất & Cộng tác"), t("appstore_productivity_sub", "Tổ chức công việc khoa học, tập trung và cộng tác cùng đội ngũ"), prod_apps), False, False, 0)

        # 7. Games & Entertainment (6 apps)
        game_ids = ["steam", "0ad", "supertuxkart", "retroarch", "clementine", "vlc"]
        game_apps = [app_map[aid] for aid in game_ids if aid in app_map]
        if game_apps:
            box.pack_start(self._create_app_grid_section(t("appstore_games_ent", "Trò chơi & Giải trí"), t("appstore_games_ent_sub", "Thư giãn cùng các tựa game tốc độ cao, chiến thuật hoặc tận hưởng âm nhạc"), game_apps), False, False, 0)"""
assert disc_sec_target in text, "disc_sec_target not found"
text = text.replace(disc_sec_target, disc_sec_replacement, 1)

# 10. Hero card
hero_card_target = """        raw_tag = app.get("hero_tag", "LỰA CHỌN CỦA BIÊN TẬP VIÊN")
        if raw_tag == "EDITORS' CHOICE":
            raw_tag = "LỰA CHỌN CỦA BIÊN TẬP VIÊN"
        lbl_tag = Gtk.Label(label=raw_tag)
        lbl_tag.get_style_context().add_class("mac-hero-tag")
        lbl_tag.set_xalign(0.0)
        left_col.pack_start(lbl_tag, False, False, 0)

        lbl_title = Gtk.Label(label=app.get("hero_title", app["name"]))
        lbl_title.get_style_context().add_class("mac-hero-title")
        lbl_title.set_xalign(0.0)
        left_col.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label=app.get("hero_sub", app["subtitle"]))
        lbl_sub.get_style_context().add_class("mac-hero-sub")
        lbl_sub.set_xalign(0.0)
        lbl_sub.set_line_wrap(True)
        left_col.pack_start(lbl_sub, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        btn_row.set_margin_top(10)

        btn_action = Gtk.Button()
        installed = is_app_installed(app)
        btn_action.set_label("Mở" if installed else "Nhận")
        btn_action.get_style_context().add_class("mac-hero-pill-btn")
        btn_action.connect("clicked", lambda _: self.handle_install_or_launch(app, None))
        self.hero_btn_action = btn_action
        self.hero_app = app
        btn_row.pack_start(btn_action, False, False, 0)

        btn_more = Gtk.Button(label="Xem chi tiết →")"""

hero_card_replacement = """        raw_tag = app.get("hero_tag")
        if not raw_tag or raw_tag in ("EDITORS' CHOICE", "LỰA CHỌN CỦA BIÊN TẬP VIÊN"):
            raw_tag = t("appstore_editors_choice", "LỰA CHỌN CỦA BIÊN TẬP VIÊN")
        lbl_tag = Gtk.Label(label=raw_tag)
        lbl_tag.get_style_context().add_class("mac-hero-tag")
        lbl_tag.set_xalign(0.0)
        left_col.pack_start(lbl_tag, False, False, 0)

        lbl_title = Gtk.Label(label=app.get("hero_title", app["name"]))
        lbl_title.get_style_context().add_class("mac-hero-title")
        lbl_title.set_xalign(0.0)
        left_col.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label=app.get("hero_sub", app["subtitle"]))
        lbl_sub.get_style_context().add_class("mac-hero-sub")
        lbl_sub.set_xalign(0.0)
        lbl_sub.set_line_wrap(True)
        left_col.pack_start(lbl_sub, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        btn_row.set_margin_top(10)

        btn_action = Gtk.Button()
        installed = is_app_installed(app)
        btn_action.set_label(t("appstore_open", "Mở") if installed else t("appstore_get", "Nhận"))
        btn_action.get_style_context().add_class("mac-hero-pill-btn")
        btn_action.connect("clicked", lambda _: self.handle_install_or_launch(app, None))
        self.hero_btn_action = btn_action
        self.hero_app = app
        btn_row.pack_start(btn_action, False, False, 0)

        btn_more = Gtk.Button(label=t("appstore_see_details", "Xem chi tiết →"))"""
assert hero_card_target in text, "hero_card_target not found"
text = text.replace(hero_card_target, hero_card_replacement, 1)

# 11. Category pages
cat_pages_target = """        categories = [
            ("arcade", "Trò chơi Arcade", ["steam", "0ad", "supertuxkart", "retroarch"]),
            ("create", "Sáng tạo", ["blender", "gimp", "inkscape", "krita", "kdenlive", "audacity", "shotcut", "freecad", "darktable"]),
            ("work", "Làm việc", ["libreoffice", "obsidian", "notion-snap-reborn", "slack", "zoom-client", "trello", "joplin-desktop", "thunderbird", "postman"]),
            ("develop", "Phát triển", ["code", "cursor", "pycharm-community", "docker", "postman", "dbeaver-ce", "android-studio", "sublime-text", "beekeeper-studio"]),
            ("play", "Giải trí", ["spotify", "vlc", "discord", "steam", "clementine", "audacity"]),
        ]
        for cat_key, cat_title, app_ids in categories:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            box.set_margin_start(28)
            box.set_margin_end(28)
            box.set_margin_bottom(36)
            scrolled.add(box)

            header_lbl = Gtk.Label(label=f"Ứng dụng {cat_title}")"""

cat_pages_replacement = """        categories = [
            ("arcade", t("appstore_arcade", "Trò chơi Arcade"), ["steam", "0ad", "supertuxkart", "retroarch"]),
            ("create", t("appstore_create", "Sáng tạo"), ["blender", "gimp", "inkscape", "krita", "kdenlive", "audacity", "shotcut", "freecad", "darktable"]),
            ("work", t("appstore_work", "Làm việc"), ["libreoffice", "obsidian", "notion-snap-reborn", "slack", "zoom-client", "trello", "joplin-desktop", "thunderbird", "postman"]),
            ("develop", t("appstore_develop", "Phát triển"), ["code", "cursor", "pycharm-community", "docker", "postman", "dbeaver-ce", "android-studio", "sublime-text", "beekeeper-studio"]),
            ("play", t("appstore_play", "Giải trí"), ["spotify", "vlc", "discord", "steam", "clementine", "audacity"]),
        ]
        for cat_key, cat_title, app_ids in categories:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            box.set_margin_start(28)
            box.set_margin_end(28)
            box.set_margin_bottom(36)
            scrolled.add(box)

            header_lbl = Gtk.Label(label=t("appstore_apps_in_cat", f"Ứng dụng {cat_title}", name=cat_title))"""
assert cat_pages_target in text, "cat_pages_target not found"
text = text.replace(cat_pages_target, cat_pages_replacement, 1)

# 12. Updates page
updates_page_target = """        self.lbl_updates_title = Gtk.Label(label="Cập nhật phần mềm")
        self.lbl_updates_title.get_style_context().add_class("mac-section-title")
        self.lbl_updates_title.set_xalign(0.0)
        self.lbl_updates_sub = Gtk.Label(label="Đang kiểm tra các bản cập nhật hệ thống và ứng dụng...")
        self.lbl_updates_sub.get_style_context().add_class("mac-app-subtitle")
        self.lbl_updates_sub.set_xalign(0.0)
        info_box.pack_start(self.lbl_updates_title, False, False, 0)
        info_box.pack_start(self.lbl_updates_sub, False, False, 0)

        # Summary Progress Bar for "Update All"
        self.updates_summary_progress = Gtk.ProgressBar()
        self.updates_summary_progress.get_style_context().add_class("mac-store-progress")
        self.updates_summary_progress.set_size_request(-1, 5)
        self.updates_summary_progress.set_no_show_all(True)
        info_box.pack_start(self.updates_summary_progress, False, False, 2)

        self.updates_summary_card.pack_start(info_box, True, True, 0)

        self.btn_update_all = Gtk.Button(label="Cập nhật tất cả")"""

updates_page_replacement = """        self.lbl_updates_title = Gtk.Label(label=t("appstore_updates_title", "Cập nhật phần mềm"))
        self.lbl_updates_title.get_style_context().add_class("mac-section-title")
        self.lbl_updates_title.set_xalign(0.0)
        self.lbl_updates_sub = Gtk.Label(label=t("appstore_updates_checking", "Đang kiểm tra các bản cập nhật hệ thống và ứng dụng..."))
        self.lbl_updates_sub.get_style_context().add_class("mac-app-subtitle")
        self.lbl_updates_sub.set_xalign(0.0)
        info_box.pack_start(self.lbl_updates_title, False, False, 0)
        info_box.pack_start(self.lbl_updates_sub, False, False, 0)

        # Summary Progress Bar for "Update All"
        self.updates_summary_progress = Gtk.ProgressBar()
        self.updates_summary_progress.get_style_context().add_class("mac-store-progress")
        self.updates_summary_progress.set_size_request(-1, 5)
        self.updates_summary_progress.set_no_show_all(True)
        info_box.pack_start(self.updates_summary_progress, False, False, 2)

        self.updates_summary_card.pack_start(info_box, True, True, 0)

        self.btn_update_all = Gtk.Button(label=t("appstore_update_all", "Cập nhật tất cả"))"""
assert updates_page_target in text, "updates_page_target not found"
text = text.replace(updates_page_target, updates_page_replacement, 1)

# 13. Updates refresh scan text
scan_updates_target = """        if hasattr(self, 'spinner'):
            self.spinner.start()
        self.set_status("Đang quét các bản cập nhật hệ thống...")"""
scan_updates_replacement = """        if hasattr(self, 'spinner'):
            self.spinner.start()
        self.set_status(t("appstore_scanning_updates", "Đang quét các bản cập nhật hệ thống..."))"""
assert scan_updates_target in text, "scan_updates_target not found"
text = text.replace(scan_updates_target, scan_updates_replacement, 1)

# 14. Updates render text
render_updates_target = """        if updates:
            self.lbl_updates_sub.set_text(f"Có {len(updates)} bản cập nhật ứng dụng và hệ thống khả dụng.")
            self.btn_update_all.set_sensitive(True)

            lbl_list = Gtk.Label(label="Bản cập nhật đang chờ")"""
render_updates_replacement = """        if updates:
            self.lbl_updates_sub.set_text(t("appstore_pending_updates", f"Có {len(updates)} bản cập nhật ứng dụng và hệ thống khả dụng."))
            self.btn_update_all.set_sensitive(True)

            lbl_list = Gtk.Label(label=t("appstore_pending_updates", "Bản cập nhật đang chờ"))"""
assert render_updates_target in text, "render_updates_target not found"
text = text.replace(render_updates_target, render_updates_replacement, 1)

btn_up_target = """                btn_up = Gtk.Button(label="CẬP NHẬT")"""
btn_up_replacement = """                btn_up = Gtk.Button(label=t("appstore_update_btn", "CẬP NHẬT"))"""
assert btn_up_target in text, "btn_up_target not found"
text = text.replace(btn_up_target, btn_up_replacement, 1)

done_up_target = """            self.lbl_updates_sub.set_text("Tất cả ứng dụng của bạn đã được cập nhật.")
            self.btn_update_all.set_sensitive(False)

            empty_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_card.get_style_context().add_class("mac-updates-summary-card")
            empty_card.set_margin_top(10)
            empty_card.set_valign(Gtk.Align.CENTER)

            check_icon = get_image("checkmark_circle", 48, "#34c759")
            check_icon.set_margin_bottom(6)
            empty_card.pack_start(check_icon, False, False, 0)

            lbl_done = Gtk.Label(label="Tất cả ứng dụng đã được cập nhật")
            lbl_done.get_style_context().add_class("mac-section-title")
            empty_card.pack_start(lbl_done, False, False, 0)

            lbl_empty = Gtk.Label(label="Không có bản cập nhật nào khả dụng vào lúc này.")
            lbl_empty.get_style_context().add_class("mac-app-subtitle")
            empty_card.pack_start(lbl_empty, False, False, 0)

            self.updates_list_container.pack_start(empty_card, False, False, 16)
            self.btn_update_all.set_label("Đã cập nhật")"""

done_up_replacement = """            self.lbl_updates_sub.set_text(t("appstore_all_updated_sub", "Tất cả ứng dụng của bạn đã được cập nhật."))
            self.btn_update_all.set_sensitive(False)

            empty_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_card.get_style_context().add_class("mac-updates-summary-card")
            empty_card.set_margin_top(10)
            empty_card.set_valign(Gtk.Align.CENTER)

            check_icon = get_image("checkmark_circle", 48, "#34c759")
            check_icon.set_margin_bottom(6)
            empty_card.pack_start(check_icon, False, False, 0)

            lbl_done = Gtk.Label(label=t("appstore_all_updated", "Tất cả ứng dụng đã được cập nhật"))
            lbl_done.get_style_context().add_class("mac-section-title")
            empty_card.pack_start(lbl_done, False, False, 0)

            lbl_empty = Gtk.Label(label=t("appstore_no_updates", "Không có bản cập nhật nào khả dụng vào lúc này."))
            lbl_empty.get_style_context().add_class("mac-app-subtitle")
            empty_card.pack_start(lbl_empty, False, False, 0)

            self.updates_list_container.pack_start(empty_card, False, False, 16)
            self.btn_update_all.set_label(t("appstore_updated_btn", "Đã cập nhật"))"""
assert done_up_target in text, "done_up_target not found"
text = text.replace(done_up_target, done_up_replacement, 1)

# 15. Detail sheet
detail_sheet_target = """        btn_act = Gtk.Button()
        installed = is_app_installed(app)
        btn_act.set_label("Mở" if installed else "Nhận")
        btn_act.get_style_context().add_class("mac-pill-btn")
        btn_act.get_style_context().add_class("pill-open" if installed else "pill-get")
        btn_act.set_valign(Gtk.Align.CENTER)
        btn_act.connect("clicked", lambda _: self.handle_install_or_launch(app, None))
        btn_box.pack_start(btn_act, False, False, 0)
        self.detail_btn_act = btn_act

        if installed:
            btn_uninstall = Gtk.Button(label="Gỡ cài đặt")"""

detail_sheet_replacement = """        btn_act = Gtk.Button()
        installed = is_app_installed(app)
        btn_act.set_label(t("appstore_open", "Mở") if installed else t("appstore_get", "Nhận"))
        btn_act.get_style_context().add_class("mac-pill-btn")
        btn_act.get_style_context().add_class("pill-open" if installed else "pill-get")
        btn_act.set_valign(Gtk.Align.CENTER)
        btn_act.connect("clicked", lambda _: self.handle_install_or_launch(app, None))
        btn_box.pack_start(btn_act, False, False, 0)
        self.detail_btn_act = btn_act

        if installed:
            btn_uninstall = Gtk.Button(label=t("appstore_uninstall", "Gỡ cài đặt"))"""
assert detail_sheet_target in text, "detail_sheet_target not found"
text = text.replace(detail_sheet_target, detail_sheet_replacement, 1)

detail_installing_target = """        if app.get("id") in self._installing_apps:
            btn_act.set_label("Đang cài đặt...")"""
detail_installing_replacement = """        if app.get("id") in self._installing_apps:
            btn_act.set_label(t("appstore_installing", "Đang cài đặt…"))"""
assert detail_installing_target in text, "detail_installing_target not found"
text = text.replace(detail_installing_target, detail_installing_replacement, 1)

detail_metrics_target = """        add_metric(f"{app.get('rating', 4.8)} ★", f"{app.get('reviews', '10K')} ĐÁNH GIÁ")
        add_metric("4+", "ĐỘ TUỔI")
        add_metric(app.get("category_name", "App"), "BẢNG XẾP HẠNG")
        add_metric(app.get("developer", "Team").split()[0], "NHÀ PHÁT TRIỂN")
        add_metric(app.get("size", "80 MB"), "DUNG LƯỢNG")

        self.detail_content.pack_start(strip, False, False, 4)

        # Description
        lbl_desc_title = Gtk.Label(label="Mô tả")
        lbl_desc_title.get_style_context().add_class("mac-section-title")
        lbl_desc_title.set_xalign(0.0)
        self.detail_content.pack_start(lbl_desc_title, False, False, 0)

        lbl_desc = Gtk.Label(label=app.get("desc", app.get("subtitle", "")))
        lbl_desc.get_style_context().add_class("mac-detail-body")
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_xalign(0.0)
        self.detail_content.pack_start(lbl_desc, False, False, 0)

        # Features
        features = app.get("features", [])
        if features:
            lbl_feat_title = Gtk.Label(label="Tính năng nổi bật")"""

detail_metrics_replacement = """        add_metric(f"{app.get('rating', 4.8)} ★", f"{app.get('reviews', '10K')} {t('appstore_ratings', 'ĐÁNH GIÁ')}")
        add_metric("4+", t("appstore_age", "ĐỘ TUỔI"))
        add_metric(app.get("category_name", "App"), t("appstore_chart", "BẢNG XẾP HẠNG"))
        add_metric(app.get("developer", "Team").split()[0], t("appstore_developer", "NHÀ PHÁT TRIỂN"))
        add_metric(app.get("size", "80 MB"), t("appstore_size", "DUNG LƯỢNG"))

        self.detail_content.pack_start(strip, False, False, 4)

        # Description
        lbl_desc_title = Gtk.Label(label=t("appstore_description", "Mô tả"))
        lbl_desc_title.get_style_context().add_class("mac-section-title")
        lbl_desc_title.set_xalign(0.0)
        self.detail_content.pack_start(lbl_desc_title, False, False, 0)

        lbl_desc = Gtk.Label(label=app.get("desc", app.get("subtitle", "")))
        lbl_desc.get_style_context().add_class("mac-detail-body")
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_xalign(0.0)
        self.detail_content.pack_start(lbl_desc, False, False, 0)

        # Features
        features = app.get("features", [])
        if features:
            lbl_feat_title = Gtk.Label(label=t("appstore_features", "Tính năng nổi bật"))"""
assert detail_metrics_target in text, "detail_metrics_target not found"
text = text.replace(detail_metrics_target, detail_metrics_replacement, 1)

# 16. Tab titles
tab_titles_target = """        titles = {
            "categories": "Danh mục",
            "discover": "Khám phá",
            "arcade": "Arcade",
            "create": "Sáng tạo",
            "work": "Làm việc",
            "develop": "Phát triển",
            "play": "Chơi",
            "updates": "Cập nhật"
        }"""
tab_titles_replacement = """        titles = {
            "categories": t("appstore_categories", "Danh mục"),
            "discover": t("appstore_discover", "Khám phá"),
            "arcade": t("appstore_arcade", "Arcade"),
            "create": t("appstore_create", "Sáng tạo"),
            "work": t("appstore_work", "Làm việc"),
            "develop": t("appstore_develop", "Phát triển"),
            "play": t("appstore_play", "Chơi"),
            "updates": t("appstore_updates", "Cập nhật")
        }"""
assert tab_titles_target in text, "tab_titles_target not found"
text = text.replace(tab_titles_target, tab_titles_replacement, 1)

# 17. Add _on_language_changed method
appstore_methods = """    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("appstore_title", "App Store"))
            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("appstore_search_placeholder", "Tìm kiếm"))
            if hasattr(self, "btn_back"):
                self.btn_back.set_tooltip_text(t("back", "Quay lại"))

            nav_titles = {
                "discover": t("appstore_discover", "Khám phá"),
                "arcade": t("appstore_arcade", "Arcade"),
                "create": t("appstore_create", "Sáng tạo"),
                "work": t("appstore_work", "Làm việc"),
                "play": t("appstore_play", "Chơi"),
                "develop": t("appstore_develop", "Phát triển"),
                "categories": t("appstore_categories", "Danh mục"),
                "updates": t("appstore_updates", "Cập nhật"),
            }
            if hasattr(self, "_nav_buttons"):
                for k, item in self._nav_buttons.items():
                    if k in nav_titles and len(item) >= 4:
                        item[3].set_text(nav_titles[k])

            if hasattr(self, "header_title") and hasattr(self, "current_tab"):
                self.header_title.set_text(nav_titles.get(self.current_tab, ""))

            if hasattr(self, "_active_cards"):
                for cards in self._active_cards.values():
                    for c in cards:
                        c.update_state()

            if hasattr(self, "hero_btn_action") and hasattr(self, "hero_app"):
                inst = is_app_installed(self.hero_app)
                self.hero_btn_action.set_label(t("appstore_open", "Mở") if inst else t("appstore_get", "Nhận"))

            if hasattr(self, "stack"):
                old_cat = self.stack.get_child_by_name("categories")
                if old_cat:
                    self.stack.remove(old_cat)
                self._build_categories_overview_page()

                old_disc = self.stack.get_child_by_name("discover")
                if old_disc:
                    self.stack.remove(old_disc)
                self._build_discover_page()

                for cat_key in ["arcade", "create", "work", "develop", "play"]:
                    old_c = self.stack.get_child_by_name(cat_key)
                    if old_c:
                        self.stack.remove(old_c)
                self._build_category_pages()

                self.select_tab(self.current_tab)
        except Exception as e:
            print(f"[AppStore] Error retranslating UI: {e}")
"""

hook_store_target = "    def _navigate_back(self):"
assert hook_store_target in text, "hook_store_target not found"
text = text.replace(hook_store_target, appstore_methods + "\n" + hook_store_target, 1)

with open("src/ui/macos_appstore_window.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched src/ui/macos_appstore_window.py")
