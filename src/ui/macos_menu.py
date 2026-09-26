"""
Apple macOS SF Symbols & Frosted Glass Context Menu Module.
Provides authentic Apple SF Symbols vector iconography and glassmorphism styling
for all desktop widgets, replacing Linux system emojis with pixel-perfect macOS symbols.
"""

import math
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

# Cache for rendered SF Symbols to guarantee instant popup performance
_SF_SYMBOL_CACHE = {}


def get_sf_symbol_pixbuf(symbol_name: str, size: int = 16, color: tuple = None) -> GdkPixbuf.Pixbuf:
    """
    Renders vector Apple SF Symbols in Cairo with 2x supersampling for extreme sharpness.
    """
    if color is None:
        if symbol_name in ("xmark", "hide", "trash", "delete"):
            color = (1.0, 0.27, 0.23) # Apple Red #ff453a
        elif symbol_name in ("sparkles", "sparkle"):
            color = (1.0, 0.84, 0.04) # Apple Amber #ffd60a
        elif symbol_name in ("check", "checkmark"):
            color = (0.04, 0.52, 1.00) # Apple Blue #0a84ff
        else:
            color = (0.92, 0.94, 0.98) # Crisp Silver/White #f1f5f9

    cache_key = (symbol_name, size, color)
    if cache_key in _SF_SYMBOL_CACHE:
        return _SF_SYMBOL_CACHE[cache_key]

    scale = 2
    px = size * scale
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, px, px)
    cr = cairo.Context(surface)
    cr.scale(scale, scale)

    cr.set_source_rgb(*color)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    s = size

    # 1. LOCK / UNLOCK
    if symbol_name in ("lock.open", "unlock"):
        bw, bh = s * 0.62, s * 0.44
        bx = (s - bw) / 2.0
        by = s - bh - 2.5
        r = 2.4
        cr.new_sub_path()
        cr.arc(bx + bw - r, by + r, r, -math.pi/2, 0)
        cr.arc(bx + bw - r, by + bh - r, r, 0, math.pi/2)
        cr.arc(bx + r, by + bh - r, r, math.pi/2, math.pi)
        cr.arc(bx + r, by + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.fill()
        # Open Shackle
        cr.set_line_width(1.8)
        cr.move_to(bx + 2.5, by)
        cr.line_to(bx + 2.5, by - s * 0.25)
        cr.arc(bx + bw * 0.5, by - s * 0.25, bw * 0.5 - 2.5, math.pi, 0)
        cr.line_to(bx + bw - 2.5, by - s * 0.16)
        cr.stroke()

    elif symbol_name in ("lock", "lock.fill"):
        bw, bh = s * 0.62, s * 0.44
        bx = (s - bw) / 2.0
        by = s - bh - 2.5
        r = 2.4
        cr.new_sub_path()
        cr.arc(bx + bw - r, by + r, r, -math.pi/2, 0)
        cr.arc(bx + bw - r, by + bh - r, r, 0, math.pi/2)
        cr.arc(bx + r, by + bh - r, r, math.pi/2, math.pi)
        cr.arc(bx + r, by + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.fill()
        # Closed Shackle
        cr.set_line_width(1.8)
        cr.move_to(bx + 2.5, by + 1.0)
        cr.line_to(bx + 2.5, by - s * 0.22)
        cr.arc(bx + bw * 0.5, by - s * 0.22, bw * 0.5 - 2.5, math.pi, 0)
        cr.line_to(bx + bw - 2.5, by + 1.0)
        cr.stroke()
        # Keyhole dot
        cr.arc(s / 2.0, by + bh * 0.45, 1.2, 0, 2*math.pi)
        cr.set_source_rgba(0.10, 0.12, 0.16, 0.95)
        cr.fill()

    elif symbol_name in ("lock.all", "lock.stack"):
        r = 1.6
        # Back lock
        cr.set_line_width(1.3)
        cr.arc(s * 0.64, s * 0.28, s * 0.14, math.pi, 0)
        cr.stroke()
        cr.new_sub_path()
        cr.arc(s * 0.46 + s * 0.38 - r, s * 0.28 + r, r, -math.pi/2, 0)
        cr.arc(s * 0.46 + s * 0.38 - r, s * 0.28 + s * 0.32 - r, r, 0, math.pi/2)
        cr.arc(s * 0.46 + r, s * 0.28 + s * 0.32 - r, r, math.pi/2, math.pi)
        cr.arc(s * 0.46 + r, s * 0.28 + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        # Front lock
        cr.arc(s * 0.36, s * 0.46, s * 0.14, math.pi, 0)
        cr.stroke()
        cr.new_sub_path()
        cr.arc(s * 0.17 + s * 0.38 - r, s * 0.46 + r, r, -math.pi/2, 0)
        cr.arc(s * 0.17 + s * 0.38 - r, s * 0.46 + s * 0.32 - r, r, 0, math.pi/2)
        cr.arc(s * 0.17 + r, s * 0.46 + s * 0.32 - r, r, math.pi/2, math.pi)
        cr.arc(s * 0.17 + r, s * 0.46 + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.fill()

    # 2. LAYOUT & DISPLAY
    elif symbol_name in ("layout", "square.grid.2x2", "rectangle.split.2x1"):
        rw, rh = s * 0.78, s * 0.68
        rx = (s - rw) / 2.0
        ry = (s - rh) / 2.0
        cr.set_line_width(1.5)
        r = 2.4
        cr.new_sub_path()
        cr.arc(rx + rw - r, ry + r, r, -math.pi/2, 0)
        cr.arc(rx + rw - r, ry + rh - r, r, 0, math.pi/2)
        cr.arc(rx + r, ry + rh - r, r, math.pi/2, math.pi)
        cr.arc(rx + r, ry + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        cr.move_to(rx + rw * 0.46, ry + 1.0)
        cr.line_to(rx + rw * 0.46, ry + rh - 1.0)
        cr.stroke()

    elif symbol_name in ("iphone", "phone"):
        pw, ph = s * 0.48, s * 0.82
        px = (s - pw) / 2.0
        py = (s - ph) / 2.0
        cr.set_line_width(1.4)
        r = 2.8
        cr.new_sub_path()
        cr.arc(px + pw - r, py + r, r, -math.pi/2, 0)
        cr.arc(px + pw - r, py + ph - r, r, 0, math.pi/2)
        cr.arc(px + r, py + ph - r, r, math.pi/2, math.pi)
        cr.arc(px + r, py + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        cr.set_line_width(1.2)
        cr.move_to(px + pw * 0.32, py + ph - 2.5)
        cr.line_to(px + pw * 0.68, py + ph - 2.5)
        cr.stroke()

    elif symbol_name in ("macbook", "laptop"):
        sw, sh = s * 0.68, s * 0.48
        sx = (s - sw) / 2.0
        sy = s * 0.22
        cr.set_line_width(1.3)
        cr.rectangle(sx, sy, sw, sh)
        cr.stroke()
        cr.move_to(s * 0.08, sy + sh + 2.2)
        cr.line_to(s * 0.92, sy + sh + 2.2)
        cr.stroke()

    # 3. SIZE & RESIZE
    elif symbol_name in ("size", "arrow.up.left.and.arrow.down.right"):
        cr.set_line_width(1.5)
        # Top-left arrow
        cr.move_to(s * 0.22, s * 0.46)
        cr.line_to(s * 0.22, s * 0.22)
        cr.line_to(s * 0.46, s * 0.22)
        cr.stroke()
        cr.move_to(s * 0.22, s * 0.22)
        cr.line_to(s * 0.48, s * 0.48)
        cr.stroke()
        # Bottom-right arrow
        cr.move_to(s * 0.78, s * 0.54)
        cr.line_to(s * 0.78, s * 0.78)
        cr.line_to(s * 0.54, s * 0.78)
        cr.stroke()
        cr.move_to(s * 0.78, s * 0.78)
        cr.line_to(s * 0.52, s * 0.52)
        cr.stroke()

    # 4. THEME & PALETTE
    elif symbol_name in ("theme", "paintpalette"):
        cr.set_line_width(1.4)
        cr.new_sub_path()
        cr.move_to(s * 0.50, s * 0.14)
        cr.curve_to(s * 0.82, s * 0.14, s * 0.90, s * 0.48, s * 0.82, s * 0.74)
        cr.curve_to(s * 0.76, s * 0.90, s * 0.58, s * 0.90, s * 0.48, s * 0.80)
        cr.curve_to(s * 0.42, s * 0.72, s * 0.32, s * 0.72, s * 0.26, s * 0.80)
        cr.curve_to(s * 0.14, s * 0.90, s * 0.08, s * 0.60, s * 0.16, s * 0.34)
        cr.curve_to(s * 0.22, s * 0.18, s * 0.36, s * 0.14, s * 0.50, s * 0.14)
        cr.close_path()
        cr.stroke()
        cr.arc(s * 0.38, s * 0.32, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.58, s * 0.30, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.72, s * 0.48, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.60, s * 0.70, 1.6, 0, 2*math.pi)
        cr.stroke()

    elif symbol_name in ("sun.max", "sun"):
        cx, cy = s / 2.0, s / 2.0
        cr.arc(cx, cy, s * 0.18, 0, 2*math.pi)
        cr.fill()
        cr.set_line_width(1.3)
        for i in range(8):
            angle = i * (math.pi / 4)
            cr.move_to(cx + math.cos(angle) * s * 0.28, cy + math.sin(angle) * s * 0.28)
            cr.line_to(cx + math.cos(angle) * s * 0.42, cy + math.sin(angle) * s * 0.42)
            cr.stroke()

    elif symbol_name in ("moon.fill", "moon"):
        cx, cy = s * 0.48, s * 0.50
        cr.arc(cx, cy, s * 0.34, math.pi * 0.25, math.pi * 1.75)
        cr.arc_negative(cx + s * 0.18, cy, s * 0.28, math.pi * 1.6, math.pi * 0.4)
        cr.close_path()
        cr.fill()

    elif symbol_name in ("circle.lefthalf.filled", "auto"):
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        cr.set_line_width(1.4)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        cr.arc(cx, cy, r - 0.7, math.pi / 2, 3 * math.pi / 2)
        cr.close_path()
        cr.fill()

    # 5. SPARKLES & EFFECTS
    elif symbol_name in ("sparkles", "sparkle"):
        cx, cy = s * 0.44, s * 0.48
        r1, r2 = s * 0.34, s * 0.08
        cr.new_sub_path()
        for i in range(8):
            rad = r1 if i % 2 == 0 else r2
            ang = i * (math.pi / 4) - math.pi / 2
            x = cx + math.cos(ang) * rad
            y = cy + math.sin(ang) * rad
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.close_path()
        cr.fill()
        cr.arc(s * 0.80, s * 0.24, 1.2, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.18, s * 0.78, 0.9, 0, 2*math.pi)
        cr.fill()

    # 6. PIN & KEEP ON TOP
    elif symbol_name in ("pin", "pin.fill"):
        cr.save()
        cr.translate(s * 0.5, s * 0.5)
        cr.rotate(-math.pi / 4)
        cr.set_line_width(1.5)
        cr.rectangle(-3.0, -7.0, 6.0, 3.5)
        cr.fill()
        cr.rectangle(-4.5, -3.5, 9.0, 2.5)
        cr.fill()
        cr.move_to(-2.5, -1.0)
        cr.line_to(-1.5, 4.0)
        cr.line_to(1.5, 4.0)
        cr.line_to(2.5, -1.0)
        cr.close_path()
        cr.fill()
        cr.move_to(0, 4.0)
        cr.line_to(0, 8.5)
        cr.stroke()
        cr.restore()

    elif symbol_name in ("pin.slash", "unpin"):
        cr.save()
        cr.translate(s * 0.5, s * 0.5)
        cr.rotate(-math.pi / 4)
        cr.set_line_width(1.5)
        cr.rectangle(-3.0, -7.0, 6.0, 3.5)
        cr.stroke()
        cr.rectangle(-4.5, -3.5, 9.0, 2.5)
        cr.stroke()
        cr.move_to(0, 4.0)
        cr.line_to(0, 8.5)
        cr.stroke()
        # Slash
        cr.move_to(-6.0, -6.0)
        cr.line_to(6.0, 6.0)
        cr.stroke()
        cr.restore()

    # 7. RESET / RELOAD
    elif symbol_name in ("reset", "arrow.counterclockwise"):
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.32
        cr.set_line_width(1.6)
        cr.arc(cx, cy, r, -math.pi * 0.4, math.pi * 0.95)
        cr.stroke()
        ax = cx + math.cos(-math.pi * 0.4) * r
        ay = cy + math.sin(-math.pi * 0.4) * r
        cr.move_to(ax - 3.2, ay - 1.4)
        cr.line_to(ax, ay)
        cr.line_to(ax + 0.8, ay + 3.4)
        cr.stroke()

    # 8. HIDE / DELETE / CLOSE
    elif symbol_name in ("xmark", "hide", "close", "delete"):
        cr.set_line_width(2.0)
        pad = s * 0.24
        cr.move_to(pad, pad)
        cr.line_to(s - pad, s - pad)
        cr.stroke()
        cr.move_to(s - pad, pad)
        cr.line_to(pad, s - pad)
        cr.stroke()

    elif symbol_name in ("check", "checkmark"):
        cr.set_line_width(1.8)
        cr.move_to(s * 0.20, s * 0.52)
        cr.line_to(s * 0.42, s * 0.74)
        cr.line_to(s * 0.82, s * 0.26)
        cr.stroke()

    # 9. MUSIC, CLOCK, CALENDAR, WEATHER, BATTERY, PHOTO
    elif symbol_name == "music":
        cr.set_line_width(1.6)
        cr.save()
        cr.translate(s * 0.30, s * 0.72)
        cr.rotate(-math.pi / 6)
        cr.scale(1.3, 1.0)
        cr.arc(0, 0, 2.4, 0, 2*math.pi)
        cr.fill()
        cr.restore()
        cr.save()
        cr.translate(s * 0.70, s * 0.60)
        cr.rotate(-math.pi / 6)
        cr.scale(1.3, 1.0)
        cr.arc(0, 0, 2.4, 0, 2*math.pi)
        cr.fill()
        cr.restore()
        cr.move_to(s * 0.36, s * 0.70)
        cr.line_to(s * 0.36, s * 0.26)
        cr.line_to(s * 0.76, s * 0.16)
        cr.line_to(s * 0.76, s * 0.58)
        cr.stroke()
        cr.set_line_width(2.6)
        cr.move_to(s * 0.36, s * 0.26)
        cr.line_to(s * 0.76, s * 0.16)
        cr.stroke()

    elif symbol_name == "clock":
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        cr.set_line_width(1.5)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        cr.move_to(cx, cy)
        cr.line_to(cx, cy - r * 0.60)
        cr.stroke()
        cr.move_to(cx, cy)
        cr.line_to(cx + r * 0.50, cy)
        cr.stroke()

    elif symbol_name == "calendar":
        rw, rh = s * 0.72, s * 0.72
        rx = (s - rw) / 2.0
        ry = (s - rh) / 2.0
        cr.set_line_width(1.4)
        r = 2.4
        cr.new_sub_path()
        cr.arc(rx + rw - r, ry + r, r, -math.pi/2, 0)
        cr.arc(rx + rw - r, ry + rh - r, r, 0, math.pi/2)
        cr.arc(rx + r, ry + rh - r, r, math.pi/2, math.pi)
        cr.arc(rx + r, ry + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        cr.move_to(rx, ry + rh * 0.30)
        cr.line_to(rx + rw, ry + rh * 0.30)
        cr.stroke()
        cr.set_line_width(1.6)
        cr.move_to(rx + rw * 0.28, ry - 1.2)
        cr.line_to(rx + rw * 0.28, ry + 1.8)
        cr.stroke()
        cr.move_to(rx + rw * 0.72, ry - 1.2)
        cr.line_to(rx + rw * 0.72, ry + 1.8)
        cr.stroke()

    elif symbol_name == "battery":
        bw, bh = s * 0.68, s * 0.40
        bx = s * 0.12
        by = (s - bh) / 2.0
        cr.set_line_width(1.4)
        r = 2.2
        cr.new_sub_path()
        cr.arc(bx + bw - r, by + r, r, -math.pi/2, 0)
        cr.arc(bx + bw - r, by + bh - r, r, 0, math.pi/2)
        cr.arc(bx + r, by + bh - r, r, math.pi/2, math.pi)
        cr.arc(bx + r, by + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        cr.rectangle(bx + bw + 0.8, by + bh * 0.28, 1.8, bh * 0.44)
        cr.fill()
        cr.rectangle(bx + 2.2, by + 2.2, bw * 0.65, bh - 4.4)
        cr.fill()

    elif symbol_name == "cloud.sun":
        cr.arc(s * 0.66, s * 0.36, 3.2, 0, 2*math.pi)
        cr.fill()
        cr.set_line_width(1.4)
        cr.new_sub_path()
        cr.arc(s * 0.34, s * 0.64, 3.6, math.pi * 0.5, math.pi * 1.5)
        cr.arc(s * 0.48, s * 0.50, 4.2, math.pi * 1.0, math.pi * 1.9)
        cr.arc(s * 0.66, s * 0.60, 3.6, math.pi * 1.5, math.pi * 0.5)
        cr.close_path()
        cr.fill()

    elif symbol_name == "photo":
        rw, rh = s * 0.76, s * 0.64
        rx = (s - rw) / 2.0
        ry = (s - rh) / 2.0
        cr.set_line_width(1.4)
        cr.rectangle(rx, ry, rw, rh)
        cr.stroke()
        cr.arc(rx + rw * 0.30, ry + rh * 0.36, 1.6, 0, 2*math.pi)
        cr.fill()
        cr.move_to(rx + 1.2, ry + rh - 1.2)
        cr.line_to(rx + rw * 0.42, ry + rh * 0.46)
        cr.line_to(rx + rw * 0.65, ry + rh * 0.68)
        cr.line_to(rx + rw * 0.82, ry + rh * 0.52)
        cr.line_to(rx + rw - 1.2, ry + rh - 1.2)
        cr.close_path()
        cr.fill()

    elif symbol_name in ("crop", "aspectratio"):
        cr.set_line_width(1.5)
        cr.move_to(s * 0.15, s * 0.35)
        cr.line_to(s * 0.15, s * 0.15)
        cr.line_to(s * 0.35, s * 0.15)
        cr.stroke()
        cr.move_to(s * 0.85, s * 0.35)
        cr.line_to(s * 0.85, s * 0.15)
        cr.line_to(s * 0.65, s * 0.15)
        cr.stroke()
        cr.move_to(s * 0.15, s * 0.65)
        cr.line_to(s * 0.15, s * 0.85)
        cr.line_to(s * 0.35, s * 0.85)
        cr.stroke()
        cr.move_to(s * 0.85, s * 0.65)
        cr.line_to(s * 0.85, s * 0.85)
        cr.line_to(s * 0.65, s * 0.85)
        cr.stroke()

    elif symbol_name == "info.circle":
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        cr.set_line_width(1.4)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        cr.arc(cx, cy - r * 0.40, 1.1, 0, 2*math.pi)
        cr.fill()
        cr.set_line_width(1.5)
        cr.move_to(cx, cy - r * 0.10)
        cr.line_to(cx, cy + r * 0.45)
        cr.stroke()

    elif symbol_name in ("arrow.triangle.2.circlepath", "refresh"):
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.32
        cr.set_line_width(1.5)
        cr.arc(cx, cy, r, -math.pi * 0.3, math.pi * 0.6)
        cr.stroke()
        cr.arc(cx, cy, r, math.pi * 0.7, math.pi * 1.6)
        cr.stroke()
        ax = cx + math.cos(math.pi * 0.6) * r
        ay = cy + math.sin(math.pi * 0.6) * r
        cr.move_to(ax - 2.0, ay - 2.5)
        cr.line_to(ax, ay)
        cr.line_to(ax + 2.5, ay - 1.0)
        cr.stroke()

    # 10. SYSTEM ICONS (GEAR, BELL, CONTROLS, BOLT, TIMER, CLIPBOARD, GLOBE, POWER, LOCATION)
    elif symbol_name in ("globe", "language"):
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        cr.set_line_width(1.4)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        # Equator
        cr.move_to(cx - r, cy)
        cr.line_to(cx + r, cy)
        cr.stroke()
        # Meridian oval
        cr.save()
        cr.translate(cx, cy)
        cr.scale(0.5, 1.0)
        cr.arc(0, 0, r, 0, 2*math.pi)
        cr.stroke()
        cr.restore()

    elif symbol_name in ("location", "location.fill"):
        cr.save()
        cr.translate(s * 0.5, s * 0.5)
        cr.rotate(-math.pi / 4)
        cr.set_line_width(1.5)
        cr.move_to(0, -s * 0.40)
        cr.line_to(s * 0.35, s * 0.38)
        cr.line_to(0, s * 0.16)
        cr.line_to(-s * 0.35, s * 0.38)
        cr.close_path()
        cr.fill()
        cr.restore()

    elif symbol_name in ("bell", "bell.fill"):
        cr.set_line_width(1.4)
        # Clapper
        cr.arc(s / 2.0, s * 0.82, 1.4, 0, 2*math.pi)
        cr.fill()
        # Bell body
        cr.move_to(s * 0.5, s * 0.16)
        cr.arc(s * 0.5, s * 0.20, 1.2, math.pi, 0)
        cr.curve_to(s * 0.65, s * 0.35, s * 0.76, s * 0.55, s * 0.82, s * 0.72)
        cr.line_to(s * 0.18, s * 0.72)
        cr.curve_to(s * 0.24, s * 0.55, s * 0.35, s * 0.35, s * 0.5, s * 0.20)
        cr.close_path()
        cr.fill()

    elif symbol_name in ("gearshape", "gear", "settings"):
        cx, cy = s / 2.0, s / 2.0
        r_out = s * 0.40
        r_in = s * 0.28
        r_hole = s * 0.15
        teeth = 6
        cr.set_line_width(1.4)
        cr.new_sub_path()
        for i in range(teeth * 2):
            ang = i * (math.pi / teeth)
            r = r_out if (i % 2 == 0) else r_in
            x = cx + math.cos(ang) * r
            y = cy + math.sin(ang) * r
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.close_path()
        cr.fill()
        cr.arc(cx, cy, r_hole, 0, 2*math.pi)
        cr.set_source_rgba(0.10, 0.12, 0.16, 0.95)
        cr.fill()
        cr.set_source_rgb(*color)

    elif symbol_name in ("slider.horizontal.3", "controls"):
        cr.set_line_width(1.5)
        # 3 slider tracks
        y1, y2, y3 = s * 0.28, s * 0.50, s * 0.72
        cr.move_to(s * 0.16, y1); cr.line_to(s * 0.84, y1); cr.stroke()
        cr.move_to(s * 0.16, y2); cr.line_to(s * 0.84, y2); cr.stroke()
        cr.move_to(s * 0.16, y3); cr.line_to(s * 0.84, y3); cr.stroke()
        # Thumbs
        cr.arc(s * 0.38, y1, 2.2, 0, 2*math.pi); cr.fill()
        cr.arc(s * 0.68, y2, 2.2, 0, 2*math.pi); cr.fill()
        cr.arc(s * 0.32, y3, 2.2, 0, 2*math.pi); cr.fill()

    elif symbol_name in ("bolt", "bolt.fill"):
        cr.move_to(s * 0.56, s * 0.12)
        cr.line_to(s * 0.26, s * 0.52)
        cr.line_to(s * 0.48, s * 0.52)
        cr.line_to(s * 0.44, s * 0.88)
        cr.line_to(s * 0.74, s * 0.44)
        cr.line_to(s * 0.52, s * 0.44)
        cr.close_path()
        cr.fill()

    elif symbol_name in ("timer", "stopwatch"):
        cx, cy = s / 2.0, s * 0.54
        r = s * 0.36
        cr.set_line_width(1.4)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        # Button top
        cr.move_to(cx - 2.5, s * 0.12)
        cr.line_to(cx + 2.5, s * 0.12)
        cr.stroke()
        cr.move_to(cx, s * 0.12)
        cr.line_to(cx, cy - r)
        cr.stroke()
        # Hand
        cr.move_to(cx, cy)
        cr.line_to(cx + r * 0.55, cy - r * 0.55)
        cr.stroke()

    elif symbol_name in ("doc.on.clipboard", "clipboard"):
        rw, rh = s * 0.60, s * 0.68
        rx, ry = (s - rw) / 2.0, s * 0.24
        cr.set_line_width(1.4)
        r = 2.0
        cr.new_sub_path()
        cr.arc(rx + rw - r, ry + r, r, -math.pi/2, 0)
        cr.arc(rx + rw - r, ry + rh - r, r, 0, math.pi/2)
        cr.arc(rx + r, ry + rh - r, r, math.pi/2, math.pi)
        cr.arc(rx + r, ry + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        # Clip
        cr.rectangle(s * 0.38, s * 0.16, s * 0.24, s * 0.14)
        cr.fill()

    elif symbol_name in ("power", "poweroff"):
        cx, cy = s / 2.0, s * 0.54
        r = s * 0.36
        cr.set_line_width(1.8)
        cr.arc(cx, cy, r, -math.pi * 0.25, math.pi * 1.25)
        cr.stroke()
        cr.move_to(cx, s * 0.14)
        cr.line_to(cx, cy - 1.0)
        cr.stroke()

    elif symbol_name in ("circle.fill", "dot"):
        cx, cy = s / 2.0, s / 2.0
        cr.arc(cx, cy, s * 0.32, 0, 2*math.pi)
        cr.fill()

    elif symbol_name in ("square", "rectangle"):
        rw, rh = s * 0.68, s * 0.68
        rx, ry = (s - rw) / 2.0, (s - rh) / 2.0
        cr.set_line_width(1.4)
        r = 2.4
        cr.new_sub_path()
        cr.arc(rx + rw - r, ry + r, r, -math.pi/2, 0)
        cr.arc(rx + rw - r, ry + rh - r, r, 0, math.pi/2)
        cr.arc(rx + r, ry + rh - r, r, math.pi/2, math.pi)
        cr.arc(rx + r, ry + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()

    elif symbol_name in ("dot.circle", "target"):
        cx, cy = s / 2.0, s / 2.0
        cr.set_line_width(1.4)
        cr.arc(cx, cy, s * 0.38, 0, 2*math.pi)
        cr.stroke()
        cr.arc(cx, cy, s * 0.18, 0, 2*math.pi)
        cr.fill()

    else:
        # Default Apple dot
        cr.arc(s / 2.0, s / 2.0, 2.2, 0, 2*math.pi)
        cr.fill()

    pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, px, px)
    if scale > 1:
        pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)

    _SF_SYMBOL_CACHE[cache_key] = pixbuf
    return pixbuf


def create_mac_menu_item(icon_name: str = None, text: str = "", on_activate = None,
                         is_destructive: bool = False, is_checked: bool = False,
                         submenu: Gtk.Menu = None, icon_color: tuple = None) -> Gtk.MenuItem:
    """
    Creates an authentic macOS style Gtk.MenuItem with:
    - 16x16 vector SF Symbol on the left
    - Crisp Apple typography in the center
    - Optional checkmark or submenu
    """
    item = Gtk.MenuItem()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
    box.set_margin_start(4)
    box.set_margin_end(6)
    box.set_margin_top(3)
    box.set_margin_bottom(3)

    # 1. Left SF Symbol Icon
    if icon_name:
        if icon_color:
            color = icon_color
        else:
            color = (1.0, 0.27, 0.23) if is_destructive else (0.92, 0.94, 0.98)
        pb = get_sf_symbol_pixbuf(icon_name, size=15, color=color)
        img = Gtk.Image.new_from_pixbuf(pb)
        img.set_valign(Gtk.Align.CENTER)
        box.pack_start(img, False, False, 0)
    else:
        spacer = Gtk.Box()
        spacer.set_size_request(15, -1)
        box.pack_start(spacer, False, False, 0)

    # 2. Text Label (Safe markup escaping)
    lbl = Gtk.Label()
    lbl.set_xalign(0.0)
    lbl.set_valign(Gtk.Align.CENTER)
    color_hex = "#ff453a" if is_destructive else "#ffffff"
    safe_text = GLib.markup_escape_text(text)
    lbl.set_markup(f"<span font_desc='Inter, -apple-system, Ubuntu Medium 10pt' foreground='{color_hex}'>{safe_text}</span>")
    box.pack_start(lbl, True, True, 0)

    # 3. Optional Checkmark on the right
    if is_checked:
        chk_pb = get_sf_symbol_pixbuf("check", size=13, color=(0.10, 0.60, 1.0))
        chk_img = Gtk.Image.new_from_pixbuf(chk_pb)
        chk_img.set_valign(Gtk.Align.CENTER)
        box.pack_end(chk_img, False, False, 0)

    item.add(box)

    if on_activate:
        item.connect("activate", on_activate)

    if submenu:
        item.set_submenu(submenu)

    return item


def create_mac_context_menu() -> Gtk.Menu:
    """Creates a Gtk.Menu with authentic macOS dark frosted glass styling."""
    menu = Gtk.Menu()
    menu.get_style_context().add_class("macos-context-menu")

    css = b"""
    menu.macos-context-menu,
    .macos-context-menu menu {
        background-color: rgba(28, 28, 34, 0.96);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 10px;
        padding: 5px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.60);
    }
    menu.macos-context-menu menuitem,
    .macos-context-menu menuitem {
        border-radius: 6px;
        padding: 3px 6px;
        transition: background-color 100ms ease;
    }
    menu.macos-context-menu menuitem:hover,
    .macos-context-menu menuitem:hover {
        background-color: #007aff;
    }
    menu.macos-context-menu separator,
    .macos-context-menu separator {
        background-color: rgba(255, 255, 255, 0.12);
        margin: 5px 6px;
        min-height: 1px;
    }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    return menu
