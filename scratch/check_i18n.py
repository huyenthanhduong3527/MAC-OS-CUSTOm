#!/usr/bin/env python3
import sys

with open("src/utils/i18n.py", "r", encoding="utf-8") as f:
    content = f.read()

# Verify current content has TRANSLATIONS
assert 'TRANSLATIONS: Dict[str, Dict[str, str]] = {' in content
print("Found TRANSLATIONS in i18n.py, ready to patch.")
