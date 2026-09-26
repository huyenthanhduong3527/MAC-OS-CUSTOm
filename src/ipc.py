"""
IPC (Inter-Process Communication) for Dynamic Island.
Enables single-instance enforcement and CLI control (toggle, expand, collapse, switch tab).
"""

import os
import socket
import threading
from gi.repository import GLib

SOCKET_PATH = os.path.expanduser("~/.config/dynamic_island/ipc.sock")

def send_command(command: str) -> bool:
    """Send command to running instance if available. Returns True if successful."""
    if not os.path.exists(SOCKET_PATH):
        return False

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(1.0)
        client.connect(SOCKET_PATH)
        client.sendall(command.encode("utf-8"))
        client.close()
        return True
    except Exception:
        # Socket file exists but stale
        try:
            os.remove(SOCKET_PATH)
        except OSError:
            pass
        return False


class IPCServer:
    def __init__(self, app):
        self.app = app
        self._running = True
        self._server = None

        os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
        if os.path.exists(SOCKET_PATH):
            test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                test_sock.settimeout(0.5)
                test_sock.connect(SOCKET_PATH)
                test_sock.close()
                raise RuntimeError("Another Dynamic Island instance is already running.")
            except (socket.error, OSError):
                # Socket file is dead/stale, safe to remove
                try:
                    os.remove(SOCKET_PATH)
                except OSError:
                    pass

        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(SOCKET_PATH)
        self._server.listen(5)

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def _listen_loop(self):
        while self._running:
            try:
                conn, _ = self._server.accept()
                data = conn.recv(1024).decode("utf-8").strip()
                conn.close()
                if data:
                    if data.lower() == "ping":
                        continue
                    GLib.idle_add(self._handle_command, data)
            except Exception:
                break

    def _handle_command(self, cmd):
        try:
            import shlex
            parts = shlex.split(cmd)
        except Exception:
            parts = cmd.split()

        if not parts:
            return
        action = parts[0].lower()

        if action == "toggle":
            if self.app.state == "expanded":
                self.app.collapse()
            else:
                self.app.expand()
        elif action == "expand":
            self.app.expand()
        elif action == "collapse":
            self.app.collapse()
        elif action == "tab" and len(parts) > 1:
            tab_name = parts[1].lower()
            self.app.expand()
            self.app.expanded_view.switch_to_tab(tab_name)
        elif action == "media":
            self.app.expand()
            self.app.expanded_view.switch_to_tab("media")
        elif action == "vitals":
            self.app.expand()
            self.app.expanded_view.switch_to_tab("vitals")
        elif action == "controls":
            self.app.expand()
            self.app.expanded_view.switch_to_tab("controls")
        elif action == "timer":
            self.app.expand()
            self.app.expanded_view.switch_to_tab("timer")
        elif action in ("settings", "preferences", "system-settings"):
            tab = parts[1].lower() if len(parts) > 1 else "general"
            self.app.open_macos_settings_window(tab)
        elif action in ("notifs", "notifications"):
            self.app.expand()
            self.app.expanded_view.switch_to_tab("notifs")
        elif action in ("clear-notifs", "clearnotifs"):
            self.app.notif_mgr.clear_all()
        elif action in ("clip-copy", "copy") and len(parts) > 1:
            copy_text = cmd[len(parts[0]):].strip()
            if hasattr(self.app, "clipboard_mgr"):
                self.app.clipboard_mgr.copy_to_clipboard(copy_text)
        elif action == "notify":
            app_name = parts[1] if len(parts) > 1 else "System"
            title = parts[2] if len(parts) > 2 else "Notice"
            body = " ".join(parts[3:]) if len(parts) > 3 else ""
            self.app._on_notification_received(app_name, title, body)
        elif action in ("airdrop-received", "airdrop_received"):
            filename = parts[1] if len(parts) > 1 else "Tệp tin"
            file_path = parts[2] if len(parts) > 2 else ""
            if hasattr(self.app, "_on_airdrop_received"):
                self.app._on_airdrop_received(filename, file_path)
            elif hasattr(self.app, "_on_airdrop_transfer_event"):
                self.app._on_airdrop_transfer_event("complete", {
                    "filename": filename,
                    "file_path": file_path,
                    "is_incoming": True
                })
        elif action in ("theme", "toggle-theme", "dark", "light"):
            from src.utils.theme import toggle_dark_mode
            toggle_dark_mode()
            if hasattr(self.app, "expanded_view") and hasattr(self.app.expanded_view, "controls_tab"):
                self.app.expanded_view.controls_tab.update()
        elif action in ("set-language", "language", "lang") and len(parts) > 1:
            lang = parts[1].strip()
            from src.utils.i18n import set_language
            set_language(lang, apply_system=False)
            if hasattr(self.app, "update_language"):
                self.app.update_language(lang)
        elif action in ("siri", "qwen", "ask-siri", "gemini", "ask-gemini", "ai"):
            self.app.expand()
            if hasattr(self.app, "expanded_view"):
                self.app.expanded_view.switch_to_tab("gemini")
                if len(parts) > 1 and hasattr(self.app.expanded_view, "gemini_tab"):
                    query_text = " ".join(parts[1:])
                    self.app.expanded_view.gemini_tab._submit_prompt(query_text)
        elif action in ("cosmos", "orbit", "solar", "toggle-cosmos", "toggle-orbit"):
            self.app.toggle_cosmic_orbit()
        elif action in ("spotlight", "search", "spotlight-search"):
            if hasattr(self.app, "toggle_spotlight"):
                self.app.toggle_spotlight()
        elif action in ("control-center", "control", "cc", "controlcenter"):
            if hasattr(self.app, "toggle_control_center"):
                self.app.toggle_control_center()
        elif action in ("control-center-close", "control-center-hide", "hide-control-center", "close-control-center"):
            if hasattr(self.app, "hide_control_center"):
                self.app.hide_control_center()
        elif action in ("calendar-dialog", "calendar-window", "open-calendar", "lunar-dialog"):
            if hasattr(self.app, "open_calendar_dialog"):
                self.app.open_calendar_dialog()
        elif action in ("calendar", "toggle-calendar", "calendar-widget"):
            if hasattr(self.app, "toggle_desktop_calendar"):
                self.app.toggle_desktop_calendar()
        elif action in ("weather-dialog", "weather-location", "weather-settings", "weather-loc"):
            if hasattr(self.app, "open_weather_dialog"):
                self.app.open_weather_dialog()
        elif action in ("weather", "toggle-weather", "weather-widget"):
            if hasattr(self.app, "toggle_desktop_weather"):
                self.app.toggle_desktop_weather()
        elif action in ("battery", "toggle-battery", "battery-widget"):
            if hasattr(self.app, "toggle_desktop_battery"):
                self.app.toggle_desktop_battery()
        elif action in ("clock", "toggle-clock", "clock-widget"):
            if hasattr(self.app, "toggle_desktop_clock"):
                self.app.toggle_desktop_clock()
        elif action in ("music-widget", "toggle-music-widget", "desktop-music"):
            if hasattr(self.app, "toggle_desktop_music"):
                self.app.toggle_desktop_music()
        elif action in ("airdrop", "open-airdrop", "mac-airdrop", "share-airdrop"):
            if hasattr(self.app, "open_airdrop_window"):
                self.app.open_airdrop_window()
            else:
                from src.ui.macos_airdrop_window import MacOSAirDropWindow
                win = MacOSAirDropWindow.get_instance()
                win.show_window()
        elif action in ("notes", "note", "open-notes", "macos-notes"):
            from src.ui.macos_notes_window import MacOSNotesWindow
            try:
                w = MacOSNotesWindow.get_instance()
                w.show_all()
                w.present()
            except Exception as e:
                print(f"[IPC] Re-initializing Notes window after error: {e}")
                MacOSNotesWindow._instance = None
                w = MacOSNotesWindow.get_instance()
                w.show_all()
                w.present()
        elif action in ("photos", "gallery", "open-photos", "macos-photos"):
            from src.ui.macos_photos_window import MacOSPhotosWindow
            try:
                w = MacOSPhotosWindow.get_instance()
                w.set_picker_mode(False)
                w.show_all()
                w.lightbox.hide()
                w.inspector_panel.hide()
                w.select_action_bar.hide()
                w.present()
            except Exception as e:
                print(f"[IPC] Re-initializing Photos window after error: {e}")
                MacOSPhotosWindow._instance = None
                w = MacOSPhotosWindow.get_instance()
                w.set_picker_mode(False)
                w.show_all()
                w.lightbox.hide()
                w.inspector_panel.hide()
                w.select_action_bar.hide()
                w.present()
        elif action in ("photobooth", "photo-booth", "open-photobooth", "vcam", "virtualcam"):
            def _open_pb():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w.show_and_present()
                except Exception as e:
                    print(f"[IPC] Error opening Photo Booth: {e}")
                return False
            GLib.idle_add(_open_pb)
        elif action in ("photobooth-4up", "photobooth-mode-4up"):
            def _set_4up():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w._set_capture_mode("4up")
                    w.show_and_present()
                except Exception as e:
                    print(f"[IPC] Error setting 4up: {e}")
                return False
            GLib.idle_add(_set_4up)
        elif action in ("photobooth-video", "photobooth-mode-video"):
            def _set_vid():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w._set_capture_mode("video")
                    w.show_and_present()
                except Exception as e:
                    print(f"[IPC] Error setting video: {e}")
                return False
            GLib.idle_add(_set_vid)
        elif action in ("photobooth-single", "photobooth-mode-single"):
            def _set_single():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w._set_capture_mode("single")
                    w.show_and_present()
                except Exception as e:
                    print(f"[IPC] Error setting single: {e}")
                return False
            GLib.idle_add(_set_single)
        elif action in ("photobooth-shutter", "photobooth-snap", "photobooth-capture"):
            def _snap():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w._on_shutter_press()
                except Exception as e:
                    print(f"[IPC] Error snapping: {e}")
                return False
            GLib.idle_add(_snap)
        elif action in ("photobooth-menu", "photobooth-context-menu"):
            def _open_pb_menu():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w.show_and_present()
                    w._show_camera_menu(w.btn_phone_cam)
                except Exception as e:
                    print(f"[IPC] Error opening Photo Booth menu: {e}")
                return False
            GLib.idle_add(_open_pb_menu)
        elif action in ("photobooth-sheet", "photobooth-continuity", "photobooth-qr"):
            def _open_pb_sheet():
                try:
                    from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
                    w = MacOSPhotoBoothWindow.get_instance()
                    w.show_and_present()
                    w._toggle_continuity_sheet(True)
                except Exception as e:
                    print(f"[IPC] Error opening Photo Booth sheet: {e}")
                return False
            GLib.idle_add(_open_pb_sheet)
        elif action in ("install-deb", "deb-installer", "pkg-installer", "open-deb") or (action in ("appstore", "store", "snap-store", "appcenter") and len(parts) > 1 and parts[1].lower().endswith(".deb")):
            deb_path = parts[1] if len(parts) > 1 else ""
            if deb_path and os.path.exists(deb_path):
                from src.ui.macos_deb_installer import MacOSDebInstallerDialog
                w = MacOSDebInstallerDialog(deb_path)
                w.show_all()
                w.present()
        elif action in ("appstore", "store", "open-appstore", "app-store", "snap-store", "appcenter", "mac-appstore"):
            from src.ui.macos_appstore_window import MacOSAppStoreWindow
            w = MacOSAppStoreWindow.get_instance()
            w.show_all()
            w.present()
        elif action in ("toggle-appstore", "toggle-store", "toggle-appcenter"):
            from src.ui.macos_appstore_window import MacOSAppStoreWindow
            w = MacOSAppStoreWindow.get_instance()
            if w.is_visible():
                w.close_window()
            else:
                w.show_all()
                w.present()
        elif action in ("close-appstore", "hide-appstore", "close-appcenter"):
            from src.ui.macos_appstore_window import MacOSAppStoreWindow
            w = MacOSAppStoreWindow.get_instance()
            w.close_window()
        elif action in ("bright", "brightness") and len(parts) > 1:
            try:
                val_str = parts[1]
                if hasattr(self.app, "brightness_ctrl"):
                    cur = self.app.brightness_ctrl.get_brightness()
                    if val_str.startswith("+"):
                        target = min(100, cur + int(val_str[1:]))
                    elif val_str.startswith("-"):
                        target = max(10, cur - int(val_str[1:]))
                    else:
                        target = max(10, min(100, int(val_str)))
                    self.app.brightness_ctrl.set_brightness(target)
            except Exception:
                pass
        elif action in ("size", "resize"):
            try:
                if len(parts) >= 4 and parts[1].lower() == "compact":
                    cw, ch = int(parts[2]), int(parts[3])
                    self.app._on_size_changed(compact_w=cw, compact_h=ch)
                elif len(parts) >= 4 and parts[1].lower() == "expanded":
                    ew, eh = int(parts[2]), int(parts[3])
                    self.app._on_size_changed(expanded_w=ew, expanded_h=eh)
                elif len(parts) >= 5:
                    cw, ch, ew, eh = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                    self.app._on_size_changed(compact_w=cw, compact_h=ch, expanded_w=ew, expanded_h=eh)
                elif len(parts) >= 3:
                    cw, ch = int(parts[1]), int(parts[2])
                    self.app._on_size_changed(compact_w=cw, compact_h=ch)
            except Exception as e:
                print(f"[IPC] Error handling size command: {e}")
        elif action == "quit":
            self.app.quit_app()

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        if os.path.exists(SOCKET_PATH):
            try:
                os.remove(SOCKET_PATH)
            except OSError:
                pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        res = send_command(cmd)
        print(f"Sent '{cmd}': {res}")
