"""
Album Art Manager & Loader for Dynamic Island.
Handles local file URLs (Firefox, VLC), remote HTTP/HTTPS URLs (Spotify),
online artwork retrieval for web/stream playback (SoundCloud, YouTube, Deezer, iTunes),
and generates sleek Apple-style rounded squircle pixbufs with disk caching.
"""

import os
import math
import hashlib
import json
import re
import threading
import urllib.parse
import urllib.request
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo

CACHE_DIR = os.path.expanduser("~/.cache/dynamic_island/art")
os.makedirs(CACHE_DIR, exist_ok=True)

_pixbuf_cache = {}
_downloading_urls = set()
_online_art_cache = {}
_searching_queries = set()

def get_rounded_pixbuf(src_pixbuf, size=48, radius=8):
    """Render a pixbuf into a smooth antialiased rounded rectangle with subtle inner border."""
    try:
        w = src_pixbuf.get_width()
        h = src_pixbuf.get_height()
        
        # Center crop to square before scaling
        crop_size = min(w, h)
        crop_x = (w - crop_size) // 2
        crop_y = (h - crop_size) // 2
        
        cropped = GdkPixbuf.Pixbuf.new_subpixbuf(src_pixbuf, crop_x, crop_y, crop_size, crop_size)
        scaled = cropped.scale_simple(size, size, GdkPixbuf.InterpType.HYPER)

        surface = cairo.ImageSurface(cairo.Format.ARGB32, size, size)
        cr = cairo.Context(surface)

        # Rounded rectangle clip path
        r = min(radius, size / 2.0)
        cr.new_sub_path()
        cr.arc(size - r, r, r, -math.pi / 2, 0)
        cr.arc(size - r, size - r, r, 0, math.pi / 2)
        cr.arc(r, size - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.clip()

        Gdk.cairo_set_source_pixbuf(cr, scaled, 0, 0)
        cr.paint()

        # Subtle specular rim
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.15)
        cr.set_line_width(1.0)
        cr.stroke()

        return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)
    except Exception as e:
        print(f"[Artwork] Error rounding pixbuf: {e}")
        return None

def is_valid_image_file(path):
    """
    Verify if a local file is a valid image, supporting standard file extensions
    as well as extensionless temporary files created by Chrome/Chromium (/tmp/.com.google.Chrome.*).
    """
    if not path or not os.path.exists(path) or os.path.isdir(path):
        return False
    # Explicitly reject desktop launcher files or text files that could cause gdk-pixbuf errors
    if path.lower().endswith(('.desktop', '.txt', '.json', '.xml', '.html', '.sh', '.py')):
        return False

    VALID_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.bmp', '.ico', '.tiff')
    if path.lower().endswith(VALID_EXTS):
        return True

    # For files without recognized extension (such as Chrome's /tmp/.com.google.Chrome.XXXXXX), check binary signature
    try:
        with open(path, 'rb') as f:
            header = f.read(32)
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                return True
            if header.startswith(b'\xff\xd8\xff'):
                return True
            if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                return True
            if header.startswith(b'BM'):
                return True
            if header.startswith(b'RIFF') and b'WEBP' in header:
                return True
            if b'<svg' in header or b'<?xml' in header:
                return True
    except Exception:
        pass
    return False

