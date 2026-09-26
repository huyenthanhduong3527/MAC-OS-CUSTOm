import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# Set up path
sys.path.insert(0, '/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX')

from src.ui.macos_settings_window import (
    get_real_storage_breakdown,
    MacStorageBarWidget,
    MacOSSettingsWindow,
)
from src.utils.icons import SVG_ICONS, get_image, get_pixbuf

print("=== 1. TESTING STORAGE DATA ===")
data = get_real_storage_breakdown()
print(f"Total GB: {data['total_gb']}")
print(f"Used GB: {data['used_gb']}")
print(f"Free GB: {data['free_gb']}")
print(f"Apps GB: {data['apps_gb']}")
print(f"macOS GB: {data['macos_gb']}")
print(f"Developer GB: {data['developer_gb']}")
print(f"Docs GB: {data['docs_gb']}")
print(f"Photos GB: {data['photos_gb']}")
print(f"Downloads GB: {data['downloads_gb']}")
print(f"Other GB: {data['other_gb']}")
assert data['total_gb'] > 0
assert data['used_gb'] >= 0
assert data['free_gb'] >= 0

print("=== 2. TESTING MAC STORAGE BAR WIDGET ===")
widget = MacStorageBarWidget(data, is_dark=False)
assert widget is not None
print("MacStorageBarWidget created successfully.")

print("=== 3. TESTING ICONS ===")
for name in ["storage_disk", "applecare", "airplane", "airplay", "pip", "screen_record", "carplay", "cellular", "personal_hotspot", "software_update", "continuity"]:
    assert name in SVG_ICONS, f"Missing icon {name}"
    img = get_image(name, 16, "#ffffff")
    assert img is not None, f"Could not create image for {name}"
print("All 11 vector icons verified.")

print("=== 4. TESTING SETTINGS WINDOW INSTANTIATION & TABS ===")
win = MacOSSettingsWindow.get_instance()
assert win is not None
print("MacOSSettingsWindow created.")

tabs_to_test = [
    ("general", "general"),
    ("storage", "storage"),
    ("about", "about"),
    ("applecare", "applecare"),
    ("continuity", "continuity"),
    ("pip_page", "pip_page"),
    ("screen_record_page", "screen_record_page"),
    ("carplay_page", "carplay_page"),
]

for tab_id, expected_child in tabs_to_test:
    win.select_tab(tab_id)
    cur = win.stack.get_visible_child_name()
    assert cur == expected_child, f"Tab {tab_id} failed: got {cur}, expected {expected_child}"
    print(f"Tab '{tab_id}' -> '{cur}' OK")

print("=== ALL TESTS PASSED! ===")
