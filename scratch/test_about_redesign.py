import os
import re
import math
import subprocess
import cairo
import gi
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def get_refined_specs():
    specs = {
        "model": "MacBook Pro",
        "subtitle": "16-inch, 2024",
        "chip_real": "Intel Xeon E5-2678 v3 @ 2.50GHz",
        "chip_apple": "Apple M3 Max (16-core CPU, 40-core GPU)",
        "show_apple_silicon": False,
        "graphics": None,
        "memory_real": "16 GB DDR4",
        "memory_apple": "16 GB Unified Memory",
        "os": "macOS Sequoia 15.1",
        "serial": "C02G80XYZ890",
        "storage": "Macintosh HD"
    }

    # 1. CPU detection
    is_intel_or_amd = False
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    cpu_raw = line.split(":", 1)[1].strip()
                    cpu_clean = re.sub(r'\(R\)|\(TM\)|Processor|CPU', '', cpu_raw).strip()
                    cpu_clean = ' '.join(cpu_clean.split())
                    specs["chip_real"] = cpu_clean
                    is_intel_or_amd = True
                    break
    except Exception:
        pass

    # 2. GPU detection
    try:
        lspci = subprocess.check_output("lspci | grep -i vga", shell=True, timeout=0.5).decode()
        gpu_raw = lspci.split(":", 2)[-1].strip()
        if "NVIDIA" in gpu_raw:
            match = re.search(r'\[(.*?)\]', gpu_raw)
            if match:
                g_str = match.group(1).replace("GeForce", "").strip()
                specs["graphics"] = f"NVIDIA GeForce {g_str}"
            else:
                specs["graphics"] = "NVIDIA " + gpu_raw.split("NVIDIA")[-1].strip()
        elif "AMD" in gpu_raw or "Advanced Micro Devices" in gpu_raw:
            match = re.search(r'\[(.*?)\]', gpu_raw)
            specs["graphics"] = match.group(1) if match else "AMD Radeon Graphics"
        elif "Intel" in gpu_raw:
            match = re.search(r'\[(.*?)\]', gpu_raw)
            specs["graphics"] = match.group(1) if match else "Intel UHD Graphics"
    except Exception:
        pass

    # 3. RAM detection
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    kb = int(line.split()[1])
                    gb_raw = kb / (1024 * 1024)
                    ram_candidates = [4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 256]
                    gb = min(ram_candidates, key=lambda x: abs(x - gb_raw) if x >= gb_raw * 0.88 else 999)
                    specs["memory_real"] = f"{gb} GB DDR4"
                    specs["memory_apple"] = f"{gb} GB Unified Memory"
                    break
    except Exception:
        pass

    return specs