def load_artwork_pixbuf(art_url, size=48, radius=8, on_ready_callback=None):
    """
    Load album art from local file:// path, absolute path, or remote URL.
    Returns GdkPixbuf or None if not yet available.
    """
    if not art_url:
        return None

    # 1. Local file:// URL or local absolute path
    if art_url.startswith("file://") or art_url.startswith("/"):
        local_path = urllib.parse.unquote(art_url[7:]) if art_url.startswith("file://") else art_url
        if is_valid_image_file(local_path):
            try:
                mtime = os.path.getmtime(local_path)
                fsize = os.path.getsize(local_path)
                cache_key = (local_path, mtime, fsize, size, radius)
                if cache_key in _pixbuf_cache:
                    return _pixbuf_cache[cache_key]

                raw = GdkPixbuf.Pixbuf.new_from_file(local_path)
                rounded = get_rounded_pixbuf(raw, size, radius)
                if rounded:
                    _pixbuf_cache[cache_key] = rounded
                    return rounded
            except Exception as e:
                print(f"[Artwork] Error loading local art '{local_path}': {e}")
        return None

    cache_key = (art_url, size, radius)
    if cache_key in _pixbuf_cache:
        return _pixbuf_cache[cache_key]

    # 2. Remote HTTP/HTTPS URL
    if art_url.startswith("http://") or art_url.startswith("https://"):
        url_hash = hashlib.md5(art_url.encode("utf-8")).hexdigest()
        disk_path = os.path.join(CACHE_DIR, f"{url_hash}.img")

        # If not cached on disk or file is invalid/too small, download in background thread
        needs_download = False
        if os.path.exists(disk_path):
            try:
                if os.path.getsize(disk_path) > 1000:
                    raw = GdkPixbuf.Pixbuf.new_from_file(disk_path)
                    rounded = get_rounded_pixbuf(raw, size, radius)
                    if rounded:
                        _pixbuf_cache[cache_key] = rounded
                        return rounded
                else:
                    os.remove(disk_path)
                    needs_download = True
            except Exception:
                try:
                    os.remove(disk_path)
                except Exception:
                    pass
                needs_download = True
        else:
            needs_download = True

        if needs_download and art_url not in _downloading_urls:
            _downloading_urls.add(art_url)
            def _downloader():
                try:
                    req = urllib.request.Request(
                        art_url,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
                    )
                    with urllib.request.urlopen(req, timeout=6) as response:
                        data = response.read()
                        if len(data) > 1000:
                            with open(disk_path, "wb") as f:
                                f.write(data)
                    _downloading_urls.discard(art_url)
                    if on_ready_callback:
                        GLib.idle_add(on_ready_callback)
                except Exception as e:
                    _downloading_urls.discard(art_url)
                    print(f"[Artwork] Download error for '{art_url}': {e}")

            threading.Thread(target=_downloader, daemon=True).start()

    return None

def _search_youtube_artwork(title, artist=""):
    """Search YouTube for video thumbnail and return high-res 1280x720 or 640x480 artwork."""
    queries = []
    full_q = f"{title} {artist}".strip()
    queries.append(full_q)
    if ' | ' in title:
        queries.append(title.split(' | ')[0].strip())
    elif '|' in title:
        queries.append(title.split('|')[0].strip())
    if ' - ' in title:
        queries.append(title.split(' - ')[0].strip())

    for q in queries:
        try:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                vids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
                if not vids:
                    vids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                seen = set()
                for vid in vids:
                    if vid in seen:
                        continue
                    seen.add(vid)
                    for name in ['maxresdefault.jpg', 'sddefault.jpg', 'hqdefault.jpg']:
                        thumb_url = f"https://i.ytimg.com/vi/{vid}/{name}"
                        try:
                            t_req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(t_req, timeout=2.5) as tr:
                                if tr.status == 200:
                                    cl = tr.headers.get('Content-Length')
                                    # YouTube returns ~1097 bytes placeholder for missing maxres
                                    if cl and int(cl) < 2000:
                                        continue
                                    return thumb_url
                        except Exception:
                            continue
        except Exception:
            pass
    return None

