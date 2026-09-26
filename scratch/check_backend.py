import os
import sys
import time
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

def main():
    display = Gdk.Display.get_default()
    print("Default Display:", display.get_name() if display else "None")
    print("Backend:", type(display).__name__)

if __name__ == "__main__":
    main()