class RedesignedAboutWindow(Gtk.Window):
    _instance = None

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        RedesignedAboutWindow._instance = self

        self.set_title("About This Mac")
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_skip_taskbar_hint(False)
        self.set_wmclass("macos-about", "MacOSAbout")
        self.set_role("about-dialog")
        self.set_default_size(580, 340)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.specs = get_refined_specs()
        self.wallpaper_theme = "sequoia"  # sequoia, sonoma, aurora, obsidian
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK
        )

        self._load_css()
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("key-press-event", self._on_key_press)

        self._build_ui()

    def _load_css(self):
        css = b"""
        .mac-traffic-btn {
            border-radius: 50%;
            min-width: 12px;
            min-height: 12px;
            padding: 0;
            margin: 0;
            border: 0.5px solid rgba(0, 0, 0, 0.25);
            background-color: transparent;
        }
        .mac-traffic-btn.red {
            background-color: #ff5f56;
            border-color: #e0443e;
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.4);
        }
        .mac-traffic-btn.yellow {
            background-color: #ffbd2e;
            border-color: #dea123;
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.4);
        }
        .mac-traffic-btn.green {
            background-color: #27c93f;
            border-color: #1aab29;
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.4);
        }
        .mac-traffic-btn .symbol {
            font-size: 7.5px;
            font-weight: 800;
            color: rgba(0, 0, 0, 0.65);
        }
        button.mac-about-btn,
        button.mac-about-btn:hover,
        button.mac-about-btn:active {
            background-image: none;
        }
        button.mac-about-btn {
            background-color: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.20);
            border-radius: 7px;
            padding: 5px 16px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
            transition: all 120ms ease;
        }
        button.mac-about-btn label {
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Ubuntu", sans-serif;
            font-size: 11px;
            font-weight: 500;
        }
        button.mac-about-btn:hover {
            background-color: rgba(255, 255, 255, 0.24);
            border-color: rgba(255, 255, 255, 0.32);
        }
        button.mac-about-btn:hover label {
            color: #ffffff;
        }
        button.mac-about-btn:active {
            background-color: rgba(255, 255, 255, 0.10);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_margin_top(14)
        root.set_margin_bottom(18)
        root.set_margin_start(16)
        root.set_margin_end(24)
        self.add(root)

        # 1. Header (Traffic lights on left)
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_bar.set_valign(Gtk.Align.CENTER)
        root.pack_start(top_bar, False, False, 0)

        def make_traffic_btn(color_cls, symbol, cb=None):
            btn = Gtk.Button()
            btn.set_size_request(12, 12)
            btn.get_style_context().add_class("mac-traffic-btn")
            btn.get_style_context().add_class(color_cls)
            lbl = Gtk.Label(label="")
            lbl.get_style_context().add_class("symbol")
            btn.add(lbl)
            btn.connect("enter-notify-event", lambda b, e: [lbl.set_text(symbol), False][1])
            btn.connect("leave-notify-event", lambda b, e: [lbl.set_text(""), False][1])
            if cb:
                btn.connect("clicked", lambda _: cb())
            return btn

        top_bar.pack_start(make_traffic_btn("red", "✕", lambda: self.hide()), False, False, 0)
        top_bar.pack_start(make_traffic_btn("yellow", "—", lambda: self.iconify()), False, False, 0)
        top_bar.pack_start(make_traffic_btn("green", "⤢", None), False, False, 0)

        # 2. Main Content (Left: MacBook, Right: Specs & Actions)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        body.set_margin_top(10)
        body.set_margin_start(8)
        root.pack_start(body, True, True, 0)

        # Left Column: MacBook Artwork
        mac_box = Gtk.EventBox()
        mac_box.set_visible_window(False)
        self.mac_canvas = Gtk.DrawingArea()
        self.mac_canvas.set_size_request(216, 195)
        self.mac_canvas.connect("draw", self._draw_macbook)
        mac_box.add(self.mac_canvas)
        mac_box.connect("button-press-event", self._on_mac_clicked)
        mac_box.set_tooltip_text("Click to cycle wallpaper theme")
        body.pack_start(mac_box, False, False, 0)

        # Right Column: Typography & Specs
        info_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        info_col.set_valign(Gtk.Align.CENTER)
        info_col.set_halign(Gtk.Align.START)
        body.pack_start(info_col, True, True, 0)

        # Header Titles (Strictly aligned to the left of specs)
        model_lbl = Gtk.Label()
        model_lbl.set_halign(Gtk.Align.START)
        model_lbl.set_xalign(0.0)
        model_lbl.set_markup(f"<span font_desc='Inter, -apple-system, Ubuntu Bold 22pt' foreground='#ffffff'>{self.specs['model']}</span>")
        info_col.pack_start(model_lbl, False, False, 0)

        sub_lbl = Gtk.Label()
        sub_lbl.set_halign(Gtk.Align.START)
        sub_lbl.set_xalign(0.0)
        sub_lbl.set_markup(f"<span font_desc='Inter, -apple-system, Ubuntu Medium 10pt' foreground='#8e8e93'>{self.specs['subtitle']}</span>")
        sub_lbl.set_margin_bottom(14)
        info_col.pack_start(sub_lbl, False, False, 0)

        # Key-Value Grid (Clean left-aligned columns matching macOS Sequoia)
        self.grid = Gtk.Grid()
        self.grid.set_halign(Gtk.Align.START)
        self.grid.set_column_spacing(18)
        self.grid.set_row_spacing(5.5)
        info_col.pack_start(self.grid, False, False, 0)

        self._render_specs_grid()

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.START)
        btn_box.set_margin_top(18)

        settings_btn = Gtk.Button(label="System Settings...")
        settings_btn.get_style_context().add_class("mac-about-btn")
        settings_btn.connect("clicked", self._open_settings)
        btn_box.pack_start(settings_btn, False, False, 0)

        more_btn = Gtk.Button(label="More Info...")
        more_btn.get_style_context().add_class("mac-about-btn")
        more_btn.connect("clicked", lambda _: self._open_settings(None, tab="vitals"))
        btn_box.pack_start(more_btn, False, False, 0)

        info_col.pack_start(btn_box, False, False, 0)

    def _render_specs_grid(self):
        for child in self.grid.get_children():
            self.grid.remove(child)

        chip_val = self.specs["chip_apple"] if self.specs["show_apple_silicon"] else self.specs["chip_real"]
        mem_val = self.specs["memory_apple"] if self.specs["show_apple_silicon"] else self.specs["memory_real"]

        specs_list = [
            ("Chip", chip_val),
        ]
        if self.specs.get("graphics") and not self.specs["show_apple_silicon"]:
            specs_list.append(("Graphics", self.specs["graphics"]))
        specs_list.extend([
            ("Memory", mem_val),
            ("Startup Disk", self.specs["storage"]),
            ("macOS", self.specs["os"]),
            ("Serial Number", self.specs["serial"]),
        ])

        for row_idx, (label_text, val_text) in enumerate(specs_list):
            k_lbl = Gtk.Label()
            k_lbl.set_halign(Gtk.Align.START)
            k_lbl.set_xalign(0.0)
            k_lbl.set_size_request(92, -1)
            k_lbl.set_markup(f"<span font_desc='Inter, -apple-system, Ubuntu Medium 10pt' foreground='#8e8e93'>{label_text}</span>")
            self.grid.attach(k_lbl, 0, row_idx, 1, 1)

            v_lbl = Gtk.Label()
            v_lbl.set_halign(Gtk.Align.START)
            v_lbl.set_xalign(0.0)
            v_lbl.set_markup(f"<span font_desc='Inter, -apple-system, Ubuntu Regular 10pt' foreground='#ffffff'>{val_text}</span>")
            v_lbl.set_selectable(True)

            if label_text == "Chip":
                chip_event = Gtk.EventBox()
                chip_event.set_visible_window(False)
                chip_event.add(v_lbl)
                chip_event.connect("button-press-event", self._toggle_chip_mode)
                chip_event.set_tooltip_text("Click to toggle Apple Silicon / Real Hardware")
                self.grid.attach(chip_event, 1, row_idx, 1, 1)
            elif label_text == "Serial Number":
                sn_event = Gtk.EventBox()
                sn_event.set_visible_window(False)
                sn_event.add(v_lbl)
                sn_event.connect("button-press-event", self._copy_serial)
                sn_event.set_tooltip_text("Click to copy Serial Number")
                self.grid.attach(sn_event, 1, row_idx, 1, 1)
            else:
                self.grid.attach(v_lbl, 1, row_idx, 1, 1)

        self.grid.show_all()

    def _toggle_chip_mode(self, widget, event):
        self.specs["show_apple_silicon"] = not self.specs["show_apple_silicon"]
        self._render_specs_grid()

    def _copy_serial(self, widget, event):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clip.set_text(self.specs["serial"], -1)
        clip.store()

    def _on_mac_clicked(self, widget, event):
        themes = ["sequoia", "sonoma", "aurora", "obsidian"]
        cur_idx = themes.index(self.wallpaper_theme) if self.wallpaper_theme in themes else 0
        self.wallpaper_theme = themes[(cur_idx + 1) % len(themes)]
        self.mac_canvas.queue_draw()

    def _open_settings(self, widget, tab="general"):
        try:
            from src.ui.macos_settings_window import MacOSSettingsWindow
            win = MacOSSettingsWindow()
            win.show_window(tab)
        except Exception:
            subprocess.Popen(["gnome-control-center"])

    def _draw_macbook(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0 - 5.0

        mw = 186.0
        mh = 118.0

        # 0. Diffused Contact Shadow underneath
        cr.save()
        cr.translate(cx, cy + mh * 0.44)
        cr.scale(1.0, 0.20)
        cr.arc(0, 0, mw * 0.54, 0, 2 * math.pi)
        sh_pat = cairo.RadialGradient(0, 0, 0, 0, 0, mw * 0.54)
        sh_pat.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.70)
        sh_pat.add_color_stop_rgba(0.7, 0.0, 0.0, 0.0, 0.22)
        sh_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        cr.set_source(sh_pat)
        cr.fill()
        cr.restore()

        # 1. Screen Lid (Aluminum Unibody Space Gray)
        lid_w = mw * 0.90
        lid_h = mh * 0.83
        lx = cx - lid_w / 2.0
        ly = cy - lid_h / 2.0 - 4.0

        r = 6.0
        cr.new_sub_path()
        cr.arc(lx + lid_w - r, ly + r, r, -math.pi/2, 0)
        cr.arc(lx + lid_w - r, ly + lid_h - r, r, 0, math.pi/2)
        cr.arc(lx + r, ly + lid_h - r, r, math.pi/2, math.pi)
        cr.arc(lx + r, ly + r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        shell_pat = cairo.LinearGradient(lx, ly, lx, ly + lid_h)
        shell_pat.add_color_stop_rgb(0.0, 0.46, 0.49, 0.54)
        shell_pat.add_color_stop_rgb(1.0, 0.28, 0.30, 0.34)
        cr.set_source(shell_pat)
        cr.fill_preserve()
        cr.set_source_rgba(0.18, 0.20, 0.24, 0.90)
        cr.set_line_width(0.8)
        cr.stroke()

        # Display Bezel (Ultra-thin black border)
        bw = 3.6
        sx = lx + bw
        sy = ly + bw
        sw = lid_w - 2 * bw
        sh = lid_h - 2 * bw

        cr.rectangle(lx + 1.2, ly + 1.2, lid_w - 2.4, lid_h - 2.4)
        cr.set_source_rgba(0.03, 0.04, 0.05, 0.98)
        cr.fill()

        # Liquid Retina Display Screen Clip (rounded top corners)
        cr.save()
        sr = 4.0
        cr.new_sub_path()
        cr.arc(sx + sw - sr, sy + sr, sr, -math.pi/2, 0)
        cr.line_to(sx + sw, sy + sh)
        cr.line_to(sx, sy + sh)
        cr.arc(sx + sr, sy + sr, sr, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.clip()

        # Wallpaper themes
        if self.wallpaper_theme == "sonoma":
            bg_pat = cairo.LinearGradient(sx, sy, sx + sw, sy + sh)
            bg_pat.add_color_stop_rgb(0.0, 0.04, 0.08, 0.25)
            bg_pat.add_color_stop_rgb(1.0, 0.12, 0.08, 0.32)
            cr.set_source(bg_pat)
            cr.paint()

            # Dynamic Sonoma Ribbons
            cr.save()
            cr.move_to(sx, sy + sh * 0.85)
            cr.curve_to(sx + sw * 0.35, sy + sh * 0.35, sx + sw * 0.65, sy + sh * 0.90, sx + sw, sy + sh * 0.30)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            w1 = cairo.LinearGradient(sx, sy + sh * 0.3, sx + sw, sy + sh)
            w1.add_color_stop_rgba(0.0, 0.55, 0.25, 0.95, 0.90)
            w1.add_color_stop_rgba(1.0, 0.30, 0.15, 0.75, 0.85)
            cr.set_source(w1)
            cr.fill()
            cr.restore()

            cr.save()
            cr.move_to(sx, sy + sh * 0.92)
            cr.curve_to(sx + sw * 0.40, sy + sh * 0.55, sx + sw * 0.75, sy + sh * 0.82, sx + sw, sy + sh * 0.62)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            w2 = cairo.LinearGradient(sx, sy + sh * 0.5, sx + sw, sy + sh)
            w2.add_color_stop_rgba(0.0, 0.96, 0.25, 0.45, 0.95)
            w2.add_color_stop_rgba(0.6, 0.98, 0.55, 0.18, 0.90)
            w2.add_color_stop_rgba(1.0, 1.00, 0.75, 0.25, 0.85)
            cr.set_source(w2)
            cr.fill()
            cr.restore()

        elif self.wallpaper_theme == "aurora":
            bg_pat = cairo.LinearGradient(sx, sy, sx + sw, sy + sh)
            bg_pat.add_color_stop_rgb(0.0, 0.01, 0.03, 0.08)
            bg_pat.add_color_stop_rgb(1.0, 0.02, 0.06, 0.14)
            cr.set_source(bg_pat)
            cr.paint()

            # Emerald ribbons
            cr.save()
            cr.move_to(sx, sy + sh * 0.75)
            cr.curve_to(sx + sw * 0.30, sy + sh * 0.20, sx + sw * 0.70, sy + sh * 0.65, sx + sw, sy + sh * 0.15)
            cr.line_to(sx + sw, sy + sh * 0.45)
            cr.curve_to(sx + sw * 0.65, sy + sh * 0.85, sx + sw * 0.25, sy + sh * 0.40, sx, sy + sh * 0.90)
            cr.close_path()
            a1 = cairo.LinearGradient(sx, sy, sx, sy + sh)
            a1.add_color_stop_rgba(0.0, 0.06, 0.85, 0.55, 0.85)
            a1.add_color_stop_rgba(1.0, 0.02, 0.65, 0.80, 0.25)
            cr.set_source(a1)
            cr.fill()
            cr.restore()

        elif self.wallpaper_theme == "obsidian":
            m_pat = cairo.LinearGradient(sx, sy, sx, sy + sh)
            m_pat.add_color_stop_rgb(0.0, 0.10, 0.11, 0.14)
            m_pat.add_color_stop_rgb(1.0, 0.04, 0.05, 0.07)
            cr.set_source(m_pat)
            cr.paint()

            # Centered Glowing Apple logo
            acx = sx + sw / 2.0
            acy = sy + sh / 2.0
            cr.save()
            cr.translate(acx, acy)
            cr.scale(1.5, 1.5)
            cr.set_source_rgba(0.92, 0.94, 0.98, 0.88)
            cr.new_sub_path()
            cr.move_to(0.6, -4.5)
            cr.curve_to(2.2, -4.5, 2.8, -3.0, 2.8, -3.0)
            cr.curve_to(1.2, -2.8, 0.6, -4.5, 0.6, -4.5)
            cr.close_path()
            cr.fill()
            cr.new_sub_path()
            cr.move_to(0.0, -2.0)
            cr.curve_to(-1.3, -2.0, -2.4, -1.0, -2.9, 0.0)
            cr.curve_to(-3.5, 1.2, -3.3, 2.9, -2.2, 4.0)
            cr.curve_to(-1.4, 4.7, -0.5, 4.4, 0.0, 4.4)
            cr.curve_to(0.5, 4.4, 1.4, 4.7, 2.2, 4.0)
            cr.curve_to(3.1, 3.1, 3.4, 1.6, 3.4, 1.6)
            cr.curve_to(2.2, 1.1, 2.2, -0.7, 3.1, -1.4)
            cr.curve_to(2.5, -2.2, 1.4, -2.0, 0.9, -2.0)
            cr.curve_to(0.5, -2.0, 0.2, -2.0, 0.0, -2.0)
            cr.close_path()
            cr.fill()
            cr.restore()

        else: # Default: macOS Sequoia Sunset
            sky_pat = cairo.LinearGradient(sx, sy, sx, sy + sh)
            sky_pat.add_color_stop_rgb(0.0, 0.12, 0.10, 0.30)
            sky_pat.add_color_stop_rgb(0.48, 0.65, 0.18, 0.35)
            sky_pat.add_color_stop_rgb(0.85, 0.96, 0.60, 0.18)
            sky_pat.add_color_stop_rgb(1.0, 0.88, 0.45, 0.12)
            cr.set_source(sky_pat)
            cr.paint()

            sun_cx = sx + sw * 0.68
            sun_cy = sy + sh * 0.68
            sun_pat = cairo.RadialGradient(sun_cx, sun_cy, 1.0, sun_cx, sun_cy, sw * 0.36)
            sun_pat.add_color_stop_rgba(0.0, 1.0, 0.96, 0.78, 0.80)
            sun_pat.add_color_stop_rgba(0.45, 0.98, 0.65, 0.22, 0.40)
            sun_pat.add_color_stop_rgba(1.0, 0.95, 0.45, 0.10, 0.0)
            cr.set_source(sun_pat)
            cr.arc(sun_cx, sun_cy, sw * 0.36, 0, 2 * math.pi)
            cr.fill()

            # Back Mountain ridge
            cr.move_to(sx, sy + sh * 0.74)
            cr.line_to(sx + sw * 0.30, sy + sh * 0.58)
            cr.line_to(sx + sw * 0.60, sy + sh * 0.69)
            cr.line_to(sx + sw * 0.82, sy + sh * 0.53)
            cr.line_to(sx + sw, sy + sh * 0.66)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            cr.set_source_rgba(0.46, 0.16, 0.14, 0.80)
            cr.fill()

            # Foreground Redwood Forest
            cr.move_to(sx, sy + sh * 0.86)
            cr.line_to(sx + sw * 0.24, sy + sh * 0.72)
            cr.line_to(sx + sw * 0.52, sy + sh * 0.82)
            cr.line_to(sx + sw * 0.78, sy + sh * 0.68)
            cr.line_to(sx + sw, sy + sh * 0.79)
            cr.line_to(sx + sw, sy + sh)
            cr.line_to(sx, sy + sh)
            cr.close_path()
            cr.set_source_rgba(0.06, 0.12, 0.10, 0.96)
            cr.fill()

        # Mini Menu Bar (top)
        cr.rectangle(sx, sy, sw, 4.5)
        cr.set_source_rgba(0.95, 0.95, 0.98, 0.18)
        cr.fill()

        # Mini Apple Logo on menu bar
        cr.arc(sx + 5.0, sy + 2.2, 1.1, 0, 2*math.pi)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        cr.fill()

        # Mini Dock (bottom)
        dock_w = sw * 0.44
        dock_h = 3.6
        dock_x = sx + (sw - dock_w) / 2.0
        dock_y = sy + sh - dock_h - 1.2
        cr.new_sub_path()
        cr.arc(dock_x + dock_w - 1.8, dock_y + 1.8, 1.8, -math.pi/2, math.pi/2)
        cr.arc(dock_x + 1.8, dock_y + 1.8, 1.8, math.pi/2, 3*math.pi/2)
        cr.close_path()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.28)
        cr.fill()

        # Mini Dock App dots
        app_colors = [
            (0.15, 0.55, 0.98), # Finder
            (0.18, 0.75, 0.95), # Safari
            (0.20, 0.82, 0.40), # Messages
            (0.96, 0.65, 0.15), # Photos
            (0.96, 0.25, 0.35), # Music
            (0.55, 0.58, 0.62), # Settings
        ]
        dot_spacing = (dock_w - 6) / (len(app_colors) - 1)
        for i, col in enumerate(app_colors):
            dx = dock_x + 3.0 + i * dot_spacing
            dy = dock_y + dock_h / 2.0
            cr.arc(dx, dy, 0.9, 0, 2*math.pi)
            cr.set_source_rgb(*col)
            cr.fill()

        # Specular Diagonal Glare
        refl = cairo.LinearGradient(sx, sy, sx + sw * 0.70, sy + sh)
        refl.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.15)
        refl.add_color_stop_rgba(0.35, 1.0, 1.0, 1.0, 0.03)
        refl.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(refl)
        cr.paint()

        # Camera Notch (Centered at top)
        notch_w = 16.0
        notch_h = 3.4
        nx = cx - notch_w / 2.0
        ny = sy
        cr.new_sub_path()
        cr.move_to(nx, ny)
        cr.line_to(nx + notch_w, ny)
        cr.arc(nx + notch_w - 1.2, ny + notch_h - 1.2, 1.2, 0, math.pi / 2)
        cr.arc(nx + 1.2, ny + notch_h - 1.2, 1.2, math.pi / 2, math.pi)
        cr.close_path()
        cr.set_source_rgba(0.02, 0.02, 0.03, 1.0)
        cr.fill()

        # Camera lens & green indicator
        cr.arc(cx - 1.5, ny + 1.5, 0.70, 0, 2 * math.pi)
        cr.set_source_rgba(0.12, 0.25, 0.45, 1.0)
        cr.fill()
        cr.arc(cx + 2.8, ny + 1.5, 0.45, 0, 2 * math.pi)
        cr.set_source_rgba(0.15, 0.85, 0.40, 0.95)
        cr.fill()

        cr.restore()

        # 2. MacBook Base (CNC Anodized Aluminum)
        base_w = mw
        base_h = 8.5
        bx = cx - base_w / 2.0
        by = ly + lid_h - 1.5

        cr.new_sub_path()
        cr.arc(bx + base_w - 3.5, by + 3.0, 3.0, -math.pi / 2, 0)
        cr.arc(bx + base_w - 3.5, by + base_h - 2.8, 2.8, 0, math.pi / 2)
        cr.arc(bx + 3.5, by + base_h - 2.8, 2.8, math.pi / 2, math.pi)
        cr.arc(bx + 3.5, by + 3.0, 3.0, math.pi, 3 * math.pi / 2)
        cr.close_path()

        base_pat = cairo.LinearGradient(bx, by, bx, by + base_h)
        base_pat.add_color_stop_rgb(0.0, 0.50, 0.53, 0.58)
        base_pat.add_color_stop_rgb(1.0, 0.26, 0.28, 0.32)
        cr.set_source(base_pat)
        cr.fill_preserve()
        cr.set_source_rgba(0.16, 0.18, 0.21, 0.90)
        cr.set_line_width(0.8)
        cr.stroke()

        # Hinge recess
        hinge_w = 42.0
        cr.rectangle(cx - hinge_w / 2.0, by - 0.5, hinge_w, 2.0)
        cr.set_source_rgba(0.10, 0.11, 0.14, 0.98)
        cr.fill()

        # Thumb Scoop
        cr.arc(cx, by + 1.6, 5.5, 0, math.pi)
        cr.set_source_rgba(0.20, 0.22, 0.26, 0.70)
        cr.fill()
        cr.arc(cx, by + 1.6, 5.5, 0, math.pi)
        cr.set_source_rgba(0.85, 0.88, 0.94, 0.75)
        cr.set_line_width(0.7)
        cr.stroke()

        # Front edge chamfer specular highlight
        cr.move_to(bx + 4.0, by + base_h - 1.0)
        cr.line_to(bx + base_w - 4.0, by + base_h - 1.0)
        cr.set_source_rgba(0.90, 0.92, 0.96, 0.75)
        cr.set_line_width(0.7)
        cr.stroke()

        return False

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 18.0

        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Rounded window squircle
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        # macOS Sequoia deep frosted dark acrylic
        bg = cairo.LinearGradient(0, 0, 0, h)
        bg.add_color_stop_rgba(0.0, 0.12, 0.13, 0.17, 0.96)
        bg.add_color_stop_rgba(1.0, 0.07, 0.08, 0.10, 0.98)
        cr.set_source(bg)
        cr.fill_preserve()

        # Specular glass border
        rim = cairo.LinearGradient(0, 0, 0, h)
        rim.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.22)
        rim.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.08)
        rim.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.12)
        cr.set_source(rim)
        cr.set_line_width(1.0)
        cr.stroke()

        return False

    def _on_button_press(self, widget, event):
        if event.button == 1 and event.y < 45:
            self._dragging = True
            self._drag_start_x = event.x
            self._drag_start_y = event.y
        return False

    def _on_button_release(self, widget, event):
        self._dragging = False
        return False

    def _on_motion_notify(self, widget, event):
        if self._dragging:
            win_x, win_y = self.get_position()
            new_x = int(win_x + event.x - self._drag_start_x)
            new_y = int(win_y + event.y - self._drag_start_y)
            self.move(new_x, new_y)
        return False

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    @classmethod
    def show_window(cls):
        if cls._instance is None:
            cls._instance = RedesignedAboutWindow()
        cls._instance.show_all()
        cls._instance.present()


if __name__ == "__main__":
    win = RedesignedAboutWindow()
    win.show_all()
    for _ in range(35):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.02)

    alloc = win.get_allocation()
    gdk_win = win.get_window()
    if gdk_win:
        pb = Gdk.pixbuf_get_from_window(gdk_win, 0, 0, alloc.width, alloc.height)
        if pb:
            out = '/home/tramvo/.gemini/antigravity-ide/brain/67c4e8d3-62be-4941-a87e-c74568edb578/test_redesign_clean.png'
            pb.savev(out, 'png', [], [])
            print('Captured clean redesigned:', out, alloc.width, alloc.height)
