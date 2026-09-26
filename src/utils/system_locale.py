"""
System Locale & Language Manager for Ubuntu / Linux GNOME.
Applies language changes across all layers of the operating system:
1. AccountsService D-Bus (User.SetLanguage, User.SetLanguages)
2. systemd User Locale (~/.config/locale.conf)
3. GNOME Desktop GSettings (org.gnome.system.locale region)
4. Active process environment (LANG, LANGUAGE, LC_*)
5. Automatic libc locale generation via locale-gen if needed
6. Authentic Apple macOS Sequoia Restart / Log Out modal confirmation
"""

import os
import subprocess
import threading
from typing import Dict, Any, Optional

import gi
gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk

def is_locale_generated(locale_name: str) -> bool:
    """Checks if the given locale is already compiled in locale -a."""
    try:
        out = subprocess.check_output(["locale", "-a"], timeout=2.0).decode("utf-8", errors="ignore")
        clean = locale_name.replace(".UTF-8", "").replace(".utf8", "").lower()
        for line in out.splitlines():
            line_clean = line.strip().replace(".utf-8", "").replace(".utf8", "").lower()
            if clean == line_clean:
                return True
        return False
    except Exception:
        return True

def ensure_locale_generated_async(locale_name: str, on_complete=None):
    """Spawns pkexec locale-gen in a thread if the locale is not yet generated."""
    if is_locale_generated(locale_name):
        if on_complete:
            on_complete(True)
        return

    def _worker():
        try:
            raw = locale_name.replace(".UTF-8", "").replace(".utf8", "")
            subprocess.run(["pkexec", "locale-gen", f"{raw}.UTF-8"], timeout=30)
            if on_complete:
                GLib.idle_add(on_complete, True)
        except Exception as e:
            print(f"[SystemLocale] locale-gen error: {e}")
            if on_complete:
                GLib.idle_add(on_complete, False)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def apply_system_language(locale_code: str, lang_code: str = "") -> Dict[str, Any]:
    """
    Applies the specified locale and language code across all Ubuntu/Linux system layers.
    Returns status dict with success flags for each subsystem.
    """
    if not locale_code:
        return {"success": False, "error": "Empty locale"}

    full_locale = locale_code if ".UTF-8" in locale_code else f"{locale_code}.UTF-8"
    raw_locale = locale_code.split(".")[0]
    short_lang = lang_code or raw_locale.split("_")[0]
    language_env = f"{full_locale}:{short_lang}:en_US:en"

    results = {
        "accounts_service": False,
        "locale_conf": False,
        "gsettings": False,
        "environ": False,
        "full_locale": full_locale,
    }

    # 1. AccountsService via D-Bus (Standard GNOME user language mechanism)
    try:
        uid = os.getuid()
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        accounts = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.Accounts",
            "/org/freedesktop/Accounts",
            "org.freedesktop.Accounts",
            None
        )
        user_path = accounts.call_sync("FindUserById", GLib.Variant("(x)", (int(uid),)), Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]
        proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
                                       "org.freedesktop.Accounts", user_path,
                                       "org.freedesktop.Accounts.User", None)
        # AccountsService versions differ: SetLanguage is widely available,
        # while SetLanguages is optional.  A failure in the optional call
        # must not undo the successful primary language update.
        try:
            proxy.call_sync("SetLanguage", GLib.Variant("(s)", (full_locale,)), Gio.DBusCallFlags.NONE, 3000, None)
            results["accounts_service"] = True
        except Exception as e:
            print(f"[SystemLocale] SetLanguage notice: {e}")
        try:
            proxy.call_sync("SetLanguages", GLib.Variant("(as)", ([full_locale, short_lang, "en_US.UTF-8", "en"],)), Gio.DBusCallFlags.NONE, 3000, None)
        except Exception:
            pass
    except Exception as e:
        print(f"[SystemLocale] AccountsService notice: {e}")

    # 2. systemd User Locale (~/.config/locale.conf)
    try:
        conf_dir = os.path.expanduser("~/.config")
        os.makedirs(conf_dir, exist_ok=True)
        conf_path = os.path.join(conf_dir, "locale.conf")
        content = f"LANG={full_locale}\nLANGUAGE={language_env}\nLC_ALL=\n"
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(content)
        results["locale_conf"] = True
    except Exception as e:
        print(f"[SystemLocale] ~/.config/locale.conf write error: {e}")

    # 3. GNOME Desktop GSettings
    try:
        subprocess.run(["gsettings", "set", "org.gnome.system.locale", "region", full_locale], timeout=2.0)
        results["gsettings"] = True
    except Exception as e:
        print(f"[SystemLocale] GSettings error: {e}")

    # 4. Current Process Environment (and future subprocesses)
    try:
        os.environ["LANG"] = full_locale
        os.environ["LANGUAGE"] = language_env
        os.environ["LC_MESSAGES"] = full_locale
        results["environ"] = True
    except Exception as e:
        print(f"[SystemLocale] os.environ error: {e}")

    # 5. Update ~/.pam_environment if present so PAM does not revert locale
    try:
        pam_env_path = os.path.expanduser("~/.pam_environment")
        if os.path.exists(pam_env_path):
            with open(pam_env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.startswith("LANG\t") or line.startswith("LANG="):
                    new_lines.append(f"LANG\tDEFAULT={full_locale}\n")
                elif line.startswith("LANGUAGE\t") or line.startswith("LANGUAGE="):
                    new_lines.append(f"LANGUAGE\tDEFAULT={full_locale}:{short_lang}\n")
                else:
                    new_lines.append(line)
            with open(pam_env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            results["pam_env"] = True
    except Exception as e:
        print(f"[SystemLocale] pam_environment notice: {e}")

    # 6. Try localectl set-locale for system-wide configuration
    try:
        subprocess.run(["localectl", "set-locale", f"LANG={full_locale}", f"LANGUAGE={full_locale}:{short_lang}"], timeout=2.0)
    except Exception:
        pass

    # 7. Check if locale needs generation
    if not is_locale_generated(full_locale):
        ensure_locale_generated_async(full_locale)

    results["success"] = any([results["accounts_service"], results["locale_conf"], results["gsettings"]])
    return results

def show_system_restart_dialog(lang_name: str, parent_window: Optional[Gtk.Window] = None):
    """
    Displays an authentic Apple macOS Sequoia Modal Dialog prompting the user
    to Log Out or Restart the system to finalize system-wide language changes.
    """
    from src.utils.i18n import t

    dialog = Gtk.Dialog(
        title=t("restart_dialog_title"),
        transient_for=parent_window,
        modal=True,
        destroy_with_parent=True
    )
    dialog.set_default_size(440, 220)
    dialog.set_resizable(False)
    dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT if parent_window else Gtk.WindowPosition.CENTER)

    box = dialog.get_content_area()
    box.set_spacing(16)
    box.set_margin_start(24)
    box.set_margin_end(24)
    box.set_margin_top(20)
    box.set_margin_bottom(12)

    # Header with Apple restart icon
    top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

    icon_box = Gtk.Box()
    icon_box.set_size_request(54, 54)
    icon_box.get_style_context().add_class("mac-general-squircle")
    icon = Gtk.Image.new_from_icon_name("system-reboot-symbolic", Gtk.IconSize.DIALOG)
    icon_box.pack_start(icon, True, True, 0)
    top_box.pack_start(icon_box, False, False, 0)

    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    title_lbl = Gtk.Label(label=t("restart_dialog_header", name=lang_name))
    title_lbl.get_style_context().add_class("mac-general-title")
    title_lbl.set_line_wrap(True)
    title_lbl.set_xalign(0.0)

    desc_lbl = Gtk.Label(label=t("restart_dialog_desc", name=lang_name))
    desc_lbl.set_line_wrap(True)
    desc_lbl.set_xalign(0.0)
    desc_lbl.get_style_context().add_class("mac-general-desc")

    text_box.pack_start(title_lbl, False, False, 0)
    text_box.pack_start(desc_lbl, False, False, 0)
    top_box.pack_start(text_box, True, True, 0)

    box.pack_start(top_box, True, True, 0)

    # Action buttons
    action_area = dialog.get_action_area()
    action_area.set_layout(Gtk.ButtonBoxStyle.END)
    action_area.set_spacing(10)

    btn_later = Gtk.Button(label=t("restart_dialog_later"))
    btn_later.get_style_context().add_class("mac-action-btn")
    dialog.add_action_widget(btn_later, Gtk.ResponseType.CANCEL)

    btn_logout = Gtk.Button(label=t("restart_dialog_logout"))
    btn_logout.get_style_context().add_class("mac-action-btn")
    dialog.add_action_widget(btn_logout, Gtk.ResponseType.APPLY)

    btn_restart = Gtk.Button(label=t("restart_dialog_restart"))
    btn_restart.get_style_context().add_class("mac-action-btn")
    btn_restart.get_style_context().add_class("primary")
    dialog.add_action_widget(btn_restart, Gtk.ResponseType.OK)

    dialog.show_all()
    resp = dialog.run()
    dialog.destroy()

    if resp == Gtk.ResponseType.OK:
        # Restart system
        try:
            subprocess.Popen(["gnome-session-quit", "--reboot"])
        except Exception:
            subprocess.Popen(["systemctl", "reboot"])
    elif resp == Gtk.ResponseType.APPLY:
        # Log out of session
        try:
            subprocess.Popen(["gnome-session-quit", "--logout", "--no-prompt"])
        except Exception:
            subprocess.Popen(["killall", "-u", os.getlogin()])
