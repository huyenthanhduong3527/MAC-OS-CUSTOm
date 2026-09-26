#!/usr/bin/env python3
import os
import sys
import time

os.environ["GDK_BACKEND"] = "x11"

import cv2
import cairo
cv2.setNumThreads(1)
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

VIDEO_PATH = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/wallpapers/sakura_torii_1080p_live.mp4"

class TestWallpaper(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        
        self.cap = cv2.VideoCapture(VIDEO_PATH)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 60.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.interval_ms = int(1000.0 / self.fps)
        print(f"[TestWallpaper] Loaded video: {self.total_frames} frames @ {self.fps} FPS ({self.interval_ms}ms/frame)")

        # Screen size
        display = Gdk.Display.get_default()
        screen = display.get_default_screen()
        self.screen_w = screen.get_width()
        self.screen_h = screen.get_height()
        print(f"[TestWallpaper] Screen geometry: {self.screen_w}x{self.screen_h}")

        self.set_title("Live Wallpaper Engine")
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.stick()
        self.set_default_size(self.screen_w, self.screen_h)
        self.move(0, 0)

        # Drawing Area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect("draw", self._on_draw)
        self.add(self.drawing_area)

        self.current_surface = None
        self.current_buf = None
        self.frame_count = 0
        self.start_time = time.time()

        self.connect("realize", self._on_realize)
        self.connect("destroy", self._on_destroy)

        # Read first frame
        self._read_next_frame()

        # Frame timer
        GLib.timeout_add(self.interval_ms, self._on_tick)

    def _on_realize(self, widget):
        gdk_win = widget.get_window()
        if gdk_win:
            try:
                gdk_win.set_pass_through(True)
            except Exception as e:
                print(f"[TestWallpaper] pass_through notice: {e}")
            widget.set_keep_below(True)

    def _read_next_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            # Seamless loop: rewind
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                return False

        h, w = frame.shape[:2]
        # If dimensions don't match screen, resize
        if (w, h) != (self.screen_w, self.screen_h):
            frame = cv2.resize(frame, (self.screen_w, self.screen_h), interpolation=cv2.INTER_LINEAR)
            h, w = self.screen_h, self.screen_w

        # OpenCV BGR -> BGRA for Cairo FORMAT_ARGB32
        bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        self.current_buf = bgra
        self.current_surface = cairo.ImageSurface.create_for_data(
            self.current_buf,
            cairo.FORMAT_ARGB32,
            w,
            h,
            w * 4
        )
        self.frame_count += 1
        return True

    def _on_tick(self):
        if self._read_next_frame():
            self.drawing_area.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        if self.current_surface:
            cr.set_source_surface(self.current_surface, 0, 0)
            cr.paint()
        return False

    def _on_destroy(self, *args):
        if self.cap:
            self.cap.release()
            self.cap = None

if __name__ == "__main__":
    win = TestWallpaper()
    win.show_all()
    # Auto stop after 5 seconds to test
    GLib.timeout_add_seconds(5, Gtk.main_quit)
    Gtk.main()
    elapsed = time.time() - win.start_time
    fps = win.frame_count / elapsed if elapsed > 0 else 0
    print(f"[TestWallpaper] Rendered {win.frame_count} frames in {elapsed:.2f}s ({fps:.1f} FPS)")
