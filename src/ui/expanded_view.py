"""
Expanded View Container for Dynamic Island.
Contains the tab navigation header and hosts Media, Vitals, Controls, Timer, Notifications, and Settings tabs.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf
from src.ui.tabs.media_tab import MediaTab
from src.ui.tabs.vitals_tab import VitalsTab
from src.ui.tabs.controls_tab import ControlsTab
from src.ui.tabs.timer_tab import TimerTab
from src.ui.tabs.notifications_tab import NotificationsTab
from src.ui.tabs.clipboard_tab import ClipboardTab
from src.ui.tabs.gemini_tab import GeminiTab
from src.ui.tabs.settings_tab import SettingsTab
from src.modules.clipboard import ClipboardManager
from src.utils.i18n import t

class ExpandedView(Gtk.Box):
    def __init__(self, media_mgr, system_mon, audio_ctrl, timer_mod, visualizer, notif_mgr=None, brightness_ctrl=None, on_collapse=None, on_offset_change=None, on_size_change=None, on_quit=None, on_cosmos_change=None, on_clock_change=None, on_music_change=None, on_calendar_change=None, on_weather_change=None, on_battery_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_name("expanded-card")
        self.get_style_context().add_class("expanded-card")
        self.get_style_context().add_class("expanded-container")

        self.notif_mgr = notif_mgr
        self.on_collapse = on_collapse

        # Top Bar: Tab Switcher + Collapse Button
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Tab Bar pill
        self.tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.tab_bar.get_style_context().add_class("tab-bar")

        self.tab_buttons = {}
        self.tab_labels = {}
        tabs = [
            ("media", t("tab_media"), "music"),
            ("vitals", t("tab_vitals"), "cpu"),
            ("controls", t("tab_controls"), "controls"),
            ("timer", t("tab_timer"), "timer"),
            ("notifs", t("tab_notifications"), "bell"),
            ("clipboard", "Clip", "clipboard"),
            ("gemini", "Qwen", "sparkles"),
            ("settings", t("settings_title"), "settings"),
        ]

        for tab_id, label, icon in tabs:
            btn = Gtk.Button()
            btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            btn_icon = Gtk.Image.new_from_pixbuf(get_pixbuf(icon, 12, "#cbd5e1"))
            btn_lbl = Gtk.Label(label=label)
            btn_content.pack_start(btn_icon, False, False, 0)
            btn_content.pack_start(btn_lbl, False, False, 0)
            btn.add(btn_content)
            btn.get_style_context().add_class("tab-button")
            btn.connect("clicked", lambda b, tid=tab_id: self.switch_to_tab(tid))
            self.tab_bar.pack_start(btn, False, False, 0)
            self.tab_buttons[tab_id] = btn
            self.tab_labels[tab_id] = btn_lbl

        nav_box.pack_start(self.tab_bar, True, True, 0)

        # Collapse chevron button
        btn_collapse = Gtk.Button()
        btn_collapse.get_style_context().add_class("tab-button")
        btn_collapse.get_style_context().add_class("collapse-button")
        collapse_icon = Gtk.Image.new_from_pixbuf(get_pixbuf("chevron_up", 12, "#cbd5e1"))
        btn_collapse.set_image(collapse_icon)
        btn_collapse.set_tooltip_text("Collapse Island")
        if self.on_collapse:
            btn_collapse.connect("clicked", lambda b: self.on_collapse())
        nav_box.pack_end(btn_collapse, False, False, 0)

        self.pack_start(nav_box, False, False, 0)

        # Stack for tab pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)

        # Create tab widgets
        self.media_tab = MediaTab(media_mgr, visualizer)
        self.vitals_tab = VitalsTab(system_mon)
        self.controls_tab = ControlsTab(audio_ctrl, brightness_ctrl=brightness_ctrl, on_collapse=self.on_collapse)
        self.timer_tab = TimerTab(timer_mod)
        self.notifs_tab = NotificationsTab(notif_mgr)
        self.clipboard_tab = ClipboardTab(ClipboardManager.get_instance())
        self.gemini_tab = GeminiTab()
        self.siri_tab = self.gemini_tab
        self.settings_tab = SettingsTab(
            on_offset_change=on_offset_change,
            on_size_change=on_size_change,
            on_quit=on_quit,
            on_cosmos_change=on_cosmos_change,
            on_clock_change=on_clock_change,
            on_music_change=on_music_change,
            on_calendar_change=on_calendar_change,
            on_weather_change=on_weather_change,
            on_battery_change=on_battery_change
        )

        self.stack.add_named(self.media_tab, "media")
        self.stack.add_named(self.vitals_tab, "vitals")
        self.stack.add_named(self.controls_tab, "controls")
        self.stack.add_named(self.timer_tab, "timer")
        self.stack.add_named(self.notifs_tab, "notifs")
        self.stack.add_named(self.clipboard_tab, "clipboard")
        self.stack.add_named(self.gemini_tab, "gemini")
        self.stack.add_named(self.settings_tab, "settings")

        self.pack_start(self.stack, True, True, 0)

        self.current_tab = "media"
        self.switch_to_tab("media")

    def switch_to_tab(self, tab_id):
        if tab_id == "siri":
            tab_id = "gemini"
        self.current_tab = tab_id
        self.stack.set_visible_child_name(tab_id)

        # If switching to Notifs, clear unread state
        if tab_id == "notifs" and self.notif_mgr:
            self.notif_mgr.mark_all_read()

        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn.get_style_context().add_class("active")
            else:
                btn.get_style_context().remove_class("active")

        if tab_id == "clipboard":
            # Rebuild once after the stack switches. Rebuilding from the 30 FPS
            # window update loop can replace a button between press and release.
            GLib.idle_add(self.clipboard_tab.update)

        self.update()

    def update_tab_labels(self):
        tab_titles = {
            "media": t("tab_media"),
            "vitals": t("tab_vitals"),
            "controls": t("tab_controls"),
            "timer": t("tab_timer"),
            "notifs": t("tab_notifications"),
            "clipboard": "Clip",
            "gemini": "Qwen",
            "settings": t("settings_title")
        }
        for tid, lbl in self.tab_labels.items():
            if tid in tab_titles:
                lbl.set_text(tab_titles[tid])

    def update(self):
        self.update_tab_labels()
        if self.current_tab == "media":
            self.media_tab.update()
        elif self.current_tab == "vitals":
            self.vitals_tab.update()
        elif self.current_tab == "controls":
            self.controls_tab.update()
        elif self.current_tab == "timer":
            self.timer_tab.update()
        elif self.current_tab == "notifs":
            self.notifs_tab.update()
