"""
Screen Brightness Controller for Dynamic Island on Linux / GNOME.
Supports:
- Hardware backlight via brightnessctl or /sys/class/backlight (laptops)
- Software display brightness via xrandr (external HDMI/DP monitors, virtual displays)
- Universal click-through Software Dimmer Overlay for desktop monitors on Wayland/XWayland
- GNOME Night Light (Ánh sáng đêm) toggle
- Non-blocking asynchronous slider throttling for smooth 60fps interaction
"""

import os
import re
import time
import shutil
import threading
import subprocess
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.config import config

class ScreenDimmerOverlay(Gtk.Window):
    """
    Transparent click-through screen dimmer overlay for external monitors (HDMI/DP/DVI)
    or Wayland/XWayland environments where hardware backlight control is unavailable.
    """
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Screen Dimmer Overlay")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.stick()
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)

        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
        self.set_app_paintable(True)

        self.alpha = 0.0
        self._dimmer_active = False

        self.connect("draw", self._on_draw)
        self.connect("realize", self._on_realize)

        self._update_geometry()

    def _update_geometry(self):
        display = Gdk.Display.get_default()
        if not display:
            return
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor:
            geo = monitor.get_geometry()
            self.set_default_size(geo.width, geo.height)
            self.resize(geo.width, geo.height)
            self.move(geo.x, geo.y)

    def _on_realize(self, widget):
        gdk_win = widget.get_window()
        if gdk_win:
            # 100% Click-through: Empty input shape region
            empty_region = cairo.Region()
            gdk_win.input_shape_combine_region(empty_region, 0, 0)

    def set_dim_level(self, pct):
        """
        pct: 10 to 100.
        100% = No dimming (alpha = 0.0) -> overlay is hidden.
        10% = Maximum dimming (alpha = 0.78).
        """
        if pct >= 99:
            self.alpha = 0.0
            if self._dimmer_active:
                self._dimmer_active = False
                self.hide()
            return

        dim_ratio = (100.0 - pct) / 90.0  # 0.0 to 1.0
        self.alpha = min(0.80, dim_ratio * 0.78)

        if not self._dimmer_active:
            self._dimmer_active = True
            self._update_geometry()
            self.show_all()
            gdk_win = self.get_window()
            if gdk_win:
                gdk_win.input_shape_combine_region(cairo.Region(), 0, 0)

        self.queue_draw()

    def _on_draw(self, widget, cr):
        if self.alpha <= 0.001:
            return False

        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0.0, 0.0, 0.0, self.alpha)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        return False


