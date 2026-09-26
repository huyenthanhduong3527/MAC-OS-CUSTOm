import os
import sys
import time
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.ui.macos_notes_window import MacOSNotesWindow

def run_test():
    win = MacOSNotesWindow.get_instance()
    
    events_log = []
    
    def log_event(widget, event, name):
        events_log.append((time.time(), name, getattr(event, "type", None)))
        return False

    win.connect("map-event", lambda w, e: log_event(w, e, "map-event"))
    win.connect("unmap-event", lambda w, e: log_event(w, e, "unmap-event"))
    win.connect("configure-event", lambda w, e: log_event(w, e, "configure-event"))
    win.connect("window-state-event", lambda w, e: log_event(w, e, f"window-state-event (state={e.new_window_state})"))
    win.connect("draw", lambda w, cr: log_event(w, None, "draw"))

    win.show_all()
    win.present()

    def step1_minimize():
        print("Step 1: Iconifying window...")
        win.iconify()
        GLib.timeout_add(1500, step2_unminimize)
        return False

    def step2_unminimize():
        print("Step 2: Deiconifying window...")
        win.deiconify()
        win.present()
        GLib.timeout_add(1500, step3_finish)
        return False

    def step3_finish():
        print(f"Total events recorded: {len(events_log)}")
        for t, name, etype in events_log:
            print(f"[{t:.3f}] {name}")
        Gtk.main_quit()
        return False

    GLib.timeout_add(1000, step1_minimize)
    Gtk.main()

if __name__ == "__main__":
    run_test()
