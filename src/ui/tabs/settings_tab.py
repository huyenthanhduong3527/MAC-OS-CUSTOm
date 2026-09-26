"""
Settings Tab for Dynamic Island.
Configures Dimensions (Width & Height for Compact Pill & Expanded Card),
Top Y-offset, hover expansion, dark mode, widgets, and quit button.
"""

import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.config import config
from src.utils.icons import get_pixbuf
from src.utils.theme import is_dark_mode, toggle_dark_mode

class SettingsTab(Gtk.Box):
    def __init__(self, on_offset_change=None, on_size_change=None, on_quit=None,
                 on_cosmos_change=None, on_clock_change=None, on_music_change=None,
                 on_calendar_change=None, on_weather_change=None, on_battery_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_style_context().add_class("tab-content")

        self.on_offset_change = on_offset_change
        self.on_size_change = on_size_change
        self.on_quit = on_quit
        self.on_cosmos_change = on_cosmos_change
        self.on_clock_change = on_clock_change
        self.on_music_change = on_music_change
        self.on_calendar_change = on_calendar_change
        self.on_weather_change = on_weather_change
        self.on_battery_change = on_battery_change

        # ScrolledWindow container so everything fits smoothly
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_hexpand(True)
        self.scroll.set_vexpand(True)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.content_box.set_margin_right(4)
        self.scroll.add(self.content_box)
        self.pack_start(self.scroll, True, True, 0)

        # 0. Open Full macOS System Settings Button
        full_settings_btn = Gtk.Button(label="Mở Cài Đặt Hệ Thống macOS (Apple System Settings)…")
        full_settings_btn.get_style_context().add_class("ctrl-btn")
        full_settings_btn.connect("clicked", lambda _: self._open_full_settings())
        self.content_box.pack_start(full_settings_btn, False, False, 4)

        # -----------------------------------------------------------------
        # SECTION 1: KÍCH THƯỚC & VỊ TRÍ (Dimensions & Position)
        # -----------------------------------------------------------------
        sec_dim_lbl = self._create_section_header("Kích thước & Vị trí (Dimensions)")
        self.content_box.pack_start(sec_dim_lbl, False, False, 2)

        # 1.1 Compact Pill Width
        w_box, self.compact_w_scale, self.compact_w_lbl = self._create_slider_row(
            "Chiều dài viên thuốc (Compact Width)",
            160, 420, 5,
            config.get("compact_width", 230),
            self._on_compact_w_change
        )
        self.content_box.pack_start(w_box, False, False, 0)

        # 1.2 Compact Pill Height
        h_box, self.compact_h_scale, self.compact_h_lbl = self._create_slider_row(
            "Chiều cao viên thuốc (Compact Height)",
            28, 55, 2,
            config.get("compact_height", 40),
            self._on_compact_h_change
        )
        self.content_box.pack_start(h_box, False, False, 0)

        # 1.3 Expanded Card Width
        ew_box, self.exp_w_scale, self.exp_w_lbl = self._create_slider_row(
            "Chiều rộng mở to (Expanded Width)",
            460, 750, 5,
            config.get("expanded_width", 505),
            self._on_exp_w_change
        )
        self.content_box.pack_start(ew_box, False, False, 0)

        # 1.4 Expanded Card Height
        eh_box, self.exp_h_scale, self.exp_h_lbl = self._create_slider_row(
            "Chiều cao mở to (Expanded Height)",
            260, 450, 5,
            config.get("expanded_height", 280),
            self._on_exp_h_change
        )
        self.content_box.pack_start(eh_box, False, False, 0)

        # 1.5 Top Offset (Y Margin)
        y_box, self.y_scale, self.y_val_lbl = self._create_slider_row(
            "Khoảng cách mép trên (Top Offset Y)",
            0, 120, 2,
            config.get("y_offset", 44),
            self._on_y_change
        )
        self.content_box.pack_start(y_box, False, False, 0)

        # 1.6 Reset Size Button
        reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        reset_box.set_halign(Gtk.Align.END)
        reset_btn = Gtk.Button(label="Đặt lại kích thước mặc định")
        reset_btn.get_style_context().add_class("ctrl-btn")
        reset_btn.connect("clicked", self._on_reset_size_clicked)
        reset_box.pack_start(reset_btn, False, False, 0)
        self.content_box.pack_start(reset_box, False, False, 2)

        # -----------------------------------------------------------------
        # SECTION 2: TÙY CHỌN HIỂN THỊ (Display & Interaction)
        # -----------------------------------------------------------------
        sec_opt_lbl = self._create_section_header("Tùy chọn hiển thị (Options)")
        self.content_box.pack_start(sec_opt_lbl, False, False, 4)

        # 2.1 Hover toggle & Demo Mode
        opt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        hover_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hover_lbl = Gtk.Label(label="Mở rộng khi rê chuột")
        hover_lbl.get_style_context().add_class("vital-label")
        self.hover_switch = Gtk.Switch()
        self.hover_switch.set_active(config.get("expand_on_hover", False))
        self.hover_switch.connect("state-set", self._on_hover_toggle)
        hover_box.pack_start(hover_lbl, False, False, 0)
        hover_box.pack_start(self.hover_switch, False, False, 0)
        opt_box.pack_start(hover_box, False, False, 0)

        demo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        demo_lbl = Gtk.Label(label="Demo Playlist")
        demo_lbl.get_style_context().add_class("vital-label")
        self.demo_switch = Gtk.Switch()
        self.demo_switch.set_active(config.get("demo_mode", False))
        self.demo_switch.connect("state-set", self._on_demo_toggle)
        demo_box.pack_start(demo_lbl, False, False, 0)
        demo_box.pack_start(self.demo_switch, False, False, 0)
        opt_box.pack_end(demo_box, False, False, 0)

        self.content_box.pack_start(opt_box, False, False, 0)

        # 2.2 GNOME Notification Banner toggle
        notif_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        notif_lbl = Gtk.Label(label="Thay thế thông báo GNOME (Hiện trên Island)")
        notif_lbl.get_style_context().add_class("vital-label")
        self.notif_switch = Gtk.Switch()
        try:
            res = subprocess.run(["gsettings", "get", "org.gnome.desktop.notifications", "show-banners"], capture_output=True, text=True)
            self.notif_switch.set_active("false" in res.stdout.lower())
        except Exception:
            self.notif_switch.set_active(True)
        self.notif_switch.connect("state-set", self._on_notif_banner_toggle)
        notif_box.pack_start(notif_lbl, False, False, 0)
        notif_box.pack_end(self.notif_switch, False, False, 0)
        self.content_box.pack_start(notif_box, False, False, 0)

        # 2.3 Dark Mode Toggle row
        dark_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dark_lbl = Gtk.Label(label="Chế độ Tối (Dark Mode OLED)")
        dark_lbl.get_style_context().add_class("vital-label")
        self.dark_switch = Gtk.Switch()
        self.dark_switch.set_active(is_dark_mode())
        self.dark_switch.connect("state-set", self._on_dark_toggle)
        dark_box.pack_start(dark_lbl, False, False, 0)
        dark_box.pack_end(self.dark_switch, False, False, 0)
        self.content_box.pack_start(dark_box, False, False, 0)

        # -----------------------------------------------------------------
        # SECTION 3: WIDGETS & VŨ TRỤ ORBIT
        # -----------------------------------------------------------------
        sec_wid_lbl = self._create_section_header("Widgets Desktop & App Launcher")
        self.content_box.pack_start(sec_wid_lbl, False, False, 4)

        # 3.1 Cosmic Orbit
        cosmos_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cosmos_lbl = Gtk.Label(label="Vũ trụ Orbit (Solar App Launcher)")
        cosmos_lbl.get_style_context().add_class("vital-label")
        self.cosmos_switch = Gtk.Switch()
        self.cosmos_switch.set_active(config.get("enable_cosmic_orbit", False))
        self.cosmos_switch.connect("state-set", self._on_cosmos_toggle)
        cosmos_box.pack_start(cosmos_lbl, False, False, 0)
        cosmos_box.pack_end(self.cosmos_switch, False, False, 0)
        self.content_box.pack_start(cosmos_box, False, False, 0)

        # 3.2 Clock Widget
        clock_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        clock_lbl = Gtk.Label(label="Widget Đồng Hồ Desktop (Apple Clock)")
        clock_lbl.get_style_context().add_class("vital-label")
        self.clock_switch = Gtk.Switch()
        self.clock_switch.set_active(config.get("enable_desktop_clock", False))
        self.clock_switch.connect("state-set", self._on_clock_toggle)
        clock_box.pack_start(clock_lbl, False, False, 0)
        clock_box.pack_end(self.clock_switch, False, False, 0)
        self.content_box.pack_start(clock_box, False, False, 0)

        # 3.3 Music Widget
        music_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        music_lbl = Gtk.Label(label="Widget Âm Nhạc Desktop (Apple Music)")
        music_lbl.get_style_context().add_class("vital-label")
        self.music_switch = Gtk.Switch()
        self.music_switch.set_active(config.get("enable_desktop_music", False))
        self.music_switch.connect("state-set", self._on_music_toggle)
        music_box.pack_start(music_lbl, False, False, 0)
        music_box.pack_end(self.music_switch, False, False, 0)
        self.content_box.pack_start(music_box, False, False, 0)

        # 3.4 Calendar & Lunar Widget
        cal_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cal_lbl = Gtk.Label(label="Widget Lịch & Âm Lịch (Apple Calendar)")
        cal_lbl.get_style_context().add_class("vital-label")
        self.cal_switch = Gtk.Switch()
        self.cal_switch.set_active(config.get("enable_desktop_calendar", True))
        self.cal_switch.connect("state-set", self._on_calendar_toggle)
        cal_box.pack_start(cal_lbl, False, False, 0)
        cal_box.pack_end(self.cal_switch, False, False, 0)
        self.content_box.pack_start(cal_box, False, False, 0)

        # 3.5 Weather Widget
        weather_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        weather_lbl = Gtk.Label(label="Widget Thời Tiết (Apple Weather)")
        weather_lbl.get_style_context().add_class("vital-label")
        self.weather_switch = Gtk.Switch()
        self.weather_switch.set_active(config.get("enable_desktop_weather", True))
        self.weather_switch.connect("state-set", self._on_weather_toggle)
        weather_box.pack_start(weather_lbl, False, False, 0)
        weather_box.pack_end(self.weather_switch, False, False, 0)
        self.content_box.pack_start(weather_box, False, False, 0)

        # 3.6 Battery Widget
        bat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bat_lbl = Gtk.Label(label="Widget Pin 4 Thiết Bị (Apple Batteries)")
        bat_lbl.get_style_context().add_class("vital-label")
        self.bat_switch = Gtk.Switch()
        self.bat_switch.set_active(config.get("enable_desktop_battery", True))
        self.bat_switch.connect("state-set", self._on_battery_toggle)
        bat_box.pack_start(bat_lbl, False, False, 0)
        bat_box.pack_end(self.bat_switch, False, False, 0)
        self.content_box.pack_start(bat_box, False, False, 0)

        # -----------------------------------------------------------------
        # SECTION 4: THAO TÁC (Quit)
        # -----------------------------------------------------------------
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.CENTER)
        quit_btn = Gtk.Button(label="Quit Dynamic Island")
        quit_btn.get_style_context().add_class("ctrl-btn")
        quit_btn.connect("clicked", lambda b: self.on_quit() if self.on_quit else Gtk.main_quit())
        action_box.pack_start(quit_btn, False, False, 0)
        self.content_box.pack_start(action_box, False, False, 8)

    def _open_full_settings(self):
        try:
            from src.ui.macos_settings_window import MacOSSettingsWindow
            win = MacOSSettingsWindow.get_instance()
            win.show_window()
        except Exception as e:
            print(f"[SettingsTab] Error opening macOS Settings: {e}")

    def _create_section_header(self, title):
        lbl = Gtk.Label(label=title)
        lbl.get_style_context().add_class("vital-value")
        lbl.set_xalign(0.0)
        lbl.set_margin_top(4)
        return lbl

    def _create_slider_row(self, title, min_val, max_val, step, current_val, callback):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=title)
        lbl.get_style_context().add_class("vital-label")
        lbl.set_xalign(0.0)
        lbl.set_size_request(220, -1)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, step)
        scale.set_draw_value(False)
        scale.set_value(current_val)
        scale.set_hexpand(True)

        val_lbl = Gtk.Label(label=f"{int(current_val)}px")
        val_lbl.get_style_context().add_class("vital-label")
        val_lbl.set_size_request(45, -1)
        val_lbl.set_xalign(1.0)

        def on_change(s):
            val = int(s.get_value())
            val_lbl.set_text(f"{val}px")
            callback(val)

        scale.connect("value-changed", on_change)

        box.pack_start(lbl, False, False, 0)
        box.pack_start(scale, True, True, 0)
        box.pack_end(val_lbl, False, False, 0)
        return box, scale, val_lbl

    def _on_compact_w_change(self, val):
        config.set("compact_width", val)
        if self.on_size_change:
            self.on_size_change(compact_w=val)

    def _on_compact_h_change(self, val):
        config.set("compact_height", val)
        if self.on_size_change:
            self.on_size_change(compact_h=val)

    def _on_exp_w_change(self, val):
        config.set("expanded_width", val)
        if self.on_size_change:
            self.on_size_change(expanded_w=val)

    def _on_exp_h_change(self, val):
        config.set("expanded_height", val)
        if self.on_size_change:
            self.on_size_change(expanded_h=val)

    def _on_y_change(self, val):
        config.set("y_offset", val)
        if self.on_offset_change:
            self.on_offset_change(val)

    def _on_reset_size_clicked(self, widget):
        self.compact_w_scale.set_value(230)
        self.compact_h_scale.set_value(40)
        self.exp_w_scale.set_value(505)
        self.exp_h_scale.set_value(280)
        self.y_scale.set_value(44)
        if self.on_size_change:
            self.on_size_change(compact_w=230, compact_h=40, expanded_w=505, expanded_h=280)
        if self.on_offset_change:
            self.on_offset_change(44)

    def _on_hover_toggle(self, switch, state):
        config.set("expand_on_hover", state)
        return False

    def _on_demo_toggle(self, switch, state):
        config.set("demo_mode", state)
        return False

    def _on_notif_banner_toggle(self, switch, state):
        val = "false" if state else "true"
        try:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", val], check=False)
        except Exception:
            pass
        return False

    def _on_dark_toggle(self, switch, state):
        toggle_dark_mode()
        return False

    def _on_cosmos_toggle(self, switch, state):
        config.set("enable_cosmic_orbit", state)
        if self.on_cosmos_change:
            self.on_cosmos_change(state)
        return False

    def _on_clock_toggle(self, switch, state):
        config.set("enable_desktop_clock", state)
        if self.on_clock_change:
            self.on_clock_change(state)
        return False

    def _on_music_toggle(self, switch, state):
        config.set("enable_desktop_music", state)
        if self.on_music_change:
            self.on_music_change(state)
        return False

    def _on_calendar_toggle(self, switch, state):
        config.set("enable_desktop_calendar", state)
        if self.on_calendar_change:
            self.on_calendar_change(state)
        return False

    def _on_weather_toggle(self, switch, state):
        config.set("enable_desktop_weather", state)
        if self.on_weather_change:
            self.on_weather_change(state)
        return False

    def _on_battery_toggle(self, switch, state):
        config.set("enable_desktop_battery", state)
        if self.on_battery_change:
            self.on_battery_change(state)
        return False
