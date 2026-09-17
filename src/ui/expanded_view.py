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
from src.ui.tabs.settings_tab import SettingsTab

class ExpandedView(Gtk.Box):
    def __init__(self, media_mgr, system_mon, audio_ctrl, timer_mod, visualizer, notif_mgr=None, on_collapse=None, on_offset_change=None, on_quit=None, on_cosmos_change=None):
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
        tabs = [
            ("media", "Music", "music"),
            ("vitals", "Vitals", "cpu"),
            ("controls", "Controls", "controls"),
            ("timer", "Timer", "timer"),
            ("notifs", "Notifs", "bell"),
            ("settings", "Settings", "settings"),
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

        nav_box.pack_start(self.tab_bar, True, True, 0)

        # Collapse Button
        collapse_btn = Gtk.Button()
        collapse_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("collapse", 14, "#94a3b8")))
        collapse_btn.get_style_context().add_class("ctrl-btn")
        collapse_btn.connect("clicked", lambda b: self.on_collapse() if self.on_collapse else None)
        nav_box.pack_end(collapse_btn, False, False, 0)

        self.pack_start(nav_box, False, False, 0)

        # Stack for tab pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)

        # Create tab widgets
        self.media_tab = MediaTab(media_mgr, visualizer)
        self.vitals_tab = VitalsTab(system_mon)
        self.controls_tab = ControlsTab(audio_ctrl, on_collapse=self.on_collapse)
        self.timer_tab = TimerTab(timer_mod)
        self.notifs_tab = NotificationsTab(notif_mgr)
        self.settings_tab = SettingsTab(on_offset_change=on_offset_change, on_quit=on_quit, on_cosmos_change=on_cosmos_change)

        self.stack.add_named(self.media_tab, "media")
        self.stack.add_named(self.vitals_tab, "vitals")
        self.stack.add_named(self.controls_tab, "controls")
        self.stack.add_named(self.timer_tab, "timer")
        self.stack.add_named(self.notifs_tab, "notifs")
        self.stack.add_named(self.settings_tab, "settings")

        self.pack_start(self.stack, True, True, 0)

        self.current_tab = "media"
        self.switch_to_tab("media")

    def switch_to_tab(self, tab_id):
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

        self.update()

    def update(self):
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
