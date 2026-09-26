#!/usr/bin/env python3
"""
Patch script for src/ui/desktop_widgets/weather_widget.py to support dynamic multilingual translation.
"""

TARGET = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/src/ui/desktop_widgets/weather_widget.py"

def patch_weather_widget():
    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Imports
    old_imp = "from src.modules.weather import WeatherManager"
    new_imp = "from src.modules.weather import WeatherManager\nfrom src.utils.i18n import t, get_current_language, add_language_listener"
    if old_imp in content:
        content = content.replace(old_imp, new_imp, 1)
        print("Updated imports in weather_widget.py")

    # 2. DesktopWeatherWidget.__init__ language listener
    old_init = """        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)"""

    new_init = """        self.set_role("desktop-widget")
        self.set_default_size(self.total_w, self.total_h)
        self.set_size_request(self.total_w, self.total_h)
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass"""

    if old_init in content:
        content = content.replace(old_init, new_init, 1)
        print("Added add_language_listener in DesktopWeatherWidget.__init__")

    # 3. Add _on_language_changed in DesktopWeatherWidget
    old_update = """    def _on_weather_update(self):
        self.queue_draw()"""

    new_update = """    def _on_weather_update(self):
        self.queue_draw()

    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self.queue_draw)"""

    if old_update in content:
        content = content.replace(old_update, new_update, 1)
        print("Added _on_language_changed in DesktopWeatherWidget")

    # 4. _on_draw high/low, rain, wind, fallback city
    old_hl = """        # High/Low indicators with clear spacing: C: 32° / T: 25°
        hl_str = f"C: {wm.temp_high}°\\nT: {wm.temp_low}°"
        self._draw_text(cr, x + w - 16, y + 42, hl_str, "-apple-system, Inter, Ubuntu Medium 10", (1.0, 1.0, 1.0, 0.90), align="right")"""

    new_hl = """        # High/Low indicators with clear spacing and localized labels
        high_lbl = t("weather_high_short", "C")
        low_lbl = t("weather_low_short", "T")
        hl_str = t("weather_hl_format", "{high_lbl}: {high}°\\n{low_lbl}: {low}°",
                   high_lbl=high_lbl, low_lbl=low_lbl, high=wm.temp_high, low=wm.temp_low)
        self._draw_text(cr, x + w - 16, y + 42, hl_str, "-apple-system, Inter, Ubuntu Medium 10", (1.0, 1.0, 1.0, 0.90), align="right")"""

    if old_hl in content:
        content = content.replace(old_hl, new_hl, 1)
        print("Updated high/low rendering in DesktopWeatherWidget")

    old_metrics = """        # Column 1: Lượng mưa (Precipitation) - Left aligned
        self._draw_text(cr, col1_x, metrics_y, "Lượng mưa", "-apple-system, Inter, Ubuntu Medium 9", (0.85, 0.92, 1.0, 0.75), align="left")"""

    new_metrics = """        # Column 1: Lượng mưa (Precipitation) - Left aligned
        self._draw_text(cr, col1_x, metrics_y, t("weather_precipitation", "Lượng mưa"), "-apple-system, Inter, Ubuntu Medium 9", (0.85, 0.92, 1.0, 0.75), align="left")"""

    if old_metrics in content:
        content = content.replace(old_metrics, new_metrics, 1)
        print("Updated precipitation label in DesktopWeatherWidget")

    old_wind = """        # Column 2: Gió (Wind) - Right aligned
        self._draw_text(cr, col2_x, metrics_y, "Gió", "-apple-system, Inter, Ubuntu Medium 9", (0.85, 0.92, 1.0, 0.75), align="right")"""

    new_wind = """        # Column 2: Gió (Wind) - Right aligned
        self._draw_text(cr, col2_x, metrics_y, t("weather_wind", "Gió"), "-apple-system, Inter, Ubuntu Medium 9", (0.85, 0.92, 1.0, 0.75), align="right")"""

    if old_wind in content:
        content = content.replace(old_wind, new_wind, 1)
        print("Updated wind label in DesktopWeatherWidget")

    old_fallback_city = 'or "Thời tiết"'
    new_fallback_city = 'or t("weather_title", "Thời tiết")'
    if old_fallback_city in content:
        content = content.replace(old_fallback_city, new_fallback_city, 1)
        print("Updated fallback city in DesktopWeatherWidget")

    # 5. Context menu labels
    old_menu = """        loc_item = Gtk.MenuItem(label="Đổi Địa Điểm Thời Tiết…")
        loc_item.connect("activate", lambda _: self._on_widget_clicked())
        menu.append(loc_item)

        pin_item = Gtk.MenuItem(label="Ghim Nền Desktop" if not self.keep_below else "Nổi Trên Cửa Sổ")
        pin_item.connect("activate", self._toggle_keep_below)
        menu.append(pin_item)

        refresh_item = Gtk.MenuItem(label="Cập Nhật Thời Tiết Ngay")
        refresh_item.connect("activate", lambda _: self.weather_mgr.refresh())
        menu.append(refresh_item)

        menu.append(Gtk.SeparatorMenuItem())
        hide_item = Gtk.MenuItem(label="Ẩn Widget Thời Tiết")"""

    new_menu = """        loc_item = Gtk.MenuItem(label=t("weather_menu_change_loc", "Đổi Địa Điểm Thời Tiết…"))
        loc_item.connect("activate", lambda _: self._on_widget_clicked())
        menu.append(loc_item)

        pin_label = t("weather_menu_pin_desktop", "Ghim Nền Desktop") if not self.keep_below else t("weather_menu_float_window", "Nổi Trên Cửa Sổ")
        pin_item = Gtk.MenuItem(label=pin_label)
        pin_item.connect("activate", self._toggle_keep_below)
        menu.append(pin_item)

        refresh_item = Gtk.MenuItem(label=t("weather_menu_refresh", "Cập Nhật Thời Tiết Ngay"))
        refresh_item.connect("activate", lambda _: self.weather_mgr.refresh())
        menu.append(refresh_item)

        menu.append(Gtk.SeparatorMenuItem())
        hide_item = Gtk.MenuItem(label=t("weather_menu_hide", "Ẩn Widget Thời Tiết"))"""

    if old_menu in content:
        content = content.replace(old_menu, new_menu, 1)
        print("Updated context menu in DesktopWeatherWidget")

    # 6. MacOSWeatherWindow title and labels
    old_win_title = 'self.set_title("Thời Tiết macOS")'
    new_win_title = 'self.set_title(t("weather_title", "Thời Tiết macOS"))'
    if old_win_title in content:
        content = content.replace(old_win_title, new_win_title, 1)
        print("Updated MacOSWeatherWindow title")

    old_nav_labels = """        self.search_entry = Gtk.Entry()
        self.search_entry.get_style_context().add_class("mac-search-entry")
        self.search_entry.set_placeholder_text("Tìm Xã, Huyện, Tỉnh...")
        self.search_entry.set_width_chars(22)
        self.search_entry.connect("activate", lambda _: self._on_search_submit())
        self._suggest_timer_id = None
        self.search_entry.connect("changed", self._on_search_changed)

        self.search_btn = Gtk.Button(label="Tìm")
        self.search_btn.get_style_context().add_class("mac-pill-btn")
        self.search_btn.connect("clicked", lambda _: self._on_search_submit())

        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(self.search_btn, False, False, 0)

        auto_btn = Gtk.Button(label="Định vị tự động")"""

    new_nav_labels = """        self.search_entry = Gtk.Entry()
        self.search_entry.get_style_context().add_class("mac-search-entry")
        self.search_entry.set_placeholder_text(t("weather_search_placeholder", "Tìm thành phố, quận huyện…"))
        self.search_entry.set_width_chars(22)
        self.search_entry.connect("activate", lambda _: self._on_search_submit())
        self._suggest_timer_id = None
        self.search_entry.connect("changed", self._on_search_changed)

        self.search_btn = Gtk.Button(label=t("weather_search_btn", "Tìm"))
        self.search_btn.get_style_context().add_class("mac-pill-btn")
        self.search_btn.connect("clicked", lambda _: self._on_search_submit())

        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(self.search_btn, False, False, 0)

        self.auto_btn = Gtk.Button(label=t("weather_auto_loc", "Định vị tự động"))
        auto_btn = self.auto_btn"""

    if old_nav_labels in content:
        content = content.replace(old_nav_labels, new_nav_labels, 1)
        print("Updated nav labels in MacOSWeatherWindow")

    old_card_titles = """        my_loc_lbl = Gtk.Label(label="VỊ TRÍ CỦA TÔI")
        my_loc_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.70))
        my_loc_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Bold 10.5"))"""

    new_card_titles = """        self.my_loc_lbl = Gtk.Label(label=t("weather_my_location", "VỊ TRÍ CỦA TÔI"))
        my_loc_lbl = self.my_loc_lbl
        my_loc_lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 0.70))
        my_loc_lbl.override_font(Pango.FontDescription("-apple-system, Inter, Ubuntu Bold 10.5"))"""

    if old_card_titles in content:
        content = content.replace(old_card_titles, new_card_titles, 1)
        print("Updated my_loc_lbl in MacOSWeatherWindow")

    old_d_title = 'd_title = Gtk.Label(label="DỰ BÁO 7 NGÀY")'
    new_d_title = 'self.d_title = Gtk.Label(label=t("weather_7day_forecast", "DỰ BÁO 7 NGÀY"))\n        d_title = self.d_title'
    if old_d_title in content:
        content = content.replace(old_d_title, new_d_title, 1)
        print("Updated d_title in MacOSWeatherWindow")

    old_aqi_title = 'aqi_title = Gtk.Label(label="CHẤT LƯỢNG KHÔNG KHÍ (AQI)")'
    new_aqi_title = 'self.aqi_title = Gtk.Label(label=t("weather_aqi", "CHẤT LƯỢNG KHÔNG KHÍ (AQI)"))\n        aqi_title = self.aqi_title'
    if old_aqi_title in content:
        content = content.replace(old_aqi_title, new_aqi_title, 1)
        print("Updated aqi_title in MacOSWeatherWindow")

    old_wind_title = 'wind_title = Gtk.Label(label="GIÓ & CẢM NHẬN")'
    new_wind_title = 'self.wind_title = Gtk.Label(label=t("weather_wind_feels", "GIÓ & CẢM NHẬN"))\n        wind_title = self.wind_title'
    if old_wind_title in content:
        content = content.replace(old_wind_title, new_wind_title, 1)
        print("Updated wind_title in MacOSWeatherWindow")

    old_admin_title = 'admin_title = Gtk.Label(label="ĐỊA DANH HÀNH CHÍNH (4 CẤP)")'
    new_admin_title = 'self.admin_title = Gtk.Label(label=t("weather_admin_tier", "ĐỊA DANH HÀNH CHÍNH (4 CẤP)"))\n        admin_title = self.admin_title'
    if old_admin_title in content:
        content = content.replace(old_admin_title, new_admin_title, 1)
        print("Updated admin_title in MacOSWeatherWindow")

    # Add language listener in MacOSWeatherWindow
    old_win_init_end = """        # Connect update listener
        self.weather_mgr.add_listener(self._on_weather_updated)

        self._update_ui_data()"""

    new_win_init_end = """        # Connect update listener
        self.weather_mgr.add_listener(self._on_weather_updated)
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

        self._update_ui_data()"""

    if old_win_init_end in content:
        content = content.replace(old_win_init_end, new_win_init_end, 1)
        print("Added language listener in MacOSWeatherWindow.__init__")

    # Add _on_language_changed and _retranslate_ui in MacOSWeatherWindow
    methods_win = """    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("weather_title", "Thời Tiết macOS"))
            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("weather_search_placeholder", "Tìm thành phố, quận huyện…"))
            if hasattr(self, "search_btn"):
                self.search_btn.set_label(t("weather_search_btn", "Tìm"))
            if hasattr(self, "auto_btn"):
                self.auto_btn.set_label(t("weather_auto_loc", "Định vị tự động"))
            if hasattr(self, "my_loc_lbl"):
                self.my_loc_lbl.set_text(t("weather_my_location", "VỊ TRÍ CỦA TÔI"))
            if hasattr(self, "d_title"):
                self.d_title.set_text(t("weather_7day_forecast", "DỰ BÁO 7 NGÀY"))
            if hasattr(self, "aqi_title"):
                self.aqi_title.set_text(t("weather_aqi", "CHẤT LƯỢNG KHÔNG KHÍ (AQI)"))
            if hasattr(self, "wind_title"):
                self.wind_title.set_text(t("weather_wind_feels", "GIÓ & CẢM NHẬN"))
            if hasattr(self, "admin_title"):
                self.admin_title.set_text(t("weather_admin_tier", "ĐỊA DANH HÀNH CHÍNH (4 CẤP)"))
            self._update_ui_data()
        except Exception as e:
            print(f"[MacOSWeatherWindow] _retranslate_ui error: {e}")

"""
    pos_win = content.find("    def _on_weather_updated(self):")
    if pos_win != -1 and "_retranslate_ui" not in content:
        content = content[:pos_win] + methods_win + content[pos_win:]
        print("Added _retranslate_ui to MacOSWeatherWindow")

    # Localize wind & humidity card text in _update_ui_data
    old_wind_markup = """        # Wind & Humidity
        self.wind_info_lbl.set_markup(
            f"💨 <b>Tốc độ gió:</b> {wm.wind_speed} km/h  ({wm.wind_dir_name})\\n"
            f"💧 <b>Độ ẩm:</b> {wm.humidity}%  •  🌡️ <b>Cảm nhận:</b> {wm.apparent_temp}°C\\n"
            f"☀️ <b>Chỉ số UV:</b> {wm.uv_index} (Trung bình)  •  🌧️ <b>Mưa 24g:</b> {wm.precipitation_24h}"
        )"""

    new_wind_markup = """        # Wind & Humidity (Localized)
        self.wind_info_lbl.set_markup(
            f"💨 <b>{t('weather_wind', 'Gió')}:</b> {wm.wind_speed} km/h  ({wm.wind_dir_name})\\n"
            f"💧 <b>{t('weather_humidity', 'Độ ẩm')}:</b> {wm.humidity}%  •  🌡️ <b>{t('weather_feels_like', 'Cảm nhận')}:</b> {wm.apparent_temp}°C\\n"
            f"☀️ <b>{t('weather_uv', 'Chỉ số UV')}:</b> {wm.uv_index}  •  🌧️ <b>{t('weather_precipitation', 'Lượng mưa')}:</b> {wm.precipitation_24h}"
        )"""

    if old_wind_markup in content:
        content = content.replace(old_wind_markup, new_wind_markup, 1)
        print("Updated wind markup in _update_ui_data")

    # Localize admin items
    old_admin_items = """        admin_items = [
            ("🏷️ Xã / Phường:", ward_text, "#38bdf8"),
            ("🏢 Quận / Huyện / TP:", dist_text, "#ffffff"),
            ("🏛️ Tỉnh / Thành phố:", prov_text, "#ffffff"),
            ("🇻🇳 Quốc gia:", country_text, "#fde047"),
            ("🌅 Mặt trời mọc:", f"{wm.sunrise}   |   🌇 Lặn: {wm.sunset}", "#cbd5e1"),
        ]"""

    new_admin_items = """        admin_items = [
            ("🏷️ Xã / Phường:", ward_text, "#38bdf8"),
            ("🏢 Quận / Huyện / TP:", dist_text, "#ffffff"),
            ("🏛️ Tỉnh / Thành phố:", prov_text, "#ffffff"),
            ("🌍 Quốc gia:", country_text, "#fde047"),
            (f"🌅 {t('weather_sunrise', 'Mặt trời mọc')}:", f"{wm.sunrise}   |   🌇 {t('weather_sunset', 'Lặn')}: {wm.sunset}", "#cbd5e1"),
        ]"""

    if old_admin_items in content:
        content = content.replace(old_admin_items, new_admin_items, 1)
        print("Updated admin items in _update_ui_data")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched weather_widget.py!")

if __name__ == "__main__":
    patch_weather_widget()
