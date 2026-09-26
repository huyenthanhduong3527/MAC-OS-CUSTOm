import os
import sys
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.ui.macos_notes_window import MacOSNotesWindow
from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
from src.ui.macos_settings_window import MacOSSettingsWindow
from src.ui.macos_photos_window import MacOSPhotosWindow
from src.ui.macos_appstore_window import MacOSAppStoreWindow
from src.ui.macos_airdrop_window import MacOSAirDropWindow

def test_app(name, create_fn):
    print(f"Testing {name}...")
    win = create_fn()
    win.realize()
    gdk_win = win.get_window()
    print(f"  -> Realized window: {type(gdk_win).__name__}")
    print(f"  -> Title: {win.get_title()}")
    print(f"  -> prgname: {GLib.get_prgname()}")
    win.destroy()
    print(f"  -> {name} PASSED!\n")

def main():
    test_app("Notes", lambda: MacOSNotesWindow())
    test_app("Settings", lambda: MacOSSettingsWindow())
    test_app("Photos", lambda: MacOSPhotosWindow())
    test_app("AirDrop", lambda: MacOSAirDropWindow())
    test_app("AppStore", lambda: MacOSAppStoreWindow())
    test_app("PhotoBooth", lambda: MacOSPhotoBoothWindow())

if __name__ == "__main__":
    main()
