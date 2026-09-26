"""
Apple Music Synchronized Lyrics Viewer Window for Linux Desktop.
Features real-time karaoke active line highlighting, auto-scroll,
draggable header, sleek dark glassmorphism, and interactive timeline seeking.
"""

import math
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from src.modules.lyrics import lyrics_manager
from src.utils.artwork import load_artwork_pixbuf


class MacOSLyricsWindow(Gtk.Window):
    def __init__(self, media_mgr):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.media_mgr = media_mgr

        self.set_title("Apple Music Lyrics")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(False)
        self.set_app_paintable(True)
        self.set_wmclass("macos-lyrics", "MacOSLyrics")
        self.set_role("lyrics-window")
        self.set_default_size(360, 520)
        self.set_keep_above(True)

        # Enable alpha channel
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self._current_track_key = None
        self._lyrics_data = None
        self._active_index = -1
        self._line_widgets = []
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_ui()
        self.connect("draw", self._on_draw)

        # Periodic timer for real-time karaoke sync
        self._sync_timer_id = GLib.timeout_add(150, self._on_sync_tick)

        # Initial load
        self.update_track()

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root_box.set_margin_top(12)
        root_box.set_margin_bottom(14)
        root_box.set_margin_start(16)
        root_box.set_margin_end(16)
        self.add(root_box)

        # 1. Header Bar (Draggable)
        header = Gtk.EventBox()
        header.connect("button-press-event", self._on_header_press)
        header.connect("button-release-event", self._on_header_release)
        header.connect("motion-notify-event", self._on_header_motion)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_bottom(12)

        # Mini artwork
        self.art_image = Gtk.Image()
        self.art_image.set_size_request(38, 38)
        header_box.pack_start(self.art_image, False, False, 0)

        # Title & Artist
        meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.title_label = Gtk.Label()
        self.title_label.set_alignment(0.0, 0.5)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_markup("<span font_weight='bold' font_size='11pt' color='#ffffff'>Đang tải...</span>")

        self.artist_label = Gtk.Label()
        self.artist_label.set_alignment(0.0, 0.5)
        self.artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.artist_label.set_markup("<span font_size='9pt' color='#94a3b8'>Apple Music</span>")

        meta_box.pack_start(self.title_label, False, False, 0)
        meta_box.pack_start(self.artist_label, False, False, 0)
        header_box.pack_start(meta_box, True, True, 0)

        # Close button (Apple style circle)
        close_btn = Gtk.Button()
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda _: self.hide())
        close_lbl = Gtk.Label()
        close_lbl.set_markup("<span font_size='11pt' font_weight='bold' color='#64748b'>✕</span>")
        close_btn.add(close_lbl)
        header_box.pack_end(close_btn, False, False, 0)

        header.add(header_box)
        root_box.pack_start(header, False, False, 0)

        # Separator line
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(10)
        root_box.pack_start(sep, False, False, 0)

        # 2. Scrolled Area for Lyrics
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_overlay_scrolling(True)
        root_box.pack_start(self.scroll, True, True, 0)

        self.lyrics_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.lyrics_box.set_margin_top(8)
        self.lyrics_box.set_margin_bottom(40)
        self.lyrics_box.set_margin_start(6)
        self.lyrics_box.set_margin_end(6)
        self.scroll.add(self.lyrics_box)

        # Placeholder loading status
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<span color='#94a3b8' font_size='12pt'>⏳ Đang tải lời bài hát...</span>")
        self.status_label.set_margin_top(60)
        self.lyrics_box.pack_start(self.status_label, True, True, 0)

    def _on_draw(self, widget, cr):
        """Draw sleek Apple dark glassmorphism card."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 22.0

        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Rounded card path
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        # Dark OLED glass material
        pat = cairo.LinearGradient(0, 0, 0, h)
        pat.add_color_stop_rgba(0.0, 0.08, 0.09, 0.12, 0.96)
        pat.add_color_stop_rgba(1.0, 0.05, 0.06, 0.08, 0.98)
        cr.set_source(pat)
        cr.fill_preserve()

        # Subtle crisp specular rim
        rim = cairo.LinearGradient(0, 0, 0, h)
        rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.15)
        rim.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.05)
        rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.08)
        cr.set_source(rim)
        cr.set_line_width(0.8)
        cr.stroke()

        return False

    def update_track(self):
        """Update header metadata and fetch lyrics if track changed."""
        title = self.media_mgr.title or "No Media Playing"
        artist = self.media_mgr.artist or ""
        key = f"{title}___{artist}"

        if key == self._current_track_key and self._lyrics_data is not None:
            return

        self._current_track_key = key
        clean_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        clean_artist = artist.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        self.title_label.set_markup(f"<span font_weight='bold' font_size='11pt' color='#ffffff'>{clean_title}</span>")
        self.artist_label.set_markup(f"<span font_size='9pt' color='#94a3b8'>{clean_artist or 'Apple Music'}</span>")

        # Load mini artwork
        art_pb = load_artwork_pixbuf(self.media_mgr.art_url, size=38, radius=8, on_ready_callback=self._refresh_art)
        if art_pb:
            self.art_image.set_from_pixbuf(art_pb)

        # Clear existing lines & show loading
        for child in self.lyrics_box.get_children():
            self.lyrics_box.remove(child)
        self._line_widgets = []
        self._active_index = -1

        self.status_label = Gtk.Label()
        self.status_label.set_markup("<span color='#94a3b8' font_size='12pt'>⏳ Đang tải lời bài hát...</span>")
        self.status_label.set_margin_top(60)
        self.lyrics_box.pack_start(self.status_label, True, True, 0)
        self.lyrics_box.show_all()

        lyrics_manager.get_lyrics_async(title, artist, self.media_mgr.duration, self._on_lyrics_loaded)

    def _refresh_art(self):
        art_pb = load_artwork_pixbuf(self.media_mgr.art_url, size=38, radius=8)
        if art_pb:
            self.art_image.set_from_pixbuf(art_pb)

    def _on_lyrics_loaded(self, lyrics_data):
        self._lyrics_data = lyrics_data

        for child in self.lyrics_box.get_children():
            self.lyrics_box.remove(child)
        self._line_widgets = []
        self._active_index = -1

        if not lyrics_data or not lyrics_data.get("lines"):
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            empty_box.set_margin_top(60)
            lbl = Gtk.Label()
            lbl.set_markup("<span color='#64748b' font_size='13pt' font_weight='bold'>🎵 Không tìm thấy lời bài hát</span>\n<span color='#475569' font_size='10pt'>Bản nhạc này chưa có dữ liệu lời trực tuyến.</span>")
            lbl.set_justify(Gtk.Justification.CENTER)
            empty_box.pack_start(lbl, False, False, 0)
            self.lyrics_box.pack_start(empty_box, True, True, 0)
            self.lyrics_box.show_all()
            return

        is_synced = lyrics_data.get("is_synced", False)

        for i, (ts, text) in enumerate(lyrics_data["lines"]):
            clean_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            ebox = Gtk.EventBox()
            ebox.set_visible_window(False)

            lbl = Gtk.Label()
            lbl.set_alignment(0.0, 0.5)
            lbl.set_line_wrap(True)
            lbl.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

            # Apple Music typography: inactive lines are muted gray
            lbl.set_markup(f"<span font_size='13pt' font_weight='bold' foreground='#94a3b8' alpha='50%'>{clean_text}</span>")

            # Click on line to jump / seek in track
            if is_synced:
                ebox.connect("button-press-event", lambda _, seek_time=ts: self._seek_to(seek_time))

            ebox.add(lbl)
            self.lyrics_box.pack_start(ebox, False, False, 3)
            self._line_widgets.append((lbl, text, ts))

        self.lyrics_box.show_all()
        self._on_sync_tick()

    def _seek_to(self, seconds):
        if hasattr(self.media_mgr, 'seek'):
            self.media_mgr.seek(seconds)

    def _on_sync_tick(self):
        """Highlight active lyric line and smooth auto-scroll."""
        if not self.get_visible():
            return True

        # Check if song changed
        title = self.media_mgr.title or ""
        artist = self.media_mgr.artist or ""
        if f"{title}___{artist}" != self._current_track_key:
            self.update_track()
            return True

        if not self._lyrics_data or not self._lyrics_data.get("is_synced") or not self._line_widgets:
            return True

        current_time = getattr(self.media_mgr, 'position', 0.0)

        # Find current active index
        new_active = -1
        lines = self._lyrics_data["lines"]
        for i in range(len(lines)):
            ts = lines[i][0]
            if current_time >= ts:
                new_active = i
            else:
                break

        if new_active != self._active_index:
            old_idx = self._active_index
            self._active_index = new_active

            # Deactivate previous
            if 0 <= old_idx < len(self._line_widgets):
                lbl, text, _ = self._line_widgets[old_idx]
                clean = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lbl.set_markup(f"<span font_size='13pt' font_weight='bold' foreground='#94a3b8' alpha='50%'>{clean}</span>")

            # Activate current: crisp white, larger, bold
            if 0 <= new_active < len(self._line_widgets):
                lbl, text, _ = self._line_widgets[new_active]
                clean = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lbl.set_markup(f"<span font_size='15pt' font_weight='heavy' foreground='#ffffff'>{clean}</span>")

                # Auto-scroll active line to comfortable reading area (about 35% from top)
                alloc = lbl.get_allocation()
                adj = self.scroll.get_vadjustment()
                if adj:
                    target_val = max(0, alloc.y - 120)
                    adj.set_value(target_val)

        return True

    # Draggable Window Methods
    def _on_header_press(self, widget, event):
        if event.button == 1:
            self._dragging = True
            self._drag_start_x = event.x
            self._drag_start_y = event.y
        return True

    def _on_header_release(self, widget, event):
        self._dragging = False
        return True

    def _on_header_motion(self, widget, event):
        if self._dragging:
            win_x, win_y = self.get_position()
            new_x = int(win_x + event.x - self._drag_start_x)
            new_y = int(win_y + event.y - self._drag_start_y)
            self.move(new_x, new_y)
        return True

    def toggle(self, parent_window=None):
        if self.get_visible():
            self.hide()
        else:
            if parent_window:
                px, py = parent_window.get_position()
                pw, ph = parent_window.get_size()
                # Place nicely next to music widget
                target_x = px + pw + 16
                target_y = py
                screen_w = self.get_screen().get_width()
                if target_x + 360 > screen_w:
                    target_x = max(10, px - 360 - 16)
                self.move(target_x, target_y)
            self.update_track()
            self.show_all()
            self.present()
