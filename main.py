#!/usr/bin/env python3
"""
Dynamic Island for GNOME on Ubuntu.
An Apple-style, physics-animated Dynamic Island for Linux.
"""

import os
import sys
import signal

# Ensure GDK uses X11 backend for precise overlay positioning on Wayland/XWayland
if "GDK_BACKEND" not in os.environ:
    os.environ["GDK_BACKEND"] = "x11"

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from src.window import DynamicIslandWindow
from src.ipc import send_command, IPCServer

def main():
    # Parse CLI flags
    args = sys.argv[1:]
    if args:
        cmd_name = args[0].lstrip("-")
        rest = " ".join(args[1:])
        cmd = f"{cmd_name} {rest}".strip()

        # Try sending to running instance
        if send_command(cmd):
            print(f"Sent '{cmd}' to running Dynamic Island.")
            return

        if cmd_name in ("theme", "toggle-theme", "dark", "light"):
            from src.utils.theme import toggle_dark_mode
            is_dark = toggle_dark_mode()
            print(f"✨ Theme switched to {'Dark' if is_dark else 'Light'} mode.")
            return
    else:
        # If already running, toggle expand/collapse without spawning duplicate
        if send_command("toggle"):
            print("✨ Dynamic Island is already running. Toggled window.")
            return

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    print("🚀 Starting Dynamic Island for GNOME...")
    app = DynamicIslandWindow()
    ipc = IPCServer(app)

    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("\n👋 Exiting Dynamic Island...")
    finally:
        ipc.stop()
        app.quit_app()

if __name__ == "__main__":
    main()
