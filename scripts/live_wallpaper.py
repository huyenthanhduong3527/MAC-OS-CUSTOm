#!/usr/bin/env python3
"""
macOS-Style High-Performance Live Video Wallpaper Engine for Ubuntu / GNOME.
Seamlessly plays looping 4K/1080p videos behind desktop widgets with zero click obstruction.
Glitch-free, low-CPU Cairo + OpenCV rendering engine.
"""

import os
import sys
import signal
import time
import json
import subprocess
import numpy as np

# Force X11 backend for proper desktop layer integration and widget compatibility
os.environ["GDK_BACKEND"] = "x11"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
WALLPAPERS_DIR = os.path.join(PROJECT_DIR, "assets", "wallpapers")
DEFAULT_VIDEO = os.path.join(WALLPAPERS_DIR, "sakura_torii_1080p_30fps.mp4")
FALLBACK_1080P = os.path.join(WALLPAPERS_DIR, "sakura_torii_1080p_live.mp4")
FALLBACK_4K = os.path.join(WALLPAPERS_DIR, "sakura_torii_4k_live.mp4")
PID_FILE = "/tmp/live_wallpaper.pid"
LOG_FILE = "/tmp/live_wallpaper.log"

CONFIG_JSON = os.path.expanduser("~/.config/dynamic_island/config.json")
SAVED_VIDEO_FILE = os.path.expanduser("~/.config/dynamic_island/live_wallpaper.path")

def get_configured_video() -> str:
    # 1. Check saved video path file
    if os.path.exists(SAVED_VIDEO_FILE):
        try:
            with open(SAVED_VIDEO_FILE, "r") as f:
                path = f.read().strip()
            if os.path.isfile(path):
                return path
        except Exception:
            pass

    # 2. Check config.json
    if os.path.exists(CONFIG_JSON):
        try:
            with open(CONFIG_JSON, "r") as f:
                data = json.load(f)
            path = data.get("live_wallpaper_video")
            if path and os.path.isfile(path):
                return path
        except Exception:
            pass

    # 3. Fallbacks
    for p in (DEFAULT_VIDEO, FALLBACK_1080P, FALLBACK_4K, "/home/tramvo/.local/share/backgrounds/sakura_torii_4k_live.mp4"):
        if os.path.isfile(p):
            return p
    return DEFAULT_VIDEO

