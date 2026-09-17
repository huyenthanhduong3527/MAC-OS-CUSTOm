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
        elif action == "settings":
            self.app.expand()
            self.app.expanded_view.switch_to_tab("settings")
        elif action in ("notifs", "notifications"):
            self.app.expand()
            self.app.expanded_view.switch_to_tab("notifs")
        elif action in ("clear-notifs", "clearnotifs"):
            self.app.notif_mgr.clear_all()
        elif action == "notify":
            app_name = parts[1] if len(parts) > 1 else "System"
            title = parts[2] if len(parts) > 2 else "Notice"
            body = " ".join(parts[3:]) if len(parts) > 3 else ""
            self.app._on_notification_received(app_name, title, body)
        elif action in ("theme", "toggle-theme", "dark", "light"):
            from src.utils.theme import toggle_dark_mode
            toggle_dark_mode()
            if hasattr(self.app, "expanded_view") and hasattr(self.app.expanded_view, "controls_tab"):
                self.app.expanded_view.controls_tab.update()
        elif action in ("cosmos", "orbit", "solar", "toggle-cosmos", "toggle-orbit"):
            self.app.toggle_cosmic_orbit()
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
