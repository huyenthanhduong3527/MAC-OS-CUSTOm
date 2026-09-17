"""
Timer and Stopwatch Tab for Expanded Dynamic Island.
Includes big digital countdown display, Pomodoro presets, start/pause, and reset buttons.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf

class TimerTab(Gtk.Box):
    def __init__(self, timer_mod):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.get_style_context().add_class("tab-content")

        self.timer_mod = timer_mod
        self.timer_mod.on_tick = self.update

        # Mode switcher (Timer / Stopwatch)
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_box.set_halign(Gtk.Align.CENTER)

        self.timer_mode_btn = Gtk.Button(label="Countdown")
        self.timer_mode_btn.get_style_context().add_class("tab-button")
        self.timer_mode_btn.get_style_context().add_class("active")
        self.timer_mode_btn.connect("clicked", self._on_select_timer)

        self.sw_mode_btn = Gtk.Button(label="Stopwatch")
        self.sw_mode_btn.get_style_context().add_class("tab-button")
        self.sw_mode_btn.connect("clicked", self._on_select_sw)

        mode_box.pack_start(self.timer_mode_btn, False, False, 0)
        mode_box.pack_start(self.sw_mode_btn, False, False, 0)
        self.pack_start(mode_box, False, False, 0)

        # Big Digital Display
        self.display_lbl = Gtk.Label(label="05:00")
        self.display_lbl.get_style_context().add_class("timer-display")
        self.pack_start(self.display_lbl, False, False, 0)

        # Quick Preset Chips (Only visible in countdown mode)
        self.preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.preset_box.set_halign(Gtk.Align.CENTER)

        presets = [("1m", 60), ("5m", 300), ("15m", 900), ("25m", 1500)]
        for label, secs in presets:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("preset-chip")
            btn.connect("clicked", lambda b, s=secs: self._on_preset(s))
            self.preset_box.pack_start(btn, False, False, 0)

        self.pack_start(self.preset_box, False, False, 0)

        # Action Buttons: Start/Pause & Reset
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ctrl_box.set_halign(Gtk.Align.CENTER)

        self.start_btn = Gtk.Button(label="Start")
        self.start_btn.get_style_context().add_class("ctrl-btn")
        self.start_btn.get_style_context().add_class("primary")
        self.start_btn.set_size_request(80, 32)
        self.start_btn.connect("clicked", self._on_toggle_start)

        self.reset_btn = Gtk.Button(label="Reset")
        self.reset_btn.get_style_context().add_class("ctrl-btn")
        self.reset_btn.set_size_request(80, 32)
        self.reset_btn.connect("clicked", self._on_reset)

        ctrl_box.pack_start(self.start_btn, False, False, 0)
        ctrl_box.pack_start(self.reset_btn, False, False, 0)
        self.pack_start(ctrl_box, False, False, 0)

        self.update()

    def update(self):
        self.display_lbl.set_text(self.timer_mod.get_display_text())
        if self.timer_mod.is_running:
            self.start_btn.set_label("Pause")
        else:
            self.start_btn.set_label("Start")

    def _on_select_timer(self, btn):
        self.timer_mod.pause()
        self.timer_mod.mode = "timer"
        self.timer_mod.remaining_seconds = self.timer_mod.target_seconds
        self.timer_mode_btn.get_style_context().add_class("active")
        self.sw_mode_btn.get_style_context().remove_class("active")
        self.preset_box.show()
        self.update()

    def _on_select_sw(self, btn):
        self.timer_mod.pause()
        self.timer_mod.mode = "stopwatch"
        self.timer_mod.elapsed_seconds = 0.0
        self.sw_mode_btn.get_style_context().add_class("active")
        self.timer_mode_btn.get_style_context().remove_class("active")
        self.preset_box.hide()
        self.update()

    def _on_preset(self, secs):
        self.timer_mod.target_seconds = secs
        self.timer_mod.remaining_seconds = secs
        self.timer_mod.pause()
        self.update()

    def _on_toggle_start(self, btn):
        if self.timer_mod.is_running:
            self.timer_mod.pause()
        else:
            if self.timer_mod.mode == "timer":
                self.timer_mod.start_timer()
            else:
                self.timer_mod.start_stopwatch()
        self.update()

    def _on_reset(self, btn):
        self.timer_mod.reset()
        self.update()
