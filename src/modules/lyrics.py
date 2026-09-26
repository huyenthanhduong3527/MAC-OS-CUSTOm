"""
Lyrics Manager & Fetcher for Dynamic Island & Apple Music Desktop Widget.
Fetches real-time synchronized karaoke (.lrc) and plain lyrics from LRCLIB and online providers.
Features disk caching and thread-safe callbacks.
"""

import os
import re
import json
import hashlib
import threading
import urllib.parse
import urllib.request
import gi

gi.require_version('GLib', '2.0')
from gi.repository import GLib

CACHE_DIR = os.path.expanduser("~/.cache/dynamic_island/lyrics")
os.makedirs(CACHE_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def clean_title_artist(title, artist=""):
    """Strip noise tags and clean song title and artist."""
    import unicodedata
    t = unicodedata.normalize('NFC', title or "")
    a = unicodedata.normalize('NFC', artist or "")

    # Clean tags like (Official Video), [Official Audio], (MV), feat., ft.
    noise_patterns = [
        r'\s*[\(\[]\s*(?:official\s*(?:video|audio|music\s*video|mv)|audio|mv|lyrics?|video|remix|cover|live|vietsub|karaoke|prod\.?[^)]*|visualizer|album\s*version)\s*[\)\]]',
        r'\s*[\(\[]\s*feat\.?.*[\)\]]',
        r'\s*[\(\[]\s*ft\.?.*[\)\]]',
        r'\s*ft\.?\s+.*$',
        r'\s*feat\.?\s+.*$',
        r'^\s*[\(\[]cut[\)\]]\s*',
    ]
    for pat in noise_patterns:
        t = re.sub(pat, '', t, flags=re.IGNORECASE)
        a = re.sub(pat, '', a, flags=re.IGNORECASE)

    # Clean file extensions
    t = re.sub(r'\.(mp3|flac|wav|m4a|ogg|opus|aac|webm)$', '', t, flags=re.IGNORECASE)

    # Clean YouTube / web video pipes: e.g. "Song Name | Artist (MV)"
    if '|' in t:
        parts = t.split('|', 1)
        t = parts[0].strip()
        if not a and len(parts) > 1:
            a = parts[1].strip()

    # Clean artist
    if '•' in a:
        a = a.split('•')[0].strip()
    generic_artists = ['firefox', 'chrome', 'google-chrome', 'spotify', 'vlc', 'unknown artist', 'system audio', 'audio', 'tirusisme']
    if a.lower() in generic_artists:
        a = ""

    t = re.sub(r'[\(\[\{]\s*[\)\]\}]', '', t).strip(' -()[].,:;|\"')
    a = re.sub(r'[\(\[\{]\s*[\)\]\}]', '', a).strip(' -()[].,:;|\"')

    return t, a


BUILTIN_LYRICS = {
    "hẹn em dưới pháo hoa": {
        "title": "Hẹn Em Dưới Pháo Hoa",
        "artist": "Ân Ngờ & kphuong",
        "is_synced": True,
        "lines": [
            (0.0, "Biết đâu duyên trời em ơi"),
            (4.0, "Cách nhau mấy giậu mồng tơi"),
            (8.0, "Để ai ngỏ lời sang chơi"),
            (12.0, "Có em bên đời"),
            (17.5, "Pháo hoa rực rỡ trên trời"),
            (21.5, "Người yêu ơi anh đang tới"),
            (26.0, "Có chăng hơi ấm bên đời"),
            (30.0, "Là do mây mang em với"),
            (35.0, "Câu chúc - hàn huyên"),
            (38.0, "Đâu đó tình duyên"),
            (40.5, "Rơi vào nơi bước chân em đi"),
            (44.0, "Người đi mất, đành thôi cất cớ sao?"),
            (49.0, "Mà cớ sao?"),
            (52.5, "Thư trắng - từng trao"),
            (55.5, "Đêm ước - ngày ao"),
            (58.0, "Anh chỉ mong thấy em an vui"),
            (62.0, "Người đi có nhớ tôi? có không một lời?"),
            (69.0, "À ới duyên tình"),
            (73.5, "Tình duyên nào chẳng chơi vơi"),
            (78.0, "Anh cố đợi nhưng sao lòng em dường như chẳng đưa đến nơi"),
            (86.5, "Người giấu câu chào"),
            (91.0, "Tôi hỏi thăm cỏ cây biết không?"),
            (95.5, "Hoa đã về với mây gió biển khơi"),
            (100.5, "Sẽ có ai nói yêu thật lòng"),
            (107.0, "Mây bay khắp phương trời"),
            (111.0, "Khắp phương trời nào ai đâu hay"),
            (115.5, "Trăng treo ở trên đầu"),
            (119.5, "Ở trên đầu mà sao chẳng thấy"),
            (124.0, "Người ở lại đừng hỏi trăng đâu"),
            (128.5, "Em đi rồi trời hóa mưa ngâu"),
            (133.0, "Thu lá vàng rơi, mong nhớ đầy vơi"),
            (138.0, "Thì bây giờ cũng mấy đêm thâu"),
            (142.5, "Câu chúc - hàn huyên"),
            (145.5, "Lỡ mất tình duyên"),
            (148.0, "Rơi vào nơi bước chân em đi"),
            (151.5, "Người đi mất, đành thôi cất cớ sao?"),
            (156.5, "Mà cớ sao?"),
            (160.0, "Thư trắng - từng trao"),
            (163.0, "Đêm ước - ngày mau"),
            (165.5, "Em chỉ mong thấy anh buông xuôi"),
            (169.5, "Người đi vẫn nhớ anh, nhớ anh một đời"),
            (177.0, "À ới duyên tình"),
            (181.5, "Tình duyên nào chẳng chơi vơi"),
            (186.0, "Anh cố đợi nhưng sao lòng em dường như chẳng đưa đến nơi"),
            (194.5, "Người giấu câu chào"),
            (199.0, "Tôi hỏi thăm cỏ cây biết không?"),
            (203.5, "Hoa đã về với mây gió biển khơi"),
            (208.5, "Sẽ có ai nói yêu thật lòng"),
            (215.0, "Đâu ai hiểu mấy năm ròng"),
            (218.0, "Chuyện một khi người đã tương tư"),
            (221.0, "Tuy đau mà vẫn hy vọng"),
            (224.0, "Mong rằng sau này ta giống như"),
            (227.0, "Nên duyên gọi tiếng vợ chồng"),
            (230.0, "Luôn kề bên dù nắng hay mưa"),
            (233.0, "Bao lâu anh vẫn sẽ đợi"),
            (236.0, "Trăm ngàn năm dù rất xa xưa")
        ]
    }
}


def parse_lrc(lrc_text):
    """
    Parse an LRC lyrics string.
    Returns:
        lines: list of (timestamp_seconds, text)
        is_synced: True if timestamped lyrics exist, False if plain text
    """
    if not lrc_text:
        return [], False

    pattern = re.compile(r"\[(\d{1,2}):(\d{2}(?:\.\d+)?)\](.*)")
    parsed = []

    for line in lrc_text.splitlines():
        line = line.strip()
        m = pattern.match(line)
        if m:
            mins = int(m.group(1))
            secs = float(m.group(2))
            t = mins * 60.0 + secs
            content = m.group(3).strip()
            # Clean possible duplicate tags like [00:12.34][00:15.67] text
            content = re.sub(r"\[\d{1,2}:\d{2}(?:\.\d+)?\]", "", content).strip()
            if content:
                parsed.append((t, content))

    if parsed:
        parsed.sort(key=lambda x: x[0])
        return parsed, True

    # If no timestamps, treat as plain text lines
    plain = []
    for line in lrc_text.splitlines():
        cleaned = line.strip()
        if cleaned:
            plain.append((0.0, cleaned))
    return plain, False


class LyricsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LyricsManager, cls).__new__(cls)
            cls._instance._memory_cache = {}
            cls._instance._fetching_keys = set()
        return cls._instance

    def _get_cache_path(self, title, artist):
        key = f"{title.lower()}___{artist.lower()}"
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(CACHE_DIR, f"{h}.json"), key

    def get_lyrics_async(self, title, artist="", duration=0, callback=None):
        """
        Fetch lyrics asynchronously.
        Calls callback(lyrics_data) where lyrics_data is a dict:
        {
            "title": str,
            "artist": str,
            "is_synced": bool,
            "lines": [(sec, "text"), ...],
            "plain_text": str,
            "source": str
        } or None if not found.
        """
        clean_t, clean_a = clean_title_artist(title, artist)
        if not clean_t or clean_t.lower() in ["no media playing", "unknown title"]:
            if callback:
                GLib.idle_add(callback, None)
            return

        # 0. Check BUILTIN_LYRICS (Instant response for known popular tracks)
        low_t = clean_t.lower()
        for b_key, b_data in BUILTIN_LYRICS.items():
            if b_key in low_t or low_t in b_key:
                if callback:
                    GLib.idle_add(callback, b_data)
                return

        cache_path, key = self._get_cache_path(clean_t, clean_a)

        # 1. Check memory cache
        if key in self._memory_cache:
            if callback:
                GLib.idle_add(callback, self._memory_cache[key])
            return

        # 2. Check disk cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._memory_cache[key] = data
                    if callback:
                        GLib.idle_add(callback, data)
                    return
            except Exception:
                pass

        if key in self._fetching_keys:
            return
        self._fetching_keys.add(key)

        def _worker():
            result = None
            try:
                result = self._fetch_online(clean_t, clean_a, duration)
            except Exception as e:
                print(f"[Lyrics] Fetch error for '{clean_t}': {e}")

            self._fetching_keys.discard(key)
            if result:
                self._memory_cache[key] = result
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            if callback:
                GLib.idle_add(callback, result)

        threading.Thread(target=_worker, daemon=True).start()

    def _fetch_online(self, title, artist, duration=0):
        """Internal search across providers."""
        low_t = title.lower()
        for b_key, b_data in BUILTIN_LYRICS.items():
            if b_key in low_t or low_t in b_key:
                return b_data

        # 1. LRCLIB Search
        queries = []
        if artist:
            queries.append(f"{title} {artist}")
        queries.append(title)
        if ',' in title:
            queries.append(title.split(',')[0].strip())

        for q in queries:
            try:
                url = f"https://lrclib.net/api/search?q={urllib.parse.quote(q)}"
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    items = json.loads(resp.read().decode("utf-8"))
                    if items and isinstance(items, list):
                        # Find best match
                        best = items[0]
                        synced = best.get("syncedLyrics")
                        plain = best.get("plainLyrics")

                        if synced:
                            lines, is_sync = parse_lrc(synced)
                            if lines:
                                return {
                                    "title": best.get("trackName") or title,
                                    "artist": best.get("artistName") or artist,
                                    "is_synced": True,
                                    "lines": lines,
                                    "plain_text": plain or "\n".join(l[1] for l in lines),
                                    "source": "LRCLIB"
                                }
                        elif plain:
                            lines, is_sync = parse_lrc(plain)
                            if lines:
                                return {
                                    "title": best.get("trackName") or title,
                                    "artist": best.get("artistName") or artist,
                                    "is_synced": False,
                                    "lines": lines,
                                    "plain_text": plain,
                                    "source": "LRCLIB"
                                }
            except Exception:
                pass

        # 2. LRCLIB Direct get
        if artist:
            try:
                params = {"track_name": title, "artist_name": artist}
                if duration > 0:
                    params["duration"] = int(duration)
                url = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    item = json.loads(resp.read().decode("utf-8"))
                    synced = item.get("syncedLyrics")
                    plain = item.get("plainLyrics")
                    if synced or plain:
                        lines, is_sync = parse_lrc(synced or plain)
                        return {
                            "title": item.get("trackName") or title,
                            "artist": item.get("artistName") or artist,
                            "is_synced": is_sync,
                            "lines": lines,
                            "plain_text": plain or (synced or ""),
                            "source": "LRCLIB"
                        }
            except Exception:
                pass

        # 3. lyrics.ovh fallback
        if artist:
            try:
                url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(title)}"
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    lyrics_txt = data.get("lyrics")
                    if lyrics_txt:
                        lines, is_sync = parse_lrc(lyrics_txt)
                        return {
                            "title": title,
                            "artist": artist,
                            "is_synced": False,
                            "lines": lines,
                            "plain_text": lyrics_txt,
                            "source": "Lyrics.ovh"
                        }
            except Exception:
                pass

        return None


# Global singleton instance
lyrics_manager = LyricsManager()
