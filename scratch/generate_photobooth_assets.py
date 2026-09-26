"""
Generates pixel-perfect, high-resolution PNG image assets for macOS Photo Booth.
Creates:
- mode_single.png
- mode_burst.png
- mode_video.png
- icon_continuity.png
- icon_effects.png
- icon_source.png
- icon_filmstrip_empty.png
- 9 Effect Thumbnails: fx_normal, fx_mirror, fx_comic, fx_sepia, fx_bw, fx_thermal, fx_popart, fx_negative, fx_alien
"""

import os
import math
import cairo
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

ASSETS_DIR = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth"
AVATAR_PATH = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/avatars/emoji_student.png"
os.makedirs(ASSETS_DIR, exist_ok=True)

def draw_mode_single():
    """Single photo mode icon: Single photo frame / camera."""
    size = 72
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    # Frame outer
    w, h = 48, 38
    x, y = (size - w) / 2, (size - h) / 2
    r = 6.0

    # Camera body
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

    cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
    cr.set_line_width(3.2)
    cr.stroke()

    # Camera lens circle
    cr.arc(size / 2, size / 2, 9, 0, 2 * math.pi)
    cr.set_line_width(3.2)
    cr.stroke()

    # Flash dot
    cr.arc(x + w - 9, y + 9, 2.5, 0, 2 * math.pi)
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
    cr.fill()

    surface.write_to_png(os.path.join(ASSETS_DIR, "mode_single.png"))

def draw_mode_burst():
    """4-Up mode icon: 2x2 grid of photo frames."""
    size = 72
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    w, h = 18, 18
    gap = 6
    total_w = w * 2 + gap
    x0 = (size - total_w) / 2
    y0 = (size - total_w) / 2
    r = 4.0

    cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
    for row in range(2):
        for col in range(2):
            bx = x0 + col * (w + gap)
            by = y0 + row * (h + gap)
            cr.new_sub_path()
            cr.arc(bx + w - r, by + r, r, -math.pi / 2, 0)
            cr.arc(bx + w - r, by + h - r, r, 0, math.pi / 2)
            cr.arc(bx + r, by + h - r, r, math.pi / 2, math.pi)
            cr.arc(bx + r, by + r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.set_line_width(2.8)
            cr.stroke()

    surface.write_to_png(os.path.join(ASSETS_DIR, "mode_burst.png"))

def draw_mode_video():
    """Video mode icon: Camcorder / film camera."""
    size = 72
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    # Main camera body
    w, h = 34, 26
    x, y = 14, (size - h) / 2
    r = 6.0

    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

    cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
    cr.set_line_width(3.2)
    cr.stroke()

    # Video lens cone (trapezoid on right)
    cr.move_to(x + w + 2, size / 2 - 4)
    cr.line_to(x + w + 16, size / 2 - 12)
    cr.line_to(x + w + 16, size / 2 + 12)
    cr.line_to(x + w + 2, size / 2 + 4)
    cr.close_path()
    cr.fill()

    surface.write_to_png(os.path.join(ASSETS_DIR, "mode_video.png"))

def draw_icon_continuity():
    """Continuity Camera: Phone with camera and wireless waves."""
    size = 64
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    # Phone body
    pw, ph = 26, 42
    px = (size - pw) / 2
    py = (size - ph) / 2
    pr = 6.0

    cr.new_sub_path()
    cr.arc(px + pw - pr, py + pr, pr, -math.pi / 2, 0)
    cr.arc(px + pw - pr, py + ph - pr, pr, 0, math.pi / 2)
    cr.arc(px + pr, py + ph - pr, pr, math.pi / 2, math.pi)
    cr.arc(px + pr, py + pr, pr, math.pi, 3 * math.pi / 2)
    cr.close_path()

    cr.set_source_rgb(0.0, 0.48, 1.0)
    cr.fill_preserve()
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.4)
    cr.set_line_width(1.5)
    cr.stroke()

    # Camera lens on phone
    cr.arc(size / 2, py + 14, 5.5, 0, 2 * math.pi)
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.fill()

    # Home indicator bar
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.8)
    cr.set_line_width(2.0)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(px + 8, py + ph - 6)
    cr.line_to(px + pw - 8, py + ph - 6)
    cr.stroke()

    surface.write_to_png(os.path.join(ASSETS_DIR, "icon_continuity.png"))

