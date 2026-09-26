"""
Main Dynamic Island Window.
Renders the Apple-style OLED pill with Cairo anti-aliased squircle, specular rim glow,
and manages 60 FPS physics animations and state transitions.
"""

import math
import os
import time
import subprocess
import threading
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from src.config import config
from src.utils.i18n import t
from src.animator import IslandAnimator
from src.utils.visualizer import AudioVisualizer
from src.modules.media import MediaManager
from src.modules.audio import AudioController
from src.modules.system import SystemMonitor
from src.modules.timer import IslandTimer
from src.modules.notification import NotificationListener, NotificationManager
from src.modules.brightness import BrightnessController
from src.modules.privacy import PrivacyMonitor
from src.modules.live_activity import LiveActivityManager
from src.modules.sound import SoundManager
from src.modules.clipboard import ClipboardManager

from src.ui.compact_view import CompactView
from src.ui.expanded_view import ExpandedView
from src.ui.event_banner import EventBanner
from src.ui.cosmic_orbit import CosmicOrbitEngine
from src.ui.macos_menu import create_mac_context_menu, create_mac_menu_item

STATE_COMPACT = "compact"
STATE_EXPANDED = "expanded"
STATE_EVENT = "event"

class DynamicIslandWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        # 1. Window setup
        self.set_title("Dynamic Island")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()
        # DOCK window type hint: permanent desktop overlay; Mutter never shows "Not Responding" dialogs
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_focus_on_map(False)
        self.set_accept_focus(True)
        self._tick_count = 0

        # RGBA transparent visual
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # 2. Dimensions & State
        self.state = STATE_COMPACT
        self.compact_w = config.get("compact_width", 230)
        self.compact_h = config.get("compact_height", 40)
        self.expanded_w = max(config.get("expanded_width", 505), 460)
        self.expanded_h = max(config.get("expanded_height", 280), 240)
        self.event_w = 270
        self.event_h = 42

        # Cosmic Orbit Celestial Engine
        self.cosmic_engine = CosmicOrbitEngine()
        self.cosmic_enabled = config.get("enable_cosmic_orbit", False)
        self.cosmic_w = 820
        self.cosmic_h = 240
        self.pill_offset_y = 48.0

        self.current_w = float(self.compact_w)
        self.current_h = float(self.compact_h)
        self.current_opacity = 0.0

        # Auto collapse timer
        self._collapse_timeout_id = None

        # 3. Load CSS
        self._load_css()

        # 4. Initialize Core Modules
        self.visualizer = AudioVisualizer(num_bars=10)
        self.media_mgr = MediaManager(on_track_change=self._on_track_changed)
        self.audio_ctrl = AudioController(on_volume_change=self._on_volume_changed)
        self.brightness_ctrl = BrightnessController.get_instance(on_change=self._on_brightness_changed)
        self.system_mon = SystemMonitor()
        self.timer_mod = IslandTimer(on_finish=self._on_timer_finished)
        self.notif_mgr = NotificationManager()
        self.notif_listener = NotificationListener(
            on_notification=self._on_notification_received,
            on_volume_change=self._on_volume_changed
        )
        self.privacy_mgr = PrivacyMonitor.get_instance()
        self.live_activity_mgr = LiveActivityManager.get_instance()
        self.sound_mgr = SoundManager.get_instance()
        self.clipboard_mgr = ClipboardManager.get_instance()

        # 5. UI Views & Stack
        self.main_overlay = Gtk.Overlay()
        self.add(self.main_overlay)

        self.view_stack = Gtk.Stack()
        self.view_stack.set_homogeneous(False)
        self.view_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.view_stack.set_transition_duration(150)

        self.compact_view = CompactView(
            self.media_mgr, self.system_mon, self.timer_mod, self.visualizer,
            notif_mgr=self.notif_mgr,
            privacy_mgr=self.privacy_mgr,
            live_activity_mgr=self.live_activity_mgr,
            on_click=self._on_compact_clicked,
            on_context_menu=self._show_context_menu
        )
        self.expanded_view = ExpandedView(
            self.media_mgr, self.system_mon, self.audio_ctrl, self.timer_mod, self.visualizer,
            notif_mgr=self.notif_mgr,
            brightness_ctrl=self.brightness_ctrl,
            on_collapse=self.collapse,
            on_offset_change=self._on_offset_changed,
            on_size_change=self._on_size_changed,
            on_quit=self.quit_app,
            on_cosmos_change=self._on_cosmos_changed,
            on_clock_change=self._on_clock_changed,
            on_music_change=self._on_music_changed,
            on_calendar_change=self._on_calendar_changed,
            on_weather_change=self._on_weather_changed,
            on_battery_change=self._on_battery_changed
        )
        self.event_banner = EventBanner(on_click=self._on_event_clicked)

        self.view_stack.add_named(self.compact_view, STATE_COMPACT)
        self.view_stack.add_named(self.expanded_view, STATE_EXPANDED)
        self.view_stack.add_named(self.event_banner, STATE_EVENT)

        self.main_overlay.add(self.view_stack)

        # 6. Event Masks
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("key-press-event", self._on_key_press)
        self.connect("motion-notify-event", self._on_mouse_motion)
        self.connect("enter-notify-event", self._on_mouse_enter)
        self.connect("leave-notify-event", self._on_mouse_leave)

        # 7. Animator
        self.animator = IslandAnimator(
            initial_w=self.compact_w,
            initial_h=self.compact_h,
            on_update=self._on_animation_step,
            on_finish=self._on_animation_finished
        )

        # 8. Main Loop Tick for UI updates (clock, visualizer, stats, cosmic orbit)
        GLib.timeout_add(33, self._on_ui_tick) # ~30 FPS

        # Initial layout & display: show only compact view
        self.main_overlay.show()
        self.view_stack.show()
        self.compact_view.show_all()
        self.event_banner.show_all()
        self.view_stack.set_visible_child_name(STATE_COMPACT)
        self.show()
        self._update_position(self.compact_w, self.compact_h)
        self._update_input_shape()
        GLib.timeout_add(500, self._disable_wm_ping)
        GLib.timeout_add(1500, self._disable_wm_ping)
        self.connect("map-event", lambda *args: GLib.timeout_add(500, self._disable_wm_ping))

        # 9. macOS Desktop Widgets Suite
        self.desktop_calendar = None
        if config.get("enable_desktop_calendar", True):
            try:
                from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
                self.desktop_calendar = DesktopCalendarWidget()
                self.desktop_calendar.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing calendar widget: {e}")

        self.desktop_weather = None
        if config.get("enable_desktop_weather", True):
            try:
                from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
                self.desktop_weather = DesktopWeatherWidget()
                self.desktop_weather.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing weather widget: {e}")

        self.desktop_battery = None
        if config.get("enable_desktop_battery", True):
            try:
                from src.ui.desktop_widgets.battery_widget import DesktopBatteryWidget
                self.desktop_battery = DesktopBatteryWidget()
                self.desktop_battery.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing battery widget: {e}")

        self.desktop_clock = None
        if config.get("enable_desktop_clock", False):
            try:
                from src.ui.desktop_widgets.clock_widget import DesktopClockWidget
                self.desktop_clock = DesktopClockWidget()
                self.desktop_clock.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing desktop clock: {e}")

        self.desktop_music = None
        if config.get("enable_desktop_music", False):
            try:
                from src.ui.desktop_widgets.music_widget import DesktopMusicWidget
                self.desktop_music = DesktopMusicWidget(self.media_mgr)
                self.desktop_music.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing desktop music widget: {e}")

        self.desktop_photo = None
        if config.get("enable_desktop_photo", True):
            try:
                from src.ui.desktop_widgets.photo_widget import DesktopPhotoWidget
                self.desktop_photo = DesktopPhotoWidget()
                self.desktop_photo.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing desktop photo widget: {e}")

        self.desktop_weekday = None
        if config.get("enable_desktop_weekday", True):
            try:
                from src.ui.desktop_widgets.weekday_clock_widget import DesktopWeekdayClockWidget
                self.desktop_weekday = DesktopWeekdayClockWidget()
                self.desktop_weekday.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing desktop weekday widget: {e}")

        self.desktop_macbook = None
        if config.get("enable_desktop_macbook", True):
            try:
                from src.ui.desktop_widgets.macbook_widget import DesktopMacBookWidget
                self.desktop_macbook = DesktopMacBookWidget()
                self.desktop_macbook.show_all()
            except Exception as e:
                print(f"[DynamicIsland] Notice initializing desktop macbook widget: {e}")

        self.spotlight_win = None
        self.control_center_win = None
        self.airdrop_win = None

        # 10. macOS AirDrop Integration
        try:
            from src.modules.airdrop import AirDropManager
            self.airdrop_mgr = AirDropManager.get_instance()
            self.airdrop_mgr.on_transfer_event = self._on_airdrop_transfer_event
        except Exception as e:
            print(f"[DynamicIsland] Notice initializing AirDrop manager: {e}")


    def _disable_wm_ping(self):
        """
        Strip _NET_WM_PING from WM_PROTOCOLS on X11/XWayland without WM_TAKE_FOCUS.
        Setting WM_TAKE_FOCUS prevented Mutter from delivering mouse clicks
        when other applications were focused.
        """
        try:
            gdk_win = self.get_window()
            if gdk_win and hasattr(gdk_win, "get_xid"):
                xid = str(gdk_win.get_xid())
                subprocess.run(
                    ["xprop", "-id", xid, "-f", "WM_PROTOCOLS", "32a", "-set", "WM_PROTOCOLS", "WM_DELETE_WINDOW"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=0.5
                )
        except Exception:
            pass
        return False

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), "ui", "styles.css")
        if os.path.exists(css_path):
            try:
                css_provider.load_from_path(css_path)
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception as e:
                print(f"[Window] CSS Notice: {e}")

    def _update_position(self, w, h):
        """Center the island horizontally at top offset."""
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo = monitor.get_geometry()

        is_anim = hasattr(self, 'animator') and self.animator.is_animating

        if self.state == STATE_COMPACT and self.cosmic_enabled and not is_anim:
            win_w = self.cosmic_w
            win_h = self.cosmic_h
            center_x = geo.x + int((geo.width - win_w) / 2)
            target_screen_y = geo.y + int(config.get("y_offset", 32))
            top_y = max(0, target_screen_y - int(self.pill_offset_y))
            actual_pill_y = target_screen_y - top_y

            self.resize(int(win_w), int(win_h))
            self.move(center_x, top_y)

            # Center and position compact pill inside the cosmic window
            self.compact_view.set_halign(Gtk.Align.CENTER)
            self.compact_view.set_valign(Gtk.Align.START)
            self.compact_view.set_margin_top(int(actual_pill_y))
            self.compact_view.set_size_request(int(self.compact_w), int(self.compact_h))
        else:
            self.compact_view.set_halign(Gtk.Align.FILL)
            self.compact_view.set_valign(Gtk.Align.FILL)
            self.compact_view.set_margin_top(0)
            center_x = geo.x + int((geo.width - w) / 2)
            top_y = geo.y + int(config.get("y_offset", 32))
            self.resize(int(w), int(h))
            self.move(center_x, top_y)

    def _update_input_shape(self):
        """Update click-through masking so only the pill & planets intercept mouse events."""
        gdk_win = self.get_window()
        if not gdk_win:
            return

        is_anim = hasattr(self, 'animator') and self.animator.is_animating
        if self.state == STATE_COMPACT and self.cosmic_enabled and not is_anim:
            region = cairo.Region()
            # 1. Compact pill input box
            pill_x = int((self.cosmic_w - self.compact_w) / 2)
            top_y = max(0, int(config.get("y_offset", 32)) - int(self.pill_offset_y))
            pill_y = int(config.get("y_offset", 32) - top_y)
            region.union(cairo.RectangleInt(pill_x, pill_y, int(self.compact_w), int(self.compact_h)))

            # 2. Input boxes around each orbiting planet
            for p in self.cosmic_engine.planets:
                eff_r = int((p.base_radius * p.scale) + 12)
                px = int(p.x - eff_r)
                py = int(p.y - eff_r)
                size = int(eff_r * 2)
                region.union(cairo.RectangleInt(px, py, size, size))

            gdk_win.input_shape_combine_region(region, 0, 0)
        elif self.state == STATE_EXPANDED:
            # Full window receives clicks in expanded mode (cover entire expanded card)
            alloc = self.get_allocation()
            w = max(int(alloc.width), int(self.current_w), int(self.expanded_w), 600)
            h = max(int(alloc.height), int(self.current_h), int(self.expanded_h), 400)
            region = cairo.Region(cairo.RectangleInt(0, 0, w, h))
            gdk_win.input_shape_combine_region(region, 0, 0)
        else:
            # Compact pill mode (non-cosmic) or event capsule mode
            alloc = self.get_allocation()
            w = max(int(alloc.width), int(self.current_w), int(self.compact_w))
            h = max(int(alloc.height), int(self.current_h), int(self.compact_h))
            region = cairo.Region(cairo.RectangleInt(0, 0, w, h))
            gdk_win.input_shape_combine_region(region, 0, 0)

    def _on_draw(self, widget, cr):
        """Cairo custom rendering: Apple OLED pill with drop shadow, specular rim light, and cosmic solar system."""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Clear background completely transparent
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        is_anim = hasattr(self, 'animator') and self.animator.is_animating
        if self.state == STATE_COMPACT and self.cosmic_enabled and not is_anim:
            pill_w = float(self.compact_w)
            pill_h = float(self.compact_h)
            pill_x = (width - pill_w) / 2.0
            top_y = max(0, int(config.get("y_offset", 32)) - int(self.pill_offset_y))
            pill_y = float(int(config.get("y_offset", 32)) - top_y)
            center_x = width / 2.0
            center_y = pill_y + pill_h / 2.0
            radius = pill_h / 2.0

            # 1. Draw glowing orbits and twinkling stardust
            self.cosmic_engine.draw_orbits(cr, center_x, center_y)

            # 2. Draw planets moving behind the Dynamic Island (z < 0)
            self.cosmic_engine.draw_planets_back(cr)

            # 3. Draw Dynamic Island OLED pill (centered at pill_x, pill_y)
            # Pitch-black OLED background (Pure seamless black, zero outer shadow or border)
            self._path_rounded_rect(cr, pill_x, pill_y, pill_w, pill_h, radius)
            pat = cairo.LinearGradient(0, pill_y, 0, pill_y + pill_h)
            pat.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 1.0)
            pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 1.0)
            cr.set_source(pat)
            cr.fill()

            # 4. Draw planets moving in front of the Dynamic Island (z >= 0), hover badges, ripples
            self.cosmic_engine.draw_planets_front(cr)
        else:
            # Calculate dynamic pill radius for normal / expanded mode
            t = min(1.0, max(0.0, (height - self.compact_h) / max(1, (self.expanded_h - self.compact_h))))
            radius = (height / 2.0) * (1.0 - t) + 26.0 * t

            x = 0.0
            y = 0.0
            w = width
            h = height

            # Pitch-Black OLED Background Pill (Pure seamless black, zero outer shadow or border)
            self._path_rounded_rect(cr, x, y, w, h, radius)
            pat = cairo.LinearGradient(0, 0, 0, height)
            pat.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 1.0)
            pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 1.0)
            cr.set_source(pat)
            cr.fill()

        return False

    def _path_rounded_rect(self, cr, x, y, w, h, r):
        """Draw smooth rounded rectangle path."""
        r = min(r, w / 2.0, h / 2.0)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def expand(self):
        """Smoothly expand island to full hub view."""
        self._cancel_collapse_timer()
        self.state = STATE_EXPANDED
        self.set_keep_above(True)
        self.present()
        self._update_input_shape()
        self.expanded_view.show_all()
        self.view_stack.set_visible_child_name(STATE_EXPANDED)
        self.expanded_view.update()
        self.animator.animate_to(self.expanded_w, self.expanded_h, 1.0)

    def collapse(self):
        """Smoothly collapse island back to compact pill."""
        self._cancel_collapse_timer()
        self.state = STATE_COMPACT
        self.view_stack.set_visible_child_name(STATE_COMPACT)
        self.compact_view.update()
        self.animator.animate_to(self.compact_w, self.compact_h, 0.0)

    def trigger_event_banner(self, duration=2.5, target_w=None, target_h=None):
        """Display short dynamic event capsule and auto-retract."""
        if self.state == STATE_EXPANDED:
            return # Don't interrupt expanded view

        w = target_w if target_w is not None else self.event_w
        h = target_h if target_h is not None else self.event_h

        self._cancel_collapse_timer()
        self.state = STATE_EVENT
        self._update_input_shape()
        self.view_stack.set_visible_child_name(STATE_EVENT)
        self.animator.animate_to(w, h, 0.5)

        self._collapse_timeout_id = GLib.timeout_add(int(duration * 1000), self._on_event_timeout)

    def _on_event_timeout(self):
        self._collapse_timeout_id = None
        if self.state == STATE_EVENT:
            self.collapse()
        return False

    def _on_animation_step(self, w, h, opacity):
        self.current_w = w
        self.current_h = h
        self.current_opacity = opacity
        self._update_position(w, h)
        self.queue_draw()

    def _on_animation_finished(self):
        if self.state == STATE_COMPACT:
            self.expanded_view.hide()
            self._update_position(self.compact_w, self.compact_h)
            self._update_input_shape()
        elif self.state == STATE_EVENT:
            self.expanded_view.hide()
            self._update_position(self.current_w, self.current_h)
            self._update_input_shape()
        elif self.state == STATE_EXPANDED:
            self._update_input_shape()

    def _on_key_press(self, widget, event):
        """Allow Escape or Up Arrow to collapse the expanded island."""
        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Up):
            if self.state == STATE_EXPANDED:
                self.collapse()
                return True
        return False

    def _on_compact_clicked(self):
        """Called directly when user clicks anywhere on the compact pill."""
        if self.cosmic_enabled and self.cosmic_engine.hovered_planet:
            return # Let planet click handle launching app
        has_unread = self.notif_mgr.unread_count > 0
        self.expand()
        if has_unread:
            self.expanded_view.switch_to_tab("notifs")

    def _on_event_clicked(self):
        """Called directly when user clicks on an event banner capsule."""
        self.expand()
        self.expanded_view.switch_to_tab("notifs")

    def _on_button_press(self, widget, event):
        if event.button == 1: # Left Click
            if self.state == STATE_COMPACT and self.cosmic_enabled:
                # 1. Check if clicking an orbiting planet!
                if self.cosmic_engine.handle_click(event.x, event.y):
                    self.queue_draw()
                    return True

                # 2. Check if clicking on the island pill
                pill_w = float(self.compact_w)
                pill_h = float(self.compact_h)
                pill_x = (self.cosmic_w - pill_w) / 2.0
                top_y = max(0, int(config.get("y_offset", 32)) - int(self.pill_offset_y))
                pill_y = float(int(config.get("y_offset", 32)) - top_y)

                if (pill_x <= event.x <= pill_x + pill_w) and (pill_y <= event.y <= pill_y + pill_h):
                    has_unread = self.notif_mgr.unread_count > 0
                    self.expand()
                    if has_unread:
                        self.expanded_view.switch_to_tab("notifs")
                    return True
                return False

            elif self.state == STATE_COMPACT or self.state == STATE_EVENT:
                has_unread = self.notif_mgr.unread_count > 0
                self.expand()
                if has_unread:
                    self.expanded_view.switch_to_tab("notifs")
            else:
                # If clicking on header area, toggle collapse
                if event.y < 38:
                    self.collapse()
        elif event.button == 3: # Right Click Context Menu
            self._show_context_menu(event)
        return False

    def _on_mouse_motion(self, widget, event):
        if self.state == STATE_COMPACT and self.cosmic_enabled:
            changed = self.cosmic_engine.handle_mouse_move(event.x, event.y)
            if changed:
                self.queue_draw()
        return False

    def _on_mouse_enter(self, widget, event):
        self._cancel_collapse_timer()
        if config.get("expand_on_hover", False) and self.state == STATE_COMPACT:
            self.expand()
        return False

    def _on_mouse_leave(self, widget, event):
        auto_sec = config.get("auto_collapse_seconds", 6)
        if auto_sec > 0 and self.state == STATE_EXPANDED:
            self._cancel_collapse_timer()
            self._collapse_timeout_id = GLib.timeout_add(auto_sec * 1000, self._on_auto_collapse_timeout)
        return False

    def _on_auto_collapse_timeout(self):
        self._collapse_timeout_id = None
        if self.state == STATE_EXPANDED:
            self.collapse()
        return False

    def _cancel_collapse_timer(self):
        if self._collapse_timeout_id:
            GLib.source_remove(self._collapse_timeout_id)
            self._collapse_timeout_id = None

    def _on_ui_tick(self):
        """Update active UI elements, visualizer waves, media status, and cosmic orbits."""
        try:
            self._tick_count += 1

            # Step visualizer waves (smooth animation when music plays)
            is_playing = self.media_mgr.is_playing()
            self.visualizer.set_playing(is_playing)
            if is_playing:
                self.visualizer.step(0.033)

            # Refresh media D-Bus status periodically (every 1s / 30 ticks) to prevent D-Bus IPC spam
            if self._tick_count % 30 == 0:
                self.media_mgr.refresh()

            if self.state == STATE_COMPACT:
                self.compact_view.update()
                if self.cosmic_enabled and not (hasattr(self, 'animator') and self.animator.is_animating):
                    width = self.get_allocated_width()
                    pill_h = self.compact_h
                    top_y = max(0, int(config.get("y_offset", 32)) - int(self.pill_offset_y))
                    pill_y = float(int(config.get("y_offset", 32)) - top_y)
                    center_x = width / 2.0
                    center_y = pill_y + pill_h / 2.0
                    self.cosmic_engine.update(0.033, center_x, center_y)
                    # Performance optimization: Only update XShape input mask every 25 ticks (~0.8s)
                    # Calling input_shape_combine_region 30 FPS saturates XWayland socket and freezes the desktop!
                    if self._tick_count % 25 == 0:
                        self._update_input_shape()
                    self.queue_draw()
            elif self.state == STATE_EXPANDED:
                self.expanded_view.update()
        except Exception as e:
            # Shield 30 FPS UI timer from any uncaught exception
            pass

        return True

    def open_airdrop_window(self):
        """Open or present the authentic macOS AirDrop window."""
        try:
            from src.ui.macos_airdrop_window import MacOSAirDropWindow
            win = MacOSAirDropWindow.get_instance()
            win.show_window()
        except Exception as e:
            print(f"[DynamicIsland] Error opening AirDrop window: {e}")

    def _on_airdrop_transfer_event(self, event_type, data):
        """Display Dynamic Island pill event banner for AirDrop transfers."""
        filename = data.get("filename", "Tệp tin")
        is_incoming = data.get("is_incoming", False)

        if hasattr(self, 'live_activity_mgr') and self.live_activity_mgr:
            progress = data.get("progress", 1.0 if event_type == "complete" else 0.0)
            self.live_activity_mgr.set_airdrop_progress(
                filename=filename,
                progress=progress,
                speed_str=data.get("speed", ""),
                is_complete=(event_type == "complete")
            )

        if event_type == "start":
            action = "Đang nhận tệp..." if is_incoming else "Đang gửi tệp..."
            if config.get("enable_notification_popup", True) and self.state != STATE_EXPANDED:
                self.event_banner.show_notification("AirDrop", action, filename)
                self.trigger_event_banner(duration=3.0, target_w=360, target_h=44)
        elif event_type == "complete":
            if is_incoming:
                file_path = data.get("file_path", "")
                self._on_airdrop_received(filename, file_path)

    def _on_airdrop_received(self, filename: str, file_path: str = ""):
        """Display authentic Dynamic Island pill banner for completed AirDrop receive."""
        if hasattr(self, 'sound_mgr') and self.sound_mgr:
            self.sound_mgr.play_airdrop()

        if config.get("enable_notification_popup", True) and self.state != STATE_EXPANDED:
            # Check if file is an image to show thumbnail
            image_path = None
            if file_path and os.path.exists(file_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
                    image_path = file_path

            # Set click handler on event banner to open the file!
            def on_banner_click():
                if file_path and os.path.exists(file_path):
                    subprocess.Popen(["xdg-open", file_path])
                else:
                    downloads = os.path.expanduser("~/Downloads")
                    subprocess.Popen(["nautilus", downloads])

            self.event_banner.on_click = on_banner_click
            self.event_banner.show_notification(
                app_name="AirDrop",
                title=f"Đã nhận: {filename}",
                body="Chạm để mở tệp (Downloads)",
                image_path=image_path
            )
            self.trigger_event_banner(duration=5.0, target_w=390, target_h=48)

    def toggle_cosmic_orbit(self):
        self.cosmic_enabled = not self.cosmic_enabled
        config.set("enable_cosmic_orbit", self.cosmic_enabled)
        if self.state == STATE_COMPACT:
            self._update_position(self.compact_w, self.compact_h)
            self._update_input_shape()
            self.queue_draw()
        print(f"[Window] Cosmic Orbit enabled: {self.cosmic_enabled}")

    def _on_cosmos_changed(self, enabled):
        self.cosmic_enabled = enabled
        if self.state == STATE_COMPACT:
            self._update_position(self.compact_w, self.compact_h)
            self._update_input_shape()
            self.queue_draw()

    def _on_notification_received(self, app_name, title, body, image_path=None):
        """Callback from NotificationListener when system notification arrives."""
        print(f"[Window] Notification: {app_name} | {title} | {body} | img={image_path}")
        self.notif_mgr.add_notification(app_name, title, body, image_path=image_path)
        if config.get("enable_notification_popup", True) and self.state != STATE_EXPANDED:
            self.event_banner.show_notification(app_name, title, body, image_path=image_path)
            self.trigger_event_banner(duration=4.5, target_w=390, target_h=48)
        elif self.state == STATE_EXPANDED:
            self.expanded_view.update()

    def _on_volume_changed(self, volume, is_muted):
        """Callback from AudioController when system volume changes."""
        if config.get("enable_volume_popup", True) and self.state != STATE_EXPANDED:
            self.event_banner.show_volume(volume, is_muted)
            self.trigger_event_banner(duration=1.8, target_w=275, target_h=40)

    def _on_brightness_changed(self, pct):
        """Callback when screen brightness changes."""
        if config.get("enable_brightness_popup", True) and self.state != STATE_EXPANDED:
            self.event_banner.show_brightness(pct)
            self.trigger_event_banner(duration=1.8, target_w=275, target_h=40)
        elif self.state == STATE_EXPANDED:
            if hasattr(self.expanded_view, "controls_tab"):
                self.expanded_view.controls_tab.update()

    def _on_track_changed(self, title, artist):
        """Callback from MediaManager when song changes."""
        if config.get("enable_track_popup", True) and self.state != STATE_EXPANDED:
            self.event_banner.show_track(title, artist)
            self.trigger_event_banner(duration=3.0)

    def _on_timer_finished(self):
        """Triggered when timer reaches 0:00."""
        if hasattr(self, "sound_mgr") and self.sound_mgr:
            self.sound_mgr.play_timer()
        self.expand()
        self.expanded_view.switch_to_tab("timer")

    def update_language(self, lang_code: str):
        """Refreshes language for Dynamic Island widgets and expanded tabs."""
        if hasattr(self, "expanded_view"):
            self.expanded_view.update()
        if hasattr(self, "compact_view"):
            self.compact_view.queue_draw()

    def _on_offset_changed(self, offset):
        self._update_position(self.current_w, self.current_h)

    def _on_size_changed(self, compact_w=None, compact_h=None, expanded_w=None, expanded_h=None):
        """Dynamically update dimensions in real-time and save to config."""
        if compact_w is not None:
            self.compact_w = int(compact_w)
            config.set("compact_width", self.compact_w)
        if compact_h is not None:
            self.compact_h = int(compact_h)
            config.set("compact_height", self.compact_h)
        if expanded_w is not None:
            self.expanded_w = max(int(expanded_w), 460)
            config.set("expanded_width", self.expanded_w)
        if expanded_h is not None:
            self.expanded_h = max(int(expanded_h), 240)
            config.set("expanded_height", self.expanded_h)

        if self.state == STATE_COMPACT:
            self.current_w = float(self.compact_w)
            self.current_h = float(self.compact_h)
            if hasattr(self, 'animator'):
                self.animator.current_w = float(self.compact_w)
                self.animator.current_h = float(self.compact_h)
                self.animator.target_w = float(self.compact_w)
                self.animator.target_h = float(self.compact_h)
            self._update_position(self.compact_w, self.compact_h)
            self._update_input_shape()
            self.queue_draw()
        elif self.state == STATE_EXPANDED:
            self.current_w = float(self.expanded_w)
            self.current_h = float(self.expanded_h)
            if hasattr(self, 'animator'):
                self.animator.current_w = float(self.expanded_w)
                self.animator.current_h = float(self.expanded_h)
                self.animator.target_w = float(self.expanded_w)
                self.animator.target_h = float(self.expanded_h)
            self._update_position(self.expanded_w, self.expanded_h)
            self._update_input_shape()
            self.queue_draw()

    def _show_context_menu(self, event):
        menu = create_mac_context_menu()

        def add_item(icon_name, label, callback, is_destructive=False):
            item = create_mac_menu_item(icon_name, label, callback, is_destructive=is_destructive)
            menu.append(item)
            return item

        add_item("aspectratio", t("menu_toggle", "Toggle Expand / Collapse"),
                 lambda i: self.collapse() if self.state == STATE_EXPANDED else self.expand())
        add_item("globe", t("menu_orbit", "Orbit"), lambda i: self.toggle_cosmic_orbit())
        menu.append(Gtk.SeparatorMenuItem())
        for icon_name, key, label, cb in [
            ("music", "menu_media", "Media Player", lambda i: (self.expand(), self.expanded_view.switch_to_tab("media"))),
            ("bolt", "menu_vitals", "System Vitals", lambda i: (self.expand(), self.expanded_view.switch_to_tab("vitals"))),
            ("slider.horizontal.3", "menu_controls", "Quick Controls", lambda i: (self.expand(), self.expanded_view.switch_to_tab("controls"))),
            ("timer", "menu_timer", "Timer & Stopwatch", lambda i: (self.expand(), self.expanded_view.switch_to_tab("timer"))),
            ("bell", "menu_notifications", "Notifications", lambda i: (self.expand(), self.expanded_view.switch_to_tab("notifs"))),
            ("doc.on.clipboard", "menu_clipboard", "Clipboard History", lambda i: (self.expand(), self.expanded_view.switch_to_tab("clipboard"))),
            ("slider.horizontal.3", "menu_control_center", "Control Center", lambda i: self.toggle_control_center()),
            ("gearshape", "menu_settings", "System Settings", lambda i: self.open_macos_settings_window()),
            ("calendar", "menu_calendar", "Calendar", lambda i: self.toggle_desktop_calendar()),
            ("cloud.sun", "menu_weather", "Weather", lambda i: self.toggle_desktop_weather()),
            ("battery", "menu_battery", "Batteries", lambda i: self.toggle_desktop_battery()),
            ("clock", "menu_clock", "Desktop Clock", lambda i: self.toggle_desktop_clock()),
            ("music", "menu_music", "Desktop Music", lambda i: self.toggle_desktop_music()),
            ("photo", "menu_photo", "Pinned Photos (Widget Ảnh)", lambda i: self.toggle_desktop_photo())
        ]:
            add_item(icon_name, t(key, label), cb)
        menu.append(Gtk.SeparatorMenuItem())
        try:
            from src.ui.desktop_widgets import is_desktop_widgets_locked, set_all_desktop_widgets_locked
            all_locked = is_desktop_widgets_locked()
            lock_label = "Khóa Cố Định Tất Cả Widget" if not all_locked else "Mở Khóa Widget (Di Chuyển & Đổi Cỡ)"
            lock_icon = "lock" if not all_locked else "lock.open"
            add_item(lock_icon, lock_label, lambda i, l=all_locked: set_all_desktop_widgets_locked(not l))
        except Exception as e:
            print(f"[DynamicIsland] Error adding widget lock menu item: {e}")
        menu.append(Gtk.SeparatorMenuItem())
        add_item("power", t("menu_quit", "Quit Dynamic Island"), lambda i: self.quit_app(), is_destructive=True)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def toggle_desktop_calendar(self):
        if self.desktop_calendar and self.desktop_calendar.get_visible():
            self.desktop_calendar.hide_widget()
        else:
            if not self.desktop_calendar:
                try:
                    from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
                    self.desktop_calendar = DesktopCalendarWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating calendar widget: {e}")
                    return
            self.desktop_calendar.show_widget()

    def open_calendar_dialog(self):
        if not self.desktop_calendar:
            try:
                from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
                self.desktop_calendar = DesktopCalendarWidget()
            except Exception as e:
                print(f"[DynamicIsland] Error creating calendar widget: {e}")
                return
        self.desktop_calendar.show_widget()
        self.desktop_calendar.present()
        self.desktop_calendar._on_widget_clicked()

    def toggle_desktop_weather(self):
        if self.desktop_weather and self.desktop_weather.get_visible():
            self.desktop_weather.hide_widget()
        else:
            if not self.desktop_weather:
                try:
                    from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
                    self.desktop_weather = DesktopWeatherWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating weather widget: {e}")
                    return
            self.desktop_weather.show_widget()

    def open_weather_dialog(self):
        if not self.desktop_weather:
            try:
                from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
                self.desktop_weather = DesktopWeatherWidget()
            except Exception as e:
                print(f"[DynamicIsland] Error creating weather widget: {e}")
                return
        self.desktop_weather.show_widget()
        self.desktop_weather.present()
        self.desktop_weather._on_widget_clicked()

    def toggle_desktop_battery(self):
        if self.desktop_battery and self.desktop_battery.get_visible():
            self.desktop_battery.hide_widget()
        else:
            if not self.desktop_battery:
                try:
                    from src.ui.desktop_widgets.battery_widget import DesktopBatteryWidget
                    self.desktop_battery = DesktopBatteryWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating battery widget: {e}")
                    return
            self.desktop_battery.show_widget()

    def toggle_desktop_photo(self):
        if self.desktop_photo and self.desktop_photo.get_visible():
            self.desktop_photo.hide_widget()
        else:
            if not self.desktop_photo:
                try:
                    from src.ui.desktop_widgets.photo_widget import DesktopPhotoWidget
                    self.desktop_photo = DesktopPhotoWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating photo widget: {e}")
                    return
            self.desktop_photo.show_widget()

    def _on_photo_changed(self, enabled):
        if enabled:
            if not self.desktop_photo:
                try:
                    from src.ui.desktop_widgets.photo_widget import DesktopPhotoWidget
                    self.desktop_photo = DesktopPhotoWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating photo widget: {e}")
                    return
            self.desktop_photo.show_widget()
        else:
            if self.desktop_photo:
                self.desktop_photo.hide_widget()

    def _on_clock_changed(self, enabled):
        if enabled:
            if not self.desktop_clock:
                try:
                    from src.ui.desktop_widgets.clock_widget import DesktopClockWidget
                    self.desktop_clock = DesktopClockWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating clock widget: {e}")
                    return
            self.desktop_clock.show_widget()
        else:
            if self.desktop_clock:
                self.desktop_clock.hide_widget()

    def _on_music_changed(self, enabled):
        if enabled:
            if not self.desktop_music:
                try:
                    from src.ui.desktop_widgets.music_widget import DesktopMusicWidget
                    self.desktop_music = DesktopMusicWidget(self.media_mgr)
                except Exception as e:
                    print(f"[DynamicIsland] Error creating music widget: {e}")
                    return
            self.desktop_music.show_widget()
        else:
            if self.desktop_music:
                self.desktop_music.hide_widget()

    def _on_calendar_changed(self, enabled):
        if enabled:
            if not self.desktop_calendar:
                try:
                    from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
                    self.desktop_calendar = DesktopCalendarWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating calendar widget: {e}")
                    return
            self.desktop_calendar.show_widget()
        else:
            if self.desktop_calendar:
                self.desktop_calendar.hide_widget()

    def _on_weather_changed(self, enabled):
        if enabled:
            if not self.desktop_weather:
                try:
                    from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
                    self.desktop_weather = DesktopWeatherWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating weather widget: {e}")
                    return
            self.desktop_weather.show_widget()
        else:
            if self.desktop_weather:
                self.desktop_weather.hide_widget()

    def _on_battery_changed(self, enabled):
        if enabled:
            if not self.desktop_battery:
                try:
                    from src.ui.desktop_widgets.battery_widget import DesktopBatteryWidget
                    self.desktop_battery = DesktopBatteryWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating battery widget: {e}")
                    return
            self.desktop_battery.show_widget()
        else:
            if self.desktop_battery:
                self.desktop_battery.hide_widget()

    def _on_weekday_changed(self, enabled):
        if enabled:
            if not self.desktop_weekday:
                try:
                    from src.ui.desktop_widgets.weekday_clock_widget import DesktopWeekdayClockWidget
                    self.desktop_weekday = DesktopWeekdayClockWidget()
                except Exception as e:
                    print(f"[DynamicIsland] Error creating weekday widget: {e}")
                    return
            self.desktop_weekday.show_widget()
        else:
            if self.desktop_weekday:
                self.desktop_weekday.hide_widget()

    def set_desktop_calendar_enabled(self, enabled): self._on_calendar_changed(enabled)
    def set_desktop_weather_enabled(self, enabled): self._on_weather_changed(enabled)
    def set_desktop_battery_enabled(self, enabled): self._on_battery_changed(enabled)
    def set_desktop_clock_enabled(self, enabled): self._on_clock_changed(enabled)
    def set_desktop_music_enabled(self, enabled): self._on_music_changed(enabled)
    def set_desktop_photo_enabled(self, enabled): self._on_photo_changed(enabled)
    def set_desktop_weekday_enabled(self, enabled): self._on_weekday_changed(enabled)

    def open_macos_settings_window(self, tab="appearance"):
        try:
            from src.ui.macos_settings_window import MacOSSettingsWindow
            win = MacOSSettingsWindow.get_instance(self)
            win.show_window(tab)
        except Exception as e:
            print(f"[DynamicIsland] Notice opening macOS settings window: {e}")

    def toggle_spotlight(self):
        if not self.spotlight_win:
            try:
                from src.ui.spotlight_search import SpotlightSearchWindow
                self.spotlight_win = SpotlightSearchWindow.get_instance(self)
            except Exception as e:
                print(f"[DynamicIsland] Error creating Spotlight search: {e}")
                return
        self.spotlight_win.toggle_spotlight()

    def toggle_control_center(self):
        if not self.control_center_win:
            try:
                from src.ui.macos_control_center import MacOSControlCenterWindow
                self.control_center_win = MacOSControlCenterWindow.get_instance(self)
            except Exception as e:
                print(f"[DynamicIsland] Error creating Control Center: {e}")
                return
        self.control_center_win.toggle_control_center()

    def hide_control_center(self):
        if self.control_center_win:
            self.control_center_win.hide_control_center()

    def quit_app(self):
        if getattr(self, '_is_quitting', False):
            return
        self._is_quitting = True

        for w in (self.desktop_calendar, self.desktop_weather, self.desktop_battery, self.desktop_clock, self.desktop_music, self.spotlight_win, self.control_center_win):
            if w:
                try:
                    w.destroy()
                except Exception:
                    pass
        self.desktop_calendar = None
        self.desktop_weather = None
        self.desktop_battery = None
        self.desktop_clock = None
        self.desktop_music = None
        self.spotlight_win = None
        self.control_center_win = None
        if hasattr(self, 'brightness_ctrl') and self.brightness_ctrl:
            try:
                self.brightness_ctrl.stop()
            except Exception:
                pass
        self.audio_ctrl.stop()
        self.notif_listener.stop()
        if Gtk.main_level() > 0:
            Gtk.main_quit()
