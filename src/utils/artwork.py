"""
Album Art Manager & Loader for Dynamic Island.
Handles local file URLs (Firefox, VLC), remote HTTP/HTTPS URLs (Spotify),
and generates sleek Apple-style rounded squircle pixbufs with caching.
"""

import os
import math
import hashlib
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
        scaled = cropped.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)

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

def load_artwork_pixbuf(art_url, size=48, radius=8, on_ready_callback=None):
    """
    Load album art from local file:// path, absolute path, or remote URL.
    Returns GdkPixbuf or None if not yet available.
    """
    if not art_url:
        return None

    cache_key = (art_url, size, radius)
    if cache_key in _pixbuf_cache:
        return _pixbuf_cache[cache_key]

    # 1. Local file:// URL
    if art_url.startswith("file://"):
        local_path = urllib.parse.unquote(art_url[7:])
        if os.path.exists(local_path):
            try:
                raw = GdkPixbuf.Pixbuf.new_from_file(local_path)
                rounded = get_rounded_pixbuf(raw, size, radius)
                if rounded:
                    _pixbuf_cache[cache_key] = rounded
                    return rounded
            except Exception as e:
                print(f"[Artwork] Error loading local art '{local_path}': {e}")
        return None

    # 2. Local raw file path
    if art_url.startswith("/") and os.path.exists(art_url):
        try:
            raw = GdkPixbuf.Pixbuf.new_from_file(art_url)
            rounded = get_rounded_pixbuf(raw, size, radius)
            if rounded:
                _pixbuf_cache[cache_key] = rounded
                return rounded
        except Exception as e:
            print(f"[Artwork] Error loading path '{art_url}': {e}")
        return None

    # 3. Remote HTTP/HTTPS URL
    if art_url.startswith("http://") or art_url.startswith("https://"):
        url_hash = hashlib.md5(art_url.encode("utf-8")).hexdigest()
        disk_path = os.path.join(CACHE_DIR, f"{url_hash}.img")

        if os.path.exists(disk_path):
            try:
                raw = GdkPixbuf.Pixbuf.new_from_file(disk_path)
                rounded = get_rounded_pixbuf(raw, size, radius)
                if rounded:
                    _pixbuf_cache[cache_key] = rounded
                    return rounded
            except Exception:
                pass

        # If not cached on disk, download in background thread
        if art_url not in _downloading_urls:
            _downloading_urls.add(art_url)
            def _downloader():
                try:
                    req = urllib.request.Request(
                        art_url,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) DynamicIsland/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=4) as response:
                        data = response.read()
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
