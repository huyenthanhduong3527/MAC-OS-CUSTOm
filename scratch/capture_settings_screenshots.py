import sys
import os
import time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

sys.path.insert(0, '/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX')

from src.ui.macos_settings_window import MacOSSettingsWindow

def capture_window_to_file(window, out_path):
    while Gtk.events_pending():
        Gtk.main_iteration()
    time.sleep(0.3)
    while Gtk.events_pending():
        Gtk.main_iteration()
    
    gdk_win = window.get_window()
    if not gdk_win:
        print(f"Error: no gdk window for {out_path}")
        return False
    
    alloc = window.get_allocation()
    pixbuf = Gdk.pixbuf_get_from_window(gdk_win, 0, 0, alloc.width, alloc.height)
    if pixbuf:
        pixbuf.savev(out_path, "png", [], [])
        print(f"Saved screenshot: {out_path} ({alloc.width}x{alloc.height})")
        return True
    return False

artifact_dir = "/home/tramvo/.gemini/antigravity-ide/brain/5c8b0e90-4565-4787-8bdd-54594301fbfc"

win = MacOSSettingsWindow()
win.show_window("general")

# Process events
for _ in range(50):
    Gtk.main_iteration_do(False)
    time.sleep(0.01)

general_path = os.path.join(artifact_dir, "macos_settings_general.png")
capture_window_to_file(win, general_path)

# Switch to storage
win.select_tab("storage")
for _ in range(50):
    Gtk.main_iteration_do(False)
    time.sleep(0.01)

storage_path = os.path.join(artifact_dir, "macos_settings_storage.png")
capture_window_to_file(win, storage_path)

win.destroy()
print("Done capturing screenshots.")
