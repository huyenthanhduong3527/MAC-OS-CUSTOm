"""
macOS Control Center (Trung tâm Điều khiển) for Dynamic Island on Ubuntu Linux.
Authentic Apple macOS Sonoma / Sequoia design:
- Top Grid: Wi-Fi, Bluetooth, AirDrop with disclosure chevrons.
- Interactive Wi-Fi Submenu: Clicking Wi-Fi opens the Network Selection view with real-time scanning,
  signal strength, connected network management (disconnect/auto-join), and one-click/password connection.
- Quick Actions: Do Not Disturb (Tập trung) and Night Light (Đèn đêm).
- Thick fluid capsule sliders for Display Brightness & Sound Volume with embedded vector icons.
- Apple Music style Now Playing media card with vibrant artwork / gradient tile and playback controls.
- Battery stats and quick system action buttons (Settings, Lock Screen, Dark/Light Mode).
"""

import os
import sys
import math
import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo

from src.utils.theme import is_dark_mode
from src.utils.icons import get_pixbuf
from src.utils.i18n import t as _t, add_language_listener

_control_center_instance = None


class MacControlSlider(Gtk.DrawingArea):
    """
    Authentic Apple macOS Control Center fluid capsule slider.
    Features:
    - Thick rounded capsule (28px height, 14px radius).
    - Crisp track with inset depth.
    - Fluid filled progress bar (Vibrant #007aff in Light mode, pure white in Dark mode).
    - Embedded icon (Sun / Speaker) on the left side of the track.
    - Auto-inverting icon contrast when the fill covers the icon.
    - Smooth click & drag handling.
    """
    def __init__(self, icon_name="sun", value=100, is_dark=False, on_change=None):
        super().__init__()
        self.icon_name = icon_name
        self.value = max(0, min(100, int(value)))
        self.is_dark = is_dark
        self.on_change = on_change
        self._dragging = False

        self.set_size_request(240, 28)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)

    def set_value(self, val):
        min_limit = 10 if self.icon_name == "sun" else 0
        val = max(min_limit, min(100, int(val)))
        if self.value != val:
            self.value = val
            self.queue_draw()

    def set_dark(self, is_dark):
        self.is_dark = is_dark
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        if w <= 10:
            w = 240
        if h <= 10:
            h = 28
        r = h / 2.0

        cr.save()

        # 1. Clip to track capsule
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, math.pi/2)
        cr.arc(r, r, r, math.pi/2, 3*math.pi/2)
        cr.close_path()

        # Track background
        if self.is_dark:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
        else:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.08)
        cr.fill_preserve()
        cr.clip()

        # 2. Draw active progress fill
        fill_w = (self.value / 100.0) * w
        if fill_w > 0:
            cr.save()
            cr.rectangle(0, 0, fill_w, h)
            if self.is_dark:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            else:
                ar, ag, ab = 0.0, 0.478, 1.0
                try:
                    from src.config import config
                    hex_col = config.get("accent_color", "#007aff").lstrip("#")
                    if len(hex_col) == 6:
                        ar, ag, ab = tuple(int(hex_col[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                except Exception:
                    pass
                cr.set_source_rgba(ar, ag, ab, 1.0)
            cr.fill()
            cr.restore()

        # 3. Draw Icon (Sun / Speaker) on track
        icon_x = 10.0
        icon_y = (h - 16.0) / 2.0

        # Draw icon on filled part
        cr.save()
        cr.rectangle(0, 0, fill_w, h)
        cr.clip()
        pb_filled = get_pixbuf(self.icon_name, 16, "#1d1d1f" if self.is_dark else "#ffffff")
        if pb_filled:
            Gdk.cairo_set_source_pixbuf(cr, pb_filled, icon_x, icon_y)
            cr.paint()
        cr.restore()

        # Draw light/muted icon on unfilled part
        cr.save()
        cr.rectangle(fill_w, 0, w - fill_w, h)
        cr.clip()
        pb_muted = get_pixbuf(self.icon_name, 16, "rgba(255,255,255,0.70)" if self.is_dark else "#8e8e93")
        if pb_muted:
            Gdk.cairo_set_source_pixbuf(cr, pb_muted, icon_x, icon_y)
            cr.paint()
        cr.restore()

        # 4. Subtle inner border for authentic depth
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, math.pi/2)
        cr.arc(r, r, r, math.pi/2, 3*math.pi/2)
        cr.close_path()
        if self.is_dark:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
        else:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.05)
        cr.set_line_width(1.0)
        cr.stroke()

        cr.restore()
        return False

    def _on_button_press(self, widget, event):
        if event.button == 1:
            self._dragging = True
            self._update_from_x(event.x)
            return True
        return False

    def _on_button_release(self, widget, event):
        if event.button == 1:
            self._dragging = False
            return True
        return False

    def _on_motion(self, widget, event):
        if self._dragging:
            self._update_from_x(event.x)
            return True
        return False

    def _update_from_x(self, x):
        w = self.get_allocated_width()
        if w > 0:
            min_limit = 10 if self.icon_name == "sun" else 0
            pct = max(min_limit, min(100, int((x / float(w)) * 100)))
            self.value = pct
            self.queue_draw()
            if self.on_change:
                self.on_change(pct)


class ControlCenterBackdrop(Gtk.Window):
    """
    Invisible full-screen click-catcher overlay.
    Any click outside the Control Center window immediately dismisses it.
    Uses cairo.OPERATOR_CLEAR for 100% transparency with zero performance overhead.
    """
    def __init__(self, on_dismiss):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_dismiss = on_dismiss
        self.set_title("ControlCenterBackdrop")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.connect("draw", self._on_draw)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.TOUCH_MASK)
        self.connect("button-press-event", self._on_press)
        self.connect("touch-event", self._on_press)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window { background-color: transparent; background: transparent; border: none; box-shadow: none; }")
        self.get_style_context().add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def update_geometry(self):
        display = Gdk.Display.get_default()
        if display and hasattr(display, "get_n_monitors") and display.get_n_monitors() > 0:
            n = display.get_n_monitors()
            min_x = min(display.get_monitor(i).get_geometry().x for i in range(n))
            min_y = min(display.get_monitor(i).get_geometry().y for i in range(n))
            max_x = max(display.get_monitor(i).get_geometry().x + display.get_monitor(i).get_geometry().width for i in range(n))
            max_y = max(display.get_monitor(i).get_geometry().y + display.get_monitor(i).get_geometry().height for i in range(n))
            sw = max_x - min_x
            sh = max_y - min_y
        else:
            min_x, min_y, sw, sh = 0, 0, 1920, 1080
        self.set_default_size(sw, sh)
        self.move(min_x, min_y)

    def _on_draw(self, widget, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        return False

    def _on_press(self, widget, event):
        if self.on_dismiss:
            self.on_dismiss()
        return True


class MacOSControlCenterWindow(Gtk.Window):
    """Floating authentic macOS Control Center panel with Wi-Fi Network Picker."""

    @classmethod
    def get_instance(cls, parent_app=None):
        global _control_center_instance
        if _control_center_instance is None:
            _control_center_instance = cls(parent_app)
        elif parent_app is not None:
            _control_center_instance.parent_app = parent_app
        return _control_center_instance

    def __init__(self, parent_app=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.parent_app = parent_app
        self.is_dark = is_dark_mode()

        # Window configuration
        self.set_title("Trung tâm Điều khiển")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        # Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Fullscreen transparent backdrop for instant click-outside dismissal
        self._backdrop = ControlCenterBackdrop(self.hide_control_center)

        # Hardware controllers
        self._init_controllers()

        # Auto-close & Dismiss properties
        self._auto_close_timer_id = None
        self._inactivity_countdown = 5
        self._mouse_inside = False

        # Open animation state
        self._open_anim_timer_id = None
        self._accent_css_provider = None

        self.set_can_focus(True)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.FOCUS_CHANGE_MASK
        )

        # Connect window events
        self.connect("draw", self._on_window_draw)
        self.connect("key-press-event", self._on_key_press)
        self.connect("button-press-event", self._on_button_press_event)
        self.connect("enter-notify-event", self._on_enter_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        self.connect("motion-notify-event", self._on_pointer_motion)

        # CSS Styling
        self._load_css()
        self._update_accent_styles()

        # Build Stack & UI Structure
        self._build_ui()
        self._update_theme_icons()
        self._language_listener_id = add_language_listener(self._on_language_changed)

        self._is_syncing_hw = False

        # Periodic refresh timer (every 2.5 seconds when visible)
        GLib.timeout_add(2500, self._periodic_refresh)

        # Pre-warm hardware state asynchronously
        self._sync_all_hardware_state_async()

    def _on_language_changed(self, _language=None):
        """Refresh visible Control Center text without rebuilding hardware controls."""
        self.set_title(_t("cc_title", "Control Center"))
        refs = getattr(self, "_translation_labels", {})
        for widget, key in refs.items():
            text = _t(key)
            if hasattr(widget, "set_text"):
                widget.set_text(text)
            elif hasattr(widget, "set_label"):
                widget.set_label(text)
        for widget, key in getattr(self, "_translation_tooltips", {}).items():
            widget.set_tooltip_text(_t(key))
        self._refresh_translated_state_labels()
        if hasattr(self, "stack") and self.stack.get_visible_child_name() == "wifi":
            self._refresh_wifi_networks_async()

    def _refresh_translated_state_labels(self):
        if hasattr(self, "wifi_is_on"):
            self.wifi_sub_lbl.set_text(getattr(self, "wifi_ssid", None) if self.wifi_is_on and getattr(self, "wifi_ssid", None) else _t("cc_on") if self.wifi_is_on else _t("cc_off"))
        if hasattr(self, "bt_is_on"):
            self.bt_sub_lbl.set_text(_t("cc_on") if self.bt_is_on else _t("cc_off"))
        if hasattr(self, "dnd_is_on"):
            self.dnd_sub_lbl.set_text(_t("cc_on") if self.dnd_is_on else _t("cc_disabled"))
        if hasattr(self, "nl_is_on"):
            self.nl_sub_lbl.set_text(_t("cc_on") if self.nl_is_on else _t("cc_disabled"))
        if hasattr(self, "last_battery_pct"):
            label = _t("cc_battery", pct=self.last_battery_pct)
            if getattr(self, "battery_charging", False):
                label += " ⚡"
            self.batt_lbl.set_text(label)

    def _init_controllers(self):
        # Brightness
        if self.parent_app and hasattr(self.parent_app, "brightness_ctrl") and self.parent_app.brightness_ctrl:
            self.brightness_ctrl = self.parent_app.brightness_ctrl
        else:
            try:
                from src.modules.brightness import BrightnessController
                self.brightness_ctrl = BrightnessController.get_instance()
            except Exception:
                self.brightness_ctrl = None

        if self.brightness_ctrl:
            self.brightness_ctrl.add_listener(self._on_external_brightness_change)

        # Media
        if self.parent_app and hasattr(self.parent_app, "media_mgr"):
            self.media_mgr = self.parent_app.media_mgr
        else:
            try:
                from src.modules.media import MediaManager
                self.media_mgr = MediaManager()
            except Exception:
                self.media_mgr = None

        # Battery
        if self.parent_app and hasattr(self.parent_app, "battery_mgr"):
            self.battery_mgr = self.parent_app.battery_mgr
        else:
            try:
                from src.modules.battery import BatteryManager
                self.battery_mgr = BatteryManager()
            except Exception:
                self.battery_mgr = None

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        .cc-root-card {
            border-radius: 18px;
            padding: 12px;
        }
        .cc-box-card {
            border-radius: 14px;
            padding: 9px 12px;
            transition: background-color 120ms ease;
        }
        .mac-dark .cc-box-card {
            background-color: rgba(255, 255, 255, 0.08);
            border: 0.5px solid rgba(255, 255, 255, 0.08);
        }
        .mac-light .cc-box-card {
            background-color: rgba(255, 255, 255, 0.72);
            border: 0.5px solid rgba(0, 0, 0, 0.06);
        }
        .mac-dark .cc-box-card:hover {
            background-color: rgba(255, 255, 255, 0.12);
        }
        .mac-light .cc-box-card:hover {
            background-color: rgba(255, 255, 255, 0.90);
        }
        .cc-title {
            font-size: 13px;
            font-weight: 600;
        }
        .mac-dark .cc-title {
            color: #ffffff;
        }
        .mac-light .cc-title {
            color: #1d1d1f;
        }
        .cc-sub {
            font-size: 11px;
            font-weight: 400;
        }
        .mac-dark .cc-sub {
            color: rgba(255, 255, 255, 0.60);
        }
        .mac-light .cc-sub {
            color: rgba(0, 0, 0, 0.55);
        }
        .cc-pct-label {
            font-size: 11.5px;
            font-weight: 600;
        }
        .mac-dark .cc-pct-label {
            color: rgba(255, 255, 255, 0.70);
        }
        .mac-light .cc-pct-label {
            color: rgba(0, 0, 0, 0.55);
        }
        .cc-chevron {
            font-size: 15px;
            font-weight: 500;
        }
        .mac-dark .cc-chevron {
            color: rgba(255, 255, 255, 0.35);
        }
        .mac-light .cc-chevron {
            color: rgba(0, 0, 0, 0.30);
        }
        .cc-slider-card {
            border-radius: 14px;
            padding: 10px 12px;
        }
        .mac-dark .cc-slider-card {
            background-color: rgba(255, 255, 255, 0.08);
            border: 0.5px solid rgba(255, 255, 255, 0.08);
        }
        .mac-light .cc-slider-card {
            background-color: rgba(255, 255, 255, 0.72);
            border: 0.5px solid rgba(0, 0, 0, 0.06);
        }
        .cc-circle-btn {
            border-radius: 16px;
            min-width: 32px;
            min-height: 32px;
            transition: all 120ms ease;
        }
        .cc-circle-btn.active-blue {
            background-color: #007aff;
        }
        .cc-circle-btn.active-indigo {
            background-color: #5856d6;
        }
        .cc-circle-btn.active-orange {
            background-color: #ff9500;
        }
        .cc-circle-btn.inactive {
            background-color: rgba(120, 120, 128, 0.20);
        }
        .cc-media-art {
            border-radius: 8px;
        }
        .cc-media-btn {
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 4px;
            border-radius: 6px;
        }
        .cc-media-btn:hover {
            background-color: rgba(255, 255, 255, 0.15);
        }
        .mac-light .cc-media-btn:hover {
            background-color: rgba(0, 0, 0, 0.08);
        }

        /* Wi-Fi Submenu Specific CSS */
        .cc-back-arrow {
            font-size: 20px;
            font-weight: 600;
            color: #007aff;
            margin-right: 2px;
        }
        .cc-header-btn {
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 2px 6px;
            border-radius: 6px;
        }
        .cc-header-btn:hover {
            background-color: rgba(255, 255, 255, 0.15);
        }
        .mac-light .cc-header-btn:hover {
            background-color: rgba(0, 0, 0, 0.07);
        }
        .cc-sep {
            min-height: 1px;
            background-color: rgba(120, 120, 128, 0.18);
        }
        .cc-section-title {
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 4px 4px 2px 4px;
        }
        .mac-dark .cc-section-title {
            color: rgba(255, 255, 255, 0.45);
        }
        .mac-light .cc-section-title {
            color: rgba(0, 0, 0, 0.45);
        }
        .cc-net-row {
            border-radius: 10px;
            padding: 7px 10px;
            transition: background-color 100ms ease;
        }
        .mac-dark .cc-net-row {
            background-color: rgba(255, 255, 255, 0.06);
        }
        .mac-light .cc-net-row {
            background-color: rgba(255, 255, 255, 0.70);
            border: 0.5px solid rgba(0, 0, 0, 0.05);
        }
        .mac-dark .cc-net-row:hover {
            background-color: rgba(255, 255, 255, 0.12);
        }
        .mac-light .cc-net-row:hover {
            background-color: rgba(255, 255, 255, 0.95);
        }
        .cc-net-entry {
            border-radius: 8px;
            padding: 5px 8px;
            font-size: 12px;
            border: 1px solid rgba(120, 120, 128, 0.3);
        }
        .mac-dark .cc-net-entry {
            background-color: rgba(0, 0, 0, 0.3);
            color: #ffffff;
        }
        .mac-light .cc-net-entry {
            background-color: #ffffff;
            color: #1d1d1f;
        }
        .cc-net-connect-btn {
            border-radius: 8px;
            padding: 5px 12px;
            background-color: #007aff;
            color: #ffffff;
            font-size: 12px;
            font-weight: 600;
            border: none;
        }
        .cc-net-connect-btn:hover {
            background-color: #0062cc;
        }
        .cc-net-disconnect-btn {
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 11px;
            background-color: rgba(255, 59, 48, 0.15);
            color: #ff3b30;
            border: none;
            font-weight: 500;
        }
        .cc-net-disconnect-btn:hover {
            background-color: rgba(255, 59, 48, 0.25);
        }
        .cc-wifi-settings-btn {
            background: transparent;
            border: none;
            box-shadow: none;
            font-size: 12.5px;
            font-weight: 500;
            padding: 6px 0;
            border-radius: 8px;
        }
        .mac-dark .cc-wifi-settings-btn {
            color: #0a84ff;
        }
        .mac-light .cc-wifi-settings-btn {
            color: #007aff;
        }
        .cc-wifi-settings-btn:hover {
            background-color: rgba(0, 122, 255, 0.08);
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _update_accent_styles(self):
        """Dynamically applies current accent color to Control Center controls."""
        accent_hex = "#007aff"
        try:
            from src.config import config
            accent_hex = config.get("accent_color", "#007aff")
        except Exception:
            pass

        if self._accent_css_provider is None:
            self._accent_css_provider = Gtk.CssProvider()
            screen = Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, self._accent_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
                )

        css = f"""
        .cc-circle-btn.active-blue {{
            background-color: {accent_hex};
        }}
        .cc-back-arrow {{
            color: {accent_hex};
        }}
        .mac-light .cc-wifi-settings-btn {{
            color: {accent_hex};
        }}
        switch:checked {{
            background-color: {accent_hex};
        }}
        .cc-link-btn {{
            color: {accent_hex};
        }}
        """.encode("utf-8")

        try:
            self._accent_css_provider.load_from_data(css)
        except Exception as e:
            print(f"[ControlCenter] Error loading accent CSS: {e}")


    def _build_ui(self):
        self._translation_labels = {}
        self._translation_tooltips = {}
        # Master Stack Container
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(180)
        self.add(self.stack)

        # ─── PAGE 1: Main Control Center View ───
        self.root_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        self.root_card.set_size_request(326, -1)
        self.root_card.get_style_context().add_class("cc-root-card")
        self.root_card.get_style_context().add_class("mac-dark" if self.is_dark else "mac-light")
        self.stack.add_named(self.root_card, "main")

        # Top 2-Column Grid
        top_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        self.root_card.pack_start(top_grid, False, False, 0)

        conn_card = self._create_connectivity_card()
        top_grid.pack_start(conn_card, True, True, 0)

        right_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        top_grid.pack_start(right_vbox, True, True, 0)

        dnd_card = self._create_dnd_card()
        right_vbox.pack_start(dnd_card, True, True, 0)

        night_card = self._create_night_light_card()
        right_vbox.pack_start(night_card, True, True, 0)

        # Display Brightness Slider Card
        disp_card = self._create_display_card()
        self.root_card.pack_start(disp_card, False, False, 0)

        # Sound Volume Slider Card
        sound_card = self._create_sound_card()
        self.root_card.pack_start(sound_card, False, False, 0)

        # Now Playing Media Card
        media_card = self._create_now_playing_card()
        self.root_card.pack_start(media_card, False, False, 0)

        # Bottom Status / Actions Bar
        bottom_bar = self._create_bottom_bar()
        self.root_card.pack_start(bottom_bar, False, False, 0)

        # ─── PAGE 2: Wi-Fi Network Picker Submenu ───
        self.wifi_view = self._build_wifi_page()
        self.stack.add_named(self.wifi_view, "wifi")

    # -------------------------------------------------------------
    # UI Component Builders - Main View
    # -------------------------------------------------------------
    def _create_connectivity_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("cc-box-card")
        card.set_size_request(154, -1)

        # --- Wi-Fi Row ---
        wifi_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)

        # Icon circle: clicks toggle power
        wifi_circle_eb = Gtk.EventBox()
        wifi_circle_eb.set_visible_window(False)
        self.wifi_circle = Gtk.Box()
        self.wifi_circle.set_size_request(32, 32)
        self.wifi_circle.set_valign(Gtk.Align.CENTER)
        self.wifi_circle.get_style_context().add_class("cc-circle-btn")
        self.wifi_icon_img = Gtk.Image()
        self.wifi_circle.pack_start(self.wifi_icon_img, True, True, 0)
        wifi_circle_eb.add(self.wifi_circle)
        wifi_circle_eb.connect("button-press-event", lambda *_: self._on_toggle_wifi())
        wifi_row.pack_start(wifi_circle_eb, False, False, 0)

        # Text + Chevron: clicks open Wi-Fi network selection page!
        wifi_label_eb = Gtk.EventBox()
        wifi_label_eb.set_visible_window(False)
        wifi_label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        wifi_label_eb.add(wifi_label_box)

        wifi_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        wifi_text.set_valign(Gtk.Align.CENTER)
        t1 = Gtk.Label(label=_t("cc_wifi"))
        self._translation_labels[t1] = "cc_wifi"
        t1.get_style_context().add_class("cc-title")
        t1.set_xalign(0.0)
        self.wifi_sub_lbl = Gtk.Label(label=_t("cc_on"))
        self.wifi_sub_lbl.get_style_context().add_class("cc-sub")
        self.wifi_sub_lbl.set_xalign(0.0)
        self.wifi_sub_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.wifi_sub_lbl.set_max_width_chars(10)
        wifi_text.pack_start(t1, False, False, 0)
        wifi_text.pack_start(self.wifi_sub_lbl, False, False, 0)
        wifi_label_box.pack_start(wifi_text, True, True, 0)

        # Disclosure chevron
        chev1 = Gtk.Label(label="›")
        chev1.get_style_context().add_class("cc-chevron")
        chev1.set_valign(Gtk.Align.CENTER)
        wifi_label_box.pack_end(chev1, False, False, 0)

        wifi_label_eb.connect("button-press-event", lambda *_: self.show_wifi_page())
        wifi_row.pack_start(wifi_label_eb, True, True, 0)
        card.pack_start(wifi_row, False, False, 0)

        # --- Bluetooth Row ---
        bt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)

        bt_circle_eb = Gtk.EventBox()
        bt_circle_eb.set_visible_window(False)
        self.bt_circle = Gtk.Box()
        self.bt_circle.set_size_request(32, 32)
        self.bt_circle.set_valign(Gtk.Align.CENTER)
        self.bt_circle.get_style_context().add_class("cc-circle-btn")
        self.bt_icon_img = Gtk.Image()
        self.bt_circle.pack_start(self.bt_icon_img, True, True, 0)
        bt_circle_eb.add(self.bt_circle)
        bt_circle_eb.connect("button-press-event", lambda *_: self._on_toggle_bluetooth())
        bt_row.pack_start(bt_circle_eb, False, False, 0)

        bt_label_eb = Gtk.EventBox()
        bt_label_eb.set_visible_window(False)
        bt_label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bt_label_eb.add(bt_label_box)

        bt_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        bt_text.set_valign(Gtk.Align.CENTER)
        t2 = Gtk.Label(label=_t("cc_bluetooth"))
        self._translation_labels[t2] = "cc_bluetooth"
        t2.get_style_context().add_class("cc-title")
        t2.set_xalign(0.0)
        self.bt_sub_lbl = Gtk.Label(label=_t("cc_on"))
        self.bt_sub_lbl.get_style_context().add_class("cc-sub")
        self.bt_sub_lbl.set_xalign(0.0)
        self.bt_sub_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.bt_sub_lbl.set_max_width_chars(10)
        bt_text.pack_start(t2, False, False, 0)
        bt_text.pack_start(self.bt_sub_lbl, False, False, 0)
        bt_label_box.pack_start(bt_text, True, True, 0)

        chev2 = Gtk.Label(label="›")
        chev2.get_style_context().add_class("cc-chevron")
        chev2.set_valign(Gtk.Align.CENTER)
        bt_label_box.pack_end(chev2, False, False, 0)

        bt_label_eb.connect("button-press-event", lambda *_: self._on_open_bluetooth_settings())
        bt_row.pack_start(bt_label_eb, True, True, 0)
        card.pack_start(bt_row, False, False, 0)

        # --- AirDrop Row ---
        ad_eb = Gtk.EventBox()
        ad_eb.set_visible_window(False)
        ad_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        ad_eb.add(ad_row)
        ad_eb.connect("button-press-event", lambda *_: self._on_toggle_airdrop())

        self.ad_circle = Gtk.Box()
        self.ad_circle.set_size_request(32, 32)
        self.ad_circle.set_valign(Gtk.Align.CENTER)
        self.ad_circle.get_style_context().add_class("cc-circle-btn")
        self.ad_circle.get_style_context().add_class("active-blue")

        pb_ad = get_pixbuf("airdrop", 18, "#ffffff")
        if pb_ad:
            ad_img = Gtk.Image.new_from_pixbuf(pb_ad)
        else:
            ad_img = Gtk.Image.new_from_icon_name("network-wireless", Gtk.IconSize.MENU)
        self.ad_circle.pack_start(ad_img, True, True, 0)
        ad_row.pack_start(self.ad_circle, False, False, 0)

        ad_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        ad_text.set_valign(Gtk.Align.CENTER)
        t3 = Gtk.Label(label=_t("cc_airdrop"))
        self._translation_labels[t3] = "cc_airdrop"
        t3.get_style_context().add_class("cc-title")
        t3.set_xalign(0.0)
        self.ad_sub_lbl = Gtk.Label(label=_t("cc_everyone"))
        self._translation_labels[self.ad_sub_lbl] = "cc_everyone"
        self.ad_sub_lbl.get_style_context().add_class("cc-sub")
        self.ad_sub_lbl.set_xalign(0.0)
        ad_text.pack_start(t3, False, False, 0)
        ad_text.pack_start(self.ad_sub_lbl, False, False, 0)
        ad_row.pack_start(ad_text, True, True, 0)

        chev3 = Gtk.Label(label="›")
        chev3.get_style_context().add_class("cc-chevron")
        chev3.set_valign(Gtk.Align.CENTER)
        ad_row.pack_end(chev3, False, False, 0)

        card.pack_start(ad_eb, False, False, 0)
        return card

    def _create_dnd_card(self):
        eb = Gtk.EventBox()
        eb.set_visible_window(False)
        eb.connect("button-press-event", lambda *_: self._on_toggle_dnd())

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.get_style_context().add_class("cc-box-card")
        box.set_size_request(154, 52)
        eb.add(box)

        self.dnd_circle = Gtk.Box()
        self.dnd_circle.set_size_request(32, 32)
        self.dnd_circle.set_valign(Gtk.Align.CENTER)
        self.dnd_circle.get_style_context().add_class("cc-circle-btn")

        self.dnd_icon_img = Gtk.Image()
        self.dnd_circle.pack_start(self.dnd_icon_img, True, True, 0)
        box.pack_start(self.dnd_circle, False, False, 0)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_box.set_valign(Gtk.Align.CENTER)
        t = Gtk.Label(label=_t("cc_focus"))
        self._translation_labels[t] = "cc_focus"
        t.get_style_context().add_class("cc-title")
        t.set_xalign(0.0)
        self.dnd_sub_lbl = Gtk.Label(label=_t("cc_disabled"))
        self.dnd_sub_lbl.get_style_context().add_class("cc-sub")
        self.dnd_sub_lbl.set_xalign(0.0)
        self.dnd_sub_lbl.set_max_width_chars(11)
        text_box.pack_start(t, False, False, 0)
        text_box.pack_start(self.dnd_sub_lbl, False, False, 0)
        box.pack_start(text_box, True, True, 0)

        return eb

    def _create_night_light_card(self):
        eb = Gtk.EventBox()
        eb.set_visible_window(False)
        eb.connect("button-press-event", lambda *_: self._on_toggle_night_light())

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.get_style_context().add_class("cc-box-card")
        box.set_size_request(154, 52)
        eb.add(box)

        self.nl_circle = Gtk.Box()
        self.nl_circle.set_size_request(32, 32)
        self.nl_circle.set_valign(Gtk.Align.CENTER)
        self.nl_circle.get_style_context().add_class("cc-circle-btn")

        self.nl_icon_img = Gtk.Image()
        self.nl_circle.pack_start(self.nl_icon_img, True, True, 0)
        box.pack_start(self.nl_circle, False, False, 0)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_box.set_valign(Gtk.Align.CENTER)
        t = Gtk.Label(label=_t("cc_night_light"))
        self._translation_labels[t] = "cc_night_light"
        t.get_style_context().add_class("cc-title")
        t.set_xalign(0.0)
        self.nl_sub_lbl = Gtk.Label(label=_t("cc_disabled"))
        self.nl_sub_lbl.get_style_context().add_class("cc-sub")
        self.nl_sub_lbl.set_xalign(0.0)
        self.nl_sub_lbl.set_max_width_chars(11)
        text_box.pack_start(t, False, False, 0)
        text_box.pack_start(self.nl_sub_lbl, False, False, 0)
        box.pack_start(text_box, True, True, 0)

        return eb

    def _create_display_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("cc-slider-card")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        t = Gtk.Label(label=_t("cc_display"))
        self._translation_labels[t] = "cc_display"
        t.get_style_context().add_class("cc-title")
        t.set_xalign(0.0)
        self.bright_pct_lbl = Gtk.Label(label="100%")
        self.bright_pct_lbl.get_style_context().add_class("cc-pct-label")
        header.pack_start(t, True, True, 0)
        header.pack_end(self.bright_pct_lbl, False, False, 0)
        card.pack_start(header, False, False, 0)

        # Thick fluid capsule slider with embedded Sun icon
        self.bright_slider = MacControlSlider(
            icon_name="sun",
            value=100,
            is_dark=self.is_dark,
            on_change=self._on_bright_slider_changed
        )
        card.pack_start(self.bright_slider, False, False, 0)

        return card

    def _create_sound_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("cc-slider-card")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        t = Gtk.Label(label=_t("cc_sound"))
        self._translation_labels[t] = "cc_sound"
        t.get_style_context().add_class("cc-title")
        t.set_xalign(0.0)
        self.sound_pct_lbl = Gtk.Label(label="70%")
        self.sound_pct_lbl.get_style_context().add_class("cc-pct-label")
        header.pack_start(t, True, True, 0)
        header.pack_end(self.sound_pct_lbl, False, False, 0)
        card.pack_start(header, False, False, 0)

        # Thick fluid capsule slider with embedded Speaker icon
        self.sound_slider = MacControlSlider(
            icon_name="volume_high",
            value=70,
            is_dark=self.is_dark,
            on_change=self._on_sound_slider_changed
        )
        card.pack_start(self.sound_slider, False, False, 0)

        return card

    def _create_now_playing_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        card.get_style_context().add_class("cc-box-card")
        card.set_size_request(-1, 56)

        # Artwork frame / tile (44x44px, border-radius: 8px)
        self.media_art_frame = Gtk.Box()
        self.media_art_frame.set_size_request(44, 44)
        self.media_art_frame.set_valign(Gtk.Align.CENTER)
        self.media_art_frame.get_style_context().add_class("cc-media-art")

        self.media_art_img = Gtk.Image()
        self.media_art_frame.pack_start(self.media_art_img, True, True, 0)
        card.pack_start(self.media_art_frame, False, False, 0)

        # Title & Artist
        text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_vbox.set_valign(Gtk.Align.CENTER)
        self.media_title_lbl = Gtk.Label(label=_t("cc_now_playing_none"))
        self._translation_labels[self.media_title_lbl] = "cc_now_playing_none"
        self.media_title_lbl.get_style_context().add_class("cc-title")
        self.media_title_lbl.set_xalign(0.0)
        self.media_title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.media_title_lbl.set_max_width_chars(14)

        self.media_artist_lbl = Gtk.Label(label="Apple Music")
        self.media_artist_lbl.get_style_context().add_class("cc-sub")
        self.media_artist_lbl.set_xalign(0.0)
        self.media_artist_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.media_artist_lbl.set_max_width_chars(14)

        text_vbox.pack_start(self.media_title_lbl, False, False, 0)
        text_vbox.pack_start(self.media_artist_lbl, False, False, 0)
        card.pack_start(text_vbox, True, True, 0)

        # Media Control Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        btn_box.set_valign(Gtk.Align.CENTER)

        # Prev
        prev_btn = Gtk.Button()
        prev_btn.get_style_context().add_class("cc-media-btn")
        self.prev_img = Gtk.Image()
        prev_btn.set_image(self.prev_img)
        prev_btn.connect("clicked", lambda *_: self._on_media_prev())
        btn_box.pack_start(prev_btn, False, False, 0)

        # Play / Pause
        self.play_btn = Gtk.Button()
        self.play_btn.get_style_context().add_class("cc-media-btn")
        self.play_img = Gtk.Image()
        self.play_btn.set_image(self.play_img)
        self.play_btn.connect("clicked", lambda *_: self._on_media_play_pause())
        btn_box.pack_start(self.play_btn, False, False, 0)

        # Next
        next_btn = Gtk.Button()
        next_btn.get_style_context().add_class("cc-media-btn")
        self.next_img = Gtk.Image()
        next_btn.set_image(self.next_img)
        next_btn.connect("clicked", lambda *_: self._on_media_next())
        btn_box.pack_start(next_btn, False, False, 0)

        card.pack_end(btn_box, False, False, 0)
        return card

    def _create_bottom_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.set_margin_top(4)

        # Battery pill
        batt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        batt_box.set_valign(Gtk.Align.CENTER)
        self.batt_icon_img = Gtk.Image()
        batt_box.pack_start(self.batt_icon_img, False, False, 0)

        self.batt_lbl = Gtk.Label(label=_t("cc_battery", pct=100))
        self.batt_lbl.get_style_context().add_class("cc-sub")
        self.batt_lbl.set_valign(Gtk.Align.CENTER)
        batt_box.pack_start(self.batt_lbl, False, False, 0)
        bar.pack_start(batt_box, True, True, 0)

        # Quick Actions
        # 1. Dark Mode quick button
        theme_btn = Gtk.Button()
        theme_btn.get_style_context().add_class("cc-media-btn")
        self.theme_img = Gtk.Image()
        theme_btn.set_image(self.theme_img)
        self._translation_tooltips[theme_btn] = "cc_theme_tooltip"
        theme_btn.set_tooltip_text(_t("cc_theme_tooltip"))
        theme_btn.connect("clicked", lambda *_: self._on_toggle_theme())
        bar.pack_end(theme_btn, False, False, 0)

        # 2. Settings button
        settings_btn = Gtk.Button()
        settings_btn.get_style_context().add_class("cc-media-btn")
        self.settings_img = Gtk.Image()
        settings_btn.set_image(self.settings_img)
        self._translation_tooltips[settings_btn] = "cc_settings_tooltip"
        settings_btn.set_tooltip_text(_t("cc_settings_tooltip"))
        settings_btn.connect("clicked", lambda *_: self._on_open_settings())
        bar.pack_end(settings_btn, False, False, 0)

        return bar

    # -------------------------------------------------------------
    # UI Component Builders - Wi-Fi Submenu View
    # -------------------------------------------------------------
    def _build_wifi_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_size_request(326, -1)
        box.get_style_context().add_class("cc-root-card")
        box.get_style_context().add_class("mac-dark" if self.is_dark else "mac-light")

        # 1. Header with Back button and Switch toggle
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        back_btn = Gtk.Button()
        back_btn.get_style_context().add_class("cc-header-btn")
        back_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        back_arrow = Gtk.Label(label="‹")
        back_arrow.get_style_context().add_class("cc-back-arrow")
        back_lbl = Gtk.Label(label=_t("cc_wifi"))
        self._translation_labels[back_lbl] = "cc_wifi"
        back_lbl.get_style_context().add_class("cc-title")

        back_box.pack_start(back_arrow, False, False, 0)
        back_box.pack_start(back_lbl, False, False, 0)
        back_btn.add(back_box)
        back_btn.connect("clicked", lambda *_: self.stack.set_visible_child_name("main"))
        header.pack_start(back_btn, False, False, 0)

        # Wi-Fi Power Switch
        self.wifi_power_switch = Gtk.Switch()
        self.wifi_power_switch.set_valign(Gtk.Align.CENTER)
        self.wifi_power_switch.connect("state-set", self._on_wifi_switch_state_set)
        header.pack_end(self.wifi_power_switch, False, False, 0)
        box.pack_start(header, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("cc-sep")
        box.pack_start(sep, False, False, 0)

        # 2. Scrollable Wi-Fi Network List
        self.wifi_scrolled = Gtk.ScrolledWindow()
        self.wifi_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.wifi_scrolled.set_min_content_height(270)
        self.wifi_scrolled.set_max_content_height(330)
        self.wifi_scrolled.set_propagate_natural_height(True)

        self.wifi_list_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.wifi_scrolled.add(self.wifi_list_vbox)
        box.pack_start(self.wifi_scrolled, True, True, 0)

        # 3. Bottom Action: "Cài đặt Wi-Fi..."
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep2.get_style_context().add_class("cc-sep")
        box.pack_start(sep2, False, False, 0)

        bottom_btn = Gtk.Button(label=_t("cc_wifi_settings"))
        self._translation_labels[bottom_btn] = "cc_wifi_settings"
        bottom_btn.get_style_context().add_class("cc-wifi-settings-btn")
        bottom_btn.connect("clicked", lambda *_: self._on_open_wifi_settings())
        box.pack_start(bottom_btn, False, False, 0)

        return box

    def show_wifi_page(self):
        """Switches stack to Wi-Fi selection page and triggers network scan."""
        self.stack.set_visible_child_name("wifi")
        self._refresh_wifi_networks_async()

    def _refresh_wifi_networks_async(self):
        # Show scanning placeholder
        for child in self.wifi_list_vbox.get_children():
            self.wifi_list_vbox.remove(child)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        loading_box.set_margin_top(20)
        loading_box.set_halign(Gtk.Align.CENTER)
        spinner = Gtk.Spinner()
        spinner.start()
        loading_lbl = Gtk.Label(label=_t("cc_wifi_scanning"))
        loading_lbl.get_style_context().add_class("cc-sub")
        loading_box.pack_start(spinner, False, False, 0)
        loading_box.pack_start(loading_lbl, False, False, 0)
        self.wifi_list_vbox.pack_start(loading_box, False, False, 0)
        self.wifi_list_vbox.show_all()

        def scan_worker():
            try:
                from src.ui.macos_settings_window import scan_available_wifi, get_wifi_status
                is_enabled, active_ssid, _ = get_wifi_status()
                networks = scan_available_wifi() if is_enabled else []
            except Exception as e:
                is_enabled, active_ssid, networks = True, None, []
            GLib.idle_add(self._render_wifi_networks, is_enabled, active_ssid, networks)

        threading.Thread(target=scan_worker, daemon=True).start()

    def _render_wifi_networks(self, is_enabled, active_ssid, networks):
        for child in self.wifi_list_vbox.get_children():
            self.wifi_list_vbox.remove(child)

        self.wifi_power_switch.handler_block_by_func(self._on_wifi_switch_state_set)
        self.wifi_power_switch.set_state(is_enabled)
        self.wifi_power_switch.handler_unblock_by_func(self._on_wifi_switch_state_set)

        if not is_enabled:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_box.set_margin_top(40)
            empty_box.set_halign(Gtk.Align.CENTER)
            lbl1 = Gtk.Label(label=_t("cc_wifi_off"))
            lbl1.get_style_context().add_class("cc-title")
            lbl2 = Gtk.Label(label=_t("cc_wifi_enable_hint"))
            lbl2.get_style_context().add_class("cc-sub")
            empty_box.pack_start(lbl1, False, False, 0)
            empty_box.pack_start(lbl2, False, False, 0)
            self.wifi_list_vbox.pack_start(empty_box, False, False, 0)
            self.wifi_list_vbox.show_all()
            return

        # ─── SECTION 1: Connected Network ───
        if active_ssid:
            sec1_lbl = Gtk.Label(label=_t("cc_wifi_connected"))
            sec1_lbl.get_style_context().add_class("cc-section-title")
            sec1_lbl.set_xalign(0.0)
            self.wifi_list_vbox.pack_start(sec1_lbl, False, False, 0)

            conn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            conn_row.get_style_context().add_class("cc-net-row")

            pb_w = get_pixbuf("wifi", 18, "#007aff")
            if pb_w:
                conn_row.pack_start(Gtk.Image.new_from_pixbuf(pb_w), False, False, 0)

            text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            t_lbl = Gtk.Label(label=active_ssid)
            t_lbl.get_style_context().add_class("cc-title")
            t_lbl.set_xalign(0.0)
            s_lbl = Gtk.Label(label=_t("cc_wifi_connected_status"))
            s_lbl.get_style_context().add_class("cc-sub")
            s_lbl.set_xalign(0.0)
            text_vbox.pack_start(t_lbl, False, False, 0)
            text_vbox.pack_start(s_lbl, False, False, 0)
            conn_row.pack_start(text_vbox, True, True, 0)

            # Checkmark + Disconnect button
            chk = Gtk.Label(label="✓")
            chk.get_style_context().add_class("cc-title")
            chk.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.0, 0.48, 1.0, 1.0))
            chk.set_valign(Gtk.Align.CENTER)
            conn_row.pack_end(chk, False, False, 0)

            dis_btn = Gtk.Button(label=_t("cc_wifi_disconnect"))
            dis_btn.get_style_context().add_class("cc-net-disconnect-btn")
            dis_btn.set_valign(Gtk.Align.CENTER)
            dis_btn.connect("clicked", lambda *_: self._on_disconnect_wifi())
            conn_row.pack_end(dis_btn, False, False, 4)

            self.wifi_list_vbox.pack_start(conn_row, False, False, 0)

        # ─── SECTION 2: Available Other Networks ───
        sec2_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sec2_lbl = Gtk.Label(label=_t("cc_wifi_available"))
        sec2_lbl.get_style_context().add_class("cc-section-title")
        sec2_lbl.set_xalign(0.0)
        sec2_box.pack_start(sec2_lbl, True, True, 0)

        ref_btn = Gtk.Button()
        ref_btn.get_style_context().add_class("cc-header-btn")
        self._translation_tooltips[ref_btn] = "cc_wifi_rescan"
        ref_btn.set_tooltip_text(_t("cc_wifi_rescan"))
        pb_ref = get_pixbuf("controls", 14, "#007aff")
        if pb_ref:
            ref_btn.set_image(Gtk.Image.new_from_pixbuf(pb_ref))
        ref_btn.connect("clicked", lambda *_: self._refresh_wifi_networks_async())
        sec2_box.pack_end(ref_btn, False, False, 0)
        self.wifi_list_vbox.pack_start(sec2_box, False, False, 4)

        other_nets = [n for n in networks if n["ssid"] != active_ssid]
        if not other_nets:
            no_nets = Gtk.Label(label=_t("cc_wifi_none"))
            no_nets.get_style_context().add_class("cc-sub")
            no_nets.set_margin_top(10)
            self.wifi_list_vbox.pack_start(no_nets, False, False, 0)
        else:
            for net in other_nets:
                row_widget = self._create_available_network_row(net)
                self.wifi_list_vbox.pack_start(row_widget, False, False, 0)

        self.wifi_list_vbox.show_all()

    def _create_available_network_row(self, net):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        eb = Gtk.EventBox()
        eb.set_visible_window(False)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.get_style_context().add_class("cc-net-row")
        eb.add(row)

        # Wi-Fi icon
        icon_color = "rgba(255, 255, 255, 0.75)" if self.is_dark else "#48484a"
        pb_sig = get_pixbuf("wifi", 16, icon_color)
        if pb_sig:
            row.pack_start(Gtk.Image.new_from_pixbuf(pb_sig), False, False, 0)
        else:
            sig = net["signal"]
            ic_name = "network-wireless-signal-excellent-symbolic" if sig >= 70 else "network-wireless-signal-good-symbolic"
            row.pack_start(Gtk.Image.new_from_icon_name(ic_name, Gtk.IconSize.MENU), False, False, 0)

        # SSID & Security
        text_v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name_lbl = Gtk.Label(label=net["ssid"])
        name_lbl.get_style_context().add_class("cc-title")
        name_lbl.set_xalign(0.0)
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)

        sec_lbl = Gtk.Label(label=_t("cc_wifi_security", security=net["security"], signal=net["signal"]))
        sec_lbl.get_style_context().add_class("cc-sub")
        sec_lbl.set_xalign(0.0)
        text_v.pack_start(name_lbl, False, False, 0)
        text_v.pack_start(sec_lbl, False, False, 0)
        row.pack_start(text_v, True, True, 0)

        # Lock icon if secured
        is_secured = "Mở" not in net["security"] and "Open" not in net["security"]
        if is_secured:
            lock_color = "rgba(255, 255, 255, 0.60)" if self.is_dark else "#8e8e93"
            pb_l = get_pixbuf("lock", 13, lock_color)
            if pb_l:
                row.pack_end(Gtk.Image.new_from_pixbuf(pb_l), False, False, 0)
            else:
                row.pack_end(Gtk.Image.new_from_icon_name("channel-secure-symbolic", Gtk.IconSize.MENU), False, False, 0)

        vbox.pack_start(eb, False, False, 0)

        # Inline Password Container (collapsible)
        pw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pw_box.set_margin_start(6)
        pw_box.set_margin_end(6)
        pw_box.set_margin_top(2)
        pw_box.set_margin_bottom(6)
        pw_box.set_no_show_all(True)

        pw_entry = Gtk.Entry()
        pw_entry.set_visibility(False)
        pw_entry.set_placeholder_text(_t("cc_wifi_password"))
        pw_entry.get_style_context().add_class("cc-net-entry")
        pw_box.pack_start(pw_entry, True, True, 0)

        conn_btn = Gtk.Button(label=_t("cc_wifi_connect"))
        conn_btn.get_style_context().add_class("cc-net-connect-btn")
        pw_box.pack_start(conn_btn, False, False, 0)

        pw_entry.show()
        conn_btn.show()
        vbox.pack_start(pw_box, False, False, 0)
        pw_box.hide()

        # Connect action
        def on_connect_clicked(_):
            pw = pw_entry.get_text().strip()
            conn_btn.set_sensitive(False)
            conn_btn.set_label(_t("cc_wifi_connecting"))
            ssid = net["ssid"]

            def do_connect():
                from src.ui.macos_settings_window import connect_wifi_network
                success, msg = connect_wifi_network(ssid, pw if is_secured else None)
                def on_done():
                    if success:
                        self._refresh_wifi_networks_async()
                    else:
                        conn_btn.set_sensitive(True)
                        conn_btn.set_label(_t("cc_wifi_retry"))
                        pw_entry.set_placeholder_text(_t("cc_wifi_wrong_password"))
                GLib.idle_add(on_done)

            threading.Thread(target=do_connect, daemon=True).start()

        conn_btn.connect("clicked", on_connect_clicked)
        pw_entry.connect("activate", on_connect_clicked)

        # Clicking row toggles password entry or connects open network
        def on_row_click(*_):
            if is_secured:
                if pw_box.get_visible():
                    pw_box.hide()
                else:
                    pw_box.show()
                    pw_entry.grab_focus()
            else:
                on_connect_clicked(None)

        eb.connect("button-press-event", on_row_click)
        eb.connect("enter-notify-event", lambda w, e: w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer")) if w.get_window() else None)
        eb.connect("leave-notify-event", lambda w, e: w.get_window().set_cursor(None) if w.get_window() else None)
        return vbox

    def _on_wifi_switch_state_set(self, switch, state):
        try:
            from src.ui.macos_settings_window import set_wifi_enabled
            threading.Thread(target=lambda: set_wifi_enabled(state), daemon=True).start()
        except Exception:
            pass
        GLib.timeout_add(800, lambda: (self._refresh_wifi_networks_async(), False)[1])
        return True

    def _on_disconnect_wifi(self):
        try:
            from src.ui.macos_settings_window import disconnect_active_wifi
            threading.Thread(target=disconnect_active_wifi, daemon=True).start()
        except Exception:
            pass
        GLib.timeout_add(800, lambda: (self._refresh_wifi_networks_async(), False)[1])

    def _on_open_wifi_settings(self):
        self.hide_control_center()
        if self.parent_app and hasattr(self.parent_app, "open_macos_settings_window"):
            self.parent_app.open_macos_settings_window("network")
        else:
            subprocess.Popen(["python3", "main.py", "settings", "network"])

    def _on_open_bluetooth_settings(self):
        self.hide_control_center()
        if self.parent_app and hasattr(self.parent_app, "open_macos_settings_window"):
            self.parent_app.open_macos_settings_window("bluetooth")
        else:
            subprocess.Popen(["python3", "main.py", "settings", "bluetooth"])

    # -------------------------------------------------------------
    # State Refreshers & Synchronizers (Fully Asynchronous)
    # -------------------------------------------------------------
    def _periodic_refresh(self):
        if self.is_visible() and self.stack.get_visible_child_name() == "main":
            self._sync_all_hardware_state_async()
        return True

    def _sync_all_hardware_state(self):
        """Asynchronous hardware state sync (non-blocking for butter-smooth UI)."""
        self._sync_all_hardware_state_async()

    def _sync_all_hardware_state_async(self):
        """Queries all hardware states on a background daemon thread to prevent freezing the GTK main loop."""
        if getattr(self, "_is_syncing_hw", False):
            return
        self._is_syncing_hw = True
        threading.Thread(target=self._hardware_sync_worker, daemon=True).start()

    def _hardware_sync_worker(self):
        state = {}
        try:
            # 1. Wi-Fi
            try:
                from src.ui.macos_settings_window import get_wifi_status
                is_wifi_on, ssid, _ = get_wifi_status()
                state["wifi"] = (is_wifi_on, ssid)
            except Exception:
                state["wifi"] = (True, "Wi-Fi")

            # 2. Bluetooth
            try:
                from src.ui.macos_settings_window import get_bluetooth_status
                has_bt, is_bt_on, _ = get_bluetooth_status()
                state["bluetooth"] = (has_bt, is_bt_on)
            except Exception:
                state["bluetooth"] = (False, False)

            # 3. Do Not Disturb (DND)
            state["dnd"] = self._is_dnd_active()

            # 4. Night Light
            is_nl = False
            if self.brightness_ctrl:
                is_nl = self.brightness_ctrl.is_night_light_enabled()
            state["night_light"] = is_nl

            # 5. Brightness
            if self.brightness_ctrl:
                state["brightness"] = self.brightness_ctrl.get_brightness()

            # 6. Sound / Volume
            try:
                from src.ui.macos_settings_window import get_system_volume
                vol, is_muted = get_system_volume()
                state["sound"] = (vol, is_muted)
            except Exception:
                pass

            # 7. Media Now Playing
            if self.media_mgr:
                try:
                    title = self.media_mgr.title or "Không phát nhạc"
                    artist = self.media_mgr.artist or "Apple Music"
                    is_playing = self.media_mgr.is_playing()
                    art_url = getattr(self.media_mgr, "art_url", None)
                    state["media"] = (title, artist, is_playing, art_url)
                except Exception:
                    pass

            # 8. Battery
            try:
                out = subprocess.check_output(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"], text=True, timeout=0.5)
                pct = 100
                charging = False
                for line in out.splitlines():
                    if "percentage:" in line:
                        pct = int(float(line.split(":")[1].replace("%", "").strip()))
                    elif "state:" in line and "charging" in line:
                        charging = True
                state["battery"] = (pct, charging)
            except Exception:
                state["battery"] = None

        except Exception as e:
            print(f"[ControlCenter] Hardware sync worker error: {e}")
        finally:
            GLib.idle_add(self._apply_hardware_state, state)

    def _apply_hardware_state(self, state):
        self._is_syncing_hw = False
        if not state:
            return False

        # 1. Wi-Fi
        if "wifi" in state:
            is_wifi_on, ssid = state["wifi"]
            self.wifi_is_on = is_wifi_on
            self.wifi_ssid = ssid
            self.wifi_sub_lbl.set_text(ssid if (is_wifi_on and ssid) else (_t("cc_on") if is_wifi_on else _t("cc_off")))
            self._update_circle_style(self.wifi_circle, is_wifi_on, "active-blue")
            pb_wifi = get_pixbuf("wifi", 18, "#ffffff" if is_wifi_on else "#8e8e93")
            if pb_wifi:
                self.wifi_icon_img.set_from_pixbuf(pb_wifi)

        # 2. Bluetooth
        if "bluetooth" in state:
            has_bt, is_bt_on = state["bluetooth"]
            self.bt_is_on = is_bt_on
            self.bt_is_on = is_bt_on
            self.bt_sub_lbl.set_text(_t("cc_on") if is_bt_on else _t("cc_off"))
            self._update_circle_style(self.bt_circle, is_bt_on, "active-blue")
            pb_bt = get_pixbuf("bluetooth", 18, "#ffffff" if is_bt_on else "#8e8e93")
            if pb_bt:
                self.bt_icon_img.set_from_pixbuf(pb_bt)

        # 3. Do Not Disturb (DND)
        if "dnd" in state:
            is_dnd = state["dnd"]
            self.dnd_is_on = is_dnd
            self.dnd_sub_lbl.set_text(_t("cc_on") if is_dnd else _t("cc_disabled"))
            self._update_circle_style(self.dnd_circle, is_dnd, "active-indigo")
            pb_dnd = get_pixbuf("moon", 18, "#ffffff" if is_dnd else "#8e8e93")
            if pb_dnd:
                self.dnd_icon_img.set_from_pixbuf(pb_dnd)

        # 4. Night Light
        if "night_light" in state:
            is_nl = state["night_light"]
            self.nl_is_on = is_nl
            self.nl_sub_lbl.set_text(_t("cc_on") if is_nl else _t("cc_disabled"))
            self._update_circle_style(self.nl_circle, is_nl, "active-orange")
            pb_nl = get_pixbuf("sun", 18, "#ffffff" if is_nl else "#8e8e93")
            if pb_nl:
                self.nl_icon_img.set_from_pixbuf(pb_nl)

        # 5. Brightness
        if "brightness" in state:
            b_val = state["brightness"]
            if not getattr(self.bright_slider, "_dragging", False):
                self.bright_slider.set_value(b_val)
                self.bright_pct_lbl.set_text(f"{int(b_val)}%")

        # 6. Sound / Volume
        if "sound" in state:
            vol, is_muted = state["sound"]
            vol_pct = int(vol * 100) if not is_muted else 0
            if not getattr(self.sound_slider, "_dragging", False):
                self.sound_slider.set_value(vol_pct)
                self.sound_pct_lbl.set_text(f"{int(vol * 100)}%" if not is_muted else _t("cc_muted"))

        # 7. Media Now Playing
        if "media" in state and state["media"]:
            title, artist, is_playing, art_url = state["media"]
            self.media_title_lbl.set_text(title)
            self.media_artist_lbl.set_text(artist)

            btn_color = "#ffffff" if self.is_dark else "#1d1d1f"
            pb_play = get_pixbuf("pause" if is_playing else "play", 15, btn_color)
            if pb_play:
                self.play_img.set_from_pixbuf(pb_play)

            pb_art = None
            if art_url and os.path.exists(art_url):
                try:
                    pb_art = GdkPixbuf.Pixbuf.new_from_file_at_scale(art_url, 44, 44, True)
                except Exception:
                    pass

            if not pb_art:
                pb_art = self._create_gradient_music_pixbuf(44, 44)

            if pb_art:
                self.media_art_img.set_from_pixbuf(pb_art)

        # 8. Battery
        if state.get("battery") is not None:
            pct, charging = state["battery"]
            self.last_battery_pct = pct
            self.battery_charging = charging
            self.batt_lbl.set_text(_t("cc_battery", pct=pct) + (" ⚡" if charging else ""))
            pb_batt = get_pixbuf("battery_charging" if charging else "battery", 16, "#34c759" if pct > 20 else "#ff3b30")
            if pb_batt:
                self.batt_icon_img.set_from_pixbuf(pb_batt)
        elif "battery" in state and state["battery"] is None:
            self.batt_lbl.set_text(_t("cc_ac_power"))
            pb_batt = get_pixbuf("battery", 16, "#34c759")
            if pb_batt:
                self.batt_icon_img.set_from_pixbuf(pb_batt)

        # 9. Dynamic Theme Icons
        self._update_theme_icons()
        return False

    def _update_theme_icons(self):
        """Updates in-memory icon pixbufs for theme without any subprocess calls."""
        btn_color = "#ffffff" if self.is_dark else "#1d1d1f"

        if hasattr(self, "bright_slider"):
            self.bright_slider.set_dark(self.is_dark)
        if hasattr(self, "sound_slider"):
            self.sound_slider.set_dark(self.is_dark)

        pb_prev = get_pixbuf("prev", 14, btn_color)
        if pb_prev and hasattr(self, "prev_img"):
            self.prev_img.set_from_pixbuf(pb_prev)

        pb_next = get_pixbuf("next", 14, btn_color)
        if pb_next and hasattr(self, "next_img"):
            self.next_img.set_from_pixbuf(pb_next)

        pb_theme = get_pixbuf("moon" if not self.is_dark else "sun", 16, btn_color)
        if pb_theme and hasattr(self, "theme_img"):
            self.theme_img.set_from_pixbuf(pb_theme)

        pb_lock = get_pixbuf("lock", 16, btn_color)
        if pb_lock and hasattr(self, "lock_img"):
            self.lock_img.set_from_pixbuf(pb_lock)

        pb_set = get_pixbuf("settings", 16, btn_color)
        if pb_set and hasattr(self, "settings_img"):
            self.settings_img.set_from_pixbuf(pb_set)

    def _create_gradient_music_pixbuf(self, w, h):
        """Creates a gorgeous Apple Music gradient icon tile."""
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surf)
        r = 8.0

        # Rounded rect
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi/2)
        cr.arc(r, h - r, r, math.pi/2, math.pi)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        # Pink-Coral Apple Music linear gradient
        pat = cairo.LinearGradient(0, 0, w, h)
        pat.add_color_stop_rgb(0.0, 0.98, 0.20, 0.45) # #fa3373
        pat.add_color_stop_rgb(1.0, 0.99, 0.42, 0.35) # #fd6c59
        cr.set_source(pat)
        cr.fill()

        # White music note inside
        pb_note = get_pixbuf("music", 22, "#ffffff")
        if pb_note:
            Gdk.cairo_set_source_pixbuf(cr, pb_note, (w - 22) / 2.0, (h - 22) / 2.0)
            cr.paint()

        pixbuf = Gdk.pixbuf_get_from_surface(surf, 0, 0, w, h)
        return pixbuf

    def _update_circle_style(self, widget, is_active, active_class):
        ctx = widget.get_style_context()
        ctx.remove_class("active-blue")
        ctx.remove_class("active-indigo")
        ctx.remove_class("active-orange")
        ctx.remove_class("inactive")
        if is_active:
            ctx.add_class(active_class)
        else:
            ctx.add_class("inactive")

    def _is_dnd_active(self):
        try:
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.notifications", "show-banners"],
                capture_output=True, text=True, timeout=0.5
            )
            return "false" in res.stdout.lower()
        except Exception:
            return False

    # -------------------------------------------------------------
    # Action Handlers
    # -------------------------------------------------------------
    def _on_toggle_wifi(self):
        new_state = not getattr(self, "wifi_is_on", True)
        try:
            from src.ui.macos_settings_window import set_wifi_enabled
            threading.Thread(target=lambda: set_wifi_enabled(new_state), daemon=True).start()
        except Exception:
            pass
        GLib.timeout_add(400, lambda: (self._sync_all_hardware_state(), False)[1])

    def _on_toggle_bluetooth(self):
        new_state = not getattr(self, "bt_is_on", True)
        try:
            from src.ui.macos_settings_window import set_bluetooth_powered
            threading.Thread(target=lambda: set_bluetooth_powered(new_state), daemon=True).start()
        except Exception:
            pass
        GLib.timeout_add(500, lambda: (self._sync_all_hardware_state(), False)[1])

    def _on_toggle_airdrop(self):
        self.hide_control_center()
        try:
            from src.ui.macos_airdrop_window import MacOSAirDropWindow
            win = MacOSAirDropWindow.get_instance()
            win.show_window()
        except Exception as e:
            print(f"[ControlCenter] Notice opening AirDrop: {e}")

    def _on_toggle_dnd(self):
        curr = self._is_dnd_active()
        target = "true" if curr else "false"
        def _set_dnd():
            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", target],
                    check=False, timeout=0.5
                )
            except Exception:
                pass
            GLib.idle_add(self._sync_all_hardware_state_async)
        threading.Thread(target=_set_dnd, daemon=True).start()

    def _on_toggle_night_light(self):
        def _set_nl():
            if self.brightness_ctrl:
                self.brightness_ctrl.toggle_night_light()
            GLib.idle_add(self._sync_all_hardware_state_async)
        threading.Thread(target=_set_nl, daemon=True).start()

    def _on_external_brightness_change(self, pct):
        GLib.idle_add(self._sync_external_brightness, pct)

    def _sync_external_brightness(self, pct):
        if hasattr(self, "bright_slider") and not getattr(self.bright_slider, "_dragging", False):
            self.bright_slider.set_value(pct)
            if hasattr(self, "bright_pct_lbl"):
                self.bright_pct_lbl.set_text(f"{int(pct)}%")
        return False

    def _on_bright_slider_changed(self, val):
        val = max(10, min(100, int(val)))
        self.bright_pct_lbl.set_text(f"{val}%")
        if self.brightness_ctrl:
            self.brightness_ctrl.set_brightness(val)

    def _on_sound_slider_changed(self, val):
        self.sound_pct_lbl.set_text(f"{val}%")
        try:
            from src.ui.macos_settings_window import set_system_volume
            set_system_volume(val / 100.0)
        except Exception:
            pass

    def _on_media_play_pause(self):
        if self.media_mgr and hasattr(self.media_mgr, "play_pause"):
            self.media_mgr.play_pause()
            GLib.timeout_add(150, lambda: (self._sync_all_hardware_state(), False)[1])

    def _on_media_prev(self):
        if self.media_mgr and hasattr(self.media_mgr, "previous"):
            self.media_mgr.previous()
            GLib.timeout_add(150, lambda: (self._sync_all_hardware_state(), False)[1])

    def _on_media_next(self):
        if self.media_mgr and hasattr(self.media_mgr, "next"):
            self.media_mgr.next()
            GLib.timeout_add(150, lambda: (self._sync_all_hardware_state(), False)[1])

    def _on_toggle_theme(self):
        from src.utils.theme import toggle_dark_mode
        self.is_dark = toggle_dark_mode()
        self._on_theme_changed()

    def _on_lock_screen(self):
        self.hide_control_center()
        try:
            subprocess.run(["gdbus", "call", "--session", "--dest", "org.gnome.ScreenSaver", "--object-path", "/org/gnome/ScreenSaver", "--method", "org.gnome.ScreenSaver.Lock"], timeout=1)
        except Exception:
            subprocess.run(["loginctl", "lock-session"], timeout=1)

    def _on_open_settings(self):
        self.hide_control_center()
        if self.parent_app and hasattr(self.parent_app, "open_macos_settings_window"):
            self.parent_app.open_macos_settings_window()
        else:
            subprocess.Popen(["python3", "main.py", "settings"])

    # -------------------------------------------------------------
    # Window Lifecycle & Drawing
    # -------------------------------------------------------------
    def _on_window_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 18.0

        cr.save()
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw rounded card with authentic macOS glassmorphism
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi/2)
        cr.arc(r, h - r, r, math.pi/2, math.pi)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        if self.is_dark:
            # Solid dark frosted glass (0.98 alpha prevents background window bleed-through)
            cr.set_source_rgba(0.12, 0.12, 0.15, 0.98)
            cr.fill_preserve()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
            cr.set_line_width(1.0)
            cr.stroke()
        else:
            # Solid light frosted platinum (0.98 alpha)
            cr.set_source_rgba(0.96, 0.96, 0.98, 0.98)
            cr.fill_preserve()
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.14)
            cr.set_line_width(1.0)
            cr.stroke()

        cr.restore()
        return False

    def _on_theme_changed(self, force_dark=None):
        if force_dark is not None:
            self.is_dark = bool(force_dark)
        else:
            self.is_dark = is_dark_mode()

        for card in (self.root_card, getattr(self, "wifi_view", None)):
            if card:
                ctx = card.get_style_context()
                if self.is_dark:
                    ctx.remove_class("mac-light")
                    ctx.add_class("mac-dark")
                else:
                    ctx.remove_class("mac-dark")
                    ctx.add_class("mac-light")

        self._update_theme_icons()
        self._update_accent_styles()
        if hasattr(self, "bright_slider") and self.bright_slider:
            self.bright_slider.set_dark(self.is_dark)
        if hasattr(self, "sound_slider") and self.sound_slider:
            self.sound_slider.set_dark(self.is_dark)
        self.queue_draw()

    def destroy(self):
        if hasattr(self, "_backdrop") and self._backdrop:
            try:
                self._backdrop.destroy()
            except Exception:
                pass
            self._backdrop = None
        super().destroy()

    def _on_button_press_event(self, widget, event):
        # Click inside -> reset auto-close timer
        self._reset_auto_close_timer()
        return False

    def _on_enter_notify(self, widget, event):
        self._mouse_inside = True
        self._reset_auto_close_timer()
        return False

    def _on_leave_notify(self, widget, event):
        alloc = self.get_allocation()
        if event.x <= 0 or event.y <= 0 or event.x >= alloc.width or event.y >= alloc.height:
            self._mouse_inside = False
            self._reset_auto_close_timer()
        return False

    def _on_pointer_motion(self, widget, event):
        self._mouse_inside = True
        self._reset_auto_close_timer()
        return False

    def _is_pointer_over_window(self):
        """Returns True if the mouse pointer is anywhere within the Control Center window bounds."""
        try:
            display = Gdk.Display.get_default()
            if not display:
                return False
            seat = display.get_default_seat()
            if not seat:
                return False
            pointer = seat.get_pointer()
            if not pointer:
                return False
            _, px, py = pointer.get_position()
            wx, wy = self.get_position()
            ww, wh = self.get_size()
            return (wx <= px <= wx + ww and wy <= py <= wy + wh)
        except Exception:
            return False

    def _start_auto_close_timer(self):
        self._cancel_auto_close_timer()
        self._inactivity_countdown = 8
        self._auto_close_timer_id = GLib.timeout_add_seconds(1, self._on_auto_close_tick)

    def _reset_auto_close_timer(self):
        self._inactivity_countdown = 8

    def _cancel_auto_close_timer(self):
        if self._auto_close_timer_id is not None:
            try:
                GLib.source_remove(self._auto_close_timer_id)
            except Exception:
                pass
            self._auto_close_timer_id = None

    def _on_auto_close_tick(self):
        if not self.is_visible():
            self._auto_close_timer_id = None
            return False
        # As long as pointer is over window or user is interacting, never close!
        if self._is_pointer_over_window() or getattr(self, "_mouse_inside", False):
            self._inactivity_countdown = 8
            return True
        self._inactivity_countdown -= 1
        if self._inactivity_countdown <= 0:
            self.hide_control_center()
            self._auto_close_timer_id = None
            return False
        return True

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if hasattr(self, "stack") and self.stack.get_visible_child_name() != "main":
                self.stack.set_visible_child_name("main")
                return True
            self.hide_control_center()
            return True
        self._reset_auto_close_timer()
        return False

    def _start_open_animation(self, target_x, target_y):
        """Authentic macOS flyout animation: smooth slide-down and fade-in from top bar."""
        if getattr(self, "_open_anim_timer_id", None) is not None:
            try:
                GLib.source_remove(self._open_anim_timer_id)
            except Exception:
                pass
            self._open_anim_timer_id = None

        start_y = target_y - 20
        self.move(target_x, start_y)
        self.set_opacity(0.1)

        if not getattr(self, "_has_shown_once", False):
            self.show_all()
            self._has_shown_once = True
        else:
            self.show()
        self.present()
        self.grab_focus()

        total_frames = 11
        self._anim_frame = 0

        def _anim_step():
            self._anim_frame += 1
            t = self._anim_frame / total_frames
            if t >= 1.0:
                self.move(target_x, target_y)
                self.set_opacity(1.0)
                self._open_anim_timer_id = None
                return False

            # Smooth cubic ease-out: 1 - (1 - t)^3
            ease = 1.0 - math.pow(1.0 - t, 3)
            curr_y = int(start_y + (target_y - start_y) * ease)
            curr_opacity = min(1.0, 0.15 + 0.85 * ease)
            self.move(target_x, curr_y)
            self.set_opacity(curr_opacity)
            return True

        self._open_anim_timer_id = GLib.timeout_add(15, _anim_step)

    def show_control_center(self):
        self._on_theme_changed()
        if hasattr(self, "stack"):
            self.stack.set_visible_child_name("main")

        # 1. Update transparent backdrop across all monitors and show it behind
        if hasattr(self, "_backdrop") and self._backdrop:
            self._backdrop.update_geometry()
            self._backdrop.show_all()
            self._backdrop.present()

        # 2. Position Control Center at top-right
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() if (display and hasattr(display, "get_primary_monitor")) else None
        if not monitor and display and hasattr(display, "get_n_monitors") and display.get_n_monitors() > 0:
            monitor = display.get_monitor(0)
        geom = monitor.get_geometry() if monitor else Gdk.Rectangle()
        sw = geom.width if geom.width > 0 else 1920

        win_w = 330
        x = geom.x + sw - win_w - 16
        y = geom.y + 36

        self.set_size_request(win_w, -1)
        self.set_can_focus(True)
        self._start_open_animation(x, y)

        # Trigger background hardware state sync (0ms UI freeze)
        self._sync_all_hardware_state_async()

    def hide_control_center(self):
        if getattr(self, "_open_anim_timer_id", None) is not None:
            try:
                GLib.source_remove(self._open_anim_timer_id)
            except Exception:
                pass
            self._open_anim_timer_id = None
        self._cancel_auto_close_timer()
        if hasattr(self, "_backdrop") and self._backdrop:
            self._backdrop.hide()
        self.hide()
        if getattr(self, "_is_standalone", False):
            Gtk.main_quit()

    def toggle_control_center(self):
        if self.is_visible():
            self.hide_control_center()
        else:
            self.show_control_center()
