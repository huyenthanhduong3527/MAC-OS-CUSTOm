import os
import sys
import gi
import time

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from src.ui.macos_notes_window import MacOSNotesWindow
from src.ui.macos_settings_window import MacOSSettingsWindow
from src.ui.macos_appstore_window import MacOSAppStoreWindow
from src.modules.notes_storage import NotesManager

ARTIFACT_DIR = "/home/tramvo/.gemini/antigravity-ide/brain/5c8b0e90-4565-4787-8bdd-54594301fbfc"

def capture_window_pixbuf(win, filename):
    win.show_all()
    # Let GTK process redraws and layout
    for _ in range(30):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.02)

    alloc = win.get_allocation()
    width = max(alloc.width, 800)
    height = max(alloc.height, 600)

    gdk_win = win.get_window()
    if gdk_win:
        pb = Gdk.pixbuf_get_from_window(gdk_win, 0, 0, width, height)
        if pb:
            out_path = os.path.join(ARTIFACT_DIR, filename)
            pb.savev(out_path, "png", [], [])
            print(f"Captured: {out_path} ({width}x{height})")
            return out_path
    print(f"Failed to capture {filename}")
    return None

def main():
    print("Testing Notes window...")
    notes_storage = NotesManager.get_instance()
    notes_win = MacOSNotesWindow()
    # Select audio note
    notes = notes_storage.get_notes(folder_id="audio")
    if not notes:
        notes = notes_storage.get_all_notes()
    for n in notes:
        if n.get("audio_file") or n.get("id") == "sample_call_note":
            notes_win.select_note(n)
            break
    notes_win.toggle_audio_inspector()
    capture_window_pixbuf(notes_win, "notes_audio_redesign.png")
    notes_win.destroy()

    print("Testing Settings window...")
    settings_win = MacOSSettingsWindow()
    capture_window_pixbuf(settings_win, "settings_vietnamese_rounded.png")
    settings_win.destroy()

    print("Testing App Store window...")
    store_win = MacOSAppStoreWindow()
    capture_window_pixbuf(store_win, "appstore_vietnamese.png")
    store_win.destroy()

    print("All captures finished!")

if __name__ == "__main__":
    main()
