"""
macOS Sound Effects Engine for Dynamic Island.
Plays authentic Apple system sounds for:
- Screenshot shutter
- AirDrop file received chime
- Power charger connected / disconnected
- Trash empty / file delete
- Subtle haptic pop / tap

Non-blocking, executes audio triggers asynchronously in background worker threads.
"""

import os
import subprocess
import threading
from src.config import config

class SoundManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SoundManager()
        return cls._instance

    def __init__(self):
        self.sound_enabled = config.get("enable_system_sounds", True)

        # Detect available sound player CLI
        self._canberra = self._check_cli("canberra-gtk-play")
        self._pw_play = self._check_cli("pw-play")

        # Map sound events to system fallback files
        self._sound_fallbacks = {
            "screenshot": [
                "/usr/share/sounds/Yaru/stereo/camera-shutter.oga",
                "/usr/share/sounds/gnome/default/alerts/click.ogg",
                "/usr/share/sounds/freedesktop/stereo/camera-shutter.oga"
            ],
            "airdrop": [
                "/usr/share/sounds/Yaru/stereo/complete.oga",
                "/usr/share/sounds/gnome/default/alerts/glass-bell.oga",
                "/usr/share/sounds/freedesktop/stereo/complete.oga"
            ],
            "power": [
                "/usr/share/sounds/Yaru/stereo/device-added.oga",
                "/usr/share/sounds/gnome/default/alerts/sonar.oga",
                "/usr/share/sounds/freedesktop/stereo/device-added.oga"
            ],
            "trash": [
                "/usr/share/sounds/Yaru/stereo/trash-empty.oga",
                "/usr/share/sounds/gnome/default/alerts/hum.ogg",
                "/usr/share/sounds/freedesktop/stereo/trash-empty.oga"
            ],
            "pop": [
                "/usr/share/sounds/gnome/default/alerts/click.ogg",
                "/usr/share/sounds/Yaru/stereo/bell.oga"
            ],
            "timer": [
                "/usr/share/sounds/Yaru/stereo/complete.oga",
                "/usr/share/sounds/freedesktop/stereo/complete.oga",
                "/usr/share/sounds/gnome/default/alerts/glass-bell.oga",
                "/usr/share/sounds/Yaru/stereo/bell.oga"
            ]
        }

    def _check_cli(self, name):
        try:
            res = subprocess.run(["which", name], capture_output=True, text=True)
            return res.returncode == 0
        except Exception:
            return False

    def play_sound(self, sound_type):
        """Play a system sound effect asynchronously."""
        if not config.get("enable_system_sounds", True):
            return

        threading.Thread(target=self._play_async, args=(sound_type,), daemon=True).start()

    def _play_async(self, sound_type):
        # 1. Try canberra-gtk-play with event ID
        event_ids = {
            "screenshot": "camera-shutter",
            "airdrop": "complete",
            "power": "device-added",
            "trash": "trash-empty",
            "pop": "button-pressed",
            "timer": "complete"
        }

        event_id = event_ids.get(sound_type)
        if self._canberra and event_id:
            try:
                res = subprocess.run(
                    ["canberra-gtk-play", "-i", event_id],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1.5
                )
                if res.returncode == 0:
                    return
            except Exception:
                pass

        # 2. Try playing fallback sound file via pw-play or canberra -f
        fallbacks = self._sound_fallbacks.get(sound_type, [])
        target_file = None
        for path in fallbacks:
            if os.path.exists(path):
                target_file = path
                break

        if target_file:
            if self._pw_play:
                try:
                    subprocess.run(
                        ["pw-play", target_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1.5
                    )
                    return
                except Exception:
                    pass
            elif self._canberra:
                try:
                    subprocess.run(
                        ["canberra-gtk-play", "-f", target_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1.5
                    )
                    return
                except Exception:
                    pass

    def play_screenshot(self):
        self.play_sound("screenshot")

    def play_airdrop(self):
        self.play_sound("airdrop")

    def play_power(self):
        self.play_sound("power")

    def play_trash(self):
        self.play_sound("trash")

    def play_pop(self):
        self.play_sound("pop")

    def play_timer(self):
        """Play the completion chime when a countdown reaches zero."""
        self.play_sound("timer")
