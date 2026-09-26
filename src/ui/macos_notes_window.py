"""
macOS Notes (Ghi chú) for Ubuntu Linux.
Authentic Apple macOS Sequoia Notes app experience:
- Window: Frosted glass aesthetics, rounded squircle corners, macOS traffic lights (🔴 🟡 🟢).
- Top Toolbar: Aa formatting popover, Checklist, Table, Paperclip attachments, Markup Pen,
  Lock, Share/AirDrop, Audio Recording, and More (...) options.
- Left Sidebar: Two-tier view with Folders (All iCloud, Quick Notes, Audio Notes, Work, Personal, Trash)
  and Notes List with search bar, pinned notes, and Yellow Compose button.
- Main Note Editor: Rich text editing, speaker-based dialogue layout, and interactive inline
  Audio Message Card with playback scrubber and transcript preview.
- Right Audio Inspector Panel (matching macOS Sequoia Audio Notes 100%):
  - Top bar with Close ✕, "Audio Message", date/duration, and options.
  - Scrollable synchronized live transcript with speaker labels and karaoke-style sync.
  - Interactive click-to-seek on any transcript line.
  - Large digital timer (e.g. 01:54.26).
  - Waveform scrubber with drag-to-seek.
  - Controls: Skip -15s, Play/Pause, Skip +15s.
  - Bottom row: Transcript toggle, Red record circle button, and Yellow 'Done' button.
- Audio Engine: GStreamer playbin for high-fidelity playback, seeking, and skip;
  Microphone recording via pw-record / arecord / GStreamer with live audio waveform.
"""

import os
import sys
import time
import math
import subprocess
import threading
from typing import List, Dict, Optional, Any

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf, Gst
import cairo

Gst.init(None)

from src.utils.theme import is_system_dark_mode
from src.utils.icons import get_pixbuf, get_image
from src.utils.i18n import t, add_language_listener
from src.modules.notes_storage import (
    get_folder_display_name,
    NotesManager,
    format_duration,
    format_precise_timer,
    RECORDINGS_DIR,
    SAMPLE_AUDIO_PATH
)

_notes_window_instance = None


class TrafficLightDot(Gtk.DrawingArea):
    """Pixel-perfect Cairo-drawn macOS traffic light dot (guaranteed 100% round)."""
    def __init__(self, color_normal, color_hover, color_border, tooltip, symbol, cb):
        super().__init__()
        self.set_size_request(14, 14)
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_border = color_border
        self.tooltip = tooltip
        self.symbol = symbol
        self.cb = cb
        self.is_hovered = False
        self.set_tooltip_text(tooltip)
        self.add_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK
        )
        self.connect("draw", self._on_draw)
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)
        self.connect("button-press-event", self._on_click)

    def _on_enter(self, w, e):
        self.is_hovered = True
        self.queue_draw()
        return False

    def _on_leave(self, w, e):
        self.is_hovered = False
        self.queue_draw()
        return False

    def _on_click(self, w, e):
        if e.button == 1:
            self.cb()
            return True
        return False

    def _on_draw(self, widget, cr: cairo.Context):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0
        r = 6.0  # Exactly 12px diameter circle

        # Draw circle
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        if self.is_hovered:
            cr.set_source_rgb(*self.color_hover)
        else:
            cr.set_source_rgb(*self.color_normal)
        cr.fill_preserve()

        # Border
        cr.set_source_rgba(*self.color_border)
        cr.set_line_width(0.75)
        cr.stroke()

        # Draw symbol on hover (✕, —, ⤢)
        if self.is_hovered and self.symbol:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.65)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(8)
            extents = cr.text_extents(self.symbol)
            cr.move_to(cx - extents.width / 2.0 - extents.x_bearing,
                       cy - extents.height / 2.0 - extents.y_bearing)
            cr.show_text(self.symbol)
        return False


class TrafficLightsWidget(Gtk.Box):
    """Authentic Apple macOS Traffic Lights: 🔴 Red, 🟡 Yellow, 🟢 Green."""
    def __init__(self, on_close, on_minimize, on_maximize):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_start(16)
        self.set_valign(Gtk.Align.CENTER)

        self.dot_red = TrafficLightDot(
            color_normal=(1.0, 0.37, 0.34),
            color_hover=(1.0, 0.28, 0.25),
            color_border=(0.88, 0.27, 0.24, 0.8),
            tooltip=t("tl_close", "Đóng"),
            symbol="✕",
            cb=on_close
        )
        self.dot_yellow = TrafficLightDot(
            color_normal=(1.0, 0.74, 0.18),
            color_hover=(1.0, 0.68, 0.10),
            color_border=(0.87, 0.63, 0.14, 0.8),
            tooltip=t("tl_minimize", "Thu nhỏ"),
            symbol="—",
            cb=on_minimize
        )
        self.dot_green = TrafficLightDot(
            color_normal=(0.15, 0.79, 0.25),
            color_hover=(0.10, 0.72, 0.20),
            color_border=(0.10, 0.67, 0.16, 0.8),
            tooltip=t("tl_zoom", "Phóng to"),
            symbol="⤢",
            cb=on_maximize
        )

        self.pack_start(self.dot_red, False, False, 0)
        self.pack_start(self.dot_yellow, False, False, 0)
        self.pack_start(self.dot_green, False, False, 0)


