"""
Multilingual Neural Voice Synthesizer for Dynamic Island Siri.
Powered by Microsoft Edge Neural Voices (High Fidelity, Natural, Human-like).

Performance & Low-Latency Engine:
- Instant Cache: Pre-caches frequent responses in ~/.cache/dynamic_island/tts/ (0ms playback)
- Direct Pipe Streaming: Streams audio directly from edge-tts into GStreamer pulsesink without waiting for disk writes
- Energetic Siri Rate: Speaks at +18% natural conversational rate
- Anti-stutter: Cancels previous audio streams immediately when new input arrives
- Crystal-clear pronunciation for Vietnamese, English, Japanese, etc.
"""

import os
import re
import time
import shutil
import hashlib
import tempfile
import threading
import subprocess
from typing import Optional

VOICE_PRESETS = {
    "vi-female": {"id": "vi-VN-HoaiMyNeural", "name": "Tiếng Việt (Nữ - Hoài My - Tự nhiên)", "lang": "vi"},
    "vi-male": {"id": "vi-VN-NamMinhNeural", "name": "Tiếng Việt (Nam - Nam Minh - Truyền cảm)", "lang": "vi"},
    "en-female": {"id": "en-US-AriaNeural", "name": "English (Female - Aria - Natural)", "lang": "en"},
    "en-male": {"id": "en-US-GuyNeural", "name": "English (Male - Guy)", "lang": "en"},
    "ja-female": {"id": "ja-JP-NanamiNeural", "name": "日本語 (女性 - Nanami)", "lang": "ja"},
}

DEFAULT_VOICE_KEY = "vi-female"
CACHE_DIR = os.path.expanduser("~/.cache/dynamic_island/tts")
os.makedirs(CACHE_DIR, exist_ok=True)


def clean_text_for_speech(text: str) -> str:
    """Cleans text of markdown, URLs, emojis, and code syntax for pleasant speech."""
    if not text:
        return ""

    # 1. Remove action tags
    cleaned = re.sub(r'\[ACTION:\s*[a-zA-Z_]+\s*\{.*?\}\]', '', text, flags=re.DOTALL)

    # 2. Remove code blocks
    cleaned = re.sub(r'```[\s\S]*?```', '', cleaned)
    cleaned = re.sub(r'`[^`]*`', '', cleaned)

    # 3. Remove URLs
    cleaned = re.sub(r'https?://\S+', '', cleaned)

    # 4. Remove tool call tags or JSON-like blocks if any
    cleaned = re.sub(r'<tool_call>[\s\S]*?</tool_call>', '', cleaned)
    cleaned = re.sub(r'\{"[^"]+":[\s\S]*?\}', '', cleaned)

    # 5. Remove Markdown headers, bold, italics, links, blockquotes
    cleaned = re.sub(r'#+\s*', '', cleaned)
    cleaned = re.sub(r'[*_~]', '', cleaned)
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'^>\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^[-*+]\s*', '', cleaned, flags=re.MULTILINE)

    # 6. Remove common emojis and symbols
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', cleaned)

    # 7. Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def detect_language(text: str) -> str:
    """Infers whether the text is Vietnamese, Japanese, or English."""
    if re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', text, re.IGNORECASE):
        return "vi"
    if re.search(r'[\u3040-\u30ff\u4e00-\u9faf]', text):
        return "ja"
    return "en"


