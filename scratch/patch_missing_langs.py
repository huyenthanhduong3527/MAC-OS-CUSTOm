#!/usr/bin/env python3
"""
Helper script to patch src/utils/i18n.py with all weather and photobooth translations for fr, es, de.
"""

from patch_i18n_weather_photobooth import TARGET_PATH, NEW_TRANSLATIONS

def patch_missing_langs():
    with open(TARGET_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    for lang in ("fr", "es", "de"):
        kv_map = NEW_TRANSLATIONS[lang]
        marker = f'    "{lang}": {{\n'
        idx = content.find(marker)
        if idx == -1:
            print(f"Warning: could not find {marker}")
            continue

        # Find the closing bracket for this language
        # It ends before the next `    #` or `    "`
        next_lang = content.find('\n    },', idx)
        if next_lang == -1:
            next_lang = idx + 5000
        section = content[idx:next_lang]

        insert_pos = idx + len(marker)
        lines = []
        for k, v in kv_map.items():
            if f'"{k}":' in section:
                continue
            v_escaped = v.replace('"', '\\"')
            lines.append(f'        "{k}": "{v_escaped}",\n')

        if lines:
            insertion = "".join(lines)
            content = content[:insert_pos] + insertion + content[insert_pos:]
            print(f"Added {len(lines)} keys to '{lang}' dictionary.")

    with open(TARGET_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched fr, es, de in i18n.py!")

if __name__ == "__main__":
    patch_missing_langs()
