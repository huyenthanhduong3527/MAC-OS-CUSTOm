"""
MPRIS2 Media Player integration via D-Bus.
Monitors Spotify, Chrome, Firefox, VLC, Amberol, Rhythmbox, etc.
Includes built-in demo player fallback when no media is playing.
"""

import time
import dbus
from gi.repository import GLib

DEMO_PLAYLIST = [
    {
        "title": "Die With A Smile",
        "artist": "Lady Gaga & Bruno Mars",
        "album": "Single",
        "length": 251, # seconds
    },
    {
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "album": "After Hours",
        "length": 200,
    },
    {
        "title": "Nơi Này Có Anh",
        "artist": "Sơn Tùng M-TP",
        "album": "Single",
        "length": 260,
    },
    {
        "title": "Birds of a Feather",
        "artist": "Billie Eilish",
        "album": "HIT ME HARD AND SOFT",
        "length": 190,
    }
]

class MediaManager:
    def __init__(self, on_track_change=None):
        self.on_track_change = on_track_change
        self.player_name = None
        self.title = "No Media Playing"
        self.artist = "Open Spotify or YouTube"
        self.album = ""
        self.art_url = None
        self.status = "Stopped" # "Playing", "Paused", "Stopped"
        self.position = 0 # seconds
        self.duration = 0 # seconds
        self.is_demo = False

        # Demo state
        self._demo_index = 0
        self._demo_playing = False
        self._demo_last_tick = time.time()

        self._bus = None
        try:
            self._bus = dbus.SessionBus()
        except Exception as e:
            print(f"[Media] DBus session bus error: {e}")

        self.refresh()

    def refresh(self):
        """Query MPRIS DBus for active media players."""
        found_player = False
        if self._bus:
            try:
                names = [s for s in self._bus.list_names() if s.startswith("org.mpris.MediaPlayer2.")]
                if names:
                    # Prefer Spotify, Chrome, Firefox, Amberol, VLC
                    priority = ["spotify", "amberol", "rhythmbox", "vlc", "chrome", "firefox", "brave"]
                    selected = names[0]
                    for p in priority:
                        match = next((n for n in names if p in n.lower()), None)
                        if match:
                            selected = match
                            break

                    self.player_name = selected
                    obj = self._bus.get_object(selected, "/org/mpris/MediaPlayer2")
                    props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")

                    status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
                    metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")

                    old_title = self.title
                    self.title = str(metadata.get("xesam:title", "Unknown Title"))
                    artists = metadata.get("xesam:artist", ["Unknown Artist"])
                    if isinstance(artists, (list, tuple, dbus.Array)):
                        self.artist = ", ".join([str(a) for a in artists])
                    else:
                        self.artist = str(artists)

                    self.album = str(metadata.get("xesam:album", ""))
                    self.art_url = str(metadata.get("mpris:artUrl", ""))
                    self.status = status

                    # Length in microseconds
                    length_us = metadata.get("mpris:length", 0)
                    self.duration = int(length_us / 1_000_000) if length_us else 0

                    try:
                        pos_us = props.Get("org.mpris.MediaPlayer2.Player", "Position")
                        self.position = int(pos_us / 1_000_000)
                    except Exception:
                        self.position = 0

                    self.is_demo = False
                    found_player = True

                    if old_title != self.title and self.status == "Playing" and self.on_track_change:
                        self.on_track_change(self.title, self.artist)

            except Exception as e:
                found_player = False

        if not found_player:
            # Fallback to Demo Player state
            self._update_demo()

    def _update_demo(self):
        self.is_demo = True
        track = DEMO_PLAYLIST[self._demo_index]
        self.title = track["title"]
        self.artist = track["artist"]
        self.album = track["album"]
        self.duration = track["length"]
        self.art_url = track.get("art_url", "")
        self.status = "Playing" if self._demo_playing else "Paused"

        now = time.time()
        dt = now - self._demo_last_tick
        self._demo_last_tick = now

        if self._demo_playing:
            self.position += int(dt)
            if self.position >= self.duration:
                self.next_track()

    def play_pause(self):
        if self.is_demo:
            self._demo_playing = not self._demo_playing
            self.status = "Playing" if self._demo_playing else "Paused"
            return

        if self._bus and self.player_name:
            try:
                obj = self._bus.get_object(self.player_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                player.PlayPause()
                self.refresh()
            except Exception as e:
                print(f"[Media] PlayPause error: {e}")

    def next_track(self):
        if self.is_demo:
            self._demo_index = (self._demo_index + 1) % len(DEMO_PLAYLIST)
            self.position = 0
            self._update_demo()
            if self.on_track_change:
                self.on_track_change(self.title, self.artist)
            return

        if self._bus and self.player_name:
            try:
                obj = self._bus.get_object(self.player_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                player.Next()
                self.refresh()
            except Exception as e:
                print(f"[Media] Next error: {e}")

    def prev_track(self):
        if self.is_demo:
            self._demo_index = (self._demo_index - 1) % len(DEMO_PLAYLIST)
            self.position = 0
            self._update_demo()
            if self.on_track_change:
                self.on_track_change(self.title, self.artist)
            return

        if self._bus and self.player_name:
            try:
                obj = self._bus.get_object(self.player_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                player.Previous()
                self.refresh()
            except Exception as e:
                print(f"[Media] Prev error: {e}")

    def is_playing(self):
        return self.status == "Playing"
