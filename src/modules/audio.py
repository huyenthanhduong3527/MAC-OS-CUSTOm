"""
Audio controller & monitor using WirePlumber (wpctl) / PipeWire.
Monitors volume changes in real-time and supports volume slider and mute controls.
"""

import subprocess
import threading
import time
import re
from gi.repository import GLib

class AudioController:
    def __init__(self, on_volume_change=None):
        self.volume = 1.0
        self.is_muted = False
        self.on_volume_change = on_volume_change
        self._running = True
        self._last_reported_vol = None
        self._last_reported_mute = None

        self.update_status()

        # Background thread to monitor volume changes for dynamic popups
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def update_status(self):
        """Query current volume and mute state via wpctl."""
        try:
            res = subprocess.run(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=0.4
            )
            if res.returncode == 0:
                output = res.stdout.strip()
                # Format: "Volume: 0.75" or "Volume: 0.75 [MUTED]"
                m = re.search(r"Volume:\s+([0-9.]+)", output)
                if m:
                    self.volume = min(1.5, max(0.0, float(m.group(1))))
                self.is_muted = "[MUTED]" in output
        except Exception:
            # Fallback
            pass

    def set_volume(self, value):
        """Set volume to float value between 0.0 and 1.0 (or up to 1.5)."""
        value = max(0.0, min(1.5, float(value)))
        self.volume = value
        try:
            subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{value:.2f}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=0.4
            )
            self._last_reported_vol = self.volume
            if self.on_volume_change:
                GLib.idle_add(self.on_volume_change, self.volume, self.is_muted)
        except Exception as e:
            print(f"[Audio] Error setting volume: {e}")

    def toggle_mute(self):
        """Toggle mute state."""
        self.is_muted = not self.is_muted
        try:
            subprocess.run(
                ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=0.4
            )
            self._last_reported_mute = self.is_muted
            if self.on_volume_change:
                GLib.idle_add(self.on_volume_change, self.volume, self.is_muted)
        except Exception as e:
            print(f"[Audio] Error toggling mute: {e}")

    def _monitor_loop(self):
        """Polls volume status every 120ms to detect changes with zero UI lag."""
        while self._running:
            time.sleep(0.12)
            self.update_status()

            if self._last_reported_vol is None:
                self._last_reported_vol = self.volume
                self._last_reported_mute = self.is_muted
                continue

            # Detect external change
            if abs(self.volume - self._last_reported_vol) > 0.01 or self.is_muted != self._last_reported_mute:
                self._last_reported_vol = self.volume
                self._last_reported_mute = self.is_muted
                if self.on_volume_change:
                    GLib.idle_add(self.on_volume_change, self.volume, self.is_muted)

    def stop(self):
        self._running = False