def draw_icon_effects():
    """Apple Sparkles Magic Icon."""
    size = 64
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    def draw_star(cx, cy, r_out, r_in):
        cr.new_sub_path()
        for i in range(8):
            r = r_out if i % 2 == 0 else r_in
            angle = i * (math.pi / 4) - math.pi / 2
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.close_path()
        cr.fill()

    # Big golden sparkle
    cr.set_source_rgb(1.0, 0.84, 0.0)
    draw_star(30, 32, 18, 5)

    # Small top right sparkle
    cr.set_source_rgb(1.0, 0.92, 0.3)
    draw_star(48, 18, 10, 3)

    # Mini bottom left sparkle
    draw_star(16, 48, 8, 2.5)

    surface.write_to_png(os.path.join(ASSETS_DIR, "icon_effects.png"))

def draw_icon_source():
    """Camera aperture icon."""
    size = 64
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    cx, cy, r = size / 2, size / 2, 20
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
    cr.set_line_width(3.0)
    cr.stroke()

    # Blades
    for i in range(6):
        a = i * (2 * math.pi / 6)
        x1 = cx + r * math.cos(a)
        y1 = cy + r * math.sin(a)
        a2 = a + 0.8
        x2 = cx + (r * 0.45) * math.cos(a2)
        y2 = cy + (r * 0.45) * math.sin(a2)
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        cr.stroke()

    surface.write_to_png(os.path.join(ASSETS_DIR, "icon_source.png"))

def draw_icon_filmstrip_empty():
    """Empty state graphic: 3 filmstrip frames."""
    size = 96
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)

    w, h = 64, 44
    x, y = (size - w) / 2, (size - h) / 2
    r = 8.0

    # Card
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

    cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
    cr.fill_preserve()
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.3)
    cr.set_line_width(2.0)
    cr.stroke()

    # Camera glyph in center
    cr.arc(size / 2, size / 2, 10, 0, 2 * math.pi)
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.5)
    cr.set_line_width(2.5)
    cr.stroke()

    surface.write_to_png(os.path.join(ASSETS_DIR, "icon_filmstrip_empty.png"))

