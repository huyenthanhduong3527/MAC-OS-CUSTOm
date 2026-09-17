"""
Main Dynamic Island Window.
Renders the Apple-style OLED pill with Cairo anti-aliased squircle, specular rim glow,
and manages 60 FPS physics animations and state transitions.
"""

import math
import os
import time
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from src.config import config
from src.animator import IslandAnimator
from src.utils.visualizer import AudioVisualizer
from src.modules.media import MediaManager
from src.modules.audio import AudioController
from src.modules.system import SystemMonitor
from src.modules.timer import IslandTimer
from src.modules.notification import NotificationListener, NotificationManager

from src.ui.compact_view import CompactView
from src.ui.expanded_view import ExpandedView
from src.ui.event_banner import EventBanner
from src.ui.cosmic_orbit import CosmicOrbitEngine

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
        # Normal top-level window with keep_above: stays permanently on top without attaching to any app's lifecycle
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_focus_on_map(False)
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
        self.expanded_w = config.get("expanded_width", 430)
        self.expanded_h = config.get("expanded_height", 220)
        self.event_w = 270
        self.event_h = 42

        # Cosmic Orbit Celestial Engine
        self.cosmic_engine = CosmicOrbitEngine()
        self.cosmic_enabled = config.get("enable_cosmic_orbit", True)
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
        self.system_mon = SystemMonitor()
        self.timer_mod = IslandTimer(on_finish=self._on_timer_finished)
        self.notif_mgr = NotificationManager()
        self.notif_listener = NotificationListener(
            on_notification=self._on_notification_received,
            on_volume_change=self._on_volume_changed
        )

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
            on_click=self._on_compact_clicked,
            on_context_menu=self._show_context_menu
        )
        self.expanded_view = ExpandedView(
            self.media_mgr, self.system_mon, self.audio_ctrl, self.timer_mod, self.visualizer,
            notif_mgr=self.notif_mgr,
            on_collapse=self.collapse,
            on_offset_change=self._on_offset_changed,
            on_quit=self.quit_app,
            on_cosmos_change=self._on_cosmos_changed
        )
        self.event_banner = EventBanner(on_click=self._on_event_clicked)

        self.view_stack.add_named(self.compact_view, STATE_COMPACT)
        self.view_stack.add_named(self.expanded_view, STATE_EXPANDED)
        self.view_stack.add_named(self.event_banner, STATE_EVENT)

        self.main_overlay.add(self.view_stack)

        # 6. Event Masks
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
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
        else:
            # Full window receives clicks in expanded or event modes
            alloc = self.get_allocation()
            w = max(int(alloc.width), int(self.current_w), 1)
            h = max(int(alloc.height), int(self.current_h), 1)
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

            # 1. Draw glowing orbits and twinkling stardust
            self.cosmic_engine.draw_orbits(cr, center_x, center_y)

            # 2. Draw planets moving behind the Dynamic Island (z < 0)
            self.cosmic_engine.draw_planets_back(cr)

            # 3. Draw Dynamic Island OLED pill (centered at pill_x, pill_y)
            radius = pill_h / 2.0
            # Outer drop shadow
            cr.save()
            for i in range(3):
                blur_offset = (3 - i) * 1.5
                cr.new_sub_path()
                self._path_rounded_rect(cr, pill_x - blur_offset, pill_y - blur_offset, pill_w + blur_offset*2, pill_h + blur_offset*2, radius + blur_offset)
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.06 + i * 0.04)
                cr.fill()
            cr.restore()

            # Pitch-black OLED background
            self._path_rounded_rect(cr, pill_x, pill_y, pill_w, pill_h, radius)
            pat = cairo.LinearGradient(0, pill_y, 0, pill_y + pill_h)
            pat.add_color_stop_rgba(0.0, 0.08, 0.08, 0.10, 1.0)
            pat.add_color_stop_rgba(1.0, 0.01, 0.01, 0.02, 1.0)
            cr.set_source(pat)
            cr.fill_preserve()

            # Specular Glass Rim Border
            rim_pat = cairo.LinearGradient(0, pill_y, 0, pill_y + pill_h)
            rim_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.32) # Crisp top highlight
            rim_pat.add_color_stop_rgba(0.3, 1.0, 1.0, 1.0, 0.16)
            rim_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.08)
            cr.set_source(rim_pat)
            cr.set_line_width(1.2)
            cr.stroke()

            # 4. Draw planets moving in front of the Dynamic Island (z >= 0), hover badges, ripples
            self.cosmic_engine.draw_planets_front(cr)
        else:
            # Calculate dynamic pill radius for normal / expanded mode
            t = min(1.0, max(0.0, (height - self.compact_h) / max(1, (self.expanded_h - self.compact_h))))
            radius = (height / 2.0) * (1.0 - t) + 26.0 * t

            x = 0.5
            y = 0.5
            w = width - 1.0
            h = height - 1.0

            # Outer Shadow
            cr.save()
            for i in range(3):
                blur_offset = (3 - i) * 1.5
                cr.new_sub_path()
                self._path_rounded_rect(cr, x - blur_offset, y - blur_offset, w + blur_offset*2, h + blur_offset*2, radius + blur_offset)
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.06 + i * 0.04)
                cr.fill()
            cr.restore()

            # Pitch-Black OLED Background Pill
            self._path_rounded_rect(cr, x, y, w, h, radius)
            pat = cairo.LinearGradient(0, 0, 0, height)
            pat.add_color_stop_rgba(0.0, 0.08, 0.08, 0.10, 1.0)
            pat.add_color_stop_rgba(1.0, 0.01, 0.01, 0.02, 1.0)
            cr.set_source(pat)
            cr.fill_preserve()

            # Specular Glass Rim Border
            rim_pat = cairo.LinearGradient(0, 0, 0, height)
            rim_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.32)
            rim_pat.add_color_stop_rgba(0.3, 1.0, 1.0, 1.0, 0.16)
            rim_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.08)
            cr.set_source(rim_pat)
            cr.set_line_width(1.2)
            cr.stroke()

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
                self._update_input_shape()
                self.queue_draw()
        elif self.state == STATE_EXPANDED:
            self.expanded_view.update()

        return True

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

    def _on_track_changed(self, title, artist):
        """Callback from MediaManager when song changes."""
        if config.get("enable_track_popup", True) and self.state != STATE_EXPANDED:
            self.event_banner.show_track(title, artist)
            self.trigger_event_banner(duration=3.0)

    def _on_timer_finished(self):
        """Triggered when timer reaches 0:00."""
        self.expand()
        self.expanded_view.switch_to_tab("timer")

    def _on_offset_changed(self, offset):
        self._update_position(self.current_w, self.current_h)

    def _show_context_menu(self, event):
        menu = Gtk.Menu()

        def add_item(label, callback):
            item = Gtk.MenuItem(label=label)
            item.connect("activate", callback)
            menu.append(item)

        add_item("Toggle Expand / Collapse", lambda i: self.collapse() if self.state == STATE_EXPANDED else self.expand())
        add_item("🪐 Vũ trụ Orbit (Solar Launcher)", lambda i: self.toggle_cosmic_orbit())
        menu.append(Gtk.SeparatorMenuItem())
        add_item("🎵 Media Player", lambda i: (self.expand(), self.expanded_view.switch_to_tab("media")))
        add_item("⚡ System Vitals", lambda i: (self.expand(), self.expanded_view.switch_to_tab("vitals")))
        add_item("🎛️ Quick Controls", lambda i: (self.expand(), self.expanded_view.switch_to_tab("controls")))
        add_item("⏱️ Timer & Stopwatch", lambda i: (self.expand(), self.expanded_view.switch_to_tab("timer")))
        add_item("🔔 Notifications", lambda i: (self.expand(), self.expanded_view.switch_to_tab("notifs")))
        add_item("⚙️ Settings", lambda i: (self.expand(), self.expanded_view.switch_to_tab("settings")))
        menu.append(Gtk.SeparatorMenuItem())
        add_item("Quit Dynamic Island", lambda i: self.quit_app())

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def quit_app(self):
        self.audio_ctrl.stop()
        self.notif_listener.stop()
        Gtk.main_quit()
