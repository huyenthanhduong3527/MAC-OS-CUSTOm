#!/usr/bin/env python3
"""
Dynamic Island for GNOME on Ubuntu.
An Apple-style, physics-animated Dynamic Island for Linux.
"""

import os
import sys
import signal

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Only force X11 backend for the Dynamic Island overlay daemon (for absolute top-center dock positioning).
# Standalone desktop apps (Notes, Photo Booth, Settings, Photos, AppStore, AirDrop, etc.) must use
# the native session backend (Wayland/X11) for buttery-smooth Dash to Dock / Mutter animations.
STANDALONE_COMMANDS = {
    "notes", "note", "mac-notes", "standalone-notes", "memo",
    "photos", "gallery", "standalone-photos", "mac-photos",
    "airdrop", "mac-airdrop", "standalone-airdrop", "share",
    "appstore", "store", "app-store", "mac-appstore", "standalone-appstore", "snap-store", "appcenter",
    "photobooth", "photo-booth", "mac-photobooth", "standalone-photobooth", "vcam", "virtualcam",
    "settings", "preferences", "system-settings", "macos-settings", "standalone-settings",
    "theme", "toggle-theme", "dark", "light",
    "spotlight", "search", "spotlight-search"
}
args_check = [a.lstrip("-") for a in sys.argv[1:]]
is_standalone_app = any(cmd in STANDALONE_COMMANDS for cmd in args_check) or any(a.lower().endswith(".deb") for a in sys.argv[1:])

if not is_standalone_app and "GDK_BACKEND" not in os.environ:
    os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

try:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)
except Exception:
    pass

from src.window import DynamicIslandWindow
from src.ipc import send_command, IPCServer