def generate_effect_thumbnails():
    """Generates 9 high-quality effect preview tiles using avatar image."""
    base_img = None
    if os.path.exists(AVATAR_PATH):
        base_img = Image.open(AVATAR_PATH).convert("RGBA")
    else:
        # Create a cute character face
        base_img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))

    tile_size = (120, 100)
    avatar = base_img.resize((84, 84), Image.Resampling.LANCZOS)

    def create_card_base(bg_color=(36, 36, 40)):
        card = Image.new("RGBA", tile_size, (0, 0, 0, 0))
        # Draw rounded rectangle card
        # Paste centered avatar
        dx = (tile_size[0] - avatar.width) // 2
        dy = (tile_size[1] - avatar.height) // 2
        return card, dx, dy

    # 1. Normal
    card, dx, dy = create_card_base()
    card.paste(avatar, (dx, dy), avatar)
    card.save(os.path.join(ASSETS_DIR, "fx_normal.png"))

    # 2. Mirror
    card, dx, dy = create_card_base()
    left_half = avatar.crop((0, 0, avatar.width // 2, avatar.height))
    mirrored_right = ImageOps.mirror(left_half)
    mirrored = Image.new("RGBA", avatar.size)
    mirrored.paste(left_half, (0, 0))
    mirrored.paste(mirrored_right, (avatar.width // 2, 0))
    card.paste(mirrored, (dx, dy), avatar)
    card.save(os.path.join(ASSETS_DIR, "fx_mirror.png"))

    # 3. Comic
    card, dx, dy = create_card_base()
    # High contrast & edges
    comic = avatar.filter(ImageFilter.EDGE_ENHANCE_MORE)
    comic = ImageEnhance.Contrast(comic).enhance(2.2)
    card.paste(comic, (dx, dy), avatar)
    card.save(os.path.join(ASSETS_DIR, "fx_comic.png"))

    # 4. Sepia
    card, dx, dy = create_card_base()
    gray = ImageOps.grayscale(avatar)
    sepia = ImageOps.colorize(gray, "#2e1c0c", "#f0d4b0")
    sepia_rgba = sepia.convert("RGBA")
    sepia_rgba.putalpha(avatar.split()[3])
    card.paste(sepia_rgba, (dx, dy), sepia_rgba)
    card.save(os.path.join(ASSETS_DIR, "fx_sepia.png"))

    # 5. Black & White
    card, dx, dy = create_card_base()
    bw = ImageOps.grayscale(avatar)
    bw = ImageEnhance.Contrast(bw).enhance(1.8)
    bw_rgba = bw.convert("RGBA")
    bw_rgba.putalpha(avatar.split()[3])
    card.paste(bw_rgba, (dx, dy), bw_rgba)
    card.save(os.path.join(ASSETS_DIR, "fx_bw.png"))

    # 6. Thermal
    card, dx, dy = create_card_base()
    gray = ImageOps.grayscale(avatar)
    thermal = ImageOps.colorize(gray, "#0000ff", "#ff0000", mid="#ffff00")
    thermal_rgba = thermal.convert("RGBA")
    thermal_rgba.putalpha(avatar.split()[3])
    card.paste(thermal_rgba, (dx, dy), thermal_rgba)
    card.save(os.path.join(ASSETS_DIR, "fx_thermal.png"))

    # 7. Pop Art (4 quadrants)
    card, dx, dy = create_card_base()
    qw, qh = avatar.width // 2, avatar.height // 2
    small_gray = ImageOps.grayscale(avatar.resize((qw, qh), Image.Resampling.LANCZOS))
    q1 = ImageOps.colorize(small_gray, "#002080", "#ff007f")
    q2 = ImageOps.colorize(small_gray, "#006000", "#00ffff")
    q3 = ImageOps.colorize(small_gray, "#600060", "#ffff00")
    q4 = ImageOps.colorize(small_gray, "#802000", "#00ff80")

    popart = Image.new("RGBA", avatar.size)
    popart.paste(q1, (0, 0))
    popart.paste(q2, (qw, 0))
    popart.paste(q3, (0, qh))
    popart.paste(q4, (qw, qh))
    popart.putalpha(avatar.split()[3])
    card.paste(popart, (dx, dy), popart)
    card.save(os.path.join(ASSETS_DIR, "fx_popart.png"))

    # 8. Negative
    card, dx, dy = create_card_base()
    rgb_inv = ImageOps.invert(avatar.convert("RGB"))
    inv_rgba = rgb_inv.convert("RGBA")
    inv_rgba.putalpha(avatar.split()[3])
    card.paste(inv_rgba, (dx, dy), inv_rgba)
    card.save(os.path.join(ASSETS_DIR, "fx_negative.png"))

    # 9. Alien (Neon Toxic Green)
    card, dx, dy = create_card_base()
    gray = ImageOps.grayscale(avatar)
    alien = ImageOps.colorize(gray, "#021a08", "#39ff14", mid="#00b33c")
    alien_rgba = alien.convert("RGBA")
    alien_rgba.putalpha(avatar.split()[3])
    card.paste(alien_rgba, (dx, dy), alien_rgba)
    card.save(os.path.join(ASSETS_DIR, "fx_alien.png"))

    print("[PhotoBooth] Generated all 9 effect thumbnail image assets!")

if __name__ == "__main__":
    draw_mode_single()
    draw_mode_burst()
    draw_mode_video()
    draw_icon_continuity()
    draw_icon_effects()
    draw_icon_source()
    draw_icon_filmstrip_empty()
    generate_effect_thumbnails()
    print("[PhotoBooth] All image assets created successfully in", ASSETS_DIR)
