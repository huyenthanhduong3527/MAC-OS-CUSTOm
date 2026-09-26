"""
Virtual Camera Engine for macOS Photo Booth.
Features:
- Seamless PipeWire Video Source registration ("macOS Photo Booth Cam") visible to Chrome, Discord, Zoom, Meet, etc.
- Optional V4L2 loopback output if /dev/video* loopback device exists.
- 3 Broadcast Modes:
  1. MODE_TROLL_IMAGE: Broadcasts any user-selected picture, meme, or avatar at 30 FPS as a live webcam feed.
  2. MODE_FAKE_LAG: Freezes current frame and draws an authentic buffering spinner + "Đang kết nối lại..." to troll friends.
  3. MODE_WEBCAM: Captures from physical webcam (if available) with real-time effect processing.
- Real-time Effects:
  - Normal, Mirror, Comic, Sepia, Black & White, Thermal, Pop Art, Negative, Alien, Fake Lag.
- Thread-safe frame generation and GStreamer pipeline management.
"""

import os
import sys
import time
import math
import glob
from typing import Optional
import threading
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gst
import cairo

# Modes
MODE_WEBCAM = "webcam"
MODE_TROLL_IMAGE = "troll_image"
MODE_FAKE_LAG = "fake_lag"
MODE_PHONE_CAMERA = "phone_camera"

# Filters
FILTER_NORMAL = "normal"
FILTER_MIRROR = "mirror"
FILTER_COMIC = "comic"
FILTER_SEPIA = "sepia"
FILTER_BW = "bw"
FILTER_THERMAL = "thermal"
FILTER_POPART = "popart"
FILTER_NEGATIVE = "negative"
FILTER_ALIEN = "alien"
FILTER_FAKELAG = "fakelag"

AVAILABLE_FILTERS = [
    (FILTER_NORMAL, "Bình thường", "✨"),
    (FILTER_MIRROR, "Gương soi", "🪞"),
    (FILTER_COMIC, "Truyện tranh", "🎨"),
    (FILTER_SEPIA, "Cổ điển", "📜"),
    (FILTER_BW, "Trắng đen", "🎞️"),
    (FILTER_THERMAL, "Tầm nhiệt", "🌡️"),
    (FILTER_POPART, "Pop Art", "🎭"),
    (FILTER_NEGATIVE, "Âm bản", "🔮"),
    (FILTER_ALIEN, "Người ngoài hành tinh", "👽"),
    (FILTER_FAKELAG, "Mạng lag (Troll)", "📶"),
]

class VirtualCameraManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = VirtualCameraManager()
        return cls._instance

    def __init__(self):
        Gst.init(None)
        self.width = 640
        self.height = 480
        self.fps = 60

        self.mode = MODE_TROLL_IMAGE
        self.active_filter = FILTER_NORMAL
        self.troll_image_path = None
        self._troll_pixbuf = None
        self._phone_pixbuf = None
        self._phone_last_frame_time = 0

        # State
        self.is_broadcasting = False
        self._pipeline = None
        self._appsrc = None
        self._running = True
        self._lock = threading.Lock()
        self._frame_callbacks = []

        # Video Recording State
        self.is_recording = False
        self._rec_pipeline = None
        self._rec_appsrc = None
        self._rec_frame_counter = 0
        self._rec_out_path = None

        # Current rendered frame cache (RGB byte buffer and GdkPixbuf)
        self._current_rgb_data = None
        self._current_pixbuf = None
        self._frame_counter = 0

        # Physical webcam device detection
        self.physical_camera_dev = self._find_physical_webcam()
        self._webcam_pipe = None

        # Load default troll image
        self._load_default_troll_image()

        # Start frame generator loop
        self._worker_thread = threading.Thread(target=self._generator_loop, daemon=True)
        self._worker_thread.start()

    def _find_physical_webcam(self):
        """Find first available physical webcam device."""
        video_devs = sorted(glob.glob('/dev/video*'))
        if video_devs:
            return video_devs[0]
        return None

    def _load_default_troll_image(self):
        """No camera connected by default -> pure black."""
        self._troll_pixbuf = None

    def set_troll_image(self, path):
        """Set a user-selected picture file to broadcast."""
        if not path or not os.path.exists(path):
            return False
        try:
            self.troll_image_path = path
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, self.width, self.height, False)
            with self._lock:
                self._troll_pixbuf = pix
            return True
        except Exception as e:
            print(f"[VirtualCamera] Error loading image {path}: {e}")
            return False

    def set_phone_frame_bytes(self, jpeg_bytes: bytes):
        """Update live camera frame received from phone, preserving natural aspect ratio."""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(jpeg_bytes)
            loader.close()
            pix = loader.get_pixbuf()
            if pix:
                with self._lock:
                    self._phone_pixbuf = pix
                    self._phone_last_frame_time = time.time()
                    self.mode = MODE_PHONE_CAMERA
                    if self.active_filter == FILTER_NORMAL:
                        self._current_pixbuf = pix
                return True
        except Exception as e:
            pass
        return False

    def set_phone_pixbuf(self, pixbuf):
        """Update live camera pixbuf directly."""
        with self._lock:
            self._phone_pixbuf = pixbuf
            self._phone_last_frame_time = time.time()
            self.mode = MODE_PHONE_CAMERA

    def set_mode(self, mode):
        with self._lock:
            self.mode = mode

    def set_filter(self, filter_name):
        with self._lock:
            self.active_filter = filter_name

    def register_frame_callback(self, callback):
        if callback not in self._frame_callbacks:
            self._frame_callbacks.append(callback)

    def unregister_frame_callback(self, callback):
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)

    def _find_v4l2_loopback_dev(self):
        """Find v4l2loopback device if present (/dev/video10 or virtual video device)."""
        if os.path.exists("/dev/video10"):
            return "/dev/video10"
        for vpath in glob.glob("/sys/devices/virtual/video4linux/video*"):
            dev_name = os.path.basename(vpath)
            cand = f"/dev/{dev_name}"
            if os.path.exists(cand):
                return cand
        return None

    def start_virtual_cam(self):
        """Starts GStreamer pipeline broadcasting to PipeWire & V4L2."""
        with self._lock:
            if self.is_broadcasting:
                return True
            try:
                loopback_dev = self._find_v4l2_loopback_dev()
                if loopback_dev:
                    pipe_str = (
                        f"appsrc name=vsrc is-live=true block=false format=time "
                        f"caps=video/x-raw,format=BGRx,width={self.width},height={self.height},framerate={self.fps}/1 ! "
                        f"videoconvert ! tee name=t "
                        f"t. ! queue ! pipewiresink name=psink "
                        f"t. ! queue ! videoconvert ! video/x-raw,format=YUY2 ! v4l2sink device={loopback_dev} sync=false"
                    )
                else:
                    pipe_str = (
                        f"appsrc name=vsrc is-live=true block=false format=time "
                        f"caps=video/x-raw,format=BGRx,width={self.width},height={self.height},framerate={self.fps}/1 ! "
                        f"videoconvert ! pipewiresink name=psink"
                    )
                self._pipeline = Gst.parse_launch(pipe_str)
                sink = self._pipeline.get_by_name("psink")
                if sink:
                    props = Gst.Structure.new_empty("props")
                    props.set_value("media.class", "Video/Source")
                    props.set_value("node.name", "macOS_Photo_Booth_Cam")
                    props.set_value("node.description", "macOS Photo Booth Cam (Default)")
                    props.set_value("priority.session", 1500)
                    props.set_value("priority.driver", 1500)
                    sink.set_property("stream-properties", props)

                self._appsrc = self._pipeline.get_by_name("vsrc")
                self._pipeline.set_state(Gst.State.PLAYING)
                self.is_broadcasting = True

                # Also automatically set as default video source in WirePlumber
                GLib.timeout_add(800, self._set_wireplumber_default)
                print(f"[VirtualCamera] Virtual camera started successfully! (V4L2: {loopback_dev}, PipeWire: Active)")
                return True
            except Exception as e:
                print(f"[VirtualCamera] Failed to start virtual cam: {e}")
                self.is_broadcasting = False
                return False

    def stop_virtual_cam(self):
        """Stops GStreamer broadcasting."""
        with self._lock:
            if not self.is_broadcasting:
                return
            try:
                if self._pipeline:
                    self._pipeline.set_state(Gst.State.NULL)
                    self._pipeline = None
                    self._appsrc = None
                self.is_broadcasting = False
                print("[VirtualCamera] Virtual camera stopped.")
            except Exception as e:
                print(f"[VirtualCamera] Error stopping virtual cam: {e}")

    def start_recording(self, out_path: str) -> bool:
        """Starts encoding live camera frames into an MP4 video file."""
        with self._lock:
            if self.is_recording:
                return False
            try:
                self._rec_out_path = out_path
                self._rec_frame_counter = 0
                pipe_str = (
                    f"appsrc name=recsrc is-live=true block=false format=time "
                    f"caps=video/x-raw,format=BGRx,width={self.width},height={self.height},framerate={self.fps}/1 ! "
                    f"videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast ! mp4mux ! filesink location=\"{out_path}\""
                )
                self._rec_pipeline = Gst.parse_launch(pipe_str)
                self._rec_appsrc = self._rec_pipeline.get_by_name("recsrc")
                self._rec_pipeline.set_state(Gst.State.PLAYING)
                self.is_recording = True
                print(f"[VirtualCamera] Started recording video to {out_path}")
                return True
            except Exception as e:
                print(f"[VirtualCamera] Failed to start video recording: {e}")
                self.is_recording = False
                self._rec_pipeline = None
                self._rec_appsrc = None
                return False

    def stop_recording(self) -> Optional[str]:
        """Stops video recording and finalizes MP4 file."""
        with self._lock:
            if not self.is_recording or not self._rec_pipeline:
                return None
            try:
                out_path = self._rec_out_path
                if self._rec_appsrc:
                    self._rec_appsrc.emit("end-of-stream")
                bus = self._rec_pipeline.get_bus()
                if bus:
                    bus.timed_pop_filtered(Gst.SECOND * 2, Gst.MessageType.EOS | Gst.MessageType.ERROR)
                self._rec_pipeline.set_state(Gst.State.NULL)
                self._rec_pipeline = None
                self._rec_appsrc = None
                self.is_recording = False
                print(f"[VirtualCamera] Video recording saved to {out_path}")
                return out_path
            except Exception as e:
                print(f"[VirtualCamera] Error stopping video recording: {e}")
                self.is_recording = False
                self._rec_pipeline = None
                self._rec_appsrc = None
                return None

    def _set_wireplumber_default(self):
        """Sets macOS Photo Booth Cam as default video source via wpctl."""
        try:
            res = subprocess.run(["wpctl", "status"], capture_output=True, text=True, timeout=1.0)
            lines = res.stdout.splitlines()
            in_video = False
            for line in lines:
                if "Video" in line:
                    in_video = True
                elif in_video and "Settings" in line:
                    break
                elif in_video and "macOS Photo Booth Cam" in line:
                    parts = line.strip().split(".")
                    if len(parts) >= 2:
                        node_id = parts[0].replace("│", "").replace("*", "").strip()
                        if node_id.isdigit():
                            subprocess.run(["wpctl", "set-default", node_id], capture_output=True, timeout=1.0)
                            print(f"[VirtualCamera] Set node {node_id} (macOS Photo Booth Cam) as default camera!")
                            break
        except Exception as e:
            print(f"[VirtualCamera] Could not set WirePlumber default: {e}")
        return False

    def _generator_loop(self):
        """Worker generating 30 FPS frames with selected filters/mode."""
        interval = 1.0 / self.fps
        while self._running:
            start_t = time.time()
            try:
                self._generate_next_frame()
            except Exception as e:
                pass

            elapsed = time.time() - start_t
            sleep_t = max(0.005, interval - elapsed)
            time.sleep(sleep_t)

    def _generate_next_frame(self):
        self._frame_counter += 1

        with self._lock:
            mode = self.mode
            filt = self.active_filter
            troll_pix = self._troll_pixbuf
            phone_pix = self._phone_pixbuf
            last_phone_time = self._phone_last_frame_time

        # Determine frame dimensions dynamically
        frame_w = self.width
        frame_h = self.height

        now = time.time()
        has_phone_feed = (mode == MODE_PHONE_CAMERA and phone_pix and (now - last_phone_time < 4.0))

        if has_phone_feed:
            frame_w = phone_pix.get_width()
            frame_h = phone_pix.get_height()

        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, frame_w, frame_h)
        cr = cairo.Context(surface)

        # 1. Base rendering according to Mode
        if has_phone_feed:
            if filt == FILTER_MIRROR:
                cr.save()
                cr.translate(frame_w, 0)
                cr.scale(-1, 1)
                Gdk.cairo_set_source_pixbuf(cr, phone_pix, 0, 0)
                cr.paint()
                cr.restore()
            else:
                Gdk.cairo_set_source_pixbuf(cr, phone_pix, 0, 0)
                cr.paint()
        elif mode == MODE_TROLL_IMAGE and troll_pix:
            if filt == FILTER_MIRROR:
                cr.save()
                cr.translate(frame_w, 0)
                cr.scale(-1, 1)
                Gdk.cairo_set_source_pixbuf(cr, troll_pix, 0, 0)
                cr.paint()
                cr.restore()
            else:
                Gdk.cairo_set_source_pixbuf(cr, troll_pix, 0, 0)
                cr.paint()
        else:
            # NO CAMERA CONNECTED: Completely pure black screen matching real Photo Booth!
            cr.set_source_rgb(0.0, 0.0, 0.0)
            cr.paint()

        # 2. Apply Filters (using Cairo operations at natural resolution)
        self._apply_cairo_filter(cr, filt, frame_w, frame_h)

        # 3. Convert surface to GdkPixbuf for UI with natural aspect ratio
        pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, frame_w, frame_h)

        with self._lock:
            self._current_pixbuf = pixbuf

        # 4. For V4L2 virtual camera / MP4 recording: scale with aspect-fit into fixed (self.width, self.height)
        if (self.is_broadcasting and self._appsrc) or (self.is_recording and self._rec_appsrc):
            v4l_surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.width, self.height)
            vcr = cairo.Context(v4l_surface)
            vcr.set_source_rgb(0.0, 0.0, 0.0)
            vcr.paint()

            # Aspect fit into V4L2 surface (never stretch or distort)
            scale = min(self.width / frame_w, self.height / frame_h)
            dw = max(1, int(frame_w * scale))
            dh = max(1, int(frame_h * scale))
            dx = (self.width - dw) // 2
            dy = (self.height - dh) // 2

            if pixbuf:
                scaled_v4l = pixbuf.scale_simple(dw, dh, GdkPixbuf.InterpType.BILINEAR)
                if scaled_v4l:
                    Gdk.cairo_set_source_pixbuf(vcr, scaled_v4l, dx, dy)
                    vcr.paint()

            try:
                rgb_bytes = bytes(v4l_surface.get_data())
            except Exception:
                rgb_bytes = b'\x00' * (self.width * self.height * 4)

            with self._lock:
                self._current_rgb_data = rgb_bytes

            if self.is_broadcasting and self._appsrc:
                try:
                    buf = Gst.Buffer.new_allocate(None, len(rgb_bytes), None)
                    buf.fill(0, rgb_bytes)
                    buf.pts = self._frame_counter * Gst.util_uint64_scale_int(1, Gst.SECOND, self.fps)
                    buf.duration = Gst.util_uint64_scale_int(1, Gst.SECOND, self.fps)
                    self._appsrc.emit("push-buffer", buf)
                except Exception:
                    pass

            if self.is_recording and self._rec_appsrc:
                try:
                    self._rec_frame_counter += 1
                    rbuf = Gst.Buffer.new_allocate(None, len(rgb_bytes), None)
                    rbuf.fill(0, rgb_bytes)
                    rbuf.pts = self._rec_frame_counter * Gst.util_uint64_scale_int(1, Gst.SECOND, self.fps)
                    rbuf.duration = Gst.util_uint64_scale_int(1, Gst.SECOND, self.fps)
                    self._rec_appsrc.emit("push-buffer", rbuf)
                except Exception:
                    pass

        # 5. Notify UI callbacks on main GLib loop
        for cb in self._frame_callbacks:
            try:
                GLib.idle_add(cb, pixbuf)
            except Exception:
                pass

    def _apply_cairo_filter(self, cr, filt, w=None, h=None):
        """Applies real-time visual filter on top of Cairo context."""
        if w is None:
            w = self.width
        if h is None:
            h = self.height

        if filt == FILTER_NORMAL:
            return

        elif filt == FILTER_MIRROR:
            pass

        elif filt == FILTER_SEPIA:
            cr.set_source_rgba(0.70, 0.45, 0.20, 0.40)
            cr.set_operator(cairo.OPERATOR_OVERLAY)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

        elif filt == FILTER_BW:
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.65)
            cr.set_operator(cairo.OPERATOR_HSL_COLOR)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

        elif filt == FILTER_THERMAL:
            pat = cairo.LinearGradient(0, 0, w, h)
            pat.add_color_stop_rgba(0.0, 0.1, 0.1, 0.9, 0.6)
            pat.add_color_stop_rgba(0.5, 0.2, 0.9, 0.2, 0.5)
            pat.add_color_stop_rgba(1.0, 1.0, 0.1, 0.1, 0.7)
            cr.set_source(pat)
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

        elif filt == FILTER_NEGATIVE:
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

        elif filt == FILTER_POPART:
            pat = cairo.RadialGradient(w / 2, h / 2, 50, w / 2, h / 2, max(w, h) / 2)
            pat.add_color_stop_rgba(0.0, 1.0, 0.2, 0.6, 0.55)
            pat.add_color_stop_rgba(1.0, 0.1, 0.8, 1.0, 0.55)
            cr.set_source(pat)
            cr.set_operator(cairo.OPERATOR_COLOR_DODGE)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

        elif filt == FILTER_COMIC:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.18)
            step = 8
            for y in range(0, h, step):
                for x in range(0, w, step):
                    cr.arc(x, y, 1.8, 0, 2 * math.pi)
            cr.fill()

        elif filt == FILTER_ALIEN:
            cr.set_source_rgba(0.1, 0.9, 0.3, 0.45)
            cr.set_operator(cairo.OPERATOR_COLOR_BURN)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

    def _surface_to_pixbuf(self, surface):
        """Converts Cairo surface to GdkPixbuf."""
        try:
            return Gdk.pixbuf_get_from_surface(surface, 0, 0, self.width, self.height)
        except Exception as e:
            print(f"[VirtualCamera] Error converting surface to pixbuf: {e}")
            return None

    def _surface_to_rgb_bytes(self, surface, pixbuf=None):
        """Converts Cairo surface to packed 24-bit RGB byte buffer for GStreamer."""
        if not pixbuf:
            pixbuf = self._surface_to_pixbuf(surface)
        if pixbuf:
            return pixbuf.get_pixels()
        return b'\x00' * (self.width * self.height * 3)

    def get_current_pixbuf(self):
        with self._lock:
            if self.mode == MODE_PHONE_CAMERA:
                now = time.time()
                if self._phone_pixbuf and (now - self._phone_last_frame_time < 4.0):
                    if self.active_filter == FILTER_NORMAL:
                        return self._phone_pixbuf
            return self._current_pixbuf

    def get_raw_pixbuf(self):
        with self._lock:
            if self.mode == MODE_PHONE_CAMERA:
                now = time.time()
                if self._phone_pixbuf and (now - self._phone_last_frame_time < 4.0):
                    return self._phone_pixbuf
            elif self.mode == MODE_TROLL_IMAGE:
                return self._troll_pixbuf
            return self._current_pixbuf

    def stop(self):
        self._running = False
        self.stop_virtual_cam()