def main():
    # Parse CLI flags
    args = sys.argv[1:]
    if args:
        # Check if any argument is a .deb file
        deb_file = None
        for arg in args:
            clean_arg = arg.strip("'\"")
            if clean_arg.lower().endswith(".deb") and os.path.exists(clean_arg):
                deb_file = os.path.abspath(clean_arg)
                break

        if deb_file:
            import shlex
            ipc_cmd = f"install-deb {shlex.quote(deb_file)}"
            if send_command(ipc_cmd):
                print(f"Sent '{ipc_cmd}' to running Dynamic Island.")
                return

            from src.ui.macos_deb_installer import MacOSDebInstallerDialog
            print(f"📦 Starting macOS Package Installer for {deb_file}...")
            w = MacOSDebInstallerDialog(deb_file)
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            w.present()
            Gtk.main()
            return

        cmd_name = args[0].lstrip("-")
        rest = " ".join(args[1:])
        cmd = f"{cmd_name} {rest}".strip()

        if cmd_name in ("notes", "note", "mac-notes", "standalone-notes", "memo"):
            import subprocess
            try:
                res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=1.0)
                for line in res.stdout.splitlines():
                    if "Ghi chú" in line or "macOS Notes" in line or "macos-notes" in line:
                        subprocess.run(["wmctrl", "-a", line.split(None, 3)[-1]], timeout=1.0)
                        print("Notes window already open, brought to front.")
                        return
            except Exception:
                pass

            GLib.set_prgname("macos-notes")
            GLib.set_application_name("Ghi chú")
            from src.ui.macos_notes_window import MacOSNotesWindow
            print("🚀 Starting standalone macOS Notes (Ghi chú)...")
            w = MacOSNotesWindow.get_instance()
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_all()
            w.present()
            Gtk.main()
            return

        if cmd_name in ("photos", "gallery", "standalone-photos", "mac-photos"):
            GLib.set_prgname("macos-photos")
            GLib.set_application_name("Ảnh")
            from src.ui.macos_photos_window import MacOSPhotosWindow
            print("🚀 Starting standalone macOS Photos (Ảnh)...")
            w = MacOSPhotosWindow.get_instance()
            w.is_standalone = True
            w.set_picker_mode(False)
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_all()
            w.lightbox.hide()
            w.inspector_panel.hide()
            w.select_action_bar.hide()
            w.present()
            Gtk.main()
            return

        if cmd_name in ("airdrop", "mac-airdrop", "standalone-airdrop", "share"):
            GLib.set_prgname("macos-airdrop")
            GLib.set_application_name("AirDrop")
            from src.ui.macos_airdrop_window import MacOSAirDropWindow
            print("🚀 Starting macOS AirDrop...")
            w = MacOSAirDropWindow.get_instance()
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_window()
            Gtk.main()
            return

        if cmd_name in ("appstore", "store", "app-store", "mac-appstore", "standalone-appstore", "snap-store", "appcenter"):
            GLib.set_prgname("macos-appstore")
            GLib.set_application_name("App Store")
            from src.ui.macos_appstore_window import MacOSAppStoreWindow
            print("🚀 Starting standalone macOS Sequoia App Store...")
            w = MacOSAppStoreWindow.get_instance()
            w.is_standalone = True
            w.show_all()
            w.present()
            Gtk.main()
            return

        if cmd_name in ("photobooth", "photo-booth", "mac-photobooth", "standalone-photobooth", "vcam", "virtualcam"):
            import subprocess
            try:
                res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=1.0)
                for line in res.stdout.splitlines():
                    if "Photo Booth" in line:
                        subprocess.run(["wmctrl", "-a", "Photo Booth"], timeout=1.0)
                        print("Photo Booth window already open, brought to front.")
                        return
            except Exception:
                pass

            GLib.set_prgname("macos-photobooth")
            GLib.set_application_name("Photo Booth")
            from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
            print("🚀 Starting standalone macOS Photo Booth & Virtual Camera...")
            w = MacOSPhotoBoothWindow.get_instance()
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_and_present()
            Gtk.main()
            return

        if cmd_name in ("settings", "preferences", "system-settings", "macos-settings", "standalone-settings"):
            tab = rest.strip() if rest.strip() else "general"
            if not cmd_name.startswith("standalone") and send_command(f"settings {tab}"):
                print(f"Sent 'settings {tab}' to running Dynamic Island.")
                return
            GLib.set_prgname("macos-settings")
            GLib.set_application_name("Cài đặt hệ thống")
            from src.ui.macos_settings_window import MacOSSettingsWindow
            print(f"🚀 Starting macOS System Settings ({tab})...")
            w = MacOSSettingsWindow.get_instance()
            w.connect("destroy", Gtk.main_quit)
            w.show_window(tab)
            Gtk.main()
            return

        # Try sending to running instance (except for explicit standalone-* flags)
        if not cmd_name.startswith("standalone") and send_command(cmd):
            print(f"Sent '{cmd}' to running Dynamic Island.")
            return

        if cmd_name in ("theme", "toggle-theme", "dark", "light"):
            from src.utils.theme import toggle_dark_mode
            is_dark = toggle_dark_mode()
            print(f"✨ Theme switched to {'Dark' if is_dark else 'Light'} mode.")
            return

        if cmd_name in ("clock", "standalone-clock", "widget"):
            from src.ui.desktop_widgets.clock_widget import DesktopClockWidget
            print("🚀 Starting standalone macOS Clock Widget...")
            w = DesktopClockWidget()
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("music-widget", "standalone-music"):
            from src.modules.media import MediaManager
            from src.ui.desktop_widgets.music_widget import DesktopMusicWidget
            print("🚀 Starting standalone macOS Music Widget...")
            mm = MediaManager()
            w = DesktopMusicWidget(mm)
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("calendar-widget", "standalone-calendar", "calendar"):
            from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
            print("🚀 Starting standalone macOS Calendar & Lunar Widget...")
            w = DesktopCalendarWidget()
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("weather-dialog", "weather-location", "weather-settings"):
            from src.modules.weather import WeatherManager
            from src.ui.desktop_widgets.weather_widget import WeatherLocationDialog, DesktopWeatherWidget
            print("🚀 Opening macOS Weather Location Dialog...")
            w = DesktopWeatherWidget()
            dlg = WeatherLocationDialog(w, w.weather_mgr)
            dlg.connect("destroy", Gtk.main_quit)
            dlg.show_all()
            Gtk.main()
            return

        if cmd_name in ("weather-widget", "standalone-weather", "weather"):
            from src.modules.weather import WeatherManager
            from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
            print("🚀 Starting standalone macOS Weather Widget...")
            wm = WeatherManager()
            w = DesktopWeatherWidget(wm)
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("battery-widget", "standalone-battery", "battery"):
            from src.modules.battery import BatteryMonitor
            from src.ui.desktop_widgets.battery_widget import DesktopBatteryWidget
            print("🚀 Starting standalone macOS 4-Ring Battery Widget...")
            bm = BatteryMonitor()
            w = DesktopBatteryWidget(bm)
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("settings", "preferences", "standalone-settings", "system-settings"):
            from src.ui.macos_settings_window import MacOSSettingsWindow
            print("🚀 Starting macOS System Settings...")
            w = MacOSSettingsWindow.get_instance()
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_window()
            Gtk.main()
            return

        if cmd_name in ("spotlight", "search", "spotlight-search"):
            from src.ui.spotlight_search import SpotlightSearchWindow
            print("🚀 Starting macOS Spotlight Search...")
            w = SpotlightSearchWindow.get_instance()
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_spotlight()
            Gtk.main()
            return

        if cmd_name in ("widgets", "desktop-widgets", "all-widgets"):
            if send_command("toggle-calendar"):
                send_command("toggle-weather")
                send_command("toggle-battery")
                print("✨ Toggled Desktop Widgets on running Dynamic Island.")
                return
            from src.ui.desktop_widgets.calendar_widget import DesktopCalendarWidget
            from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
            from src.ui.desktop_widgets.battery_widget import DesktopBatteryWidget
            print("🚀 Starting macOS Desktop Widgets...")
            cw = DesktopCalendarWidget()
            ww = DesktopWeatherWidget()
            bw = DesktopBatteryWidget()
            cw.show_all()
            ww.show_all()
            bw.show_all()
            cw.connect("destroy", Gtk.main_quit)
            Gtk.main()
            return

        if cmd_name in ("photo-widget", "standalone-photo", "photo"):
            from src.ui.desktop_widgets.photo_widget import DesktopPhotoWidget
            print("🚀 Starting standalone macOS Photo Widget...")
            w = DesktopPhotoWidget()
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("weekday-widget", "standalone-weekday", "weekday-clock", "weekday"):
            from src.ui.desktop_widgets.weekday_clock_widget import DesktopWeekdayClockWidget
            print("🚀 Starting standalone macOS Weekday Clock Widget...")
            w = DesktopWeekdayClockWidget()
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("macbook-widget", "standalone-macbook", "macbook"):
            from src.ui.desktop_widgets.macbook_widget import DesktopMacBookWidget
            print("🚀 Starting standalone macOS MacBook Widget...")
            w = DesktopMacBookWidget()
            w.connect("destroy", Gtk.main_quit)
            w.show_all()
            Gtk.main()
            return

        if cmd_name in ("wallpaper", "live-wallpaper", "live_wallpaper"):
            import subprocess
            script = os.path.join(BASE_DIR, "scripts", "live_wallpaper.py")
            sub_args = args[1:] if len(args) > 1 else ["status"]
            subprocess.run([sys.executable, script] + sub_args)
            return

        if cmd_name in ("control-center", "control", "cc", "controlcenter"):
            from src.ui.macos_control_center import MacOSControlCenterWindow
            print("🚀 Starting macOS Control Center...")
            w = MacOSControlCenterWindow.get_instance()
            w._is_standalone = True
            w.connect("delete-event", lambda *_: Gtk.main_quit())
            w.show_control_center()
            Gtk.main()
            return

        if cmd_name in ("size", "resize"):
            from src.config import config
            sub_args = args[1:]
            if not sub_args:
                cw = config.get("compact_width", 230)
                ch = config.get("compact_height", 40)
                ew = config.get("expanded_width", 505)
                eh = config.get("expanded_height", 280)
                y = config.get("y_offset", 44)
                print("📏 Dynamic Island Dimensions:")
                print(f"   Compact (Pill):   {cw} x {ch} px")
                print(f"   Expanded (Card):  {ew} x {eh} px")
                print(f"   Top Offset (Y):   {y} px")
                return
            try:
                if sub_args[0].lower() == "compact" and len(sub_args) >= 3:
                    config.set("compact_width", int(sub_args[1]))
                    config.set("compact_height", int(sub_args[2]))
                    print(f"✨ Updated compact dimensions to {sub_args[1]}x{sub_args[2]}px in config.")
                elif sub_args[0].lower() == "expanded" and len(sub_args) >= 3:
                    config.set("expanded_width", int(sub_args[1]))
                    config.set("expanded_height", int(sub_args[2]))
                    print(f"✨ Updated expanded dimensions to {sub_args[1]}x{sub_args[2]}px in config.")
                elif len(sub_args) >= 4:
                    config.set("compact_width", int(sub_args[0]))
                    config.set("compact_height", int(sub_args[1]))
                    config.set("expanded_width", int(sub_args[2]))
                    config.set("expanded_height", int(sub_args[3]))
                    print(f"✨ Updated dimensions in config: Compact={sub_args[0]}x{sub_args[1]}px, Expanded={sub_args[2]}x{sub_args[3]}px.")
                elif len(sub_args) >= 2:
                    config.set("compact_width", int(sub_args[0]))
                    config.set("compact_height", int(sub_args[1]))
                    print(f"✨ Updated compact dimensions to {sub_args[0]}x{sub_args[1]}px in config.")
            except Exception as e:
                print(f"Error updating dimensions: {e}")
            return

        # If it was a control command, do not start a redundant second process
        if cmd_name in ("toggle", "expand", "collapse", "tab", "media", "vitals", "controls", "timer", "settings", "notifs", "quit", "hide", "toggle-clock", "toggle-music-widget", "toggle-calendar", "toggle-weather", "toggle-battery", "calendar", "weather", "weather-dialog", "weather-location", "weather-settings", "battery", "bright", "brightness", "size", "resize", "toggle-appstore", "close-appstore", "photo", "photo-widget", "weekday", "weekday-clock", "macbook", "macbook-widget"):
            print(f"Notice: Dynamic Island is not currently active to handle '{cmd}'.")
            return
    else:
        # If already running, toggle expand/collapse without spawning duplicate
        if send_command("toggle"):
            print("✨ Dynamic Island is already running. Toggled window.")
            return

    # Check if another instance is already running via ping
    if send_command("ping"):
        print("✨ Dynamic Island is already running.")
        return

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Disable GNOME Mutter unresponsiveness modal for seamless background overlay
    import subprocess
    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.mutter", "check-alive-timeout", "0"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
        )
    except Exception:
        pass

    GLib.set_prgname("dynamic-island")
    GLib.set_application_name("Dynamic Island")

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
