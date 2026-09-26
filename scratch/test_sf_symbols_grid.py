import cairo
import math
import gi
import os

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

def draw_symbol(cr, symbol_name, s=24):
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    if symbol_name == "lock.open":
        bw, bh = s * 0.62, s * 0.44
        bx = (s - bw) / 2.0
        by = s - bh - 2.5
        r = 2.4
        # Rounded lock body
        cr.new_sub_path()
        cr.arc(bx + bw - r, by + r, r, -math.pi/2, 0)
        cr.arc(bx + bw - r, by + bh - r, r, 0, math.pi/2)
        cr.arc(bx + r, by + bh - r, r, math.pi/2, math.pi)
        cr.arc(bx + r, by + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.fill()
        # Open Shackle (Left stem goes up, curves right, ends open higher)
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

    elif symbol_name == "lock.all":
        # Apple SF Symbol: square.grid.2x2 or dual locks
        # Front lock
        bw, bh = s * 0.48, s * 0.36
        bx, by = s * 0.14, s * 0.52
        cr.rectangle(bx, by, bw, bh)
        cr.fill()
        cr.set_line_width(1.5)
        cr.arc(bx + bw * 0.5, by, bw * 0.32, math.pi, 0)
        cr.stroke()
        # Back lock outline
        bx2, by2 = s * 0.38, s * 0.34
        cr.set_line_width(1.3)
        cr.rectangle(bx2, by2, bw, bh)
        cr.stroke()
        cr.arc(bx2 + bw * 0.5, by2, bw * 0.32, math.pi, 0)
        cr.stroke()

    elif symbol_name == "layout":
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

    elif symbol_name == "size":
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

    elif symbol_name == "paintpalette":
        # Apple SF Symbol: paintpalette
        cr.set_line_width(1.4)
        cr.new_sub_path()
        # Organic kidney palette
        cr.move_to(s * 0.50, s * 0.14)
        cr.curve_to(s * 0.82, s * 0.14, s * 0.90, s * 0.48, s * 0.82, s * 0.74)
        cr.curve_to(s * 0.76, s * 0.90, s * 0.58, s * 0.90, s * 0.48, s * 0.80)
        cr.curve_to(s * 0.42, s * 0.72, s * 0.32, s * 0.72, s * 0.26, s * 0.80)
        cr.curve_to(s * 0.14, s * 0.90, s * 0.08, s * 0.60, s * 0.16, s * 0.34)
        cr.curve_to(s * 0.22, s * 0.18, s * 0.36, s * 0.14, s * 0.50, s * 0.14)
        cr.close_path()
        cr.stroke()
        # 3 paint drops
        cr.arc(s * 0.38, s * 0.32, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.58, s * 0.30, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.72, s * 0.48, 1.3, 0, 2*math.pi)
        cr.fill()
        # Thumb hole
        cr.arc(s * 0.60, s * 0.70, 1.6, 0, 2*math.pi)
        cr.stroke()

    elif symbol_name == "sparkles":
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
        cr.arc(s * 0.80, s * 0.24, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(s * 0.18, s * 0.78, 1.0, 0, 2*math.pi)
        cr.fill()

    elif symbol_name == "pin":
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

    elif symbol_name == "reset":
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

    elif symbol_name == "xmark":
        cr.set_line_width(2.0)
        pad = s * 0.24
        cr.move_to(pad, pad)
        cr.line_to(s - pad, s - pad)
        cr.stroke()
        cr.move_to(s - pad, pad)
        cr.line_to(pad, s - pad)
        cr.stroke()

    elif symbol_name == "music":
        # Apple SF Symbol: music.note (double eighth note with beam)
        cr.set_line_width(1.6)
        # Note 1
        cr.save()
        cr.translate(s * 0.30, s * 0.72)
        cr.rotate(-math.pi / 6)
        cr.scale(1.3, 1.0)
        cr.arc(0, 0, 2.4, 0, 2*math.pi)
        cr.fill()
        cr.restore()
        # Note 2
        cr.save()
        cr.translate(s * 0.70, s * 0.60)
        cr.rotate(-math.pi / 6)
        cr.scale(1.3, 1.0)
        cr.arc(0, 0, 2.4, 0, 2*math.pi)
        cr.fill()
        cr.restore()
        # Stems and beam
        cr.move_to(s * 0.36, s * 0.70)
        cr.line_to(s * 0.36, s * 0.26)
        cr.line_to(s * 0.76, s * 0.16)
        cr.line_to(s * 0.76, s * 0.58)
        cr.stroke()
        # Thick beam
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
        # Hour & minute hands
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
        # Top red/filled header bar
        cr.move_to(rx, ry + rh * 0.30)
        cr.line_to(rx + rw, ry + rh * 0.30)
        cr.stroke()
        # Binder rings
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
        # Terminal nub
        cr.rectangle(bx + bw + 0.8, by + bh * 0.28, 1.8, bh * 0.44)
        cr.fill()
        # Fill bars inside
        cr.rectangle(bx + 2.2, by + 2.2, bw * 0.65, bh - 4.4)
        cr.fill()

    elif symbol_name == "cloud.sun":
        # Sun
        cr.arc(s * 0.66, s * 0.36, 3.2, 0, 2*math.pi)
        cr.fill()
        # Cloud
        cr.set_line_width(1.4)
        cr.new_sub_path()
        cr.arc(s * 0.34, s * 0.64, 3.6, math.pi * 0.5, math.pi * 1.5)
        cr.arc(s * 0.48, s * 0.50, 4.2, math.pi * 1.0, math.pi * 1.9)
        cr.arc(s * 0.66, s * 0.60, 3.6, math.pi * 1.5, math.pi * 0.5)
        cr.close_path()
        cr.fill()

    elif symbol_name == "photo":
        # Photo frame
        rw, rh = s * 0.76, s * 0.64
        rx = (s - rw) / 2.0
        ry = (s - rh) / 2.0
        cr.set_line_width(1.4)
        cr.rectangle(rx, ry, rw, rh)
        cr.stroke()
        # Sun circle
        cr.arc(rx + rw * 0.30, ry + rh * 0.36, 1.6, 0, 2*math.pi)
        cr.fill()
        # Mountains
        cr.move_to(rx + 1.2, ry + rh - 1.2)
        cr.line_to(rx + rw * 0.42, ry + rh * 0.46)
        cr.line_to(rx + rw * 0.65, ry + rh * 0.68)
        cr.line_to(rx + rw * 0.82, ry + rh * 0.52)
        cr.line_to(rx + rw - 1.2, ry + rh - 1.2)
        cr.close_path()
        cr.fill()

    elif symbol_name == "info.circle":
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        cr.set_line_width(1.4)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        # 'i'
        cr.arc(cx, cy - r * 0.40, 1.1, 0, 2*math.pi)
        cr.fill()
        cr.set_line_width(1.5)
        cr.move_to(cx, cy - r * 0.10)
        cr.line_to(cx, cy + r * 0.45)
        cr.stroke()

    else:
        # Default dot
        cr.arc(s / 2.0, s / 2.0, 2.5, 0, 2*math.pi)
        cr.fill()


# Render a sprite sheet to check all icons
icons = [
    "lock.open", "lock", "lock.all", "layout", "size", "paintpalette",
    "sparkles", "pin", "reset", "xmark", "music", "clock",
    "calendar", "battery", "cloud.sun", "photo", "info.circle"
]

cols = 6
rows = math.ceil(len(icons) / cols)
icon_sz = 32
pad = 12
w = cols * (icon_sz + pad) + pad
h = rows * (icon_sz + pad) + pad

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
cr = cairo.Context(surface)
cr.set_source_rgb(0.12, 0.13, 0.16)
cr.paint()

for idx, name in enumerate(icons):
    r_idx = idx // cols
    c_idx = idx % cols
    x = pad + c_idx * (icon_sz + pad)
    y = pad + r_idx * (icon_sz + pad)

    # background slot
    cr.set_source_rgba(1, 1, 1, 0.06)
    cr.rectangle(x, y, icon_sz, icon_sz)
    cr.fill()

    cr.save()
    cr.translate(x, y)
    if name == "xmark":
        cr.set_source_rgb(1.0, 0.27, 0.23)
    elif name == "sparkles":
        cr.set_source_rgb(1.0, 0.84, 0.04)
    else:
        cr.set_source_rgb(0.92, 0.94, 0.98)
    draw_symbol(cr, name, s=icon_sz)
    cr.restore()

out_path = "/home/tramvo/.gemini/antigravity-ide/brain/67c4e8d3-62be-4941-a87e-c74568edb578/all_sf_symbols.png"
surface.write_to_png(out_path)
print("Saved all symbols to:", out_path)
