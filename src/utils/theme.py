"""
Theme helper for Dynamic Island and GNOME Desktop.
Handles detecting and toggling between Dark Mode and Light Mode.
"""

import os
import subprocess

def is_dark_mode() -> bool:
    """Return True if system color-scheme is set to prefer-dark."""
    try:
        res = subprocess.check_output(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            timeout=1
        ).decode().strip().strip("'")
        return res == "prefer-dark"
    except Exception:
        return False

def toggle_dark_mode() -> bool:
    """
    Toggle between dark and light mode.
    Returns True if the new mode is dark, False if light.
    """
    current_dark = is_dark_mode()
    new_is_dark = not current_dark
    new_scheme = "prefer-dark" if new_is_dark else "default"

    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", new_scheme],
            timeout=1
        )
    except Exception as e:
        print(f"[Theme] Error setting color-scheme: {e}")

    # Synchronize GTK theme if MacTahoe themes exist
    home = os.path.expanduser("~")
    target_theme = "MacTahoe-Dark" if new_is_dark else "MacTahoe-Light"
    theme_path = os.path.join(home, ".themes", target_theme)
    if os.path.exists(theme_path):
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", target_theme],
                timeout=1
            )
        except Exception as e:
            print(f"[Theme] Error setting gtk-theme: {e}")

    return new_is_dark
