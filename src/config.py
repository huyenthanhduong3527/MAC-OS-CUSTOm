"""
Configuration manager for Dynamic Island.
Handles loading and saving user preferences to ~/.config/dynamic_island/config.json.
"""

import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/dynamic_island")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "y_offset": 44,                 # Distance from the top of the screen in pixels (below GNOME top bar)
    "compact_width": 230,            # Width of the idle pill
    "compact_height": 40,            # Height of the idle pill
    "expanded_width": 430,           # Width of the expanded card
    "expanded_height": 220,          # Height of the expanded card
    "animation_speed": 1.0,          # Speed multiplier (1.0 = normal 60fps spring)
    "auto_collapse_seconds": 6,      # Auto collapse back to compact after N seconds of inactivity (0 = never)
    "expand_on_hover": False,        # If True, hovering expands the island; if False, click to toggle
    "accent_color": "#0ea5e9",       # Accent color for bars and highlights (Cyan)
    "clock_24h": True,               # 24-hour format
    "demo_mode": False,              # Use demo media player if no MPRIS player is active
    "enable_volume_popup": True,     # Auto-pop when system volume changes
    "enable_track_popup": True,      # Auto-pop when song changes
    "enable_notification_popup": True, # Auto-pop when system desktop notification arrives
    "enable_cosmic_orbit": False,    # Cosmic Orbit App Launcher (disabled by default)
}

class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
        except Exception as e:
            print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

config = Config()
