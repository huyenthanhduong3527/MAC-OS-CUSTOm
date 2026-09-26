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

is_system_dark_mode = is_dark_mode

def set_dark_mode(is_dark: bool) -> bool:
    """Set system color-scheme to dark or light mode."""
    new_scheme = "prefer-dark" if is_dark else "default"
    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", new_scheme],
            timeout=1
        )
    except Exception as e:
        print(f"[Theme] Error setting color-scheme: {e}")

    home = os.path.expanduser("~")
    curr_accent = "blue"
    try:
        res = subprocess.check_output(
            ["gsettings", "get", "org.gnome.desktop.interface", "accent-color"],
            timeout=1
        ).decode().strip().strip("'\"")
        if res:
            curr_accent = res
    except Exception:
        pass

    if curr_accent == "slate":
        mactahoe_col = "grey"
    elif curr_accent in ("multi", ""):
        mactahoe_col = "blue"
    else:
        mactahoe_col = curr_accent

    mode = "Dark" if is_dark else "Light"
    candidate = f"MacTahoe-{mode}-{mactahoe_col}"
    if os.path.exists(os.path.join(home, ".themes", candidate)):
        target_theme = candidate
    else:
        target_theme = f"MacTahoe-{mode}"

    theme_path = os.path.join(home, ".themes", target_theme)
    if os.path.exists(theme_path):
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", target_theme],
                timeout=1
            )
        except Exception as e:
            print(f"[Theme] Error setting gtk-theme: {e}")
    return is_dark

def toggle_dark_mode() -> bool:
    """
    Toggle between dark and light mode.
    Returns True if the new mode is dark, False if light.
    """
    return set_dark_mode(not is_dark_mode())