class BrightnessController:
    _instance = None
    _lock_singleton = threading.Lock()

    @classmethod
    def get_instance(cls, on_change=None):
        if cls._instance is None:
            with cls._lock_singleton:
                if cls._instance is None:
                    cls._instance = cls(on_change=on_change)
        elif on_change:
            cls._instance.add_listener(on_change)
        return cls._instance

    def __init__(self, on_change=None):
        # Enforce singleton pattern if constructor called directly
        if BrightnessController._instance is not None and getattr(self, '_initialized', False):
            if on_change:
                self.add_listener(on_change)
            return

        BrightnessController._instance = self
        self._initialized = True

        self._listeners = []
        if on_change:
            self._listeners.append(on_change)

        self.outputs = []
        self._has_brightnessctl = shutil.which("brightnessctl") is not None
        self._has_sys_backlight = (
            os.path.exists("/sys/class/backlight") and
            len(os.listdir("/sys/class/backlight")) > 0
        )
        self._pending_brightness = None
        self._worker_running = True
        self._worker_thread = None
        self._lock = threading.Lock()

        # Software Dimmer Overlay for desktop HDMI/DP monitors
        self.dimmer = None
        try:
            self.dimmer = ScreenDimmerOverlay()
        except Exception as e:
            print(f"[Brightness] Notice initializing dimmer overlay: {e}")

        # 1. Detect and restore saved brightness across reboots
        self.brightness = self._detect_initial_brightness()
        self._detect_xrandr_outputs()

        # 2. Apply initial brightness immediately on startup
        self._apply_initial_brightness()

        # 3. Background worker for throttled async setting
        self._worker_thread = threading.Thread(target=self._apply_loop, daemon=True)
        self._worker_thread.start()

        # 4. Delayed re-application (1.5s and 3.5s) to ensure late-starting Xwayland/monitors adopt saved brightness
        GLib.timeout_add(1500, self._delayed_reapply)
        GLib.timeout_add(3500, self._delayed_reapply)

    def add_listener(self, callback):
        if callback and callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, pct):
        for cb in list(self._listeners):
            try:
                cb(pct)
            except Exception as e:
                print(f"[Brightness] Listener notice: {e}")

    def _read_hardware_backlight(self):
        if not self._has_sys_backlight:
            return None
        if self._has_brightnessctl:
            try:
                cur = subprocess.run(["brightnessctl", "get"], capture_output=True, text=True, timeout=0.5)
                mx = subprocess.run(["brightnessctl", "max"], capture_output=True, text=True, timeout=0.5)
                if cur.returncode == 0 and mx.returncode == 0:
                    c = float(cur.stdout.strip())
                    m = float(mx.stdout.strip())
                    if m > 0:
                        return max(10, min(100, int((c / m) * 100)))
            except Exception:
                pass
        try:
            base = "/sys/class/backlight"
            if os.path.exists(base):
                for dev in os.listdir(base):
                    dev_path = os.path.join(base, dev)
                    b_file = os.path.join(dev_path, "brightness")
                    mb_file = os.path.join(dev_path, "max_brightness")
                    if os.path.exists(b_file) and os.path.exists(mb_file):
                        with open(b_file, "r") as f:
                            c = float(f.read().strip())
                        with open(mb_file, "r") as f:
                            m = float(f.read().strip())
                        if m > 0:
                            return max(10, min(100, int((c / m) * 100)))
        except Exception:
            pass
        return None

    def _detect_initial_brightness(self):
        """
        Determine initial brightness level upon boot or startup.
        Prioritizes:
        1. User's saved preference in config.json ("screen_brightness") - ensures settings persist across reboot!
        2. Hardware laptop backlight reading if available
        3. 100% as safe default
        Clamped to [10, 100] (never 0%).
        """
        # 1. User saved preference in config
        saved = config.get("screen_brightness")
        if saved is not None:
            try:
                val = int(saved)
                if 10 <= val <= 100:
                    return val
            except (ValueError, TypeError):
                pass

        # 2. Hardware backlight (laptops)
        hw = self._read_hardware_backlight()
        if hw is not None and 10 <= hw <= 100:
            return hw

        # 3. Fallback safe default
        return 100

    def _apply_initial_brightness(self):
        """Apply the restored brightness on startup to dimmer overlay and system outputs."""
        pct = self.brightness

        # Apply software dimmer overlay if needed
        if self.dimmer and not self._has_sys_backlight:
            GLib.idle_add(self.dimmer.set_dim_level, pct)

        # Apply to hardware / xrandr asynchronously
        threading.Thread(target=self._execute_set, args=(pct,), daemon=True).start()

    def _delayed_reapply(self):
        """Re-apply saved brightness to ensure late-starting Xwayland/monitors adopt it."""
        try:
            self._detect_xrandr_outputs()
            if self.dimmer and not self._has_sys_backlight:
                self.dimmer.set_dim_level(self.brightness)
            self._execute_set(self.brightness)
        except Exception as e:
            print(f"[Brightness] Re-apply notice: {e}")
        return False

    def _detect_xrandr_outputs(self):
        try:
            env = dict(os.environ)
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0"
            res = subprocess.run(["xrandr"], capture_output=True, text=True, timeout=1.0, env=env)
            outs = []
            for line in res.stdout.splitlines():
                if " connected" in line:
                    parts = line.split()
                    if parts:
                        outs.append(parts[0])
            self.outputs = outs
        except Exception:
            self.outputs = []

    def get_brightness(self):
        return self.brightness

    def set_brightness(self, pct):
        """Request brightness change (10-100%). Clamped to 10% min to avoid black screen."""
        pct = max(10, min(100, int(pct)))
        self.brightness = pct

        # Instantly update software dimmer overlay on GTK main thread for zero latency
        if self.dimmer and not self._has_sys_backlight:
            GLib.idle_add(self.dimmer.set_dim_level, pct)

        with self._lock:
            self._pending_brightness = pct

        config.set("screen_brightness", pct)
        self._notify_listeners(pct)

    def _apply_loop(self):
        """Worker thread to debounce and execute brightness adjustments."""
        last_applied = -1
        while self._worker_running:
            target = None
            with self._lock:
                if self._pending_brightness is not None and self._pending_brightness != last_applied:
                    target = self._pending_brightness
                    self._pending_brightness = None

            if target is not None:
                self._execute_set(target)
                last_applied = target

            time.sleep(0.04)  # ~25Hz throttle for silky smooth slider performance

    def _execute_set(self, pct):
        # 1. Try brightnessctl if available
        if self._has_brightnessctl:
            try:
                subprocess.run(["brightnessctl", "set", f"{pct}%"], capture_output=True, timeout=0.8)
            except Exception:
                pass

        # 2. Refresh outputs if empty
        if not self.outputs:
            self._detect_xrandr_outputs()

        # 3. Apply via xrandr for connected outputs
        if self.outputs:
            val = 0.15 + 0.85 * (pct / 100.0)
            val_str = f"{val:.2f}"
            env = dict(os.environ)
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0"
            for out in self.outputs:
                try:
                    subprocess.run(
                        ["xrandr", "--output", out, "--brightness", val_str],
                        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=0.8, env=env
                    )
                except Exception:
                    pass

    def is_night_light_enabled(self):
        try:
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.settings-daemon.plugins.color", "night-light-enabled"],
                capture_output=True, text=True, timeout=0.5
            )
            return "true" in res.stdout.lower()
        except Exception:
            return False

    def toggle_night_light(self):
        current = self.is_night_light_enabled()
        target = "false" if current else "true"
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.settings-daemon.plugins.color", "night-light-enabled", target],
                check=False, timeout=0.5
            )
            return not current
        except Exception:
            return current

    def stop(self):
        self._worker_running = False
        if self.dimmer:
            GLib.idle_add(self.dimmer.destroy)
            self.dimmer = None