def fetch_online_artwork_async(title, artist="", on_found_callback=None):
    """
    Search online (YouTube HD, iTunes Apple Music, Deezer) in a background thread for high-res album art.
    Invokes on_found_callback(artwork_url) on the GLib main thread once resolved.
    """
    if not title or title.lower() in ["unknown title", "no media playing"]:
        return

    try:
        from src.modules.lyrics import clean_title_artist
        clean_t, clean_artist = clean_title_artist(title, artist)
    except Exception:
        import unicodedata
        clean_t = unicodedata.normalize('NFC', title or "")
        clean_artist = unicodedata.normalize('NFC', artist or "")

    cache_key = (clean_t.lower(), clean_artist.lower())
    if cache_key in _online_art_cache:
        cached_url = _online_art_cache[cache_key]
        if cached_url and on_found_callback:
            try:
                GLib.idle_add(on_found_callback, cached_url)
            except Exception:
                try:
                    on_found_callback(cached_url)
                except Exception:
                    pass
        return

    if cache_key in _searching_queries:
        return

    _searching_queries.add(cache_key)

    def _worker():
        found_url = None

        # Check if the title or artist indicates YouTube / Remix / Video / CJK
        title_lower = title.lower()
        is_video_or_remix = any(
            w in title_lower for w in [
                'remix', 'tiktok', 'edm', 'mashup', 'official', 'mv', 'video', '|', '[',
                'live', 'lyrics', 'audio', 'karaoke', 'lofi', 'nhạc trung', 'hot trend'
            ]
        ) or any(ord(c) > 0x2E80 for c in title)

        # Strategy 1: YouTube HD search (prioritized for remixes, videos, tiktok, and asian tracks)
        if is_video_or_remix:
            found_url = _search_youtube_artwork(title, artist)

        # Strategy 2: iTunes Search API (1000x1000 Apple Music cover art)
        if not found_url:
            queries = []
            if clean_artist:
                queries.append(f"{clean_t} {clean_artist}")
            queries.append(clean_t)
            if clean_artist:
                queries.append(f"{clean_artist} {clean_t}")

            for q in queries:
                if found_url:
                    break
                try:
                    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(q)}&media=music&limit=3"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        for item in data.get("results", []):
                            item_track = (item.get("trackName") or "").lower()
                            item_artist = (item.get("artistName") or "").lower()
                            # Verify relevance: either track or artist should have substantial overlap
                            t_match = clean_t.lower() in item_track or item_track in clean_t.lower()
                            a_match = clean_artist.lower() in item_artist or item_artist in clean_artist.lower() if clean_artist else True
                            if t_match or a_match:
                                raw_art = item.get("artworkUrl100", "")
                                if raw_art:
                                    found_url = raw_art.replace("100x100bb", "1000x1000bb")
                                    break
                except Exception:
                    pass

        # Strategy 3: Deezer API fallback
        if not found_url:
            for q in [f"{clean_t} {clean_artist}".strip(), clean_t]:
                if found_url:
                    break
                try:
                    url = f"https://api.deezer.com/search?q={urllib.parse.quote(q)}&limit=3"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        for item in data.get("data", []):
                            item_track = (item.get("title") or "").lower()
                            item_artist = (item.get("artist", {}).get("name") or "").lower()
                            t_match = clean_t.lower() in item_track or item_track in clean_t.lower()
                            a_match = clean_artist.lower() in item_artist or item_artist in clean_artist.lower() if clean_artist else True
                            if t_match or a_match:
                                album_info = item.get("album", {})
                                found_url = album_info.get("cover_xl") or album_info.get("cover_big")
                                if found_url:
                                    break
                except Exception:
                    pass

        # Strategy 4: Fallback to YouTube HD if not yet found
        if not found_url:
            found_url = _search_youtube_artwork(title, artist)

        _searching_queries.discard(cache_key)
        _online_art_cache[cache_key] = found_url

        if found_url and on_found_callback:
            try:
                GLib.idle_add(on_found_callback, found_url)
            except Exception:
                try:
                    on_found_callback(found_url)
                except Exception:
                    pass

    threading.Thread(target=_worker, daemon=True).start()

def invalidate_artwork_cache(art_url=None):
    """Evict cached pixbufs from memory so new artwork renders immediately."""
    global _pixbuf_cache
    if art_url is None:
        _pixbuf_cache.clear()
    else:
        keys_to_remove = [k for k in _pixbuf_cache if k[0] == art_url]
        for k in keys_to_remove:
            _pixbuf_cache.pop(k, None)