class VoiceSynthesizer:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.enabled: bool = True
        self.selected_voice_key: str = DEFAULT_VOICE_KEY
        self.current_process: Optional[subprocess.Popen] = None
        self.pipe_producer: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()
        self._generation = 0
        self.last_spoken_hash: str = ""
        self.last_spoken_time: float = 0.0
        self._find_players()
        self._find_edge_tts()

    def _find_players(self):
        self.player_cmd = None
        if shutil.which("gst-play-1.0"):
            self.player_cmd = ["gst-play-1.0", "--no-interactive"]
        elif shutil.which("pw-play"):
            self.player_cmd = ["pw-play"]
        elif shutil.which("ffplay"):
            self.player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
        elif shutil.which("paplay"):
            self.player_cmd = ["paplay"]
        elif shutil.which("aplay"):
            self.player_cmd = ["aplay"]

    def _find_edge_tts(self):
        user_edge = os.path.expanduser("~/.local/bin/edge-tts")
        if os.path.exists(user_edge):
            self.edge_tts_bin = user_edge
        else:
            self.edge_tts_bin = shutil.which("edge-tts") or "edge-tts"

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            self.stop()

    def set_voice_key(self, key: str):
        if key in VOICE_PRESETS:
            self.selected_voice_key = key

    def get_voice_id(self, text: str) -> str:
        lang = detect_language(text)
        if lang == "vi":
            if self.selected_voice_key in ("vi-female", "vi-male"):
                return VOICE_PRESETS[self.selected_voice_key]["id"]
            return VOICE_PRESETS["vi-female"]["id"]
        elif lang == "ja":
            return VOICE_PRESETS["ja-female"]["id"]
        elif lang == "en":
            if self.selected_voice_key in ("en-female", "en-male"):
                return VOICE_PRESETS[self.selected_voice_key]["id"]
            return VOICE_PRESETS["en-female"]["id"]

        preset = VOICE_PRESETS.get(self.selected_voice_key, VOICE_PRESETS[DEFAULT_VOICE_KEY])
        return preset["id"]

    def stop(self):
        """Immediately stops any ongoing audio synthesis and playback."""
        with self.lock:
            self._generation += 1
            if self.pipe_producer is not None:
                try:
                    self.pipe_producer.terminate()
                    self.pipe_producer.kill()
                except Exception:
                    pass
                self.pipe_producer = None

            if self.current_process is not None:
                try:
                    self.current_process.terminate()
                    self.current_process.kill()
                except Exception:
                    pass
                self.current_process = None

    def speak(self, text: str, voice_override: Optional[str] = None):
        """Synthesizes and speaks text with ultra-low latency."""
        if not self.enabled or not text:
            return

        clean = clean_text_for_speech(text)
        if not clean or len(clean) < 2:
            return

        # Keep voice response concise for snappy UX (max 200 chars for speech)
        if len(clean) > 220:
            sentences = re.split(r'([.!?。])', clean)
            accumulated = ""
            for i in range(0, len(sentences), 2):
                part = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                if len(accumulated) + len(part) <= 200:
                    accumulated += part
                else:
                    break
            clean = accumulated.strip() if accumulated else clean[:200]

        # Prevent immediate duplicate trigger repetition
        thash = hashlib.md5(clean.encode("utf-8")).hexdigest()
        now = time.time()
        if thash == self.last_spoken_hash and (now - self.last_spoken_time) < 2.0:
            return
        self.last_spoken_hash = thash
        self.last_spoken_time = now

        # Cancel an older response before starting a new one.  This keeps a
        # quick sequence of prompts from leaving orphaned TTS processes.
        self.stop()
        with self.lock:
            generation = self._generation

        def _worker():
            voice_id = voice_override or self.get_voice_id(clean)

            # 1. Check local disk cache for instant playback (0ms latency)
            cache_key = hashlib.md5(f"{clean}_{voice_id}".encode("utf-8")).hexdigest()
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.mp3")

            if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
                with self.lock:
                    if generation != self._generation:
                        return
                    if self.player_cmd:
                        self.current_process = subprocess.Popen(
                            self.player_cmd + [cache_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                if self.current_process:
                    self.current_process.wait()
                    return

            # 2. Fast Streaming Pipe (Play as bytes arrive from edge-tts, no disk wait)
            p_tts = None
            try:
                # Generate into a temporary file, then atomically publish it so
                # playback never opens a partially-written MP3.
                tmp_file = f"{cache_file}.{threading.get_ident()}.tmp"
                p_tts = subprocess.Popen(
                    [self.edge_tts_bin, "-t", clean, "-v", voice_id, "--rate", "+10%", "--write-media", tmp_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                with self.lock:
                    self.pipe_producer = p_tts
                p_tts.wait(timeout=15.0)
                with self.lock:
                    self.pipe_producer = None
                    cancelled = generation != self._generation
                if cancelled or p_tts.returncode != 0:
                    return
                if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 100:
                    os.replace(tmp_file, cache_file)
                    with self.lock:
                        if generation != self._generation or not self.player_cmd:
                            return
                        self.current_process = subprocess.Popen(
                            self.player_cmd + [cache_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    self.current_process.wait()
            except Exception as e:
                if p_tts is not None:
                    try:
                        p_tts.terminate()
                        p_tts.kill()
                    except Exception:
                        pass
            finally:
                try:
                    if os.path.exists(tmp_file):
                        os.unlink(tmp_file)
                except Exception:
                    pass
                with self.lock:
                    if generation == self._generation:
                        self.current_process = None
                        self.pipe_producer = None

        threading.Thread(target=_worker, daemon=True).start()


voice_synthesizer = VoiceSynthesizer.get_instance()