class WaveformScrubberWidget(Gtk.DrawingArea):
    """
    Cairo-drawn interactive audio waveform scrubber.
    Supports clicking and dragging to seek, visual played vs remaining state,
    and live animated audio levels during recording.
    """
    def __init__(self, on_seek_callback=None):
        super().__init__()
        self.on_seek_callback = on_seek_callback
        self.progress = 0.0  # 0.0 to 1.0
        self.is_recording = False
        self.live_level = 0.2
        self.is_hovered = False
        self.set_size_request(-1, 32)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)

    def set_progress(self, p: float):
        p = max(0.0, min(1.0, float(p)))
        if abs(self.progress - p) > 0.002:
            self.progress = p
            self.queue_draw()

    def set_recording(self, recording: bool, level: float = 0.2):
        self.is_recording = recording
        self.live_level = level
        self.queue_draw()

    def _on_draw(self, widget, cr: cairo.Context):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        if w <= 0 or h <= 0:
            return

        is_dark = is_system_dark_mode()
        bar_count = max(30, int(w / 6.0))
        bar_w = max(2.0, (w / float(bar_count)) - 2.5)
        cy = h / 2.0

        for i in range(bar_count):
            x = i * (bar_w + 2.5) + 1.5
            frac = i / float(bar_count)

            # Pseudo-waveform height pattern
            pattern = math.sin(i * 0.38) * 0.4 + math.cos(i * 0.85) * 0.35 + math.sin(i * 1.5) * 0.25
            height = max(4.0, (h * 0.75) * abs(pattern))

            if self.is_recording:
                # Modulate with live audio level
                height = max(4.0, height * (0.4 + self.live_level * 1.2))

            y1 = cy - height / 2.0
            y2 = cy + height / 2.0

            # Color: Played bars vs unplayed bars
            if frac <= self.progress:
                # Played: Apple Accent Yellow/Gold
                cr.set_source_rgba(0.96, 0.65, 0.14, 0.95)
            else:
                # Remaining: muted gray
                if is_dark:
                    cr.set_source_rgba(1.0, 1.0, 1.0, 0.25)
                else:
                    cr.set_source_rgba(0.0, 0.0, 0.0, 0.2)

            cr.rectangle(x, y1, bar_w, height)
            cr.fill()

        # Scrubber playhead handle
        head_x = self.progress * w
        cr.set_source_rgba(0.96, 0.65, 0.14, 1.0)
        cr.arc(head_x, cy, 5.0 if self.is_hovered else 4.0, 0, 2 * math.pi)
        cr.fill()

    def _on_button_press(self, widget, event):
        w = widget.get_allocated_width()
        if w > 0:
            self.progress = max(0.0, min(1.0, event.x / float(w)))
            self.queue_draw()
            if self.on_seek_callback:
                self.on_seek_callback(self.progress)
        return True

    def _on_motion(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            w = widget.get_allocated_width()
            if w > 0:
                self.progress = max(0.0, min(1.0, event.x / float(w)))
                self.queue_draw()
                if self.on_seek_callback:
                    self.on_seek_callback(self.progress)
        return True

    def _on_enter(self, widget, event):
        self.is_hovered = True
        self.queue_draw()
        return False

    def _on_leave(self, widget, event):
        self.is_hovered = False
        self.queue_draw()
        return False


class InlineAudioCardWidget(Gtk.Box):
    """
    Embedded Audio Message Card in the note body (matching macOS Sequoia Apple Notes capsule).
    - Top Row: Audio Icon squircle, Title, Date, and 'Bản bóc băng' inspector toggle button.
    - Middle Row: Waveform scrubber with progress playhead.
    - Bottom Row: Time display (01:54 / 02:12), Skip -15s, Circular Play/Pause, Skip +15s.
    """
    def __init__(self, audio_data: Dict[str, Any], on_play_pause, on_skip, on_open_inspector, on_seek=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.audio_data = audio_data
        self.on_play_pause = on_play_pause
        self.on_skip = on_skip
        self.on_open_inspector = on_open_inspector
        self.on_seek = on_seek

        self.get_style_context().add_class("mac-inline-audio-card")
        self.set_margin_top(8)
        self.set_margin_bottom(16)
        self.set_margin_start(4)
        self.set_margin_end(4)

        card_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_content.set_margin_top(12)
        card_content.set_margin_bottom(12)
        card_content.set_margin_start(16)
        card_content.set_margin_end(16)
        self.pack_start(card_content, False, False, 0)

        # 1. Top Row: Icon + Title + Date & Action Buttons
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card_content.pack_start(top_row, False, False, 0)

        # Mic / Wave squircle badge
        badge = Gtk.Box()
        badge.get_style_context().add_class("mac-audio-badge")
        badge.set_size_request(34, 34)
        badge.set_valign(Gtk.Align.CENTER)
        badge_img = get_image("mic", 16, "#ffffff")
        badge.pack_start(badge_img, True, True, 0)
        top_row.pack_start(badge, False, False, 0)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info_box.set_valign(Gtk.Align.CENTER)
        title_text = audio_data.get("title", "Ghi âm thoại")
        self.lbl_title = Gtk.Label(label=title_text)
        self.lbl_title.get_style_context().add_class("audio-card-title")
        self.lbl_title.set_xalign(0.0)
        info_box.pack_start(self.lbl_title, False, False, 0)

        date_str = audio_data.get("date_str", "2 thg 5, 2024 lúc 19:34")
        self.lbl_date = Gtk.Label(label=date_str)
        self.lbl_date.get_style_context().add_class("audio-card-date")
        self.lbl_date.set_xalign(0.0)
        info_box.pack_start(self.lbl_date, False, False, 0)

        top_row.pack_start(info_box, True, True, 0)

        # Right: 'Bản bóc băng' inspector toggle button
        self.btn_open_trans = Gtk.Button()
        self.btn_open_trans.get_style_context().add_class("mac-audio-trans-btn")
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.pack_start(get_image("transcript_bubble", 14, "#e39c12"), False, False, 0)
        lbl_trans_btn = Gtk.Label(label="Bản bóc băng")
        lbl_trans_btn.get_style_context().add_class("audio-trans-btn-text")
        btn_box.pack_start(lbl_trans_btn, False, False, 0)
        self.btn_open_trans.add(btn_box)
        self.btn_open_trans.set_tooltip_text("Mở / Đóng bảng bóc băng thoại")
        self.btn_open_trans.connect("clicked", lambda _: self.on_open_inspector() if self.on_open_inspector else None)
        top_row.pack_end(self.btn_open_trans, False, False, 0)

        # 2. Middle Row: Waveform Scrubber
        self.waveform_scrubber = WaveformScrubberWidget(on_seek_callback=self._on_inline_seek)
        card_content.pack_start(self.waveform_scrubber, False, False, 2)

        # 3. Bottom Row: Time and Playback Controls
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        card_content.pack_start(bottom_row, False, False, 0)

        cur_str = format_duration(audio_data.get("current_pos_sec", 114.26))
        dur_str = format_duration(audio_data.get("duration_sec", 132.26))
        self.lbl_time = Gtk.Label(label=f"{cur_str} / {dur_str}")
        self.lbl_time.get_style_context().add_class("audio-card-time")
        self.lbl_time.set_valign(Gtk.Align.CENTER)
        self.lbl_time.set_xalign(0.0)
        bottom_row.pack_start(self.lbl_time, True, True, 0)

        # Controls: Skip -15, Play/Pause, Skip +15
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_box.set_valign(Gtk.Align.CENTER)

        self.btn_rew = Gtk.Button()
        self.btn_rew.set_size_request(28, 28)
        self.btn_rew.get_style_context().add_class("mac-audio-pill-btn")
        self.btn_rew.add(get_image("replay_15", 16, "#e39c12"))
        self.btn_rew.set_tooltip_text("Tua lùi 15 giây")
        self.btn_rew.connect("clicked", lambda _: self.on_skip(-15))
        ctrl_box.pack_start(self.btn_rew, False, False, 0)

        self.btn_play = Gtk.Button()
        self.btn_play.set_size_request(34, 34)
        self.btn_play.get_style_context().add_class("mac-audio-play-btn")
        self.btn_play_img = get_image("play", 16, "#ffffff")
        self.btn_play.add(self.btn_play_img)
        self.btn_play.set_tooltip_text("Phát / Tạm dừng")
        self.btn_play.connect("clicked", lambda _: self.on_play_pause())
        ctrl_box.pack_start(self.btn_play, False, False, 0)

        self.btn_fwd = Gtk.Button()
        self.btn_fwd.set_size_request(28, 28)
        self.btn_fwd.get_style_context().add_class("mac-audio-pill-btn")
        self.btn_fwd.add(get_image("forward_15", 16, "#e39c12"))
        self.btn_fwd.set_tooltip_text("Tua tới 15 giây")
        self.btn_fwd.connect("clicked", lambda _: self.on_skip(15))
        ctrl_box.pack_start(self.btn_fwd, False, False, 0)

        bottom_row.pack_end(ctrl_box, False, False, 0)

    def _on_inline_seek(self, fraction: float):
        if self.on_seek:
            self.on_seek(fraction)

    def update_play_state(self, is_playing: bool):
        self.btn_play.remove(self.btn_play_img)
        icon_name = "pause" if is_playing else "play"
        self.btn_play_img = get_image(icon_name, 16, "#ffffff")
        self.btn_play.add(self.btn_play_img)
        self.btn_play.show_all()

    def update_time(self, cur_sec: float, dur_sec: float):
        cur_str = format_duration(cur_sec)
        dur_str = format_duration(dur_sec)
        self.lbl_time.set_text(f"{cur_str} / {dur_str}")
        if dur_sec > 0:
            frac = max(0.0, min(1.0, cur_sec / float(dur_sec)))
            self.waveform_scrubber.set_progress(frac)
        else:
            self.waveform_scrubber.set_progress(0.0)


class AudioInspectorPanel(Gtk.Box):
    """
    Right slide-out Audio Inspector panel (matching macOS Sequoia 100%).
    - Header: Close ✕, 'Audio Message', subtitle date/duration, options (...).
    - Scrollable Live Transcript with speaker labels and karaoke sync.
    - Large digital timer (01:54.26).
    - Waveform Scrubber with seek.
    - Control buttons: Skip -15s, Play/Pause, Skip +15s.
    - Bottom action row: Transcript toggle, Red record button, Yellow 'Done' button.
    """
    def __init__(self, on_close, on_play_pause, on_skip, on_seek, on_record_toggle, on_done, on_seek_seconds=None,
                 on_insert_transcript=None, on_export_audio=None, on_delete_audio=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_close = on_close
        self.on_play_pause = on_play_pause
        self.on_skip = on_skip
        self.on_seek = on_seek
        self.on_record_toggle = on_record_toggle
        self.on_done = on_done
        self.on_seek_seconds = on_seek_seconds
        self.on_insert_transcript = on_insert_transcript
        self.on_export_audio = on_export_audio
        self.on_delete_audio = on_delete_audio

        self.get_style_context().add_class("mac-audio-inspector")
        self.set_size_request(360, -1)

        self.transcript_lines: List[Dict[str, Any]] = []
        self.line_widgets: List[Gtk.Widget] = []
        self.active_line_idx = -1

        self._setup_ui()
        self.load_transcript([])
        self.show_all()
        self.set_no_show_all(True)
        self.hide()

    def _setup_ui(self):
        # 1. Header Bar
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class("mac-inspector-header")
        header.set_margin_top(12)
        header.set_margin_bottom(12)
        header.set_margin_start(16)
        header.set_margin_end(16)
        self.pack_start(header, False, False, 0)

        # Close ✕ button
        self.btn_close = Gtk.Button()
        self.btn_close.set_size_request(28, 28)
        self.btn_close.get_style_context().add_class("mac-circle-btn")
        lbl_x = Gtk.Label(label="✕")
        lbl_x.get_style_context().add_class("inspector-close-symbol")
        self.btn_close.add(lbl_x)
        self.btn_close.set_tooltip_text("Đóng bảng ghi âm")
        self.btn_close.connect("clicked", lambda _: self.on_close())
        header.pack_start(self.btn_close, False, False, 0)

        # Title & Subtitle in Center
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_box.set_valign(Gtk.Align.CENTER)
        self.lbl_header_title = Gtk.Label(label=t("notes_audio_message", "Ghi âm thoại"))
        self.lbl_header_title.get_style_context().add_class("inspector-title")
        self.lbl_header_title.set_halign(Gtk.Align.CENTER)
        title_box.pack_start(self.lbl_header_title, False, False, 0)

        self.lbl_header_subtitle = Gtk.Label(label="")
        self.lbl_header_subtitle.get_style_context().add_class("inspector-subtitle")
        self.lbl_header_subtitle.set_halign(Gtk.Align.CENTER)
        title_box.pack_start(self.lbl_header_subtitle, False, False, 0)

        header.pack_start(title_box, True, True, 0)

        # Trash / Delete Audio Button
        self.btn_trash_audio = Gtk.Button()
        self.btn_trash_audio.set_size_request(28, 28)
        self.btn_trash_audio.get_style_context().add_class("mac-circle-btn")
        self.btn_trash_audio.get_style_context().add_class("mac-trash-btn")
        self.btn_trash_audio.add(get_image("trash", 15, "#ff3b30"))
        self.btn_trash_audio.set_tooltip_text("Xóa bản ghi âm này (Delete audio message)")
        self.btn_trash_audio.connect("clicked", lambda _: self._delete_audio())
        header.pack_start(self.btn_trash_audio, False, False, 0)

        # Options (...) button
        self.btn_more = Gtk.Button()
        self.btn_more.set_size_request(28, 28)
        self.btn_more.get_style_context().add_class("mac-circle-btn")
        self.btn_more.add(get_image("dots_horizontal", 16, "#8e8e93"))
        self.btn_more.set_tooltip_text("Tùy chọn ghi âm & bóc băng thoại")
        self.btn_more.connect("clicked", self._show_audio_options_menu)
        header.pack_start(self.btn_more, False, False, 0)

        # Thin separator
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep1.get_style_context().add_class("mac-separator")
        self.pack_start(sep1, False, False, 0)

        # 2. Player Controls Area (Placed at TOP for direct access, no blank void!)
        player_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        player_area.get_style_context().add_class("mac-inspector-bottom")
        player_area.set_margin_top(14)
        player_area.set_margin_bottom(14)
        player_area.set_margin_start(20)
        player_area.set_margin_end(20)
        self.pack_start(player_area, False, False, 0)

        # 2.1 Digital Timer (e.g. 00:00.00)
        self.lbl_digital_timer = Gtk.Label(label="00:00.00")
        self.lbl_digital_timer.get_style_context().add_class("mac-digital-timer")
        self.lbl_digital_timer.set_halign(Gtk.Align.CENTER)
        player_area.pack_start(self.lbl_digital_timer, False, False, 0)

        # 2.2 Waveform Scrubber
        self.waveform_scrubber = WaveformScrubberWidget(on_seek_callback=self.on_seek)
        player_area.pack_start(self.waveform_scrubber, False, False, 0)

        # 2.3 Controls Row: Skip -15s, Play/Pause, Skip +15s
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        ctrl_row.set_halign(Gtk.Align.CENTER)

        self.btn_skip_back = Gtk.Button()
        self.btn_skip_back.set_size_request(36, 36)
        self.btn_skip_back.get_style_context().add_class("mac-audio-pill-btn")
        self.btn_skip_back.add(get_image("replay_15", 22, "#e39c12"))
        self.btn_skip_back.set_tooltip_text("Tua lùi 15 giây")
        self.btn_skip_back.connect("clicked", lambda _: self.on_skip(-15))
        ctrl_row.pack_start(self.btn_skip_back, False, False, 0)

        self.btn_play_pause = Gtk.Button()
        self.btn_play_pause.set_size_request(44, 44)
        self.btn_play_pause.get_style_context().add_class("mac-audio-large-play-btn")
        self.play_icon = get_image("play", 20, "#ffffff")
        self.btn_play_pause.add(self.play_icon)
        self.btn_play_pause.set_tooltip_text("Phát / Tạm dừng")
        self.btn_play_pause.connect("clicked", lambda _: self.on_play_pause())
        ctrl_row.pack_start(self.btn_play_pause, False, False, 0)

        self.btn_skip_fwd = Gtk.Button()
        self.btn_skip_fwd.set_size_request(36, 36)
        self.btn_skip_fwd.get_style_context().add_class("mac-audio-pill-btn")
        self.btn_skip_fwd.add(get_image("forward_15", 22, "#e39c12"))
        self.btn_skip_fwd.set_tooltip_text("Tua tới 15 giây")
        self.btn_skip_fwd.connect("clicked", lambda _: self.on_skip(15))
        ctrl_row.pack_start(self.btn_skip_fwd, False, False, 0)

        player_area.pack_start(ctrl_row, False, False, 4)

        # 2.4 Action Row: Transcript toggle, Red Record Button, Yellow 'Xong'
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        action_row.set_margin_top(4)

        # Left: Transcript toggle (speech bubble icon)
        self.btn_trans_toggle = Gtk.Button()
        self.btn_trans_toggle.set_size_request(36, 36)
        self.btn_trans_toggle.get_style_context().add_class("mac-circle-btn")
        self.btn_trans_toggle.add(get_image("transcript_bubble", 18, "#8e8e93"))
        self.btn_trans_toggle.set_tooltip_text("Bật / Tắt hiển thị bóc băng")
        self.btn_trans_toggle.connect("clicked", self._toggle_transcript_view)
        action_row.pack_start(self.btn_trans_toggle, False, False, 0)

        # Center: Record red circle button
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        center_box.set_halign(Gtk.Align.CENTER)
        self.btn_record = Gtk.Button()
        self.btn_record.set_size_request(36, 36)
        self.btn_record.get_style_context().add_class("mac-audio-record-btn")
        self.record_icon = get_image("mic", 16, "#ffffff")
        self.btn_record.add(self.record_icon)
        self.btn_record.set_tooltip_text("Bắt đầu / Dừng ghi âm")
        self.btn_record.connect("clicked", lambda _: self.on_record_toggle())
        center_box.pack_start(self.btn_record, False, False, 0)
        action_row.pack_start(center_box, True, True, 0)

        # Right: Yellow 'Xong' button
        self.btn_done = Gtk.Button(label=t("done", "Xong"))
        self.btn_done.get_style_context().add_class("mac-audio-done-btn")
        self.btn_done.set_tooltip_text("Hoàn thành ghi âm và lưu vào ghi chú")
        self.btn_done.connect("clicked", lambda _: self.on_done())
        action_row.pack_end(self.btn_done, False, False, 0)

        player_area.pack_start(action_row, False, False, 0)

        # Thin separator
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep2.get_style_context().add_class("mac-separator")
        self.pack_start(sep2, False, False, 0)

        # 3. Transcript Header & Scrollable Transcript Area (BOTTOM)
        transcript_header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        transcript_header_row.set_margin_start(20)
        transcript_header_row.set_margin_end(20)
        transcript_header_row.set_margin_top(10)
        transcript_header_row.set_margin_bottom(4)
        lbl_sec = Gtk.Label(label=t("notes_transcript", "Bản ghi lời thoại").upper())
        self.lbl_transcript_sec = lbl_sec
        lbl_sec.get_style_context().add_class("transcript-section-header")
        lbl_sec.set_xalign(0.0)
        transcript_header_row.pack_start(lbl_sec, True, True, 0)
        self.pack_start(transcript_header_row, False, False, 0)

        self.scroll_transcript = Gtk.ScrolledWindow()
        self.scroll_transcript.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll_transcript.get_style_context().add_class("mac-transcript-scroll")

        self.transcript_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.transcript_box.set_margin_top(8)
        self.transcript_box.set_margin_bottom(16)
        self.transcript_box.set_margin_start(16)
        self.transcript_box.set_margin_end(16)
        self.scroll_transcript.add(self.transcript_box)
        self.pack_start(self.scroll_transcript, True, True, 0)

    def load_transcript(self, segments: List[Dict[str, Any]]):
        """Populate the transcript box with interactive lines or clean empty placeholder."""
        # Clear existing
        for child in self.transcript_box.get_children():
            self.transcript_box.remove(child)

        self.transcript_lines = segments
        self.line_widgets = []
        self.active_line_idx = -1

        if isinstance(segments, str):
            if segments.strip():
                segments = [{"speaker": "", "text": segments.strip(), "start_time": 0.0}]
            else:
                segments = []
        elif not isinstance(segments, (list, tuple)):
            segments = []

        if not segments:
            # Clean Apple empty state instead of blank void
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_halign(Gtk.Align.CENTER)
            empty_box.set_margin_top(30)
            empty_box.set_margin_bottom(30)
            icon_empty = get_image("transcript_bubble", 28, "#8e8e93")
            empty_box.pack_start(icon_empty, False, False, 0)
            lbl_empty = Gtk.Label(label="Chưa có bản bóc băng cho bản ghi này")
            lbl_empty.get_style_context().add_class("transcript-empty-label")
            lbl_empty.set_halign(Gtk.Align.CENTER)
            empty_box.pack_start(lbl_empty, False, False, 0)
            self.transcript_box.pack_start(empty_box, True, True, 0)
            self.transcript_box.show_all()
            return

        for idx, seg in enumerate(segments):
            if isinstance(seg, str):
                speaker = ""
                text = seg
                start_t = 0.0
            elif isinstance(seg, dict):
                speaker = seg.get("speaker", "")
                text = seg.get("text", "")
                start_t = float(seg.get("start_time", 0.0) or 0.0)
            else:
                continue

            line_event = Gtk.EventBox()
            line_event.set_visible_window(False)
            line_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            line_box.get_style_context().add_class("transcript-line-box")

            if speaker:
                lbl_speaker = Gtk.Label(label=f"{speaker}")
                lbl_speaker.get_style_context().add_class("transcript-speaker")
                lbl_speaker.set_xalign(0.0)
                line_box.pack_start(lbl_speaker, False, False, 0)

            lbl_text = Gtk.Label(label=text)
            lbl_text.get_style_context().add_class("transcript-text")
            lbl_text.set_xalign(0.0)
            lbl_text.set_line_wrap(True)
            line_box.pack_start(lbl_text, False, False, 0)

            line_event.add(line_box)

            # Click line to seek to its start time!
            line_event.connect("button-press-event", lambda w, e, t=start_t: self._on_line_clicked(t))

            self.transcript_box.pack_start(line_event, False, False, 0)
            self.line_widgets.append(line_box)

        self.transcript_box.show_all()

    def _on_line_clicked(self, start_t: float):
        if self.on_seek_seconds:
            self.on_seek_seconds(start_t)

    def highlight_at_time(self, cur_time: float):
        """Highlight active transcript line and scroll into view."""
        active_idx = -1
        for i, seg in enumerate(self.transcript_lines):
            if seg.get("start_time", 0.0) <= cur_time <= seg.get("end_time", 99999.0):
                active_idx = i
                break

        if active_idx != self.active_line_idx:
            # Clear old
            if 0 <= self.active_line_idx < len(self.line_widgets):
                self.line_widgets[self.active_line_idx].get_style_context().remove_class("transcript-line-active")

            # Set new
            self.active_line_idx = active_idx
            if 0 <= active_idx < len(self.line_widgets):
                w = self.line_widgets[active_idx]
                w.get_style_context().add_class("transcript-line-active")

                # Auto-scroll smoothly
                alloc = w.get_allocation()
                adj = self.scroll_transcript.get_vadjustment()
                if adj:
                    target_y = alloc.y - 40
                    adj.set_value(max(0.0, target_y))

    def update_timer(self, cur_sec: float, dur_sec: float):
        """Update digital timer display and waveform progress."""
        self.lbl_digital_timer.set_text(format_precise_timer(cur_sec))
        if dur_sec > 0:
            frac = max(0.0, min(1.0, cur_sec / float(dur_sec)))
            self.waveform_scrubber.set_progress(frac)
        else:
            self.waveform_scrubber.set_progress(0.0)

    def update_play_state(self, is_playing: bool):
        self.btn_play_pause.remove(self.play_icon)
        icon_name = "pause" if is_playing else "play"
        self.play_icon = get_image(icon_name, 20, "#ffffff")
        self.btn_play_pause.add(self.play_icon)
        self.btn_play_pause.show_all()

    def update_record_state(self, is_recording: bool):
        if is_recording:
            self.btn_record.get_style_context().add_class("recording-active")
            self.waveform_scrubber.set_recording(True)
        else:
            self.btn_record.get_style_context().remove_class("recording-active")
            self.waveform_scrubber.set_recording(False)

    def _toggle_transcript_view(self, btn):
        is_visible = self.scroll_transcript.get_visible()
        child = self.btn_trans_toggle.get_child()
        if is_visible:
            self.scroll_transcript.hide()
            if child:
                self.btn_trans_toggle.remove(child)
            self.btn_trans_toggle.add(get_image("transcript_bubble", 18, "#8e8e93"))
        else:
            self.scroll_transcript.show()
            if child:
                self.btn_trans_toggle.remove(child)
            self.btn_trans_toggle.add(get_image("transcript_bubble", 18, "#e39c12"))
        self.btn_trans_toggle.show_all()

    def _show_audio_options_menu(self, widget):
        pop = Gtk.Popover.new(self.btn_more)
        pop.set_position(Gtk.PositionType.BOTTOM)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)

        is_dark = is_system_dark_mode()

        def make_action(icon_name, text, cb, is_destructive=False):
            b = Gtk.Button()
            b.get_style_context().add_class("mac-popover-item")
            if is_destructive:
                b.get_style_context().add_class("destructive")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_start(4)
            box.set_margin_end(6)
            box.set_margin_top(3)
            box.set_margin_bottom(3)
            icon_color = "#ff3b30" if is_destructive else ("#86868b" if not is_dark else "#98989d")
            icon_img = get_image(icon_name, size=16, color=icon_color)
            icon_box = Gtk.Box()
            icon_box.set_size_request(20, 20)
            icon_box.pack_start(icon_img, True, True, 0)
            box.pack_start(icon_box, False, False, 0)
            lbl = Gtk.Label(label=text)
            lbl.set_xalign(0.0)
            if is_destructive:
                lbl.get_style_context().add_class("destructive-label")
            box.pack_start(lbl, True, True, 0)
            b.add(box)
            b.set_halign(Gtk.Align.FILL)
            b.connect("clicked", lambda _: [cb(), pop.popdown()])
            return b

        vbox.pack_start(make_action("copy", "Sao chép bản ghi chép", self._copy_transcript), False, False, 0)
        vbox.pack_start(make_action("doc_text", "Chèn bản ghi chép vào nội dung", self._insert_transcript), False, False, 0)
        vbox.pack_start(make_action("download", "Xuất tệp ghi âm (.wav)...", self._export_audio), False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("mac-separator")
        vbox.pack_start(sep, False, False, 2)

        vbox.pack_start(make_action("trash", "Xóa bản ghi âm này", self._delete_audio, is_destructive=True), False, False, 0)

        pop.add(vbox)
        pop.show_all()
        pop.popup()

    def _copy_transcript(self):
        lines = []
        for item in self.transcript_lines:
            spk = item.get("speaker", "Speaker")
            txt = item.get("text", "")
            lines.append(f"{spk}:\n{txt}")
        full_text = "\n\n".join(lines)
        if full_text:
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.set_text(full_text, -1)

    def _insert_transcript(self):
        lines = []
        for item in self.transcript_lines:
            spk = item.get("speaker", "Speaker")
            txt = item.get("text", "")
            lines.append(f"{spk}: {txt}")
        full_text = "\n".join(lines)
        if self.on_insert_transcript and full_text:
            self.on_insert_transcript(full_text)

    def _export_audio(self):
        if self.on_export_audio:
            self.on_export_audio()

    def _delete_audio(self):
        if self.on_delete_audio:
            self.on_delete_audio()


class MacOSNotesWindow(Gtk.Window):
    """
    Main macOS Sequoia Notes Application Window for Ubuntu Linux.
    Complete replica matching the user's screenshot.
    """
    _instance = None
    _css_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MacOSNotesWindow()
        else:
            try:
                if not hasattr(cls._instance, "props") or cls._instance.__grefcount__ <= 0:
                    cls._instance = MacOSNotesWindow()
            except Exception:
                cls._instance = MacOSNotesWindow()
        return cls._instance

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        GLib.set_prgname("macos-notes")
        if not GLib.get_application_name():
            GLib.set_application_name(t("notes_title", "Ghi chú"))
        self.set_title("Ghi chú (macOS Notes)")
        self.set_wmclass("macos-notes", "MacOSNotes")
        self.set_role("notes")
        self._is_iconified = False

        # App Icon
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "notes_icon.png"
        )
        try:
            if os.path.exists(icon_path):
                self.set_icon_from_file(icon_path)
            else:
                self.set_icon_name("accessories-text-editor")
        except Exception as e:
            print(f"[Notes] Error setting icon: {e}")

        self.set_default_size(1180, 780)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_resizable(True)

        geom = Gdk.Geometry()
        geom.min_width = 800
        geom.min_height = 520
        self.set_geometry_hints(None, geom, Gdk.WindowHints.MIN_SIZE)

        self._is_maximized = False
        self._is_sidebar_visible = True
        self._is_inspector_visible = True
        self.is_dark = is_system_dark_mode()

        self.notes_mgr = NotesManager.get_instance()
        self.current_folder = "all"
        self.current_query = ""
        self.current_note: Optional[Dict[str, Any]] = None

        # Audio Player State
        self.player = None
        self.is_playing = False
        self.current_audio_time = 114.26  # Initialized to screenshot's 01:54.26!
        self.current_audio_duration = 132.26
        self._playback_timer_id = None

        # Recording State
        self.is_recording = False
        self.record_proc = None
        self.record_file_path = None
        self.record_start_time = 0.0

        # RGBA Visual for smooth corners
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        self._init_audio_player()
        self._load_css()
        self._setup_ui()
        self.set_title(t("notes_title", "Ghi chú"))
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass

        # Connect window events
        self.connect("draw", self._on_window_draw)
        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("window-state-event", self._on_window_state_event)

        # Select first note by default (matching the screenshot!)
        self._load_initial_note()

    def _init_audio_player(self):
        """Initialize GStreamer playbin pipeline."""
        try:
            self.player = Gst.ElementFactory.make("playbin", "notes_player")
            bus = self.player.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_gst_message)
        except Exception as e:
            print(f"[Notes] Error initializing GStreamer: {e}")
            self.player = None

    def _on_gst_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self._pause_audio()
            self._seek_audio_seconds(0.0)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"[Notes] GStreamer error: {err}, {debug}")
            self._pause_audio()

    def _load_initial_note(self):
        """Select 'Call with Rigo Rangel' by default."""
        notes = self.notes_mgr.get_notes(self.current_folder, self.current_query)
        if notes:
            self.select_note(notes[0])

    def _setup_ui(self):
        # Master Stack / Overlay Root for Edge Resizing
        self.master_overlay = Gtk.Overlay()
        self.add(self.master_overlay)

        # Main App Window Card
        self.root_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root_card.get_style_context().add_class("mac-notes-window")
        self.master_overlay.add(self.root_card)

        # Setup edge & corner resize handles on overlay
        self._setup_resize_handles()

        # -------------------------------------------------------------
        # 1. TOP TOOLBAR & HEADERBAR
        # -------------------------------------------------------------
        self.header_event_box = Gtk.EventBox()
        self.header_event_box.set_visible_window(False)
        self.header_event_box.connect("button-press-event", self._on_header_button_press)
        self.root_card.pack_start(self.header_event_box, False, False, 0)

        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.toolbar.get_style_context().add_class("mac-notes-toolbar")
        self.header_event_box.add(self.toolbar)

        # Left: Traffic Lights (🔴 🟡 🟢)
        tl = TrafficLightsWidget(
            on_close=self.close_window,
            on_minimize=self.iconify,
            on_maximize=self.toggle_maximize
        )
        self.toolbar.pack_start(tl, False, False, 0)

        # Sidebar Toggle Button
        self.btn_sidebar_toggle = Gtk.Button()
        self.btn_sidebar_toggle.set_valign(Gtk.Align.CENTER)
        self.btn_sidebar_toggle.set_size_request(30, 30)
        self.btn_sidebar_toggle.get_style_context().add_class("mac-tool-btn")
        self.btn_sidebar_toggle.set_tooltip_text(t("notes_toggle_sidebar", "Ẩn / Hiện thanh bên"))
        self.btn_sidebar_toggle.add(get_image("sidebar", 16, "#6e6e73"))
        self.btn_sidebar_toggle.connect("clicked", lambda _: self.toggle_sidebar())
        self.toolbar.pack_start(self.btn_sidebar_toggle, False, False, 0)

        # Center Title: Note title
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        center_box.set_valign(Gtk.Align.CENTER)
        self.lbl_window_title = Gtk.Label(label=t("notes_title", "Ghi chú"))
        self.lbl_window_title.get_style_context().add_class("mac-window-title")
        self.lbl_window_title.set_halign(Gtk.Align.CENTER)
        center_box.pack_start(self.lbl_window_title, False, False, 0)

        self.lbl_window_subtitle = Gtk.Label(label=t("notes_no_notes", "Không có ghi chú nào"))
        self.lbl_window_subtitle.get_style_context().add_class("mac-window-subtitle")
        self.lbl_window_subtitle.set_halign(Gtk.Align.CENTER)
        center_box.pack_start(self.lbl_window_subtitle, False, False, 0)
        self.toolbar.pack_start(center_box, True, True, 0)

        # Right Action Icons: Aa, Checklist, Table, Paperclip, Pen, Lock, Share, Mic, More
        right_tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        right_tools.set_valign(Gtk.Align.CENTER)

        def make_tool_btn(icon_name, tooltip, cb):
            btn = Gtk.Button()
            btn.set_size_request(28, 28)
            btn.get_style_context().add_class("mac-tool-btn")
            btn.set_tooltip_text(tooltip)
            btn.add(get_image(icon_name, 16, "#6e6e73"))
            btn.connect("clicked", lambda _: cb())
            return btn

        # Format Aa
        self.btn_format = make_tool_btn("format_aa", t("notes_format_tooltip", "Định dạng chữ (Format)"), self._show_format_popover)
        right_tools.pack_start(self.btn_format, False, False, 0)

        # Checklist
        self.btn_toolbar_checklist = make_tool_btn("checklist", t("notes_checklist_tooltip", "Chèn danh sách việc cần làm"), self._insert_checklist)
        right_tools.pack_start(self.btn_toolbar_checklist, False, False, 0)

        # Table
        self.btn_toolbar_table = make_tool_btn("table", t("notes_table_tooltip", "Chèn bảng"), self._insert_table)
        right_tools.pack_start(self.btn_toolbar_table, False, False, 0)

        # Paperclip / Attachment
        self.btn_toolbar_paperclip = make_tool_btn("paperclip", t("notes_attach_tooltip", "Đính kèm tệp / hình ảnh"), self._attach_file)
        right_tools.pack_start(self.btn_toolbar_paperclip, False, False, 0)

        # Pen / Markup
        self.btn_toolbar_markup = make_tool_btn("pen_markup", t("notes_markup_tooltip", "Bút vẽ & phác thảo"), self._toggle_markup)
        right_tools.pack_start(self.btn_toolbar_markup, False, False, 0)

        # Lock
        self.btn_toolbar_lock = make_tool_btn("lock", t("notes_lock_tooltip", "Khóa ghi chú"), self._toggle_lock)
        right_tools.pack_start(self.btn_toolbar_lock, False, False, 0)

        # Share / AirDrop
        self.btn_toolbar_share = make_tool_btn("share", t("notes_share_tooltip", "Chia sẻ qua AirDrop / Email"), self._share_note)
        right_tools.pack_start(self.btn_toolbar_share, False, False, 0)

        # Audio Recording / Mic
        self.btn_toolbar_mic = make_tool_btn("mic", t("notes_audio_tooltip", "Ghi âm & bóc băng thoại"), self.toggle_audio_inspector)
        right_tools.pack_start(self.btn_toolbar_mic, False, False, 0)

        # Delete / Trash Can Button
        self.btn_toolbar_trash = make_tool_btn("trash", t("notes_delete_tooltip", "Xóa ghi chú này"), self._delete_current)
        self.btn_toolbar_trash.get_style_context().add_class("mac-trash-btn")
        right_tools.pack_start(self.btn_toolbar_trash, False, False, 0)

        # More (...)
        self.btn_more_toolbar = make_tool_btn("dots_horizontal", t("notes_more_tooltip", "Tùy chọn khác"), self._show_more_menu)
        right_tools.pack_start(self.btn_more_toolbar, False, False, 0)

        self.toolbar.pack_start(right_tools, False, False, 8)

        # Separator line under toolbar
        sep_toolbar = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep_toolbar.get_style_context().add_class("mac-separator")
        self.root_card.pack_start(sep_toolbar, False, False, 0)

        # -------------------------------------------------------------
        # 2. MAIN WORKSPACE: SIDEBAR + EDITOR + AUDIO INSPECTOR
        # -------------------------------------------------------------
        self.workspace_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.root_card.pack_start(self.workspace_box, True, True, 0)

        # 2.1 Left Sidebar (Folders + Notes List)
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.sidebar_box.get_style_context().add_class("mac-notes-sidebar")
        self.workspace_box.pack_start(self.sidebar_box, False, False, 0)

        self._setup_sidebar_folders()
        self._setup_sidebar_notes_list()

        # Vertical separator
        sep_side = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep_side.get_style_context().add_class("mac-separator")
        self.workspace_box.pack_start(sep_side, False, False, 0)

        # 2.2 Center Note Editor Area
        self._setup_note_editor()

        # Vertical separator before inspector
        self.sep_inspector = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.sep_inspector.get_style_context().add_class("mac-separator")
        self.sep_inspector.set_no_show_all(True)
        self.sep_inspector.hide()
        self.workspace_box.pack_start(self.sep_inspector, False, False, 0)

        # 2.3 Right Audio Inspector Panel
        self.audio_inspector = AudioInspectorPanel(
            on_close=self.hide_audio_inspector,
            on_play_pause=self._toggle_play_pause,
            on_skip=self._skip_audio,
            on_seek=self._seek_audio_fraction,
            on_record_toggle=self._toggle_mic_recording,
            on_done=self._on_done_recording,
            on_seek_seconds=self._seek_audio_seconds,
            on_insert_transcript=self._insert_transcript_to_note,
            on_export_audio=self._export_audio_file,
            on_delete_audio=self._delete_audio_from_current_note
        )
        self.audio_inspector.set_no_show_all(True)
        self.audio_inspector.hide()
        self.workspace_box.pack_start(self.audio_inspector, False, False, 0)

    def _setup_resize_handles(self):
        """Add 8 edge and corner resize handles around the window overlay."""
        def make_handle(cursor_name, edge, width, height, halign, valign):
            eb = Gtk.EventBox()
            eb.set_visible_window(True)
            eb.set_opacity(0.0)
            eb.set_size_request(width, height)
            eb.set_halign(halign)
            eb.set_valign(valign)

            def on_realize(widget):
                win = widget.get_window()
                if win:
                    cursor = Gdk.Cursor.new_from_name(widget.get_display(), cursor_name)
                    win.set_cursor(cursor)

            def on_button_press(widget, event):
                if event.button == 1 and not getattr(self, "_is_maximized", False):
                    self.begin_resize_drag(
                        edge,
                        event.button,
                        int(event.x_root),
                        int(event.y_root),
                        event.time
                    )
                    return True
                return False

            eb.connect("realize", on_realize)
            eb.connect("button-press-event", on_button_press)
            self.master_overlay.add_overlay(eb)
            return eb

        # 4 Edges
        make_handle("ns-resize", Gdk.WindowEdge.NORTH, -1, 6, Gtk.Align.FILL, Gtk.Align.START)
        make_handle("ns-resize", Gdk.WindowEdge.SOUTH, -1, 6, Gtk.Align.FILL, Gtk.Align.END)
        make_handle("ew-resize", Gdk.WindowEdge.WEST, 6, -1, Gtk.Align.START, Gtk.Align.FILL)
        make_handle("ew-resize", Gdk.WindowEdge.EAST, 6, -1, Gtk.Align.END, Gtk.Align.FILL)

        # 4 Corners
        make_handle("nwse-resize", Gdk.WindowEdge.NORTH_WEST, 14, 14, Gtk.Align.START, Gtk.Align.START)
        make_handle("nesw-resize", Gdk.WindowEdge.NORTH_EAST, 14, 14, Gtk.Align.END, Gtk.Align.START)
        make_handle("nesw-resize", Gdk.WindowEdge.SOUTH_WEST, 14, 14, Gtk.Align.START, Gtk.Align.END)
        make_handle("nwse-resize", Gdk.WindowEdge.SOUTH_EAST, 16, 16, Gtk.Align.END, Gtk.Align.END)

    def _setup_sidebar_folders(self):
        """Column 1 of Sidebar: Folders list."""
        self.folders_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.folders_container.set_size_request(160, -1)
        self.folders_container.get_style_context().add_class("mac-folders-col")

        # Top label
        lbl_folders = Gtk.Label(label="iCloud")
        lbl_folders.get_style_context().add_class("mac-sidebar-section-header")
        lbl_folders.set_xalign(0.0)
        lbl_folders.set_margin_start(16)
        lbl_folders.set_margin_top(12)
        lbl_folders.set_margin_bottom(4)
        self.folders_container.pack_start(lbl_folders, False, False, 0)

        self.folder_buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.folders_container.pack_start(self.folder_buttons_box, True, True, 0)

        self._refresh_folders_list()
        self.sidebar_box.pack_start(self.folders_container, False, False, 0)

        # Vertical divider inside sidebar
        sep_folder = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep_folder.get_style_context().add_class("mac-separator")
        self.sidebar_box.pack_start(sep_folder, False, False, 0)

    def _refresh_folders_list(self):
        for child in self.folder_buttons_box.get_children():
            self.folder_buttons_box.remove(child)

        for folder in self.notes_mgr.folders:
            f_id = folder["id"]
            f_name = get_folder_display_name(f_id, folder.get("name", ""))
            f_icon = folder["icon"]
            count = self.notes_mgr.get_folder_count(f_id)

            btn = Gtk.Button()
            btn.get_style_context().add_class("mac-folder-item")
            if f_id == self.current_folder:
                btn.get_style_context().add_class("selected")

            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_box.set_margin_start(12)
            btn_box.set_margin_end(12)
            btn_box.set_margin_top(6)
            btn_box.set_margin_bottom(6)

            # Icon in gold or muted color
            icon_color = "#e39c12" if f_id == self.current_folder else "#8e8e93"
            btn_box.pack_start(get_image(f_icon, 15, icon_color), False, False, 0)

            lbl_name = Gtk.Label(label=f_name)
            lbl_name.get_style_context().add_class("folder-name")
            lbl_name.set_xalign(0.0)
            btn_box.pack_start(lbl_name, True, True, 0)

            if count > 0:
                lbl_cnt = Gtk.Label(label=str(count))
                lbl_cnt.get_style_context().add_class("folder-count")
                btn_box.pack_start(lbl_cnt, False, False, 0)

            btn.add(btn_box)
            btn.connect("clicked", lambda _, fid=f_id: self._select_folder(fid))
            self.folder_buttons_box.pack_start(btn, False, False, 0)

        self.folder_buttons_box.show_all()

    def _select_folder(self, folder_id: str):
        self.current_folder = folder_id
        self._refresh_folders_list()
        self._refresh_notes_list()

    def _setup_sidebar_notes_list(self):
        """Column 2 of Sidebar: Search bar, New Note button, and Notes cards list."""
        self.notes_list_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notes_list_col.set_size_request(220, -1)
        self.notes_list_col.get_style_context().add_class("mac-notes-col")

        # Top Bar: Search Entry + Compose Button
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top_bar.set_margin_start(10)
        top_bar.set_margin_end(10)
        top_bar.set_margin_top(10)
        top_bar.set_margin_bottom(4)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(t("notes_search_placeholder", "Tìm kiếm…"))
        self.search_entry.get_style_context().add_class("mac-notes-search")
        self.search_entry.connect("search-changed", self._on_search_changed)
        top_bar.pack_start(self.search_entry, True, True, 0)

        # Apple Notes signature Yellow Compose button
        self.btn_new_note = Gtk.Button()
        self.btn_new_note.set_size_request(28, 28)
        self.btn_new_note.get_style_context().add_class("mac-notes-compose-btn")
        self.btn_new_note.add(get_image("plus", 14, "#ffffff"))
        self.btn_new_note.set_tooltip_text(t("notes_new_note", "Soạn ghi chú mới"))
        self.btn_new_note.connect("clicked", lambda _: self._create_new_note())
        top_bar.pack_start(self.btn_new_note, False, False, 0)

        self.notes_list_col.pack_start(top_bar, False, False, 0)

        # Scrolled Window for notes cards
        self.scroll_notes = Gtk.ScrolledWindow()
        self.scroll_notes.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.notes_cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.notes_cards_box.set_margin_start(8)
        self.notes_cards_box.set_margin_end(8)
        self.notes_cards_box.set_margin_bottom(8)
        self.scroll_notes.add(self.notes_cards_box)
        self.notes_list_col.pack_start(self.scroll_notes, True, True, 0)

        self.sidebar_box.pack_start(self.notes_list_col, False, False, 0)
        self._refresh_notes_list()

    def _refresh_notes_list(self):
        for child in self.notes_cards_box.get_children():
            self.notes_cards_box.remove(child)

        notes = self.notes_mgr.get_notes(self.current_folder, self.current_query)

        for note in notes:
            n_id = note["id"]
            n_title = note.get("title", t("notes_untitled", "Không có tiêu đề"))
            n_date = note.get("created_at", "")
            n_body = note.get("body", "")
            has_audio = note.get("audio") is not None
            is_pinned = note.get("pinned", False)

            btn = Gtk.Button()
            btn.get_style_context().add_class("mac-note-card")
            if self.current_note and self.current_note.get("id") == n_id:
                btn.get_style_context().add_class("selected")

            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            card_box.set_margin_start(10)
            card_box.set_margin_end(10)
            card_box.set_margin_top(8)
            card_box.set_margin_bottom(8)

            # Title Row with pin indicator
            title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            if is_pinned:
                pin_img = get_image("pin", size=13, color="#e39c12")
                title_row.pack_start(pin_img, False, False, 0)

            lbl_t = Gtk.Label(label=n_title)
            lbl_t.get_style_context().add_class("note-card-title")
            lbl_t.set_xalign(0.0)
            lbl_t.set_ellipsize(Pango.EllipsizeMode.END)
            title_row.pack_start(lbl_t, True, True, 0)

            if has_audio:
                # Audio message badge
                audio_img = get_image("waveform", size=13, color="#007aff" if not self.is_dark else "#0a84ff")
                title_row.pack_start(audio_img, False, False, 0)

            card_box.pack_start(title_row, False, False, 0)

            # Date and preview snippet
            snippet_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl_d = Gtk.Label(label=n_date.split(" lúc ")[-1] if " lúc " in n_date else n_date[:12])
            lbl_d.get_style_context().add_class("note-card-date")
            snippet_row.pack_start(lbl_d, False, False, 0)

            first_line = n_body.strip().split("\n")[0] if n_body.strip() else "Không có văn bản phụ"
            lbl_prev = Gtk.Label(label=first_line)
            lbl_prev.get_style_context().add_class("note-card-preview")
            lbl_prev.set_xalign(0.0)
            lbl_prev.set_ellipsize(Pango.EllipsizeMode.END)
            snippet_row.pack_start(lbl_prev, True, True, 0)

            card_box.pack_start(snippet_row, False, False, 0)

            btn.add(card_box)
            btn.connect("clicked", lambda _, n=note: self.select_note(n))
            btn.connect("button-press-event", lambda w, ev, n=note: self._on_note_card_button_press(w, ev, n))
            self.notes_cards_box.pack_start(btn, False, False, 0)

        self.notes_cards_box.show_all()

    def _on_note_card_button_press(self, widget, event, note):
        if event.button == 3:  # Right-click
            self.select_note(note)
            self._show_note_context_menu(widget, note, event)
            return True
        return False

    def _show_note_context_menu(self, widget, note, event):
        menu = Gtk.Menu()
        menu.get_style_context().add_class("mac-context-menu")
        is_dark = is_system_dark_mode()

        def make_menu_item(icon_name, text, cb, is_destructive=False):
            item = Gtk.MenuItem()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            if is_destructive:
                icon_color = "#ff3b30" if not is_dark else "#ff453a"
            elif icon_name == "pin":
                icon_color = "#e39c12"
            else:
                icon_color = "#86868b" if not is_dark else "#98989d"

            icon_img = get_image(icon_name, size=16, color=icon_color)
            icon_box = Gtk.Box()
            icon_box.set_size_request(20, 20)
            icon_box.pack_start(icon_img, True, True, 0)
            box.pack_start(icon_box, False, False, 0)

            lbl = Gtk.Label(label=text)
            lbl.set_xalign(0.0)
            if is_destructive:
                lbl.get_style_context().add_class("destructive-label")
            box.pack_start(lbl, True, True, 0)
            item.add(box)
            item.connect("activate", lambda _: cb())
            return item

        is_trash = note.get("in_trash", False)
        if is_trash:
            menu.append(make_menu_item("restore", t("notes_restore", "Khôi phục ghi chú"), lambda: self._restore_note_by_id(note["id"])))
            menu.append(make_menu_item("trash", t("notes_delete_forever", "Xóa vĩnh viễn"), lambda: self._delete_note_by_id(note["id"]), is_destructive=True))
        else:
            is_pinned = note.get("pinned", False)
            pin_text = t("notes_unpin", "Bỏ ghim") if is_pinned else t("notes_pin", "Ghim ghi chú")
            menu.append(make_menu_item("pin_slash" if is_pinned else "pin", pin_text, lambda: [self.notes_mgr.toggle_pin(note["id"]), self._refresh_notes_list()]))
            menu.append(make_menu_item("duplicate", t("notes_duplicate", "Tạo bản sao (Duplicate)"), lambda: [self.notes_mgr.duplicate_note(note["id"]), self._refresh_notes_list()]))

            sep = Gtk.SeparatorMenuItem()
            menu.append(sep)

            menu.append(make_menu_item("trash", t("notes_delete", "Xóa ghi chú (Delete)"), lambda: self._delete_note_by_id(note["id"]), is_destructive=True))

        menu.show_all()
        menu.popup_at_pointer(event)

    def _setup_note_editor(self):
        """Center Main Note Editor Area."""
        self.editor_scroll = Gtk.ScrolledWindow()
        self.editor_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.editor_scroll.get_style_context().add_class("mac-editor-scroll")

        self.editor_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.editor_container.set_margin_start(36)
        self.editor_container.set_margin_end(36)
        self.editor_container.set_margin_top(24)
        self.editor_container.set_margin_bottom(36)
        self.editor_scroll.add(self.editor_container)

        # 1. Date Header Subtitle (e.g. "May 2, 2024 at 7:34 PM")
        self.lbl_note_date = Gtk.Label(label="May 2, 2024 at 7:34 PM")
        self.lbl_note_date.get_style_context().add_class("editor-date-header")
        self.lbl_note_date.set_halign(Gtk.Align.CENTER)
        self.editor_container.pack_start(self.lbl_note_date, False, False, 0)

        # 2. Large Note Title Entry
        self.title_entry = Gtk.Entry()
        self.title_entry.set_text("Cuộc gọi với Rigo Rangel")
        self.title_entry.get_style_context().add_class("editor-title-entry")
        self.title_entry.connect("changed", self._on_title_changed)
        self.editor_container.pack_start(self.title_entry, False, False, 0)

        # 3. Embedded Inline Audio Message Card Container (Capsule right under title)
        self.audio_card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.editor_container.pack_start(self.audio_card_box, False, False, 0)

        # 4. Rich Text Content (Dialogue / Body)
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.get_style_context().add_class("editor-text-view")
        self.text_buffer = self.text_view.get_buffer()
        self.text_buffer.connect("changed", self._on_body_changed)

        # Create tags for speakers and formatting
        self.tag_speaker = self.text_buffer.create_tag(
            "speaker_tag",
            weight=Pango.Weight.BOLD,
            scale=1.05,
            foreground="#1d1d1f" if not self.is_dark else "#f5f5f7"
        )
        self.tag_body = self.text_buffer.create_tag(
            "body_tag",
            scale=1.0,
            foreground="#3a3a3c" if not self.is_dark else "#d1d1d6"
        )
        self.tag_checklist_circle = self.text_buffer.create_tag(
            "checklist_circle",
            weight=Pango.Weight.BOLD,
            scale=1.15,
            foreground="#e39c12"  # Apple Notes signature Amber/Orange checklist accent
        )
        self.tag_completed = self.text_buffer.create_tag(
            "completed_task",
            strikethrough=True,
            foreground="#86868b" if not self.is_dark else "#636366"
        )

        self.text_view.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.text_view.connect("key-press-event", self._on_text_view_key_press)
        self.text_view.connect("button-press-event", self._on_text_view_button_press)
        self.text_view.connect("motion-notify-event", self._on_text_view_motion_notify)

        self.editor_container.pack_start(self.text_view, False, False, 0)

        # 5. Locked Note Shield Overlay
        self.locked_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.locked_box.set_no_show_all(True)
        self.locked_box.set_valign(Gtk.Align.CENTER)
        self.locked_box.set_halign(Gtk.Align.CENTER)
        self.locked_box.set_margin_top(60)
        self.locked_box.set_margin_bottom(60)

        lock_icon_big = get_image("lock", 48, "#e39c12")
        self.locked_box.pack_start(lock_icon_big, False, False, 0)

        lbl_locked_title = Gtk.Label()
        lbl_locked_title.set_markup("<span font='16' weight='bold'>Ghi chú này đã được khóa</span>")
        self.locked_box.pack_start(lbl_locked_title, False, False, 0)

        lbl_locked_sub = Gtk.Label(label="Nội dung đã được bảo vệ bằng mật khẩu ghi chú macOS.")
        lbl_locked_sub.get_style_context().add_class("editor-date-header")
        self.locked_box.pack_start(lbl_locked_sub, False, False, 0)

        self.btn_unlock_note = Gtk.Button(label="Mở khóa ghi chú...")
        self.btn_unlock_note.get_style_context().add_class("mac-audio-done-btn")
        self.btn_unlock_note.connect("clicked", lambda _: self._toggle_lock())
        self.locked_box.pack_start(self.btn_unlock_note, False, False, 0)

        self.editor_container.pack_start(self.locked_box, False, False, 0)

        self.workspace_box.pack_start(self.editor_scroll, True, True, 0)

    def select_note(self, note: Any):
        """Load a note into the editor and update audio inspector."""
        if isinstance(note, str):
            note = self.notes_mgr.get_note_by_id(note) or {}
        self._is_loading_note = True
        try:
            self.current_note = note

            # Update top toolbar title
            title = note.get("title", "Không có tiêu đề")
            self.lbl_window_title.set_text(title)
            date_str = note.get("created_at", "")
            self.lbl_window_subtitle.set_text(f"iCloud - {date_str}")

            # Update editor fields
            self.lbl_note_date.set_text(date_str)
            self.title_entry.set_text(title)

            # Populate body text
            self.text_buffer.set_text("")
            body = note.get("body", "")
            self._format_and_insert_body(body)

            # Inline Audio Card
            for child in self.audio_card_box.get_children():
                self.audio_card_box.remove(child)

            audio_data = note.get("audio")
            if audio_data:
                self.inline_card = InlineAudioCardWidget(
                    audio_data=audio_data,
                    on_play_pause=self._toggle_play_pause,
                    on_skip=self._skip_audio,
                    on_open_inspector=self.toggle_audio_inspector,
                    on_seek=self._seek_audio_fraction
                )
                self.audio_card_box.pack_start(self.inline_card, False, False, 0)
                self.audio_card_box.show_all()

                # Load into audio inspector
                self.audio_inspector.load_transcript(audio_data.get("transcript", []))
                dur = float(audio_data.get("duration_sec") or audio_data.get("duration") or 0.0)
                cur = float(audio_data.get("current_pos_sec") or audio_data.get("current_pos") or 0.0)
                self.current_audio_duration = dur
                self.current_audio_time = cur
                self.audio_inspector.update_timer(cur, dur)
                self.audio_inspector.lbl_header_subtitle.set_text(
                    audio_data.get("sub_date_str", "5/2/25, 7:06 PM 02:12")
                )

                # Set player URI
                audio_file = audio_data.get("file_path", "")
                if os.path.exists(audio_file) and self.player:
                    self.player.set_state(Gst.State.READY)
                    self.player.set_property("uri", f"file://{os.path.abspath(audio_file)}")
            else:
                self.current_audio_duration = 0.0
                self.current_audio_time = 0.0
                self.audio_inspector.load_transcript([])
                self.audio_inspector.update_timer(0.0, 0.0)
                self.audio_inspector.lbl_header_subtitle.set_text("")
                if not getattr(self, "is_recording", False):
                    self.hide_audio_inspector()

            # Update lock state
            self._update_editor_lock_state(note.get("locked", False))
        finally:
            self._is_loading_note = False

        self._refresh_notes_list()

    def _format_and_insert_body(self, text: str):
        """Format dialogue text with bold speaker names and clean checklist circles."""
        # Auto-upgrade any old ugly '🔘 [ ] ' or '🔘 [x] ' to clean Apple circles
        text = text.replace("🔘 [ ] ", "○ ").replace("🔘 [x] ", "● ").replace("🔘 [ ]", "○ ")
        lines = text.split("\n")
        iter_end = self.text_buffer.get_end_iter()

        for line in lines:
            line_s = line.strip()
            if line_s in ("Tonio", "Rigo", "Rodrigo", "Speaker 1", "Speaker 2"):
                self.text_buffer.insert_with_tags(iter_end, f"{line}\n", self.tag_speaker)
            else:
                self.text_buffer.insert_with_tags(iter_end, f"{line}\n", self.tag_body)
            iter_end = self.text_buffer.get_end_iter()

        self._schedule_reapply_checklist_tags()

    # -----------------------------------------------------------------
    # Audio Playback & Skip Controls
    # -----------------------------------------------------------------
    def _toggle_play_pause(self):
        if not self.current_note or not self.current_note.get("audio"):
            # If no audio, open inspector to record!
            self.show_audio_inspector()
            return

        if self.is_playing:
            self._pause_audio()
        else:
            self._play_audio()

    def _play_audio(self):
        if not self.player:
            return

        audio_data = self.current_note.get("audio") if self.current_note else None
        if not audio_data:
            return

        audio_path = audio_data.get("file_path", "")
        if not os.path.exists(audio_path):
            # Fallback to sample audio
            audio_path = SAMPLE_AUDIO_PATH

        if os.path.exists(audio_path):
            self.player.set_property("uri", f"file://{os.path.abspath(audio_path)}")

        self.player.set_state(Gst.State.PLAYING)
        self.is_playing = True

        if hasattr(self, "inline_card") and self.inline_card:
            self.inline_card.update_play_state(True)
        self.audio_inspector.update_play_state(True)

        # Start timer loop
        if self._playback_timer_id is None:
            self._playback_timer_id = GLib.timeout_add(30, self._on_playback_tick)

    def _pause_audio(self):
        if self.player:
            self.player.set_state(Gst.State.PAUSED)
        self.is_playing = False

        if hasattr(self, "inline_card") and self.inline_card:
            self.inline_card.update_play_state(False)
        self.audio_inspector.update_play_state(False)

        if self._playback_timer_id:
            GLib.source_remove(self._playback_timer_id)
            self._playback_timer_id = None

    def _skip_audio(self, delta_seconds: float):
        """Skip backward or forward by delta_seconds (e.g. -15 or +15)."""
        new_time = max(0.0, min(self.current_audio_duration, self.current_audio_time + delta_seconds))
        self._seek_audio_seconds(new_time)

    def _seek_audio_fraction(self, fraction: float):
        """Seek via scrubber fraction 0.0 - 1.0."""
        new_time = fraction * self.current_audio_duration
        self._seek_audio_seconds(new_time)

    def _seek_audio_seconds(self, seconds: float):
        self.current_audio_time = seconds
        if self.player:
            nanos = int(seconds * Gst.SECOND)
            self.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanos
            )

        self.audio_inspector.update_timer(self.current_audio_time, self.current_audio_duration)
        self.audio_inspector.highlight_at_time(self.current_audio_time)
        if hasattr(self, "inline_card") and self.inline_card:
            self.inline_card.update_time(self.current_audio_time, self.current_audio_duration)

    def _on_playback_tick(self):
        if not self.is_playing:
            return False

        if self.player:
            success, pos = self.player.query_position(Gst.Format.TIME)
            if success:
                self.current_audio_time = pos / float(Gst.SECOND)
            else:
                self.current_audio_time += 0.03

            success_dur, dur = self.player.query_duration(Gst.Format.TIME)
            if success_dur and dur > 0:
                self.current_audio_duration = dur / float(Gst.SECOND)

        # Update displays
        self.audio_inspector.update_timer(self.current_audio_time, self.current_audio_duration)
        self.audio_inspector.highlight_at_time(self.current_audio_time)
        if hasattr(self, "inline_card") and self.inline_card:
            self.inline_card.update_time(self.current_audio_time, self.current_audio_duration)

        # End of stream check
        if self.current_audio_time >= self.current_audio_duration:
            self._pause_audio()
            self._seek_audio_seconds(0.0)
            return False

        return True

    # -----------------------------------------------------------------
    # Microphone Recording
    # -----------------------------------------------------------------
    def _toggle_mic_recording(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording from microphone."""
        if not self.current_note:
            self._create_new_note()
        self._pause_audio()
        self.is_recording = True
        self.record_start_time = time.time()
        self.record_file_path = os.path.join(RECORDINGS_DIR, f"rec_{int(time.time())}.wav")

        # Try pw-record or arecord or GStreamer
        try:
            cmd = ["pw-record", "--rate", "22050", "--channels", "1", self.record_file_path]
            self.record_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            try:
                cmd = ["arecord", "-f", "cd", "-t", "wav", self.record_file_path]
                self.record_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"[Notes] Could not launch mic recording: {e}")
                self.record_proc = None

        self.audio_inspector.update_record_state(True)
        GLib.timeout_add(50, self._on_record_tick)

    def _stop_recording(self):
        """Stop microphone recording."""
        self.is_recording = False
        if self.record_proc:
            try:
                self.record_proc.terminate()
                self.record_proc.wait(timeout=1.0)
            except Exception:
                pass
            self.record_proc = None

        self.audio_inspector.update_record_state(False)

    def _on_record_tick(self):
        if not self.is_recording:
            return False

        elapsed = time.time() - self.record_start_time
        self.audio_inspector.update_timer(elapsed, elapsed)
        # Random simulated audio level for live waveform animation
        level = 0.2 + 0.6 * math.sin(elapsed * 4.0) ** 2
        self.audio_inspector.waveform_scrubber.set_recording(True, level)
        return True

    def _on_done_recording(self):
        """Save recorded audio and embed into note, or dismiss inspector."""
        if self.is_recording:
            self._stop_recording()

        if self.record_file_path and os.path.exists(self.record_file_path):
            rec_dur = max(2.0, time.time() - getattr(self, "record_start_time", time.time()))
            new_audio = {
                "id": f"audio-{int(time.time())}",
                "title": "Ghi âm thoại",
                "file_path": self.record_file_path,
                "date_str": time.strftime("%b %d, %Y lúc %I:%M %p"),
                "sub_date_str": time.strftime("%d/%m/%y, %H:%M"),
                "duration_sec": rec_dur,
                "current_pos_sec": 0.0,
                "preview_text": "Bản ghi âm thoại mới...",
                "transcript": [
                    {
                        "speaker": "Tôi",
                        "text": "Bản ghi âm đã được lưu thành công vào ghi chú.",
                        "start_time": 0.0,
                        "end_time": rec_dur
                    }
                ]
            }

            if self.current_note:
                self.notes_mgr.update_note(self.current_note["id"], audio=new_audio)
                self.select_note(self.current_note)

            self.record_file_path = None

        self._pause_audio()
        self.hide_audio_inspector()

    # -----------------------------------------------------------------
    # Inspector & Sidebar Toggle
    # -----------------------------------------------------------------
    def show_audio_inspector(self, *args, **kwargs):
        if not self.current_note:
            # When user opens audio inspector without a note open, create a new note
            self._create_new_note()

        audio_data = self.current_note.get("audio") if self.current_note else None
        if audio_data:
            dur = float(audio_data.get("duration_sec") or audio_data.get("duration") or 0.0)
            cur = float(audio_data.get("current_pos_sec") or audio_data.get("current_pos") or 0.0)
            self.audio_inspector.load_transcript(audio_data.get("transcript", []))
            self.audio_inspector.lbl_header_title.set_text(audio_data.get("title", "Ghi âm thoại"))
            self.audio_inspector.update_timer(cur, dur)
            date_str = audio_data.get("sub_date_str") or audio_data.get("date_str") or time.strftime("%d/%m/%Y lúc %H:%M")
            if "•" not in date_str and dur > 0:
                date_str = f"{date_str} • {format_duration(dur)}"
            self.audio_inspector.lbl_header_subtitle.set_text(date_str)
            self.audio_inspector.btn_trash_audio.set_sensitive(True)
            self.audio_inspector.btn_more.set_sensitive(True)
        else:
            now_str = time.strftime("%d/%m/%Y lúc %H:%M")
            self.audio_inspector.lbl_header_title.set_text("Ghi âm thoại")
            self.audio_inspector.lbl_header_subtitle.set_text(now_str)
            self.audio_inspector.update_timer(0.0, 0.0)
            self.audio_inspector.waveform_scrubber.set_progress(0.0)
            self.audio_inspector.load_transcript([])
            self.audio_inspector.update_record_state(getattr(self, "is_recording", False))
            self.audio_inspector.update_play_state(getattr(self, "is_playing", False))
            self.audio_inspector.btn_trash_audio.set_sensitive(False)
            self.audio_inspector.btn_more.set_sensitive(False)

        self._is_inspector_visible = True
        self.audio_inspector.set_no_show_all(False)
        self.audio_inspector.show_all()
        self.audio_inspector.set_no_show_all(True)
        self.sep_inspector.show()
        if hasattr(self, "btn_toolbar_mic"):
            self.btn_toolbar_mic.get_style_context().add_class("toolbar-btn-active")

    def hide_audio_inspector(self):
        self._is_inspector_visible = False
        if getattr(self, "is_recording", False):
            self._stop_recording()
        self._pause_audio()
        if hasattr(self, "audio_inspector"):
            self.audio_inspector.hide()
        if hasattr(self, "sep_inspector"):
            self.sep_inspector.hide()
        if hasattr(self, "btn_toolbar_mic"):
            self.btn_toolbar_mic.get_style_context().remove_class("toolbar-btn-active")

    def toggle_audio_inspector(self):
        if self._is_inspector_visible and hasattr(self, "audio_inspector") and self.audio_inspector.get_visible():
            self.hide_audio_inspector()
        else:
            self.show_audio_inspector()

    def toggle_sidebar(self):
        self._is_sidebar_visible = not self._is_sidebar_visible
        if self._is_sidebar_visible:
            self.sidebar_box.show()
        else:
            self.sidebar_box.hide()

    # -----------------------------------------------------------------
    # Note Actions
    # -----------------------------------------------------------------
    def _create_new_note(self):
        new_n = self.notes_mgr.create_note(title=t("notes_new", "Ghi chú mới"), folder=self.current_folder)
        self._refresh_notes_list()
        self.select_note(new_n)
        self.title_entry.grab_focus()

    def _on_title_changed(self, entry):
        if getattr(self, "_is_loading_note", False):
            return
        if self.current_note:
            new_title = entry.get_text()
            self.current_note["title"] = new_title
            self.lbl_window_title.set_text(new_title or "Không có tiêu đề")
            self.notes_mgr.update_note(self.current_note["id"], title=new_title)
            self._refresh_notes_list()

    def _on_body_changed(self, buf):
        self._schedule_reapply_checklist_tags()
        if getattr(self, "_is_loading_note", False):
            return
        if self.current_note:
            start_it = buf.get_start_iter()
            end_it = buf.get_end_iter()
            text = buf.get_text(start_it, end_it, True)
            self.current_note["body"] = text
            self.notes_mgr.update_note(self.current_note["id"], body=text)

    def _on_search_changed(self, entry):
        self.current_query = entry.get_text().strip()
        self._refresh_notes_list()

    def _show_format_popover(self):
        """Show Aa formatting options popover."""
        pop = Gtk.Popover.new(self.btn_format)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)

        formats = [
            (t("format_title", "Tiêu đề lớn (Title)"), lambda: self._apply_format("title")),
            (t("format_heading", "Đầu đề (Heading)"), lambda: self._apply_format("heading")),
            (t("format_subheading", "Đầu đề phụ (Subheading)"), lambda: self._apply_format("subheading")),
            (t("format_body", "Thân bài (Body)"), lambda: self._apply_format("body")),
            (t("format_mono", "Đơn cách (Monospaced)"), lambda: self._apply_format("mono")),
            (t("format_bullet", "Danh sách dấu chấm (Bullet List)"), lambda: self._apply_format("bullet")),
            (t("format_number", "Danh sách số (Numbered List)"), lambda: self._apply_format("number")),
        ]

        for fmt_lbl, cb in formats:
            b = Gtk.Button()
            b.get_style_context().add_class("mac-popover-item")
            lbl = Gtk.Label(label=fmt_lbl)
            lbl.set_xalign(0.0)
            b.add(lbl)
            b.set_halign(Gtk.Align.FILL)
            b.connect("clicked", lambda _, f=cb, p=pop: [f(), p.popdown()])
            vbox.pack_start(b, False, False, 0)

        pop.add(vbox)
        pop.show_all()
        pop.popup()

    def _apply_format(self, fmt_type: str):
        buf = self.text_buffer
        insert_mark = buf.get_insert()
        cursor_it = buf.get_iter_at_mark(insert_mark)
        line_start = cursor_it.copy()
        line_start.set_line_offset(0)

        if fmt_type == "bullet":
            buf.insert(line_start, "• ")
        elif fmt_type == "number":
            buf.insert(line_start, "1. ")
        elif fmt_type == "title":
            buf.insert(line_start, "# ")
        elif fmt_type == "heading":
            buf.insert(line_start, "## ")
        elif fmt_type == "subheading":
            buf.insert(line_start, "### ")
        elif fmt_type == "mono":
            buf.insert(cursor_it, "`code`")

    def _schedule_reapply_checklist_tags(self):
        """Debounced caller for checklist styling."""
        if getattr(self, "_checklist_tag_idle_pending", False):
            return
        self._checklist_tag_idle_pending = True
        def _apply():
            self._checklist_tag_idle_pending = False
            self._reapply_checklist_tags()
            return False
        GLib.idle_add(_apply)

    def _insert_checklist(self):
        buf = self.text_buffer
        bounds = buf.get_selection_bounds()
        if bounds:
            sel_start, sel_end = bounds
            start_line = sel_start.get_line()
            end_line = sel_end.get_line()
            for line_idx in range(start_line, end_line + 1):
                l_s = buf.get_iter_at_line(line_idx)
                l_e = l_s.copy()
                l_e.forward_to_line_end()
                lt = buf.get_text(l_s, l_e, False)
                if lt.startswith("○ ") or lt.startswith("● "):
                    del_end = l_s.copy()
                    del_end.forward_chars(2)
                    buf.delete(l_s, del_end)
                elif lt.startswith("🔘 [ ] ") or lt.startswith("🔘 [x] "):
                    prefix_len = len("🔘 [ ] ") if lt.startswith("🔘 [ ] ") else len("🔘 [x] ")
                    del_end = l_s.copy()
                    del_end.forward_chars(prefix_len)
                    buf.delete(l_s, del_end)
                    buf.insert(l_s, "○ ")
                elif lt.strip():
                    buf.insert(l_s, "○ ")
            self._schedule_reapply_checklist_tags()
            return

        insert_mark = buf.get_insert()
        cursor_it = buf.get_iter_at_mark(insert_mark)
        line_start = cursor_it.copy()
        line_start.set_line_offset(0)
        line_end = line_start.copy()
        line_end.forward_to_line_end()
        line_text = buf.get_text(line_start, line_end, False)

        # If line already has checklist prefix, toggle it off
        if line_text.startswith("○ ") or line_text.startswith("● "):
            del_end = line_start.copy()
            del_end.forward_chars(2)
            buf.delete(line_start, del_end)
        elif line_text.startswith("🔘 [ ] ") or line_text.startswith("🔘 [x] "):
            prefix_len = len("🔘 [ ] ") if line_text.startswith("🔘 [ ] ") else len("🔘 [x] ")
            del_end = line_start.copy()
            del_end.forward_chars(prefix_len)
            buf.delete(line_start, del_end)
            buf.insert(line_start, "○ ")
        else:
            buf.insert(line_start, "○ ")

        self._schedule_reapply_checklist_tags()

    def _on_text_view_key_press(self, widget, event):
        """Auto-continue or exit checklist on Enter press, matching macOS Notes."""
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            buf = widget.get_buffer()
            insert_mark = buf.get_insert()
            cursor_it = buf.get_iter_at_mark(insert_mark)
            line_start = cursor_it.copy()
            line_start.set_line_offset(0)
            line_end = line_start.copy()
            line_end.forward_to_line_end()
            line_text = buf.get_text(line_start, line_end, False)

            # If empty checklist item ("○ " or "● "), pressing Enter cancels checklist mode
            if line_text in ("○ ", "● ", "🔘 [ ] ", "🔘 [x] "):
                buf.delete(line_start, line_end)
                return True
            elif line_text.startswith("○ ") or line_text.startswith("● "):
                buf.insert(cursor_it, "\n○ ")
                self._schedule_reapply_checklist_tags()
                return True
            elif line_text.startswith("• "):
                if line_text == "• ":
                    buf.delete(line_start, line_end)
                    return True
                buf.insert(cursor_it, "\n• ")
                return True
        elif event.keyval == Gdk.KEY_BackSpace:
            buf = widget.get_buffer()
            insert_mark = buf.get_insert()
            cursor_it = buf.get_iter_at_mark(insert_mark)
            offset = cursor_it.get_line_offset()
            if offset == 2:
                line_start = cursor_it.copy()
                line_start.set_line_offset(0)
                line_prefix = buf.get_text(line_start, cursor_it, False)
                if line_prefix in ("○ ", "● "):
                    buf.delete(line_start, cursor_it)
                    self._schedule_reapply_checklist_tags()
                    return True
        return False

    def _on_text_view_motion_notify(self, widget, event):
        """Show pointer/hand cursor when hovering over the checklist circular checkbox."""
        win_type = widget.get_window_type(event.window) if event.window else Gtk.TextWindowType.TEXT
        if win_type in (Gtk.TextWindowType.TEXT, Gtk.TextWindowType.WIDGET):
            x, y = widget.window_to_buffer_coords(win_type, int(event.x), int(event.y))
            res = widget.get_iter_at_location(x, y)
            it = res[1] if isinstance(res, tuple) else res
            offset = it.get_line_offset()
            if offset <= 3:
                line_start = it.copy()
                line_start.set_line_offset(0)
                line_end = line_start.copy()
                line_end.forward_to_line_end()
                lt = widget.get_buffer().get_text(line_start, line_end, False)
                if lt.startswith("○ ") or lt.startswith("● ") or lt.startswith("🔘"):
                    text_win = widget.get_window(Gtk.TextWindowType.TEXT)
                    if text_win:
                        if not hasattr(self, "_hand_cursor"):
                            self._hand_cursor = Gdk.Cursor.new_from_name(widget.get_display(), "pointer")
                        text_win.set_cursor(self._hand_cursor)
                        return False
        text_win = widget.get_window(Gtk.TextWindowType.TEXT)
        if text_win:
            text_win.set_cursor(None)
        return False

    def _on_text_view_button_press(self, widget, event):
        """Clicking on a checklist circle toggles it between completed (●) and pending (○)."""
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            win_type = widget.get_window_type(event.window) if event.window else Gtk.TextWindowType.TEXT
            if win_type in (Gtk.TextWindowType.TEXT, Gtk.TextWindowType.WIDGET):
                x, y = widget.window_to_buffer_coords(win_type, int(event.x), int(event.y))
            else:
                x, y = widget.window_to_buffer_coords(Gtk.TextWindowType.TEXT, int(event.x), int(event.y))

            res = widget.get_iter_at_location(x, y)
            it = res[1] if isinstance(res, tuple) else res
            line_start = it.copy()
            line_start.set_line_offset(0)
            line_end = line_start.copy()
            line_end.forward_to_line_end()
            line_text = widget.get_buffer().get_text(line_start, line_end, False)

            offset = it.get_line_offset()
            if offset <= 3:
                if line_text.startswith("○ ") or line_text.startswith("🔘 [ ] "):
                    prefix_len = 2 if line_text.startswith("○ ") else len("🔘 [ ] ")
                    del_end = line_start.copy()
                    del_end.forward_chars(prefix_len)
                    widget.get_buffer().delete(line_start, del_end)
                    widget.get_buffer().insert(line_start, "● ")
                    self._schedule_reapply_checklist_tags()
                    return True
                elif line_text.startswith("● ") or line_text.startswith("🔘 [x] ") or line_text.startswith("✓ "):
                    prefix_len = 2 if (line_text.startswith("● ") or line_text.startswith("✓ ")) else len("🔘 [x] ")
                    del_end = line_start.copy()
                    del_end.forward_chars(prefix_len)
                    widget.get_buffer().delete(line_start, del_end)
                    widget.get_buffer().insert(line_start, "○ ")
                    self._schedule_reapply_checklist_tags()
                    return True
        return False

    def _reapply_checklist_tags(self):
        """Applies amber styling to circles and strikethrough to completed items."""
        buf = getattr(self, "text_buffer", None)
        if not buf:
            return
        start_it = buf.get_start_iter()
        end_it = buf.get_end_iter()
        buf.remove_tag(self.tag_completed, start_it, end_it)
        buf.remove_tag(self.tag_checklist_circle, start_it, end_it)

        num_lines = buf.get_line_count()
        for line_idx in range(num_lines):
            l_s = buf.get_iter_at_line(line_idx)
            l_e = l_s.copy()
            l_e.forward_to_line_end()
            txt = buf.get_text(l_s, l_e, False)
            if txt.startswith("○ "):
                c_e = l_s.copy()
                c_e.forward_chars(1)
                buf.apply_tag(self.tag_checklist_circle, l_s, c_e)
            elif txt.startswith("● ") or txt.startswith("✓ "):
                c_e = l_s.copy()
                c_e.forward_chars(1)
                buf.apply_tag(self.tag_checklist_circle, l_s, c_e)
                txt_s = l_s.copy()
                txt_s.forward_chars(2)
                buf.apply_tag(self.tag_completed, txt_s, l_e)

    def _insert_table(self):
        buf = self.text_buffer
        insert_mark = buf.get_insert()
        cursor_it = buf.get_iter_at_mark(insert_mark)
        table_str = "\n| Cột 1 | Cột 2 | Cột 3 |\n| --- | --- | --- |\n| Dữ liệu 1 | Dữ liệu 2 | Dữ liệu 3 |\n"
        buf.insert(cursor_it, table_str)

    def _attach_file(self):
        dlg = Gtk.FileChooserDialog(
            title="Đính kèm tệp / hình ảnh vào ghi chú",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dlg.add_button("Hủy", Gtk.ResponseType.CANCEL)
        dlg.add_button("Đính kèm", Gtk.ResponseType.OK)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            if path:
                base = os.path.basename(path)
                ext = os.path.splitext(path)[1].lower()
                it = self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert())
                if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
                    self.text_buffer.insert(it, f"\n🖼️ [{base}]({path})\n")
                else:
                    self.text_buffer.insert(it, f"\n📎 [{base}]({path})\n")
        dlg.destroy()

    def _toggle_markup(self):
        """Show macOS Markup annotation & sketch tool palette."""
        anchor = getattr(self, "btn_toolbar_markup", self.toolbar)
        self.markup_popover = Gtk.Popover.new(anchor)
        pop = self.markup_popover
        pop.set_position(Gtk.PositionType.BOTTOM)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)

        # Title Header
        lbl_header = Gtk.Label()
        lbl_header.set_markup("<b>Công cụ phác thảo &amp; Bút vẽ (Markup)</b>")
        lbl_header.set_xalign(0.0)
        vbox.pack_start(lbl_header, False, False, 0)

        # Tools Row
        tools_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        markup_tools = [
            ("pen", "Bút mực", "🖋️"),
            ("highlighter", "Dạ quang", "🖍️"),
            ("pencil", "Bút chì", "✏️"),
            ("eraser", "Tẩy", "🧹"),
        ]
        for t_id, t_name, t_icon in markup_tools:
            b = Gtk.Button(label=f"{t_icon} {t_name}")
            b.get_style_context().add_class("mac-popover-item")
            def on_tool_click(tname=t_name):
                buf = self.text_buffer
                it = buf.get_iter_at_mark(buf.get_insert())
                buf.insert(it, f"\n> 🎨 **[{tname}]**: [Vùng phác thảo đã chèn - Sẵn sàng vẽ]\n")
                pop.popdown()
            b.connect("clicked", lambda _, tn=t_name: on_tool_click(tn))
            tools_row.pack_start(b, False, False, 0)
        vbox.pack_start(tools_row, False, False, 0)

        # Colors Palette Row
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("mac-separator")
        vbox.pack_start(sep, False, False, 2)

        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        color_box.set_halign(Gtk.Align.CENTER)
        colors = [
            ("#1d1d1f", "Đen"),
            ("#007aff", "Xanh"),
            ("#ff3b30", "Đỏ"),
            ("#ffcc00", "Vàng"),
            ("#34c759", "Xanh lá"),
            ("#af52de", "Tím")
        ]
        for col_hex, col_name in colors:
            dot = Gtk.Button()
            dot.set_size_request(24, 24)
            dot.set_tooltip_text(f"Màu {col_name}")
            css_prov = Gtk.CssProvider()
            css_prov.load_from_data(f"button {{ background-color: {col_hex}; border-radius: 12px; border: 2px solid rgba(255,255,255,0.7); min-width: 24px; min-height: 24px; padding: 0; }}".encode())
            dot.get_style_context().add_provider(css_prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            def on_color_click(cn=col_name):
                buf = self.text_buffer
                it = buf.get_iter_at_mark(buf.get_insert())
                buf.insert(it, f" [Màu {cn}]")
                pop.popdown()
            dot.connect("clicked", lambda _, cn=col_name: on_color_click(cn))
            color_box.pack_start(dot, False, False, 0)

        vbox.pack_start(color_box, False, False, 0)

        pop.add(vbox)
        pop.show_all()
        pop.popup()

    def _toggle_lock(self):
        """Toggle lock state with visual locked shield and toolbar icon change."""
        if not self.current_note:
            return
        is_locked = self.current_note.get("locked", False)
        new_state = not is_locked
        self.current_note["locked"] = new_state
        self.notes_mgr.update_note(self.current_note["id"], locked=new_state)
        self._update_editor_lock_state(new_state)
        self._refresh_notes_list()

    def _update_editor_lock_state(self, is_locked: bool):
        """Update editor visibility based on lock status."""
        if is_locked:
            self.text_view.hide()
            self.audio_card_box.hide()
            if hasattr(self, "locked_box"):
                self.locked_box.show()
            if hasattr(self, "btn_toolbar_lock"):
                child = self.btn_toolbar_lock.get_child()
                if child:
                    self.btn_toolbar_lock.remove(child)
                self.btn_toolbar_lock.add(get_image("lock", 16, "#e39c12"))
                self.btn_toolbar_lock.set_tooltip_text("Mở khóa ghi chú này")
                self.btn_toolbar_lock.show_all()
        else:
            if hasattr(self, "locked_box"):
                self.locked_box.hide()
            self.text_view.show()
            self.audio_card_box.show()
            if hasattr(self, "btn_toolbar_lock"):
                child = self.btn_toolbar_lock.get_child()
                if child:
                    self.btn_toolbar_lock.remove(child)
                self.btn_toolbar_lock.add(get_image("unlock", 16, "#6e6e73"))
                self.btn_toolbar_lock.set_tooltip_text("Khóa ghi chú này")
                self.btn_toolbar_lock.show_all()

    def _share_note(self):
        """Show macOS Sequoia Share menu popover."""
        if not self.current_note:
            return
        anchor = getattr(self, "btn_toolbar_share", self.toolbar)
        self.share_popover = Gtk.Popover.new(anchor)
        pop = self.share_popover
        pop.set_position(Gtk.PositionType.BOTTOM)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)

        is_dark = is_system_dark_mode()

        def make_share_item(icon_name, text, cb):
            b = Gtk.Button()
            b.get_style_context().add_class("mac-popover-item")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_start(4)
            box.set_margin_end(6)
            box.set_margin_top(3)
            box.set_margin_bottom(3)
            img = get_image(icon_name, 16, "#007aff" if not is_dark else "#0a84ff")
            ibox = Gtk.Box()
            ibox.set_size_request(20, 20)
            ibox.pack_start(img, True, True, 0)
            box.pack_start(ibox, False, False, 0)
            lbl = Gtk.Label(label=text)
            lbl.set_xalign(0.0)
            lbl.get_style_context().add_class("mac-popover-label")
            box.pack_start(lbl, True, True, 0)
            b.add(box)
            b.set_halign(Gtk.Align.FILL)
            b.connect("clicked", lambda _: [cb(), pop.popdown()])
            return b

        title = self.current_note.get("title", "Ghi chú")
        body = self.current_note.get("body", "")

        def do_airdrop():
            try:
                from src.ui.macos_airdrop_window import MacOSAirDropWindow
                w = MacOSAirDropWindow.get_instance()
                w.show_window()
            except Exception as e:
                print(f"[Notes] AirDrop error: {e}")

        def do_copy():
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.set_text(f"{title}\n\n{body}", -1)

        def do_email():
            import urllib.parse
            subject = urllib.parse.quote(title)
            b_text = urllib.parse.quote(body)
            subprocess.Popen(["xdg-open", f"mailto:?subject={subject}&body={b_text}"])

        def do_export():
            self._export_note_txt()

        vbox.pack_start(make_share_item("airdrop", "Chia sẻ qua AirDrop...", do_airdrop), False, False, 0)
        vbox.pack_start(make_share_item("copy", "Sao chép toàn bộ nội dung", do_copy), False, False, 0)
        vbox.pack_start(make_share_item("mail", "Gửi qua Email...", do_email), False, False, 0)
        vbox.pack_start(make_share_item("export_txt", "Xuất ra tệp văn bản (.txt)...", do_export), False, False, 0)

        pop.add(vbox)
        pop.show_all()
        pop.popup()

    def _show_more_menu(self):
        anchor = getattr(self, "btn_more_toolbar", self.toolbar)
        pop = Gtk.Popover.new(anchor)
        pop.set_position(Gtk.PositionType.BOTTOM)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)

        is_dark = is_system_dark_mode()

        def make_action(icon_name, text, cb, is_destructive=False):
            b = Gtk.Button()
            b.get_style_context().add_class("mac-popover-item")
            if is_destructive:
                b.get_style_context().add_class("destructive")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_start(4)
            box.set_margin_end(6)
            box.set_margin_top(3)
            box.set_margin_bottom(3)

            if is_destructive:
                icon_color = "#ff3b30" if not is_dark else "#ff453a"
            elif icon_name == "pin":
                icon_color = "#e39c12"  # Apple Notes Amber/Yellow accent
            elif icon_name == "info_circle":
                icon_color = "#007aff" if not is_dark else "#0a84ff"
            elif icon_name == "export_txt":
                icon_color = "#34c759" if not is_dark else "#30d158"
            else:
                icon_color = "#86868b" if not is_dark else "#98989d"

            icon_img = get_image(icon_name, size=16, color=icon_color)
            icon_img.set_halign(Gtk.Align.CENTER)
            icon_img.set_valign(Gtk.Align.CENTER)
            icon_box = Gtk.Box()
            icon_box.set_size_request(20, 20)
            icon_box.pack_start(icon_img, True, True, 0)
            box.pack_start(icon_box, False, False, 0)

            lbl = Gtk.Label(label=text)
            lbl.set_xalign(0.0)
            lbl.get_style_context().add_class("mac-popover-label")
            if is_destructive:
                lbl.get_style_context().add_class("destructive-label")
            box.pack_start(lbl, True, True, 0)

            b.add(box)
            b.set_halign(Gtk.Align.FILL)
            b.connect("clicked", lambda _: [cb(), pop.popdown()])
            return b

        if self.current_note:
            is_pinned = self.current_note.get("pinned", False)
            vbox.pack_start(make_action("pin_slash" if is_pinned else "pin", "Bỏ ghim" if is_pinned else "Ghim ghi chú", self._toggle_pin_current), False, False, 0)
            vbox.pack_start(make_action("duplicate", "Tạo bản sao (Duplicate)", self._duplicate_current), False, False, 0)
            vbox.pack_start(make_action("info_circle", "Thông tin ghi chú (Info)", self._show_note_info), False, False, 0)
            vbox.pack_start(make_action("export_txt", "Xuất ra tệp văn bản (.txt)...", self._export_note_txt), False, False, 0)
            is_locked = self.current_note.get("locked", False)
            vbox.pack_start(make_action("unlock" if is_locked else "lock", "Mở khóa ghi chú" if is_locked else "Khóa ghi chú (Lock)", self._toggle_lock), False, False, 0)

            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.get_style_context().add_class("mac-separator")
            vbox.pack_start(sep, False, False, 3)

            vbox.pack_start(make_action("trash", "Xóa ghi chú (Delete)", self._delete_current, is_destructive=True), False, False, 0)
        else:
            vbox.pack_start(make_action("new_note", "Tạo ghi chú mới", self._new_note), False, False, 0)

        pop.add(vbox)
        pop.show_all()
        pop.popup()

    def _show_note_info(self):
        if not self.current_note:
            return
        title = self.current_note.get("title", "Không có tiêu đề")
        body = self.current_note.get("body", "")
        created = self.current_note.get("created_at", "Không rõ")
        updated = self.current_note.get("updated_at", created)
        word_count = len(body.split())
        char_count = len(body)
        line_count = len(body.splitlines())

        anchor = getattr(self, "btn_more_toolbar", self.toolbar)
        pop = Gtk.Popover.new(anchor)
        pop.set_position(Gtk.PositionType.BOTTOM)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        lbl_t = Gtk.Label()
        lbl_t.set_markup(f"<b>{title}</b>")
        lbl_t.set_halign(Gtk.Align.START)
        box.pack_start(lbl_t, False, False, 0)

        info_text = (
            f"<b>Số từ:</b> {word_count}\n"
            f"<b>Số ký tự:</b> {char_count}\n"
            f"<b>Số dòng:</b> {line_count}\n"
            f"<b>Ngày tạo:</b> {created}\n"
            f"<b>Sửa lần cuối:</b> {updated}"
        )
        lbl_info = Gtk.Label()
        lbl_info.set_markup(info_text)
        lbl_info.set_xalign(0.0)
        box.pack_start(lbl_info, False, False, 0)

        pop.add(box)
        pop.show_all()
        pop.popup()

    def _export_note_txt(self):
        if not self.current_note:
            return
        dialog = Gtk.FileChooserDialog(
            title="Xuất ghi chú thành tệp văn bản",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        safe_title = "".join(c for c in self.current_note.get("title", "note") if c.isalnum() or c in (' ', '_', '-')).strip()
        dialog.set_current_name(f"{safe_title or 'note'}.txt")
        dialog.set_do_overwrite_confirmation(True)

        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            dest = dialog.get_filename()
            dialog.destroy()
            try:
                content = f"{self.current_note.get('title', '')}\n\n{self.current_note.get('body', '')}"
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                print(f"[Notes] Error exporting note: {e}")
        else:
            dialog.destroy()

    def _insert_transcript_to_note(self, text: str):
        if not self.current_note:
            return
        buf = self.text_buffer
        end_iter = buf.get_end_iter()
        prefix = "\n\n--- Bản ghi chép thoại ---\n"
        buf.insert(end_iter, prefix + text)
        self._on_text_changed(buf)

    def _export_audio_file(self):
        dialog = Gtk.FileChooserDialog(
            title="Xuất tệp ghi âm",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_current_name("audio_message.wav")
        dialog.set_do_overwrite_confirmation(True)

        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            dest = dialog.get_filename()
            dialog.destroy()
            try:
                src = None
                if self.current_note and self.current_note.get("audio"):
                    src = self.current_note["audio"].get("audio_file")
                if not src or not os.path.exists(src):
                    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "sample_audio_call.wav")
                if src and os.path.exists(src):
                    import shutil
                    shutil.copyfile(src, dest)
            except Exception as e:
                print(f"[Notes] Error exporting audio: {e}")
        else:
            dialog.destroy()

    def _delete_audio_from_current_note(self):
        self._pause_audio()
        if self.current_note:
            note_id = self.current_note.get("id")
            self.current_note["audio"] = None
            if note_id:
                self.notes_mgr.update_note(note_id, audio=None)

        if getattr(self, "record_file_path", None) and os.path.exists(self.record_file_path):
            try:
                os.remove(self.record_file_path)
            except Exception:
                pass
            self.record_file_path = None

        self.current_audio_duration = 0.0
        self.current_audio_time = 0.0
        if self.player:
            self.player.set_state(Gst.State.NULL)

        for child in self.audio_card_box.get_children():
            self.audio_card_box.remove(child)

        self.audio_inspector.load_transcript([])
        self.audio_inspector.update_timer(0.0, 0.0)
        self.audio_inspector.lbl_header_subtitle.set_text("")
        self.audio_inspector.waveform_scrubber.set_progress(0.0)

        self.hide_audio_inspector()
        self._refresh_notes_list()

    def _toggle_pin_current(self):
        if self.current_note:
            self.notes_mgr.toggle_pin(self.current_note["id"])
            self._refresh_notes_list()

    def _duplicate_current(self):
        if self.current_note:
            dup = self.notes_mgr.duplicate_note(self.current_note["id"])
            self._refresh_notes_list()
            if dup:
                self.select_note(dup)

    def _delete_current(self):
        if not self.current_note:
            return
        note_id = self.current_note["id"]
        is_in_trash = self.current_note.get("in_trash", False)
        self.notes_mgr.delete_note(note_id, permanent=is_in_trash)
        self._refresh_folders_list()
        self._refresh_notes_list()
        remaining = self.notes_mgr.get_notes(self.current_folder, self.current_query)
        if remaining:
            self.select_note(remaining[0])
        else:
            self._clear_editor_empty()

    def _delete_note_by_id(self, note_id: str):
        note = self.notes_mgr.get_note_by_id(note_id)
        is_in_trash = note.get("in_trash", False) if note else False
        self.notes_mgr.delete_note(note_id, permanent=is_in_trash)
        self._refresh_folders_list()
        self._refresh_notes_list()
        if self.current_note and self.current_note.get("id") == note_id:
            remaining = self.notes_mgr.get_notes(self.current_folder, self.current_query)
            if remaining:
                self.select_note(remaining[0])
            else:
                self._clear_editor_empty()

    def _restore_note_by_id(self, note_id: str):
        self.notes_mgr.restore_note(note_id)
        self._refresh_folders_list()
        self._refresh_notes_list()
        remaining = self.notes_mgr.get_notes(self.current_folder, self.current_query)
        if remaining:
            self.select_note(remaining[0])
        else:
            self._clear_editor_empty()

    def _clear_editor_empty(self):
        self.current_note = None
        self._is_loading_note = True
        try:
            self.lbl_window_title.set_text(t("notes_title", "Ghi chú"))
            self.lbl_window_subtitle.set_text(t("notes_no_notes", "Không có ghi chú nào"))
            self.lbl_note_date.set_text("")
            self.title_entry.set_text("")
            self.title_entry.set_placeholder_text(t("notes_empty_placeholder", "Không có ghi chú"))
            self.text_buffer.set_text("")
            for child in self.audio_card_box.get_children():
                self.audio_card_box.remove(child)
            self.audio_inspector.load_transcript([])
            self.audio_inspector.update_timer(0.0, 0.0)
            self.audio_inspector.lbl_header_subtitle.set_text("")
            self.current_audio_duration = 0.0
            self.current_audio_time = 0.0
            self._update_editor_lock_state(False)
            self.hide_audio_inspector()
        finally:
            self._is_loading_note = False

    def _on_key_press_event(self, widget, event):
        focus = self.get_focus()
        is_typing = (focus == self.title_entry or focus == self.text_view or 
                     (focus and isinstance(focus, (Gtk.Entry, Gtk.TextView))))

        # Ctrl+Delete or Ctrl+Backspace: always delete current note
        if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval in (Gdk.KEY_BackSpace, Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
            self._delete_current()
            return True

        # Plain Delete or BackSpace when not actively typing text in an entry/editor
        if not is_typing and event.keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete, Gdk.KEY_BackSpace):
            self._delete_current()
            return True

        return False

    # -----------------------------------------------------------------
    # Window Chrome & Event Handlers
    # -----------------------------------------------------------------
    def _on_header_button_press(self, widget, event):
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.toggle_maximize()
            return True
        elif event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            if not getattr(self, "_is_maximized", False):
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                return True
        return False

    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("notes_title", "Ghi chú"))
            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("notes_search_placeholder", "Tìm kiếm…"))
            if hasattr(self, "btn_new_note"):
                self.btn_new_note.set_tooltip_text(t("notes_new_note", "Soạn ghi chú mới"))
            if hasattr(self, "btn_sidebar_toggle"):
                self.btn_sidebar_toggle.set_tooltip_text(t("notes_toggle_sidebar", "Ẩn / Hiện thanh bên"))
            if hasattr(self, "btn_format"):
                self.btn_format.set_tooltip_text(t("notes_format_tooltip", "Định dạng chữ (Format)"))
            if hasattr(self, "btn_toolbar_checklist"):
                self.btn_toolbar_checklist.set_tooltip_text(t("notes_checklist_tooltip", "Chèn danh sách việc cần làm"))
            if hasattr(self, "btn_toolbar_table"):
                self.btn_toolbar_table.set_tooltip_text(t("notes_table_tooltip", "Chèn bảng"))
            if hasattr(self, "btn_toolbar_paperclip"):
                self.btn_toolbar_paperclip.set_tooltip_text(t("notes_attach_tooltip", "Đính kèm tệp / hình ảnh"))
            if hasattr(self, "btn_toolbar_markup"):
                self.btn_toolbar_markup.set_tooltip_text(t("notes_markup_tooltip", "Bút vẽ & phác thảo"))
            if hasattr(self, "btn_toolbar_lock"):
                self.btn_toolbar_lock.set_tooltip_text(t("notes_lock_tooltip", "Khóa ghi chú"))
            if hasattr(self, "btn_toolbar_share"):
                self.btn_toolbar_share.set_tooltip_text(t("notes_share_tooltip", "Chia sẻ qua AirDrop / Email"))
            if hasattr(self, "btn_toolbar_mic"):
                self.btn_toolbar_mic.set_tooltip_text(t("notes_audio_tooltip", "Ghi âm & bóc băng thoại"))
            if hasattr(self, "btn_toolbar_trash"):
                self.btn_toolbar_trash.set_tooltip_text(t("notes_delete_tooltip", "Xóa ghi chú này"))
            if hasattr(self, "btn_more_toolbar"):
                self.btn_more_toolbar.set_tooltip_text(t("notes_more_tooltip", "Tùy chọn khác"))

            if hasattr(self, "audio_inspector"):
                self.audio_inspector.btn_done.set_label(t("done", "Xong"))
                self.audio_inspector.btn_skip_back.set_tooltip_text(t("notes_rewind_15", "Tua lùi 15 giây"))
                self.audio_inspector.btn_skip_fwd.set_tooltip_text(t("notes_forward_15", "Tua tới 15 giây"))
                self.audio_inspector.btn_play_pause.set_tooltip_text(t("notes_play_pause", "Phát / Tạm dừng"))
                self.audio_inspector.btn_trans_toggle.set_tooltip_text(t("notes_transcript_toggle", "Bật / Tắt hiển thị bóc băng"))
                self.audio_inspector.btn_record.set_tooltip_text(t("notes_record", "Ghi âm"))
                self.audio_inspector.btn_more.set_tooltip_text(t("notes_more_tooltip", "Tùy chọn khác"))
                if hasattr(self.audio_inspector, "lbl_transcript_sec"):
                    self.audio_inspector.lbl_transcript_sec.set_text(t("notes_transcript", "Bản ghi lời thoại").upper())
                if not self.current_note or not self.current_note.get("audio"):
                    self.audio_inspector.lbl_header_title.set_text(t("notes_audio_message", "Ghi âm thoại"))

            self._refresh_folders_list()
            self._refresh_notes_list()

            if not self.current_note:
                self._clear_editor_empty()
        except Exception as e:
            print(f"[Notes] Error retranslating UI: {e}")

    def _on_window_state_event(self, widget, event):
        is_max = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        is_icon = bool(event.new_window_state & Gdk.WindowState.ICONIFIED)
        was_icon = getattr(self, "_is_iconified", False)
        self._is_iconified = is_icon

        if is_icon:
            return False

        if was_icon and not is_icon:
            self.queue_draw()
        elif self._is_maximized != is_max:
            self._is_maximized = is_max
            self.queue_draw()
        return False

    def toggle_maximize(self):
        if self._is_maximized:
            self.unmaximize()
            self._is_maximized = False
        else:
            self.maximize()
            self._is_maximized = True

    def close_window(self):
        self._pause_audio()
        self._stop_recording()
        self.destroy()

    def _on_delete_event(self, widget, event):
        self._pause_audio()
        self._stop_recording()
        return False

    def _on_window_draw(self, widget, cr: cairo.Context):
        if getattr(self, "_is_iconified", False):
            return False

        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 16.0 if not getattr(self, "_is_maximized", False) else 0.0

        cr.save()
        if r > 0:
            cr.set_operator(cairo.Operator.CLEAR)
            cr.paint()
            cr.set_operator(cairo.Operator.OVER)
            cr.new_sub_path()
            cr.arc(w - r, r, r, -math.pi / 2, 0)
            cr.arc(w - r, h - r, r, 0, math.pi / 2)
            cr.arc(r, h - r, r, math.pi / 2, math.pi)
            cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.clip()

        # Background fill
        is_dark = is_system_dark_mode()
        if is_dark:
            cr.set_source_rgb(0.12, 0.12, 0.14)
        else:
            cr.set_source_rgb(0.98, 0.98, 0.99)
        cr.paint()

        # Subtle glass border
        if r > 0:
            if is_dark:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
            else:
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.1)
            cr.set_line_width(1.0)
            cr.arc(w - r, r, r, -math.pi / 2, 0)
            cr.arc(w - r, h - r, r, 0, math.pi / 2)
            cr.arc(r, h - r, r, math.pi / 2, math.pi)
            cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.stroke()
        cr.restore()
        return False

    def _load_css(self):
        if MacOSNotesWindow._css_loaded:
            return

        is_dark = self.is_dark
        css = f"""
        /* macOS Sequoia Notes CSS Design System */
        .mac-notes-window {{
            background-color: {('#1e1e20' if is_dark else '#fbfbfd')};
            border-radius: 16px;
        }}

        /* Toolbar */
        .mac-notes-toolbar {{
            background: {('rgba(35, 35, 38, 0.85)' if is_dark else 'rgba(246, 246, 248, 0.9)')};
            padding: 8px 12px;
            min-height: 48px;
        }}
        .mac-window-title {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Cantarell, sans-serif;
            font-size: 13px;
            font-weight: 700;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .mac-window-subtitle {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Cantarell, sans-serif;
            font-size: 11px;
            color: #8e8e93;
        }}

        /* Traffic Lights */
        .mac-traffic-light {{
            border-radius: 10px;
            border: none;
            padding: 0;
            margin: 0;
        }}
        .tl-red {{ background-color: #ff5f56; }}
        .tl-yellow {{ background-color: #ffbd2e; }}
        .tl-green {{ background-color: #27c93f; }}
        .tl-symbol {{
            font-size: 9px;
            font-weight: 800;
            color: rgba(0, 0, 0, 0.6);
        }}

        /* Buttons & Tools */
        .mac-tool-btn {{
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 4px;
        }}
        .mac-tool-btn:hover {{
            background-color: {('rgba(255, 255, 255, 0.1)' if is_dark else 'rgba(0, 0, 0, 0.06)')};
        }}
        .mac-tool-btn.mac-trash-btn:hover {{
            background-color: rgba(255, 69, 58, 0.18);
        }}
        .mac-tool-btn.toolbar-btn-active {{
            background-color: {('rgba(227, 156, 18, 0.28)' if is_dark else 'rgba(227, 156, 18, 0.22)')};
        }}
        .mac-circle-btn {{
            background: {('rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.05)')};
            border-radius: 14px;
            border: none;
            padding: 0;
        }}
        .mac-circle-btn:hover {{
            background: {('rgba(255, 255, 255, 0.18)' if is_dark else 'rgba(0, 0, 0, 0.12)')};
        }}

        /* Separator */
        .mac-separator {{
            background-color: {('rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.08)')};
            min-height: 1px;
            min-width: 1px;
        }}

        /* Sidebar & Folders */
        .mac-notes-sidebar {{
            background-color: {('#18181a' if is_dark else '#f2f2f6')};
        }}
        .mac-sidebar-section-header {{
            font-size: 11px;
            font-weight: 700;
            color: #8e8e93;
        }}
        .mac-folder-item {{
            background: transparent;
            border: none;
            border-radius: 8px;
            margin: 1px 8px;
            padding: 0;
        }}
        .mac-folder-item:hover {{
            background-color: {('rgba(255, 255, 255, 0.06)' if is_dark else 'rgba(0, 0, 0, 0.04)')};
        }}
        .mac-folder-item.selected {{
            background-color: {('#2c2c2e' if is_dark else '#e5e5ea')};
        }}
        .folder-name {{
            font-size: 13px;
            font-weight: 500;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .folder-count {{
            font-size: 12px;
            color: #8e8e93;
        }}

        /* Notes List Column */
        .mac-notes-col {{
            background-color: {('#1e1e20' if is_dark else '#f9f9fb')};
        }}
        .mac-notes-search {{
            border-radius: 8px;
            font-size: 12px;
            padding: 4px 8px;
            background-color: {('#2c2c2e' if is_dark else '#e9e9ee')};
            border: none;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .mac-notes-compose-btn {{
            background-color: #e39c12;
            border-radius: 6px;
            border: none;
            padding: 0;
        }}
        .mac-notes-compose-btn:hover {{
            background-color: #f5a623;
        }}

        /* Note Cards */
        .mac-note-card {{
            background: transparent;
            border: none;
            border-radius: 8px;
            padding: 0;
            margin: 1px 4px;
        }}
        .mac-note-card:hover {{
            background-color: {('rgba(255, 255, 255, 0.05)' if is_dark else 'rgba(0, 0, 0, 0.04)')};
        }}
        .mac-note-card.selected {{
            background-color: {('#2c2c2e' if is_dark else '#e5e5ea')};
        }}
        .note-card-title {{
            font-size: 13px;
            font-weight: 700;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .note-card-date {{
            font-size: 11px;
            color: #8e8e93;
        }}
        .note-card-preview {{
            font-size: 11px;
            color: #8e8e93;
        }}
        .note-pin-glyph {{
            font-size: 10px;
        }}
        .note-audio-badge {{
            font-size: 11px;
        }}

        /* Editor Area */
        .editor-date-header {{
            font-size: 11px;
            font-weight: 600;
            color: #8e8e93;
            margin-bottom: 8px;
        }}
        .editor-title-entry {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Cantarell, sans-serif;
            font-size: 26px;
            font-weight: 800;
            background: transparent;
            border: none;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
            padding: 0;
            box-shadow: none;
        }}
        .editor-text-view {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Cantarell, sans-serif;
            font-size: 14px;
            background: transparent;
            color: {('#d1d1d6' if is_dark else '#3a3a3c')};
        }}

        /* Inline Audio Card */
        .mac-inline-audio-card {{
            background-color: {('#2c2c2e' if is_dark else '#f2f2f7')};
            border-radius: 14px;
            border: 1px solid {('rgba(255, 255, 255, 0.10)' if is_dark else 'rgba(0, 0, 0, 0.08)')};
            box-shadow: 0 2px 8px {('rgba(0, 0, 0, 0.25)' if is_dark else 'rgba(0, 0, 0, 0.04)')};
        }}
        .mac-audio-badge {{
            background: linear-gradient(135deg, #ff9500 0%, #e39c12 100%);
            border-radius: 10px;
        }}
        .mac-audio-trans-btn {{
            background-color: {('rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.05)')};
            border-radius: 14px;
            border: 1px solid {('rgba(255, 255, 255, 0.06)' if is_dark else 'rgba(0, 0, 0, 0.06)')};
            padding: 3px 10px;
        }}
        .mac-audio-trans-btn:hover {{
            background-color: {('rgba(255, 255, 255, 0.14)' if is_dark else 'rgba(0, 0, 0, 0.09)')};
        }}
        .audio-trans-btn-text {{
            font-size: 11px;
            font-weight: 600;
            color: #e39c12;
        }}
        .audio-card-title {{
            font-size: 13px;
            font-weight: 700;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .audio-card-date {{
            font-size: 11px;
            color: #8e8e93;
        }}
        .audio-card-time {{
            font-size: 12px;
            font-weight: 600;
            color: #e39c12;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Mono", monospace;
        }}
        .audio-card-transcript-header {{
            font-size: 11px;
            font-weight: 700;
            color: #8e8e93;
            margin-top: 4px;
        }}
        .audio-card-transcript-preview {{
            font-size: 12px;
            color: {('#a1a1a6' if is_dark else '#6e6e73')};
        }}
        .mac-audio-pill-btn {{
            background: transparent;
            border: none;
            border-radius: 14px;
            padding: 0;
        }}
        .mac-audio-pill-btn:hover {{
            background-color: {('rgba(255, 255, 255, 0.1)' if is_dark else 'rgba(0, 0, 0, 0.06)')};
        }}
        .mac-audio-play-btn {{
            background-color: #1d1d1f;
            border-radius: 17px;
            border: none;
            padding: 0;
        }}
        .mac-audio-play-btn:hover {{
            background-color: #3a3a3c;
        }}

        /* Audio Inspector Panel */
        .mac-audio-inspector, .mac-transcript-scroll, .mac-transcript-scroll viewport {{
            background-color: {('#1c1c1e' if is_dark else '#f7f7f9')};
        }}
        .transcript-section-header {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #8e8e93;
        }}
        .transcript-empty-label {{
            font-size: 12px;
            color: #8e8e93;
            font-style: italic;
        }}
        .inspector-title {{
            font-size: 13px;
            font-weight: 700;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .inspector-subtitle {{
            font-size: 11px;
            color: #8e8e93;
        }}
        .inspector-close-symbol {{
            font-size: 12px;
            font-weight: 700;
            color: #8e8e93;
        }}

        /* Transcript lines */
        .transcript-line-box {{
            padding: 6px 8px;
            border-radius: 8px;
        }}
        .transcript-line-box:hover {{
            background-color: {('rgba(255, 255, 255, 0.05)' if is_dark else 'rgba(0, 0, 0, 0.03)')};
        }}
        .transcript-line-active {{
            background-color: {('rgba(227, 156, 18, 0.15)' if is_dark else 'rgba(227, 156, 18, 0.12)')};
        }}
        .transcript-speaker {{
            font-size: 13px;
            font-weight: 700;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .transcript-text {{
            font-size: 13px;
            color: {('#d1d1d6' if is_dark else '#3a3a3c')};
        }}

        /* Digital Timer & Audio Controls */
        .mac-digital-timer {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Mono", monospace, sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .mac-audio-large-play-btn {{
            background-color: #1d1d1f;
            border-radius: 22px;
            border: none;
            padding: 0;
        }}
        .mac-audio-large-play-btn:hover {{
            background-color: #3a3a3c;
        }}
        .mac-audio-record-btn {{
            background-color: #ff3b30;
            border-radius: 18px;
            border: none;
            padding: 0;
        }}
        .mac-audio-record-btn:hover {{
            background-color: #e02d23;
        }}
        .recording-active {{
            background-color: #ff453a;
            box-shadow: 0 0 10px rgba(255, 69, 58, 0.8);
        }}
        .mac-audio-done-btn {{
            background: transparent;
            border: none;
            font-size: 14px;
            font-weight: 700;
            color: #e39c12;
            padding: 6px 12px;
        }}
        .mac-audio-done-btn:hover {{
            color: #f5a623;
        }}

        /* Popover items */
        .mac-popover-item {{
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 4px 6px;
            font-size: 13px;
            color: {('#f5f5f7' if is_dark else '#1d1d1f')};
        }}
        .mac-popover-item:hover {{
            background-color: {('#3a3a3c' if is_dark else '#ebebed')};
            color: {('#ffffff' if is_dark else '#000000')};
        }}
        .mac-popover-item.destructive:hover {{
            background-color: rgba(255, 59, 48, 0.12);
        }}
        .mac-popover-item.destructive .destructive-label,
        .destructive-label {{
            color: {('#ff453a' if is_dark else '#ff3b30')};
        }}
        """

        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(css.encode("utf-8"))
            screen = Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            MacOSNotesWindow._css_loaded = True
        except Exception as e:
            print(f"[Notes] Error loading CSS: {e}")


def launch_notes_app():
    """Launch macOS Notes app standalone."""
    app = MacOSNotesWindow.get_instance()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    launch_notes_app()