def set_configured_video(video_path: str) -> str:
    abs_path = os.path.abspath(os.path.expanduser(video_path))
    if not os.path.isfile(abs_path):
        print(f"❌ File video không tồn tại: {abs_path}")
        return None

    # Save to SAVED_VIDEO_FILE
    try:
        os.makedirs(os.path.dirname(SAVED_VIDEO_FILE), exist_ok=True)
        with open(SAVED_VIDEO_FILE, "w") as f:
            f.write(abs_path)
    except Exception as e:
        print(f"Notice: {e}")

    # Save to config.json
    try:
        os.makedirs(os.path.dirname(CONFIG_JSON), exist_ok=True)
        if os.path.exists(CONFIG_JSON):
            with open(CONFIG_JSON, "r") as f:
                data = json.load(f)
        else:
            data = {}
        data["live_wallpaper_video"] = abs_path
        with open(CONFIG_JSON, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Notice: {e}")

    return abs_path

def sync_lockscreen_background(image_path=None):
    """Synchronize lockscreen background with current desktop wallpaper using high-res frosted glass blur."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        if not image_path:
            res = subprocess.run(["gsettings", "get", "org.gnome.desktop.background", "picture-uri"], capture_output=True, text=True)
            uri = res.stdout.strip().strip("'")
            if uri.startswith("file://"):
                image_path = uri[7:]
        if image_path and os.path.isfile(image_path):
            dest = os.path.expanduser("~/.themes/MacTahoe-Dark/gnome-shell/assets/background.png")
            im = Image.open(image_path).convert("RGB")
            im = im.resize((1920, 1080), Image.Resampling.LANCZOS)
            im = im.filter(ImageFilter.GaussianBlur(radius=40))
            im = ImageEnhance.Brightness(im).enhance(0.72)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            im.save(dest, "PNG", optimize=True)
    except Exception:
        pass

def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def get_running_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if is_pid_running(pid):
                return pid
            else:
                os.remove(PID_FILE)
        except Exception:
            pass
    return None

def open_file_chooser():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk

    dialog = Gtk.FileChooserDialog(
        title="🎬 Chọn Video Hình Nền Động (Live Wallpaper)",
        parent=None,
        action=Gtk.FileChooserAction.OPEN
    )
    dialog.add_buttons(
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
        Gtk.STOCK_OPEN, Gtk.ResponseType.OK
    )

    # Initial folder
    start_dir = WALLPAPERS_DIR if os.path.isdir(WALLPAPERS_DIR) else os.path.expanduser("~/Videos")
    dialog.set_current_folder(start_dir)

    filter_video = Gtk.FileFilter()
    filter_video.set_name("Video Files (*.mp4, *.mkv, *.webm, *.mov, *.avi)")
    filter_video.add_mime_type("video/*")
    for ext in ("*.mp4", "*.mkv", "*.webm", "*.mov", "*.avi", "*.m4v"):
        filter_video.add_pattern(ext)
        filter_video.add_pattern(ext.upper())
    dialog.add_filter(filter_video)

    filter_all = Gtk.FileFilter()
    filter_all.set_name("Tất cả các tệp (*.*)")
    filter_all.add_pattern("*")
    dialog.add_filter(filter_all)

    dialog.set_default_size(800, 500)
    dialog.set_position(Gtk.WindowPosition.CENTER)

    chosen_file = None
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        chosen_file = dialog.get_filename()
    dialog.destroy()
    while Gtk.events_pending():
        Gtk.main_iteration()

    return chosen_file

def run_wallpaper_window(video_path=None):
    import cv2
    cv2.setNumThreads(1)
    import cairo
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gtk, Gdk, GLib

    target_video = video_path or get_configured_video()
    if not os.path.isfile(target_video):
        for fb in (DEFAULT_VIDEO, FALLBACK_1080P, FALLBACK_4K, "/home/tramvo/.local/share/backgrounds/sakura_torii_4k_live.mp4"):
            if os.path.isfile(fb):
                target_video = fb
                break

    print(f"🎬 [LiveWallpaper] Opening video: {target_video}")
    cap = cv2.VideoCapture(target_video)
    if not cap.isOpened():
        print(f"❌ [LiveWallpaper] Error opening video: {target_video}")
        sys.exit(1)

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    target_fps = min(60.0, max(30.0, video_fps))
    interval_ms = max(16, int(1000.0 / target_fps))

    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    geom = monitor.get_geometry()
    screen_w = geom.width
    screen_h = geom.height
    screen_x = geom.x
    screen_y = geom.y

    print(f"🖥️ [LiveWallpaper] Display: {screen_w}x{screen_h} at ({screen_x},{screen_y}) | {target_fps:.1f} FPS ({interval_ms}ms)")

    # Pre-allocate static BGRA buffer to eliminate GC allocations
    bgra_buf = np.empty((screen_h, screen_w, 4), dtype=np.uint8)
    surface = cairo.ImageSurface.create_for_data(
        bgra_buf,
        cairo.FORMAT_ARGB32,
        screen_w,
        screen_h,
        screen_w * 4
    )

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_title("macOS Live Wallpaper")
    win.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
    win.set_decorated(False)
    win.set_skip_taskbar_hint(True)
    win.set_skip_pager_hint(True)
    win.stick()
    win.set_role("desktop-wallpaper")
    win.set_default_size(screen_w, screen_h)
    win.move(screen_x, screen_y)

    drawing_area = Gtk.DrawingArea()
    drawing_area.set_size_request(screen_w, screen_h)
    win.add(drawing_area)

    def on_draw(widget, cr):
        cr.set_source_surface(surface, 0, 0)
        cr.paint()
        return False

    drawing_area.connect("draw", on_draw)

    def raise_desktop_widgets():
        try:
            from gi.repository import GdkX11
            disp = GdkX11.X11Display.get_default()
            if not disp:
                return
            out = subprocess.check_output(["xprop", "-root", "_NET_CLIENT_LIST"], stderr=subprocess.DEVNULL).decode()
            for part in out.split(","):
                part = part.strip()
                if "0x" in part:
                    hex_str = part.split()[-1]
                    try:
                        xid = int(hex_str, 16)
                        cls_out = subprocess.check_output(["xprop", "-id", hex(xid), "WM_CLASS"], stderr=subprocess.DEVNULL).decode()
                        if "desktop-widget" in cls_out:
                            gw = GdkX11.X11Window.foreign_new_for_display(disp, xid)
                            if gw:
                                gw.raise_()
                    except Exception:
                        pass
        except Exception:
            pass

    def on_realize(widget):
        gdk_win = widget.get_window()
        if gdk_win:
            try:
                gdk_win.set_pass_through(True)
            except Exception as e:
                print(f"[LiveWallpaper] pass_through notice: {e}")
            # Ensure wallpaper stays at the absolute bottom
            gdk_win.lower()
        # Raise existing desktop widgets above wallpaper
        GLib.idle_add(raise_desktop_widgets)

    win.connect("realize", on_realize)

    def read_frame():
        nonlocal cap
        ret, frame = cap.read()
        if not ret:
            # Seamless loop rewind
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                return False

        h, w = frame.shape[:2]
        if (w, h) != (screen_w, screen_h):
            frame = cv2.resize(frame, (screen_w, screen_h), interpolation=cv2.INTER_LINEAR)

        cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA, dst=bgra_buf)
        surface.mark_dirty()
        return True

    def on_tick():
        if read_frame():
            drawing_area.queue_draw()
        return True

    def enforce_bottom_layer():
        gdk_win = win.get_window()
        if gdk_win and win.get_visible():
            gdk_win.lower()
        return True

    # Read frame 0
    read_frame()

    # Schedule frame updates
    GLib.timeout_add(interval_ms, on_tick)

    def on_shutdown(*args):
        try:
            if cap:
                cap.release()
        except Exception:
            pass
        Gtk.main_quit()

    signal.signal(signal.SIGINT, on_shutdown)
    signal.signal(signal.SIGTERM, on_shutdown)

    win.show_all()
    print("✨ [LiveWallpaper] Engine started successfully!")
    Gtk.main()

def main():
    args = sys.argv[1:]
    cmd = args[0].lower() if args else "start"

    if cmd == "--run":
        # Internal worker process
        video_arg = args[1] if len(args) > 1 else None
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        try:
            run_wallpaper_window(video_arg)
        finally:
            if os.path.exists(PID_FILE):
                try: os.remove(PID_FILE)
                except Exception: pass
        return

    if cmd in ("help", "--help", "-h"):
        print("🌟 BỘ ĐIỀU KHIỂN HÌNH NỀN (LIVE & STATIC WALLPAPER)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("• Chuyển đổi qua lại giữa động và tĩnh:")
        print("    live_wallpaper toggle")
        print("• Chuyển sang hình nền tĩnh (tắt hình nền động):")
        print("    live_wallpaper static")
        print("    live_wallpaper static /đường_dẫn/ảnh.jpg")
        print("    live_wallpaper stop")
        print("• Chuyển sang hình nền động (bật video):")
        print("    live_wallpaper start")
        print("    live_wallpaper set /đường_dẫn/video.mp4")
        print("    live_wallpaper choose  (chọn video bằng giao diện)")
        print("• Kiểm tra trạng thái hiện tại:")
        print("    live_wallpaper status")
        print("• Mở thư mục video có sẵn:")
        print("    live_wallpaper dir")
        return

    if cmd in ("toggle", "switch", "chuyendoi", "chuyen"):
        pid = get_running_pid()
        if pid:
            print("🔄 Đang chuyển từ hình nền động sang hình nền tĩnh...")
            subprocess.run([sys.executable, os.path.abspath(__file__), "stop"])
            print("🖼️ Đã chuyển về hình nền tĩnh GNOME.")
        else:
            print("🔄 Đang chuyển từ hình nền tĩnh sang hình nền động...")
            subprocess.run([sys.executable, os.path.abspath(__file__), "start"])
        return

    if cmd in ("static", "tinh"):
        pid = get_running_pid()
        if pid:
            subprocess.run([sys.executable, os.path.abspath(__file__), "stop"])
        if len(args) > 1:
            img_path = os.path.abspath(os.path.expanduser(args[1]))
            if os.path.isfile(img_path):
                uri = f"file://{img_path}"
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri])
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri])
                sync_lockscreen_background(img_path)
                print(f"🖼️ Đã đặt và kích hoạt hình nền tĩnh: {img_path}")
            else:
                print(f"❌ File ảnh không tồn tại: {img_path}")
        else:
            print("🖼️ Đã chuyển về hình nền tĩnh GNOME.")
        return

    if cmd in ("stop", "kill"):
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"🛑 Đã dừng Live Wallpaper (PID {pid}).")
            except Exception as e:
                print(f"Lỗi khi dừng PID {pid}: {e}")
            if os.path.exists(PID_FILE):
                try: os.remove(PID_FILE)
                except Exception: pass
        else:
            subprocess.run(["pkill", "-f", "live_wallpaper --run"])
            print("🛑 Live Wallpaper hiện không chạy.")
        return

    if cmd in ("dir", "folder", "open"):
        print(f"📂 Mở thư mục hình nền video: {WALLPAPERS_DIR}")
        subprocess.Popen(["xdg-open", WALLPAPERS_DIR])
        return

    if cmd in ("choose", "select", "pick"):
        chosen = open_file_chooser()
        if chosen and os.path.isfile(chosen):
            set_configured_video(chosen)
            print(f"✅ Đã chọn video mới: {chosen}")
            subprocess.run([sys.executable, os.path.abspath(__file__), "restart"])
        else:
            print("Đã hủy chọn file.")
        return

    if cmd in ("set", "change"):
        if len(args) < 2:
            print("Cú pháp: live_wallpaper set /đường_dẫn_tới/video.mp4")
            return
        video_path = args[1]
        valid_path = set_configured_video(video_path)
        if valid_path:
            print(f"✅ Đã lưu cấu hình video: {valid_path}")
            subprocess.run([sys.executable, os.path.abspath(__file__), "restart"])
        return

    if cmd == "status":
        pid = get_running_pid()
        current_vid = get_configured_video()
        if pid:
            print(f"🟢 Live Wallpaper đang CHẠY (PID {pid}).")
        else:
            print("⚪ Live Wallpaper đang TẮT.")
        print(f"🎬 Video hiện tại: {current_vid}")
        return

    if cmd == "restart":
        main_stop = [sys.executable, os.path.abspath(__file__), "stop"]
        subprocess.run(main_stop)
        time.sleep(0.5)
        new_video = args[1] if len(args) > 1 and os.path.isfile(args[1]) else None
        if new_video:
            set_configured_video(new_video)
        main_start = [sys.executable, os.path.abspath(__file__), "start"]
        subprocess.run(main_start)
        return

    # Check if first argument is a video file directly
    if os.path.isfile(cmd):
        set_configured_video(cmd)
        print(f"✅ Đã chọn video: {cmd}")
        subprocess.run([sys.executable, os.path.abspath(__file__), "restart"])
        return

    # Start command
    video_arg = None
    foreground = False

    for a in args:
        if a in ("--foreground", "-f"):
            foreground = True
        elif os.path.isfile(a):
            video_arg = set_configured_video(a)

    if not video_arg:
        video_arg = get_configured_video()

    pid = get_running_pid()
    if pid:
        print(f"⚠️ Live Wallpaper đang chạy rồi (PID {pid}).")
        print("Để đổi video mới, chạy lệnh: live_wallpaper set /đường_dẫn/video.mp4")
        print("Hoặc: live_wallpaper choose (để chọn file bằng chuột)")
        return

    if foreground:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        try:
            run_wallpaper_window(video_arg)
        finally:
            if os.path.exists(PID_FILE):
                try: os.remove(PID_FILE)
                except Exception: pass
    else:
        # Launch daemonized in background
        cmd_exec = [sys.executable, "-u", os.path.abspath(__file__), "--run", video_arg]
        log_fd = open(LOG_FILE, "a")
        proc = subprocess.Popen(
            cmd_exec,
            stdout=log_fd,
            stderr=log_fd,
            start_new_session=True
        )
        print(f"🚀 [LiveWallpaper] Đã khởi chạy hình nền động (PID {proc.pid})")
        print(f"🎬 Video đang phát: {video_arg}")
        print(f"📄 Log: {LOG_FILE}")
        time.sleep(0.5)
        if is_pid_running(proc.pid):
            print("✅ Live Wallpaper đang phát mượt mà!")
        else:
            print("❌ Tiến trình lỗi. Kiểm tra /tmp/live_wallpaper.log để biết chi tiết.")

if __name__ == "__main__":
    main()
