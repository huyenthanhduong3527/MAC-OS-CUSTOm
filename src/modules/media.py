"""
Universal Audio & Media Manager for Dynamic Island.
Detects ANY audio playing on the system via PipeWire / WirePlumber streams (SoundCloud,
browser tabs, Spotify, games, VLC, videos, etc.) and integrates with MPRIS2 D-Bus.
Features a high-efficiency background thread to monitor playback with zero UI latency.
"""

import time
import subprocess
import os
import json
import re
import threading
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk
from src.utils.artwork import fetch_online_artwork_async, load_artwork_pixbuf, invalidate_artwork_cache

DEMO_PLAYLIST = [
    {
        "title": "Die With A Smile",
        "artist": "Lady Gaga & Bruno Mars",
        "album": "Single",
        "length": 251,
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

GENERIC_TITLES = {
    "audiostream", "playback", "audiocallbackdriver", "pulseaudio",
    "output", "stream", "alsa playback", "bell", "system sound"
}

def clean_media_title(raw_title, app_name):
    """Clean and extract artist/title from raw stream names or web audio titles."""
    if not raw_title:
        return f"{app_name} Audio", app_name

    import unicodedata
    raw_title = unicodedata.normalize('NFC', raw_title)
    raw_title = re.sub(r'^\s*[\(\[]cut[\)\]]\s*', '', raw_title, flags=re.I)

    title = raw_title.strip()
    if title.lower() in GENERIC_TITLES:
        return f"{app_name} Audio", app_name

    # Remove file extension if playing local files e.g. .mp3, .flac, .wav
    title = re.sub(r'\.(mp3|flac|wav|m4a|ogg|opus|aac|webm)$', '', title, flags=re.IGNORECASE).strip()

    # Split SoundCloud-style: "Song Title by Artist"
    if " by " in title:
        parts = title.rsplit(" by ", 1)
        t = parts[0].strip()
        a = parts[1].strip()
        # Clean common tags
        for tag in ["FREE DOWNLOAD", "[FREE DOWNLOAD]", "(FREE DOWNLOAD)", "Free Download", "Official Audio", "(Official Video)"]:
            t = t.replace(tag, "").strip()
        t = re.sub(r'[\(\[\{]\s*[\)\]\}]', '', t).strip()
        return t or title, f"{a} • {app_name}"

    # Split "Artist - Title" or "Title - Artist"
    if " - " in title:
        parts = title.split(" - ", 1)
        return parts[0].strip(), f"{parts[1].strip()} • {app_name}"

    return title, app_name


def match_stream_to_mpris(active_stream, mpris_list):
    """Accurately link a PipeWire audio stream to an MPRIS player instance."""
    if not active_stream or not mpris_list:
        return None

    app_lower = (active_stream.get('app') or '').lower()
    bin_lower = (active_stream.get('binary') or '').lower()

    BROWSER_KEYS = ('chrome', 'chromium', 'google-chrome', 'google chrome', 'brave', 'firefox', 'opera', 'vivaldi', 'edge', 'msedge')
    is_stream_browser = any(k in app_lower or k in bin_lower for k in BROWSER_KEYS)

    # 1. First pass: exact match by binary, app name, or browser class
    for p in mpris_list:
        p_name = (p.get('name') or '').lower()
        p_bin = (p.get('binary') or '').lower()
        p_bus = (p.get('bus_name') or '').lower()

        if bin_lower and (bin_lower == p_bin or bin_lower in p_bus):
            return p
        if app_lower and (app_lower in p_name or p_name in app_lower or app_lower in p_bus):
            return p
        if is_stream_browser and any(k in p_name or k in p_bin or k in p_bus for k in BROWSER_KEYS):
            return p

    # 2. Fallback: If only one MPRIS player has a valid title, link it
    valid_players = [p for p in mpris_list if p.get('title') and p.get('title') not in ('Unknown Title', 'No Media Playing')]
    if len(valid_players) == 1:
        return valid_players[0]

    return None


class MediaManager:
    def __init__(self, on_track_change=None):
        self.on_track_change = on_track_change
        self.player_name = "System Audio"
        self.app_binary = ""
        self.title = "No Media Playing"
        self.artist = "Play any music or audio"
        self.album = ""
        self.art_url = None
        self.status = "Stopped" # "Playing", "Paused", "Stopped"
        self.position = 0
        self.duration = 0
        self.is_demo = False
        self.is_stream_audio = False
        self.stream_id = None
        self.shuffle = False
        self.loop_status = "None"

        # Demo state
        self._demo_index = 0
        self._demo_playing = False
        self._demo_last_tick = time.time()

        self._bus = None
        try:
            DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SessionBus()
            self._bus.add_signal_receiver(
                self._on_dbus_property_changed,
                signal_name="PropertiesChanged",
                dbus_interface="org.freedesktop.DBus.Properties",
                path="/org/mpris/MediaPlayer2"
            )
        except Exception as e:
            print(f"[Media] DBus session bus error: {e}")

        self._lock = threading.Lock()
        self._running = True

        # Start background polling thread for real-time audio detection (fast 0.35s responsiveness)
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _on_dbus_property_changed(self, interface, changed_props, invalidated_props):
        """Zero-latency MPRIS track/status change handler via D-Bus signal."""
        if interface == "org.mpris.MediaPlayer2.Player" or "PlaybackStatus" in changed_props or "Metadata" in changed_props:
            GLib.idle_add(self._trigger_immediate_poll)

    def _trigger_immediate_poll(self):
        threading.Thread(target=self._poll_status, daemon=True).start()

    def is_playing(self):
        # Non-blocking atomic read: never blocks the GTK UI tick
        return self.status == "Playing"

    def refresh(self):
        """Called by UI tick to sync any state changes."""
        # Non-blocking: background thread keeps data updated
        pass

    def get_app_icon(self, size=18):
        """Fetch themed application icon for the currently playing source."""
        theme = Gtk.IconTheme.get_default()
        candidates = []
        if self.app_binary:
            candidates.append(self.app_binary.lower())
        if self.player_name:
            candidates.append(self.player_name.lower())
            candidates.append(self.player_name.lower().replace(" ", "-"))

        for c in candidates:
            if c and theme.has_icon(c):
                try:
                    return theme.load_icon(c, size, 0)
                except Exception:
                    pass
        return None

    def _monitor_loop(self):
        """Background thread that queries PipeWire streams and MPRIS every 0.35s."""
        while self._running:
            try:
                self._poll_status()
            except Exception as e:
                pass
            time.sleep(0.35)

    def _poll_status(self):
        active_stream = self._get_active_pipewire_stream()
        mpris_playing, mpris_paused = self._query_mpris_players()

        old_title = self.title
        old_status = self.status
        need_art_fetch = False
        fetch_t = ""
        fetch_a = ""

        with self._lock:
            all_mpris = []
            if mpris_playing:
                all_mpris.append(mpris_playing)
            all_mpris.extend(mpris_paused)

            # CASE 1: Active MPRIS player is explicitly "Playing" (e.g. Spotify, YouTube with MPRIS)
            if mpris_playing:
                self._apply_mpris(mpris_playing)

            # CASE 2: Active PipeWire stream is actively outputting sound (SoundCloud, browser, videos, games)
            elif active_stream:
                matching_mpris = match_stream_to_mpris(active_stream, all_mpris)
                # If matching MPRIS player is explicitly paused, respect Paused status and do NOT force Playing!
                if matching_mpris and matching_mpris.get('status') == 'Paused':
                    self._apply_mpris(matching_mpris)
                    self.status = "Paused"
                else:
                    self.is_demo = False
                    self.is_stream_audio = True
                    self.status = "Playing"
                    self.player_name = active_stream['app']
                    self.app_binary = active_stream.get('binary', '')
                    self.stream_id = active_stream.get('id')

                    # If matching MPRIS has a track title, prioritize it over raw generic PipeWire stream names
                    if matching_mpris and matching_mpris.get('title') and matching_mpris.get('title') not in ("Unknown Title", "No Media Playing"):
                        self._apply_mpris(matching_mpris)
                        self.status = "Playing"
                    else:
                        raw_title = active_stream.get('title', '')
                        t, a = clean_media_title(raw_title, active_stream['app'])

                        if raw_title and raw_title.lower() not in GENERIC_TITLES:
                            if self.title != t or self.artist != a:
                                self.title = t
                                self.artist = a
                                self.art_url = None
                                self._art_is_low_res = True
                                need_art_fetch = True
                                fetch_t = self.title
                                fetch_a = self.artist
                            self.album = ""
                            self.duration = 0
                            self.position += 1 # Live playback ticker
                        else:
                            if not self.title or self.title in ("No Media Playing", "Unknown Title", f"{active_stream['app']} Audio"):
                                self.title = t
                                self.artist = a
                                self.art_url = None
                                self._art_is_low_res = True
                            self.position += 1

            # CASE 3: No active audio stream, but an MPRIS player was paused recently
            elif mpris_paused:
                self._apply_mpris(mpris_paused[0])
                self.status = "Paused"

            # CASE 4: Nothing playing anywhere
            else:
                if self.is_demo and self._demo_playing:
                    self._update_demo()
                else:
                    self.status = "Stopped"
                    self.title = "No Media Playing"
                    self.artist = "Play any music or audio"
                    self.album = ""
                    self.art_url = None
                    self.position = 0
                    self.duration = 0
                    self.is_stream_audio = False

        if need_art_fetch and fetch_t:
            target_t = fetch_t
            fetch_online_artwork_async(fetch_t, fetch_a, lambda url, t=target_t: self._on_online_art_found(url, t))

        if (self.title != old_title or self.status != old_status) and self.status in ("Playing", "Paused") and self.on_track_change:
            GLib.idle_add(self.on_track_change, self.title, self.artist)

    def _is_low_res_art(self, art_url):
        """Check if artwork URL points to a low-res thumbnail (e.g. Chrome's 150x83 tmp image)."""
        if not art_url:
            return True
        if any(b in art_url for b in ["tmp/.com.google.Chrome", "tmp/.org.chromium", "tmp/.com.brave", "tmp/.com.vivaldi", "tmp/.com.microsoft"]):
            return True
        if "default.jpg" in art_url and "maxresdefault.jpg" not in art_url and "sddefault.jpg" not in art_url:
            return True
        import urllib.parse
        path = art_url[7:] if art_url.startswith("file://") else art_url
        path = urllib.parse.unquote(path)
        if os.path.exists(path):
            try:
                from gi.repository import GdkPixbuf
                info, w, h = GdkPixbuf.Pixbuf.get_file_info(path)
                if w < 300 or h < 300:
                    return True
            except Exception:
                pass
        return False

    def _apply_mpris(self, p):
        self.is_demo = False
        self.is_stream_audio = False

        old_title = self.title
        old_artist = self.artist
        new_title = p.get('title') or "Unknown Title"
        new_artist = p.get('artist') or "Unknown Artist"
        new_art_url = p.get('art_url')
        new_status = p.get('status', 'Playing')

        track_changed = (new_title != old_title) or (new_artist != old_artist)

        self.status = new_status
        self.player_name = p.get('name', 'Media Player')
        self.app_binary = p.get('binary', p.get('name', '').lower())
        self.title = new_title
        self.artist = new_artist

        is_low_res = False
        if track_changed:
            # Clear old artwork immediately so old cover doesn't stick
            self.art_url = None
            self._art_is_low_res = True

        if new_art_url:
            new_is_low = self._is_low_res_art(new_art_url)
            # Only update self.art_url if we don't already have a valid high-res image for this song
            if not self.art_url or getattr(self, "_art_is_low_res", True):
                self.art_url = new_art_url
                self._art_is_low_res = new_is_low
            elif not new_is_low:
                # new_art_url is itself high-res, accept it
                self.art_url = new_art_url
                self._art_is_low_res = False
            is_low_res = getattr(self, "_art_is_low_res", False)
        elif not self.art_url:
            is_low_res = True
            self._art_is_low_res = True
        else:
            is_low_res = getattr(self, "_art_is_low_res", False)

        self.duration = p.get('duration', 0)
        self.position = p.get('position', 0)
        self._mpris_bus_name = p.get('bus_name')
        if p.get('shuffle') is not None:
            self.shuffle = p['shuffle']
        if p.get('loop') is not None:
            self.loop_status = p['loop']

        # If MPRIS player didn't provide an art URL OR provided a low-res thumbnail, fetch high-res art
        if (not self.art_url or is_low_res) and self.title and self.title not in ("Unknown Title", "No Media Playing"):
            target_title = self.title
            fetch_online_artwork_async(self.title, self.artist, lambda url, t=target_title: self._on_online_art_found(url, t))

    def _on_online_art_found(self, art_url, for_title=None):
        if not art_url:
            return
        with self._lock:
            # Ensure the fetched artwork matches current song
            if for_title and self.title != for_title:
                return
            if self.status in ("Playing", "Paused"):
                self.art_url = art_url
                self._art_is_low_res = False
        # Pre-cache pixbufs for all common display sizes so they are instantly ready
        load_artwork_pixbuf(art_url, size=400, radius=24, on_ready_callback=None)
        load_artwork_pixbuf(art_url, size=256, radius=18, on_ready_callback=None)
        load_artwork_pixbuf(art_url, size=128, radius=14, on_ready_callback=None)
        load_artwork_pixbuf(art_url, size=48, radius=10, on_ready_callback=None)
        load_artwork_pixbuf(art_url, size=18, radius=5, on_ready_callback=None)
        if self.on_track_change:
            GLib.idle_add(self.on_track_change, self.title, self.artist)

    def _get_active_pipewire_stream(self):
        """Query PipeWire nodes for any running audio output stream."""
        # Method 1: pw-dump Node (fastest & most detailed)
        try:
            out = subprocess.check_output(['pw-dump', 'Node'], text=True, timeout=0.8)
            data = json.loads(out)
            for obj in data:
                info = obj.get('info', {})
                props = info.get('props', {})
                if props.get('media.class') == 'Stream/Output/Audio':
                    state = info.get('state', '')
                    corked = props.get('pulse.corked', False)
                    if state == 'running' and not corked:
                        app = props.get('application.name') or props.get('node.name') or 'Audio'
                        if 'speech-dispatcher' in app.lower():
                            continue
                        title = props.get('media.name') or ''
                        binary = props.get('application.process.binary') or ''
                        return {
                            'id': obj.get('id'),
                            'app': app,
                            'title': title,
                            'binary': binary
                        }
        except Exception:
            pass

        # Method 2: wpctl status fallback
        try:
            out = subprocess.check_output(['wpctl', 'status'], text=True, timeout=0.8)
            streams_idx = out.find('Streams:')
            if streams_idx != -1:
                streams_section = out[streams_idx:]
                lines = streams_section.split('\n')
                current_app = None
                for line in lines:
                    m_app = re.search(r'^\s*(\d+)\.\s+([^\s].+)', line)
                    if m_app:
                        current_app = m_app.group(2).strip()
                    if '[active]' in line and current_app:
                        if 'speech-dispatcher' in current_app.lower():
                            continue
                        return {
                            'id': None,
                            'app': current_app,
                            'title': f'{current_app} Audio',
                            'binary': current_app.lower()
                        }
        except Exception:
            pass

        return None

    def _query_mpris_players(self):
        """Query MPRIS players on DBus with fast non-blocking timeouts."""
        if not self._bus:
            return None, []

        playing = []
        paused = []
        try:
            names = [s for s in self._bus.list_names() if s.startswith("org.mpris.MediaPlayer2.")]
            for n in names:
                try:
                    obj = self._bus.get_object(n, "/org/mpris/MediaPlayer2")
                    props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                    status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus", timeout=0.06))

                    if status not in ("Playing", "Paused"):
                        continue

                    metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata", timeout=0.06)

                    raw_name = n.replace("org.mpris.MediaPlayer2.", "")
                    app_name = raw_name.split(".")[0].capitalize()

                    title = str(metadata.get("xesam:title", ""))
                    artists = metadata.get("xesam:artist", [])
                    if isinstance(artists, (list, tuple, dbus.Array)):
                        artist = ", ".join([str(a) for a in artists])
                    else:
                        artist = str(artists)

                    length_us = metadata.get("mpris:length", 0)
                    dur = int(length_us / 1_000_000) if length_us else 0

                    pos = 0
                    try:
                        pos_us = props.Get("org.mpris.MediaPlayer2.Player", "Position", timeout=0.05)
                        pos = int(pos_us / 1_000_000)
                    except Exception:
                        pass

                    shuf = None
                    try:
                        shuf = bool(props.Get("org.mpris.MediaPlayer2.Player", "Shuffle", timeout=0.04))
                    except Exception:
                        pass

                    loop = None
                    try:
                        loop = str(props.Get("org.mpris.MediaPlayer2.Player", "LoopStatus", timeout=0.04))
                    except Exception:
                        pass

                    info = {
                        "bus_name": str(n),
                        "name": app_name,
                        "binary": raw_name.split(".")[0].lower(),
                        "status": status,
                        "title": title,
                        "artist": artist,
                        "album": str(metadata.get("xesam:album", "")),
                        "art_url": str(metadata.get("mpris:artUrl", "")),
                        "duration": dur,
                        "position": pos,
                        "shuffle": shuf,
                        "loop": loop
                    }

                    if status == "Playing":
                        playing.append(info)
                    elif status == "Paused":
                        paused.append(info)
                except Exception:
                    pass
        except Exception:
            pass

        first_playing = playing[0] if playing else None
        return first_playing, paused

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

        # 1. Try MPRIS if active player has an MPRIS bus name
        bus_name = getattr(self, '_mpris_bus_name', None)
        if not bus_name and self._bus:
            # Search for any MPRIS player matching current player name
            names = [s for s in self._bus.list_names() if s.startswith("org.mpris.MediaPlayer2.")]
            for n in names:
                if self.player_name.lower() in n.lower() or self.app_binary in n.lower():
                    bus_name = n
                    break

        if self._bus and bus_name:
            try:
                obj = self._bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                player.PlayPause()
                time.sleep(0.05)
                self._poll_status()
                return
            except Exception as e:
                pass

        # 2. Toggle mute on default audio sink if it's a generic stream without MPRIS
        try:
            subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], check=False)
        except Exception:
            pass

    def next_track(self):
        if self.is_demo:
            self._demo_index = (self._demo_index + 1) % len(DEMO_PLAYLIST)
            self.position = 0
            self._update_demo()
            if self.on_track_change:
                self.on_track_change(self.title, self.artist)
            return

        bus_name = getattr(self, '_mpris_bus_name', None)
        if self._bus and bus_name:
            try:
                obj = self._bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                player.Next()
                time.sleep(0.05)
                self._poll_status()
            except Exception:
                pass

    def prev_track(self):
        if self.is_demo:
            self._demo_index = (self._demo_index - 1) % len(DEMO_PLAYLIST)
            self.position = 0
            self._update_demo()
            if self.on_track_change:
                self.on_track_change(self.title, self.artist)
            return

        bus_name = getattr(self, '_mpris_bus_name', None)
        if self._bus and bus_name:
            try:
                obj = self._bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                player.Previous()
                time.sleep(0.05)
                self._poll_status()
            except Exception:
                pass

    def seek(self, position_seconds):
        if self.is_demo:
            self.position = max(0, min(int(position_seconds), self.duration))
            return

        bus_name = getattr(self, '_mpris_bus_name', None)
        if self._bus and bus_name:
            try:
                obj = self._bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                # Try SetPosition if trackid is available, else SetPosition with /
                track_id = getattr(self, '_mpris_trackid', "/org/mpris/MediaPlayer2/CurrentTrack")
                player.SetPosition(track_id, dbus.Int64(int(position_seconds * 1_000_000)))
                self.position = int(position_seconds)
            except Exception:
                try:
                    # Alternative: relative seek
                    offset = int((position_seconds - self.position) * 1_000_000)
                    player.Seek(dbus.Int64(offset))
                    self.position = int(position_seconds)
                except Exception:
                    pass

    def toggle_shuffle(self):
        """Toggles shuffle mode on active player or local state."""
        self.shuffle = not getattr(self, "shuffle", False)
        bus_name = getattr(self, '_mpris_bus_name', None)
        if self._bus and bus_name:
            try:
                obj = self._bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                props.Set("org.mpris.MediaPlayer2.Player", "Shuffle", dbus.Boolean(self.shuffle))
            except Exception:
                pass
        try:
            cmd_arg = "On" if self.shuffle else "Off"
            subprocess.run(["playerctl", "shuffle", cmd_arg], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5)
        except Exception:
            pass
        return self.shuffle

    def toggle_repeat(self):
        """Cycles loop status: None -> Playlist -> Track -> None."""
        curr = getattr(self, "loop_status", "None")
        if curr == "None":
            self.loop_status = "Playlist"
        elif curr == "Playlist":
            self.loop_status = "Track"
        else:
            self.loop_status = "None"

        bus_name = getattr(self, '_mpris_bus_name', None)
        if self._bus and bus_name:
            try:
                obj = self._bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                props.Set("org.mpris.MediaPlayer2.Player", "LoopStatus", dbus.String(self.loop_status))
            except Exception:
                pass
        try:
            subprocess.run(["playerctl", "loop", self.loop_status], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5)
        except Exception:
            pass
        return self.loop_status

    def stop(self):
        self._running = False
