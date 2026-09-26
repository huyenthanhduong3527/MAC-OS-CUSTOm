#!/usr/bin/env python3
import re
import sys
from update_i18n import VI_ADDITIONS, EN_ADDITIONS, JA_ADDITIONS

with open("src/utils/i18n.py", "r", encoding="utf-8") as f:
    text = f.read()

def dict_to_lines(d, indent="        "):
    lines = []
    for k, v in d.items():
        escaped_v = v.replace('"', '\\"')
        lines.append(f'{indent}"{k}": "{escaped_v}",')
    return "\n".join(lines)

# 1. Patch VI
vi_target = '"unlink_google_account": "Hủy liên kết tài khoản này",\n    },'
vi_replacement = f'"unlink_google_account": "Hủy liên kết tài khoản này",\n{dict_to_lines(VI_ADDITIONS)}\n    }},'
assert vi_target in text, "Could not find vi target"
text = text.replace(vi_target, vi_replacement, 1)

# 2. Patch EN
en_target = '"unlink_google_account": "Unlink This Account",\n    },'
en_replacement = f'"unlink_google_account": "Unlink This Account",\n{dict_to_lines(EN_ADDITIONS)}\n    }},'
assert en_target in text, "Could not find en target"
text = text.replace(en_target, en_replacement, 1)

# 3. Patch JA
ja_target = '"unlink_google_account": "このアカウントのリンクを解除",\n    },'
ja_replacement = f'"unlink_google_account": "このアカウントのリンクを解除",\n{dict_to_lines(JA_ADDITIONS)}\n    }},'
assert ja_target in text, "Could not find ja target"
text = text.replace(ja_target, ja_replacement, 1)

# 4. Patch I18nManager to add file monitoring for multi-process sync
mgr_target = """class I18nManager:
    def __init__(self):
        self._current_lang = "vi"
        self._preferred_languages: List[str] = ["vi", "en"]
        self._listeners: List[Callable[[str], None]] = []
        self._load_from_config()"""

mgr_replacement = """class I18nManager:
    def __init__(self):
        self._current_lang = "vi"
        self._preferred_languages: List[str] = ["vi", "en"]
        self._listeners: List[Callable[[str], None]] = []
        self._file_monitor = None
        self._load_from_config()
        self._setup_file_monitor()

    def _setup_file_monitor(self):
        try:
            from gi.repository import Gio
            f = Gio.File.new_for_path(CONFIG_PATH)
            self._file_monitor = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
            if self._file_monitor:
                self._file_monitor.connect("changed", self._on_config_file_changed)
        except Exception as e:
            pass

    def _on_config_file_changed(self, monitor, file, other_file, event_type):
        try:
            from gi.repository import Gio, GLib
            if event_type in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CHANGED):
                old_lang = self._current_lang
                self._load_from_config()
                if self._current_lang != old_lang:
                    for listener in list(self._listeners):
                        try:
                            GLib.idle_add(listener, self._current_lang)
                        except Exception as e:
                            print(f"[i18n] listener callback error: {e}")
        except Exception:
            pass"""

assert mgr_target in text, "Could not find I18nManager __init__ target"
text = text.replace(mgr_target, mgr_replacement, 1)

with open("src/utils/i18n.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched src/utils/i18n.py")
