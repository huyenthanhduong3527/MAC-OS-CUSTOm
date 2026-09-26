"""
Media Player Tab for Expanded Dynamic Island.
Includes album art, title/artist, play/pause/prev/next controls, seekbar, and live audio visualizer.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_image, get_pixbuf
from src.utils.artwork import load_artwork_pixbuf

class LargeVisualizerArea(Gtk.DrawingArea):
    """Smooth multi-bar frequency visualizer."""
    def __init__(self, visualizer):
        super().__init__()
        self.visualizer = visualizer
        self.set_size_request(80, 24)
        self.connect("draw", self.on_draw)

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        bars = self.visualizer.bars
        n = len(bars)
        bar_w = 3.5
        spacing = 3.0
        total_w = n * bar_w + (n - 1) * spacing
        start_x = (width - total_w) / 2

        cr.set_source_rgba(0.06, 0.65, 0.95, 0.9)

        for i, val in enumerate(bars):
            h = max(3.0, val * height)
            y = (height - h) / 2 # Centered wave bounce
            x = start_x + i * (bar_w + spacing)
            cr.rectangle(x, y, bar_w, h)
            cr.fill()
        return False


class MediaTab(Gtk.Box):
    def __init__(self, media_mgr, visualizer):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.get_style_context().add_class("tab-content")

        self.media_mgr = media_mgr
        self.visualizer = visualizer

        # Top row: Album art + Info + Visualizer
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Album art container
        self.art_box = Gtk.Box()
        self.art_box.set_size_request(48, 48)
        self.art_box.get_style_context().add_class("media-album-art")
        self.art_icon = Gtk.Image.new_from_pixbuf(get_pixbuf("music", 22, "#38bdf8"))
        self.art_box.set_center_widget(self.art_icon)
        top_row.pack_start(self.art_box, False, False, 0)

        # Title & Artist
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_valign(Gtk.Align.CENTER)

        self.title_lbl = Gtk.Label(label="Title")
        self.title_lbl.get_style_context().add_class("media-title")
        self.title_lbl.set_xalign(0.0)
        self.title_lbl.set_ellipsize(3) # End ellipsize
        self.title_lbl.set_max_width_chars(22)

        self.artist_lbl = Gtk.Label(label="Artist")
        self.artist_lbl.get_style_context().add_class("media-artist")
        self.artist_lbl.set_xalign(0.0)
        self.artist_lbl.set_ellipsize(3)
        self.artist_lbl.set_max_width_chars(26)

        info_box.pack_start(self.title_lbl, False, False, 0)
        info_box.pack_start(self.artist_lbl, False, False, 0)
        top_row.pack_start(info_box, True, True, 0)

        # Visualizer waves
        self.vis_area = LargeVisualizerArea(visualizer)
        self.vis_area.set_valign(Gtk.Align.CENTER)
        top_row.pack_end(self.vis_area, False, False, 0)

        self.pack_start(top_row, False, False, 0)

        # Progress slider & Time labels
        progress_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        progress_row.pack_start(self.scale, False, False, 0)

        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.pos_lbl = Gtk.Label(label="0:00")
        self.pos_lbl.get_style_context().add_class("media-time")
        self.dur_lbl = Gtk.Label(label="0:00")
        self.dur_lbl.get_style_context().add_class("media-time")
        time_row.pack_start(self.pos_lbl, False, False, 0)
        time_row.pack_end(self.dur_lbl, False, False, 0)
        progress_row.pack_start(time_row, False, False, 0)

        self.pack_start(progress_row, False, False, 0)

        # Playback Controls
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        ctrl_row.set_halign(Gtk.Align.CENTER)

        self.prev_btn = Gtk.Button()
        self.prev_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("prev", 16, "#f8fafc")))
        self.prev_btn.get_style_context().add_class("ctrl-btn")
        self.prev_btn.connect("clicked", self._on_prev)

        self.play_btn = Gtk.Button()
        self.play_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("play", 18, "#000000")))
        self.play_btn.get_style_context().add_class("ctrl-btn")
        self.play_btn.get_style_context().add_class("primary")
        self.play_btn.connect("clicked", self._on_play)

        self.next_btn = Gtk.Button()
        self.next_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("next", 16, "#f8fafc")))
        self.next_btn.get_style_context().add_class("ctrl-btn")
        self.next_btn.connect("clicked", self._on_next)

        ctrl_row.pack_start(self.prev_btn, False, False, 0)
        ctrl_row.pack_start(self.play_btn, False, False, 0)
        ctrl_row.pack_start(self.next_btn, False, False, 0)

        self.pack_start(ctrl_row, False, False, 0)

        self.update()

    def update(self):
        self.title_lbl.set_text(self.media_mgr.title)
        self.artist_lbl.set_text(self.media_mgr.artist)

        # Update album artwork
        art_pix = load_artwork_pixbuf(self.media_mgr.art_url, size=48, radius=10, on_ready_callback=self.update)
        if art_pix:
            self.art_icon.set_from_pixbuf(art_pix)
        else:
            app_ico = self.media_mgr.get_app_icon(32)
            if app_ico:
                self.art_icon.set_from_pixbuf(app_ico)
            else:
                self.art_icon.set_from_pixbuf(get_pixbuf("music", 22, "#38bdf8"))

        # Update play icon & visualizer visibility
        if self.media_mgr.is_playing():
            self.play_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("pause", 18, "#000000")))
            if not self.vis_area.get_visible():
                self.vis_area.show()
            self.vis_area.queue_draw()
        else:
            self.play_btn.set_image(Gtk.Image.new_from_pixbuf(get_pixbuf("play", 18, "#000000")))
            if self.vis_area.get_visible():
                self.vis_area.hide()

        # Update progress
        dur = self.media_mgr.duration
        pos = self.media_mgr.position
        if dur > 0:
            self.scale.show()
            self.scale.set_range(0, dur)
            self.scale.set_value(min(dur, pos))
            self.pos_lbl.set_text(self._format_time(pos))
            self.dur_lbl.set_text(self._format_time(dur))
        else:
            self.scale.hide()
            self.pos_lbl.set_text("LIVE AUDIO" if self.media_mgr.is_playing() else "PAUSED")
            self.dur_lbl.set_text(self._format_time(pos) if pos > 0 else "")

    def _format_time(self, seconds):
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins}:{secs:02d}"

    def _on_play(self, btn):
        self.media_mgr.play_pause()
        self.update()

    def _on_next(self, btn):
        self.media_mgr.next_track()
        self.update()

    def _on_prev(self, btn):
        self.media_mgr.prev_track()
        self.update()
