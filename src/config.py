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
    "enable_brightness_popup": True, # Auto-pop when screen brightness changes
    "screen_brightness": 100,        # Default screen brightness percentage
    "enable_track_popup": True,      # Auto-pop when song changes
    "enable_notification_popup": True, # Auto-pop when system desktop notification arrives
    "enable_cosmic_orbit": False,    # Cosmic Orbit App Launcher (disabled by default)
    "enable_desktop_clock": False,   # Apple macOS Analog Clock Desktop Widget
    "desktop_clock_x": 1680,         # X position on desktop (Top-right)
    "desktop_clock_y": 24,           # Y position on desktop
    "desktop_clock_size": 180,       # Size of clock widget in pixels
    "desktop_clock_smooth_sec": True, # Smooth fluid sweep for second hand
    "desktop_clock_dark_mode": True,  # Translucent dark frosted glass face
    "enable_desktop_music": True,    # Apple Music Desktop Widget
    "desktop_music_x": 380,          # X position for music widget (Right of photos)
    "desktop_music_y": 290,          # Y position for music widget
    "desktop_music_scale": 1.0,      # Scale factor for music widget (0.65 to 1.85)
    "desktop_music_theme": "dark",   # Dark translucent frosted glass
    "desktop_music_layout": "photo_vertical", # photo_vertical (iOS / reference photo card) or classic
    "desktop_weekday_bg": "transparent", # transparent vs frosted glass card
    "desktop_weekday_show_sec": False,   # Clean - HH:MM - format matching reference photo
    "desktop_weekday_x": 580,        # Centered weekday clock
    "desktop_weekday_y": 177,
    "lock_desktop_widgets": True,    # Lock widgets in place (disable accidental dragging)
    "enable_desktop_calendar": True, # Apple Calendar & Vietnamese Lunar Widget
    "desktop_calendar_x": 30,        # Top-left row
    "desktop_calendar_y": 70,
    "desktop_calendar_dark": True,
    "enable_desktop_weather": True,  # Apple Weather Widget
    "desktop_weather_x": 380,        # Next to calendar
    "desktop_weather_y": 70,
    "weather_city": "",
    "enable_desktop_battery": False, # Apple 4-Ring Battery Widget
    "desktop_battery_x": 30,
    "desktop_battery_y": 600,
    "enable_desktop_photo": True,    # Apple Desktop Photo Frame Widget
    "desktop_photo_x": 30,           # Below calendar
    "desktop_photo_y": 290,
    "desktop_photo_scale": 1.0,      # Scale factor for photo widget (0.65 to 1.85)
    "desktop_photo_strip_path": "assets/photos/photo_strip_duo.png",
    "desktop_photo_path_1": "assets/photos/photo_girl_top.png",
    "desktop_photo_path_2": "assets/photos/photo_girl_bottom.png",
    "enable_desktop_macbook": True,   # Apple MacBook & Power Profile Battery Widget
    "desktop_macbook_x": 30,          # Below photos / left column
    "desktop_macbook_y": 600,         # Y position for MacBook widget
    "desktop_macbook_scale": 1.0,     # Scale factor for MacBook widget
    "desktop_macbook_name": "MacBook Pro", # Display device name
    "desktop_macbook_chassis": "space_gray", # Chassis finish (space_gray, silver, midnight, starlight)
    "desktop_macbook_wallpaper": "sonoma",   # Screen wallpaper (sonoma, sequoia, aurora, cyber, minimal)
    "device_name": "",               # Custom device display name (empty = use system hostname)
    "language": "vi",                # Active display language (vi, en, fr, ja, etc.)
    "preferred_languages": ["vi", "en"], # Preferred languages list
    "menu_bar_show_app_name": False, # Hide active app name on menu bar for clean macOS look
}

class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
        except Exception:
            pass

    def save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            tmp_file = CONFIG_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            os.replace(tmp_file, CONFIG_FILE)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

config = Config()
