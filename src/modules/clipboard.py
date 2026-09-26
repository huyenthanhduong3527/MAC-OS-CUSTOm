"""
Clipboard History Manager for Dynamic Island.
Monitors system clipboard changes via Gtk.Clipboard owner-change signal.
Categorizes copied items (Text, URLs, Code) and maintains a history of up to 30 items
for instant 1-tap re-copying from Dynamic Island Expanded View.
Supports persistent disk storage and seamless cross-app pasting on Wayland and X11.
"""

import os
import time
import json
import re
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class ClipboardManager:
    _instance = None

    @classmethod
    def get_instance(cls, on_change=None):
        if cls._instance is None:
            cls._instance = ClipboardManager(on_change=on_change)
        elif on_change:
            cls._instance.callbacks.append(on_change)
        return cls._instance

    def __init__(self, on_change=None):
        self.callbacks = [on_change] if on_change else []
        self.history = []
        self.max_items = 30
        self._next_id = 1
        self._is_internal_copy = False
        self._history_save_lock = threading.Lock()
        self._history_save_revision = 0

        self.history_file = os.path.expanduser("~/.config/dynamic_island/clipboard_history.json")
        self._load_history()

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.primary_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self.clipboard.connect("owner-change", self._on_owner_change)

        # Initial check for any existing clipboard content
        self.clipboard.request_text(self._on_initial_text)

    def _load_history(self):
        """Load persistent clipboard history from disk."""
        if not os.path.exists(self.history_file):
            return
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                valid_items = []
                for item in data[:self.max_items]:
                    if isinstance(item, dict) and "text" in item and item["text"].strip():
                        valid_items.append(item)
                self.history = valid_items
                if self.history:
                    max_id = max(item.get("id", 0) for item in self.history)
                    self._next_id = max(max_id + 1, 1)
        except Exception as e:
            print(f"[ClipboardManager] Error loading history from {self.history_file}: {e}")

    def _save_history(self):
        """Save history items to disk atomically."""
        self._history_save_revision += 1
        revision = self._history_save_revision
        self._write_history_snapshot([dict(item) for item in self.history], revision)

    def _save_history_async(self):
        """Persist a snapshot without making the GTK event loop wait for disk I/O."""
        self._history_save_revision += 1
        revision = self._history_save_revision
        snapshot = [dict(item) for item in self.history]
        threading.Thread(
            target=self._write_history_snapshot,
            args=(snapshot, revision),
            daemon=True,
        ).start()

    def _write_history_snapshot(self, snapshot, revision):
        try:
            with self._history_save_lock:
                if revision != self._history_save_revision:
                    return
                os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
                tmp_path = f"{self.history_file}.tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.history_file)
        except Exception as e:
            print(f"[ClipboardManager] Error saving history: {e}")

    def add_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def _on_owner_change(self, clipboard, event):
        if self._is_internal_copy:
            return
        clipboard.request_text(self._on_text_received)

    def _on_initial_text(self, clipboard, text, data=None):
        if text and text.strip():
            self._add_entry(text.strip())

    def _on_text_received(self, clipboard, text, data=None):
        if self._is_internal_copy:
            return
        if text and text.strip():
            self._add_entry(text.strip())

    def _add_entry(self, text):
        # Ignore if identical to the most recent entry
        if self.history and self.history[0]["text"] == text:
            return

        # Deduplicate: if already exists down the history list, remove older duplicate
        self.history = [item for item in self.history if item["text"] != text]

        item_type = self._classify_text(text)
        preview = self._make_preview(text)

        entry = {
            "id": self._next_id,
            "text": text,
            "preview": preview,
            "type": item_type,
            "length": len(text),
            "lines": text.count("\n") + 1,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M")
        }
        self._next_id += 1

        self.history.insert(0, entry)
        if len(self.history) > self.max_items:
            self.history = self.history[:self.max_items]

        self._save_history()
        self._notify_callbacks()

    def _classify_text(self, text):
        stripped = text.strip()
        # 1. URL detection
        if re.match(r'^(https?://|ftp://|www\.)\S+$', stripped, re.IGNORECASE):
            return "url"

        # 2. Code and CLI command detection
        code_keywords = [
            "def ", "class ", "import ", "from ", "function", "const ", "let ", "var ",
            "return ", "public ", "private ", "void ", "async ", "await ",
            "sudo ", "docker ", "kubectl ", "git ", "npm ", "pip ", "curl ", "apt "
        ]
        code_syntax = ["{", "}", ";", "=>", "==", "!=", "->", "::", "</", "/>"]
        lines = text.splitlines()

        keyword_hits = sum(1 for kw in code_keywords if kw in text)
        syntax_hits = sum(1 for sym in code_syntax if sym in text)

        if (len(lines) > 1 and (keyword_hits >= 1 or syntax_hits >= 2)) or (len(lines) == 1 and keyword_hits >= 1 and (syntax_hits >= 1 or "(" in text or "=" in text)):
            return "code"

        return "text"

    def _make_preview(self, text):
        lines = text.strip().splitlines()
        if len(lines) == 1:
            return lines[0][:90] + ("…" if len(lines[0]) > 90 else "")
        else:
            return "\n".join(lines[:3]) + ("\n…" if len(lines) > 3 else "")

    def copy_to_clipboard(self, text):
        """
        Re-copy selected history item back into system clipboard.
        Gtk owns the native selection on both X11 and Wayland, so no external
        clipboard process or synchronous store request is needed here.
        """
        self._is_internal_copy = True

        # Gtk.Clipboard.store() can enter a nested wait for the desktop clipboard
        # manager. Keeping ownership in this long-running app avoids that UI freeze.
        try:
            self.clipboard.set_text(text, -1)
            self.primary_clipboard.set_text(text, -1)
        except Exception as e:
            print(f"[ClipboardManager] GTK set_text error: {e}")
            self._is_internal_copy = False
            return False

        # Move this item to top of history. Persistence is deliberately off the
        # GTK thread because a history item may contain a large amount of text.
        for idx, item in enumerate(self.history):
            if item["text"] == text:
                entry = self.history.pop(idx)
                entry["timestamp"] = time.time()
                entry["time_str"] = time.strftime("%H:%M")
                self.history.insert(0, entry)
                self._save_history_async()
                break

        # Release the recursion lock after owner-change signals have settled.
        GLib.timeout_add(1000, self._reset_internal_flag)
        return True

    def _reset_internal_flag(self):
        self._is_internal_copy = False
        return False

    def remove_item(self, item_id):
        self.history = [item for item in self.history if item["id"] != item_id]
        self._save_history()
        self._notify_callbacks()

    def clear_history(self):
        self.history = []
        self._save_history()
        self._notify_callbacks()

    def _notify_callbacks(self):
        for cb in self.callbacks:
            try:
                cb(self.history)
            except Exception as e:
                print(f"[ClipboardManager] Callback error: {e}")
