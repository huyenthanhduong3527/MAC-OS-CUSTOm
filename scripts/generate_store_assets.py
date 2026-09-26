#!/usr/bin/env python3
"""
Generate authentic, high-resolution icons for macOS App Store:
1. 21 Categories icons (48x48) into assets/category_icons/
2. 6 Featured Apps squircle icons (128x128) into assets/app_icons/
"""

import os
import math
import cairo

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT_DIR = os.path.join(BASE_DIR, "assets", "category_icons")
APP_DIR = os.path.join(BASE_DIR, "assets", "app_icons")

os.makedirs(CAT_DIR, exist_ok=True)
os.makedirs(APP_DIR, exist_ok=True)

def draw_squircle(cr, x, y, w, h, r):
    """Draw smooth squircle rounded rectangle."""
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi/2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi/2)
    cr.arc(x + r, y + h - r, r, math.pi/2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3*math.pi/2)
    cr.close_path()

# =========================================================================
# 1. GENERATE 6 FEATURED APPS (128x128 SQUIRCLES)
# =========================================================================

def generate_viator():
    """Viator: Emerald green with stylized white 'V' loop and dot."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)

    draw_squircle(cr, 4, 4, 120, 120, 26)
    cr.set_source_rgb(0.06, 0.50, 0.38) # #0f8061
    cr.fill()

    # White stylized 'V' with circle/dot
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.set_line_width(12)
    cr.set_line_cap(cairo.LineCap.ROUND)
    cr.set_line_join(cairo.LineJoin.ROUND)

    cr.move_to(44, 48)
    cr.line_to(64, 88)
    cr.line_to(76, 62)
    cr.stroke()

    # Dot beside V
    cr.arc(88, 50, 6.5, 0, 2 * math.pi)
    cr.fill()

    surf.write_to_png(os.path.join(APP_DIR, "viator.png"))

def generate_omnifocus():
    """OmniFocus 4: Deep obsidian squircle with vibrant purple checkmark."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)

    draw_squircle(cr, 4, 4, 120, 120, 26)
    cr.set_source_rgb(0.11, 0.08, 0.16) # #1c152a
    cr.fill()

    # Glowing purple checkmark
    cr.set_line_width(15)
    cr.set_line_cap(cairo.LineCap.ROUND)
    cr.set_line_join(cairo.LineJoin.ROUND)

    # Outer glow
    cr.set_source_rgba(0.58, 0.25, 0.98, 0.4)
    cr.move_to(38, 64)
    cr.line_to(56, 82)
    cr.line_to(92, 46)
    cr.stroke()

    # Vibrant core
    cr.set_line_width(13)
    cr.set_source_rgb(0.60, 0.28, 0.96) # #9947f5
    cr.move_to(38, 64)
    cr.line_to(56, 82)
    cr.line_to(92, 46)
    cr.stroke()

    surf.write_to_png(os.path.join(APP_DIR, "omnifocus.png"))

def generate_headspace():
    """Headspace: Warm orange smiling circle inside squircle."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)

    # White squircle background
    draw_squircle(cr, 4, 4, 120, 120, 26)
    cr.set_source_rgb(0.98, 0.98, 0.99)
    cr.fill()

    # Big cheerful orange circle
    cr.arc(64, 64, 46, 0, 2 * math.pi)
    cr.set_source_rgb(0.96, 0.49, 0.14) # #f47e24
    cr.fill()

    # Calm happy curve smile
    cr.set_source_rgb(0.20, 0.12, 0.05)
    cr.set_line_width(4.5)
    cr.set_line_cap(cairo.LineCap.ROUND)
    cr.arc(64, 62, 16, 0.2 * math.pi, 0.8 * math.pi)
    cr.stroke()

    surf.write_to_png(os.path.join(APP_DIR, "headspace.png"))

def generate_planta():
    """Planta: Deep forest green squircle with clean white text Planta."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)

    draw_squircle(cr, 4, 4, 120, 120, 26)
    cr.set_source_rgb(0.14, 0.32, 0.20) # #245233
    cr.fill()

    # Crisp Planta typography
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.select_font_face("SF Pro Text, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(25)
    xb, yb, w, h, _, _ = cr.text_extents("Planta")
    cr.move_to(64 - w/2 - xb, 64 + h/2)
    cr.show_text("Planta")

    surf.write_to_png(os.path.join(APP_DIR, "planta.png"))

def generate_trello():
    """Trello: Classic sky blue squircle with two white card boards."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)

    draw_squircle(cr, 4, 4, 120, 120, 26)
    cr.set_source_rgb(0.00, 0.47, 0.75) # #0079bf
    cr.fill()

    # Left column board (tall)
    draw_squircle(cr, 36, 34, 24, 60, 5)
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.fill()

    # Right column board (medium)
    draw_squircle(cr, 68, 34, 24, 42, 5)
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.fill()

    surf.write_to_png(os.path.join(APP_DIR, "trello.png"))

def generate_noted():
    """Noted: Vibrant coral red squircle with stylized 'N.' logo."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)

    draw_squircle(cr, 4, 4, 120, 120, 26)
    # Red gradient
    pat = cairo.LinearGradient(0, 0, 128, 128)
    pat.add_color_stop_rgb(0.0, 0.94, 0.22, 0.35) # #f03859
    pat.add_color_stop_rgb(1.0, 0.82, 0.15, 0.28)
    cr.set_source(pat)
    cr.fill()

    # Stylized bold 'N.'
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.select_font_face("SF Pro Display, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(68)
    xb, yb, w, h, _, _ = cr.text_extents("N.")
    cr.move_to(64 - w/2 - xb, 64 + h/2)
    cr.show_text("N.")

    surf.write_to_png(os.path.join(APP_DIR, "noted.png"))

# =========================================================================
# 2. GENERATE 21 CATEGORIES ICONS (48x48)
# =========================================================================

def create_cat_icon(filename, draw_fn):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 48, 48)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)
    draw_fn(cr)
    surf.write_to_png(os.path.join(CAT_DIR, filename))

# 1. Business: Brown leather briefcase
def cat_business(cr):
    # Main briefcase body
    draw_squircle(cr, 8, 16, 32, 24, 4)
    cr.set_source_rgb(0.68, 0.48, 0.30)
    cr.fill()
    # Handle
    cr.set_line_width(3)
    cr.set_source_rgb(0.50, 0.32, 0.18)
    cr.arc(24, 16, 6, math.pi, 2*math.pi)
    cr.stroke()
    # Clasp
    cr.set_source_rgb(0.92, 0.78, 0.35)
    cr.rectangle(21, 24, 6, 5)
    cr.fill()
    # Straps
    cr.set_source_rgb(0.55, 0.36, 0.20)
    cr.rectangle(13, 16, 3, 24)
    cr.rectangle(32, 16, 3, 24)
    cr.fill()

# 2. Developer Tools: Blue crossed wrench and screwdriver
def cat_developer(cr):
    cr.save()
    cr.translate(24, 24)
    cr.set_source_rgb(0.08, 0.58, 0.98)
    # Wrench
    cr.rotate(math.pi / 4)
    cr.rectangle(-3, -16, 6, 32)
    cr.arc(0, -14, 7, 0, 2*math.pi)
    cr.arc(0, 14, 7, 0, 2*math.pi)
    cr.fill()
    # Screwdriver
    cr.rotate(-math.pi / 2)
    cr.rectangle(-3, -16, 6, 20)
    cr.rectangle(-4.5, 4, 9, 12)
    cr.fill()
    cr.restore()

# 3. Education: Slate graduation cap
def cat_education(cr):
    # Mortarboard rhombus
    cr.set_source_rgb(0.38, 0.42, 0.48)
    cr.move_to(24, 12)
    cr.line_to(44, 22)
    cr.line_to(24, 30)
    cr.line_to(4, 22)
    cr.close_path()
    cr.fill()
    # Skullcap
    cr.arc(24, 28, 10, 0, math.pi)
    cr.fill()
    # Tassel
    cr.set_source_rgb(0.85, 0.70, 0.25)
    cr.set_line_width(2)
    cr.move_to(24, 22)
    cr.line_to(10, 28)
    cr.line_to(10, 36)
    cr.stroke()

# 4. Entertainment: Popcorn box
def cat_entertainment(cr):
    # Popcorn on top
    cr.set_source_rgb(0.98, 0.85, 0.30)
    for cx, cy in [(18, 14), (24, 12), (30, 14), (20, 18), (28, 18)]:
        cr.arc(cx, cy, 5, 0, 2*math.pi)
        cr.fill()
    # Red box
    cr.move_to(12, 20)
    cr.line_to(36, 20)
    cr.line_to(32, 40)
    cr.line_to(16, 40)
    cr.close_path()
    cr.set_source_rgb(0.92, 0.20, 0.20)
    cr.fill()
    # White stripes
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.move_to(19, 20); cr.line_to(22, 20); cr.line_to(21, 40); cr.line_to(18, 40); cr.fill()
    cr.move_to(26, 20); cr.line_to(29, 20); cr.line_to(28, 40); cr.line_to(25, 40); cr.fill()

# 5. Finance: Green credit card & wallet
def cat_finance(cr):
    # Card / Wallet
    draw_squircle(cr, 8, 14, 32, 22, 4)
    cr.set_source_rgb(0.20, 0.70, 0.35)
    cr.fill()
    # Magnetic stripe / band
    cr.set_source_rgb(0.12, 0.48, 0.22)
    cr.rectangle(8, 19, 32, 5)
    cr.fill()
    # Chip
    cr.set_source_rgb(0.95, 0.85, 0.40)
    draw_squircle(cr, 12, 27, 6, 5, 1.5)
    cr.fill()

# 6. Games: Blue/orange rocket
def cat_games(cr):
    cr.save()
    cr.translate(24, 24)
    cr.rotate(-math.pi / 4)
    # Rocket body
    cr.set_source_rgb(0.12, 0.60, 0.98)
    cr.arc(0, -6, 8, math.pi, 2*math.pi)
    cr.line_to(8, 12)
    cr.line_to(-8, 12)
    cr.close_path()
    cr.fill()
    # Thruster flame
    cr.set_source_rgb(0.98, 0.55, 0.15)
    cr.move_to(-5, 12)
    cr.line_to(0, 22)
    cr.line_to(5, 12)
    cr.close_path()
    cr.fill()
    # Porthole
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.arc(0, 0, 3.5, 0, 2*math.pi)
    cr.fill()
    cr.restore()

# 7. Graphics & Design: Geometric fan / color palette
def cat_graphics(cr):
    colors = [
        (0.95, 0.25, 0.25),
        (0.98, 0.60, 0.15),
        (0.98, 0.82, 0.20),
        (0.25, 0.75, 0.35),
        (0.15, 0.60, 0.98),
        (0.65, 0.30, 0.85)
    ]
    for i, (r, g, b) in enumerate(colors):
        ang = math.pi * (1.1 + i * 0.16)
        cr.save()
        cr.translate(24, 30)
        cr.rotate(ang)
        draw_squircle(cr, -3, 0, 6, 18, 3)
        cr.set_source_rgb(r, g, b)
        cr.fill()
        cr.restore()

# 8. Health & Fitness: Green running figure
def cat_health(cr):
    cr.set_source_rgb(0.20, 0.78, 0.30)
    # Head
    cr.arc(28, 12, 4.5, 0, 2*math.pi)
    cr.fill()
    # Torso & limbs
    cr.set_line_width(3.8)
    cr.set_line_cap(cairo.LineCap.ROUND)
    # Body
    cr.move_to(26, 17); cr.line_to(22, 28)
    cr.stroke()
    # Legs
    cr.move_to(22, 28); cr.line_to(16, 38)
    cr.move_to(22, 28); cr.line_to(32, 33); cr.line_to(34, 40)
    cr.stroke()
    # Arms
    cr.move_to(25, 20); cr.line_to(34, 18)
    cr.move_to(25, 20); cr.line_to(16, 24); cr.line_to(12, 20)
    cr.stroke()

# 9. Lifestyle: Red armchair
def cat_lifestyle(cr):
    cr.set_source_rgb(0.88, 0.22, 0.24)
    # Seat
    draw_squircle(cr, 12, 22, 24, 12, 3)
    cr.fill()
    # Backrest
    draw_squircle(cr, 15, 12, 18, 14, 4)
    cr.fill()
    # Armrests
    draw_squircle(cr, 10, 20, 5, 12, 2)
    draw_squircle(cr, 33, 20, 5, 12, 2)
    cr.fill()
    # Wooden legs
    cr.set_source_rgb(0.45, 0.28, 0.15)
    cr.set_line_width(2.5)
    cr.move_to(14, 34); cr.line_to(11, 42)
    cr.move_to(34, 34); cr.line_to(37, 42)
    cr.stroke()

# 10. Medical: Purple stethoscope
def cat_medical(cr):
    cr.set_source_rgb(0.60, 0.30, 0.88)
    cr.set_line_width(3)
    cr.set_line_cap(cairo.LineCap.ROUND)
    # Stethoscope tubes
    cr.arc(24, 20, 11, 0, math.pi)
    cr.stroke()
    cr.move_to(24, 31); cr.line_to(24, 36)
    cr.stroke()
    # Bell
    cr.arc(24, 38, 5, 0, 2*math.pi)
    cr.fill()
    # Earpieces
    cr.move_to(13, 20); cr.line_to(13, 14)
    cr.move_to(35, 20); cr.line_to(35, 14)
    cr.stroke()

# 11. Music: Connected eighth notes
def cat_music(cr):
    cr.set_source_rgb(0.15, 0.65, 0.95)
    # Left note head
    cr.arc(16, 32, 5, 0, 2*math.pi)
    cr.fill()
    # Right note head
    cr.arc(32, 28, 5, 0, 2*math.pi)
    cr.fill()
    # Stems
    cr.set_line_width(3.2)
    cr.move_to(20, 32); cr.line_to(20, 14)
    cr.move_to(36, 28); cr.line_to(36, 10)
    cr.stroke()
    # Beam bar
    cr.set_line_width(5.5)
    cr.move_to(19, 14); cr.line_to(37, 10)
    cr.stroke()

# 12. News: Grey folded newspaper
def cat_news(cr):
    cr.set_source_rgb(0.48, 0.52, 0.58)
    draw_squircle(cr, 10, 12, 28, 24, 3)
    cr.fill()
    # Headlines lines
    cr.set_source_rgb(0.95, 0.95, 0.98)
    cr.rectangle(14, 16, 12, 6)
    cr.fill()
    cr.set_line_width(2)
    for y in [26, 30]:
        cr.move_to(14, y); cr.line_to(34, y)
        cr.stroke()

# 13. Photo & Video: Camera
def cat_photo(cr):
    # Camera body
    cr.set_source_rgb(0.38, 0.42, 0.48)
    draw_squircle(cr, 8, 16, 32, 22, 5)
    cr.fill()
    # Top prism
    cr.move_to(18, 16); cr.line_to(22, 11); cr.line_to(26, 11); cr.line_to(30, 16)
    cr.fill()
    # Lens
    cr.set_source_rgb(0.18, 0.20, 0.24)
    cr.arc(24, 27, 7.5, 0, 2*math.pi)
    cr.fill()
    # Blue reflection
    cr.set_source_rgb(0.25, 0.70, 0.98)
    cr.arc(24, 27, 4.5, 0, 2*math.pi)
    cr.fill()

# 14. Productivity: Blue paper airplane
def cat_productivity(cr):
    cr.save()
    cr.translate(24, 24)
    cr.set_source_rgb(0.08, 0.52, 0.98)
    cr.move_to(16, -16)
    cr.line_to(-16, 2)
    cr.line_to(-4, 6)
    cr.line_to(16, -16)
    cr.fill()
    cr.set_source_rgb(0.04, 0.40, 0.85)
    cr.move_to(16, -16)
    cr.line_to(-4, 6)
    cr.line_to(-2, 16)
    cr.line_to(4, 10)
    cr.line_to(16, -16)
    cr.fill()
    cr.restore()

# 15. Reference: Rounded quote bubble
def cat_reference(cr):
    cr.set_source_rgb(0.42, 0.46, 0.52)
    draw_squircle(cr, 8, 12, 32, 24, 6)
    cr.fill()
    # Speech tail
    cr.move_to(16, 36); cr.line_to(16, 42); cr.line_to(24, 36)
    cr.fill()
    # Double quotation marks
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.select_font_face("SF Pro Display, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(20)
    cr.move_to(15, 30)
    cr.show_text("“ ”")

# 16. Safari Extensions: Blue compass
def cat_safari(cr):
    # Compass circle
    cr.arc(24, 24, 16, 0, 2*math.pi)
    cr.set_source_rgb(0.12, 0.58, 0.95)
    cr.fill()
    # Needle red half
    cr.set_source_rgb(0.95, 0.20, 0.20)
    cr.move_to(24, 24); cr.line_to(28, 20); cr.line_to(32, 16); cr.line_to(24, 24)
    cr.fill()
    # Needle white half
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.move_to(24, 24); cr.line_to(20, 28); cr.line_to(16, 32); cr.line_to(24, 24)
    cr.fill()
    # Center pin
    cr.arc(24, 24, 2.5, 0, 2*math.pi)
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.fill()

# 17. Social Networking: Two overlapping speech bubbles
def cat_social(cr):
    # Pink bubble
    cr.set_source_rgb(0.92, 0.20, 0.45)
    cr.arc(20, 20, 11, 0, 2*math.pi)
    cr.fill()
    cr.move_to(14, 28); cr.line_to(11, 33); cr.line_to(18, 30); cr.fill()
    # Cyan bubble
    cr.set_source_rgb(0.15, 0.68, 0.95)
    cr.arc(30, 26, 9, 0, 2*math.pi)
    cr.fill()
    cr.move_to(32, 33); cr.line_to(36, 38); cr.line_to(36, 32); cr.fill()

# 18. Sports: Green soccer field / ball
def cat_sports(cr):
    # Green field card
    draw_squircle(cr, 8, 14, 32, 22, 4)
    cr.set_source_rgb(0.22, 0.72, 0.32)
    cr.fill()
    # White field markings
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.set_line_width(1.8)
    cr.arc(24, 25, 5, 0, 2*math.pi)
    cr.stroke()
    cr.move_to(24, 14); cr.line_to(24, 36)
    cr.stroke()

# 19. Travel: Cyan passenger plane
def cat_travel(cr):
    cr.save()
    cr.translate(24, 24)
    cr.rotate(-math.pi / 4)
    cr.set_source_rgb(0.08, 0.65, 0.95)
    # Fuselage
    draw_squircle(cr, -3, -16, 6, 32, 3)
    cr.fill()
    # Wings
    cr.move_to(-16, -2); cr.line_to(16, -2); cr.line_to(16, 3); cr.line_to(-16, 3)
    cr.fill()
    # Tail wings
    cr.move_to(-8, 12); cr.line_to(8, 12); cr.line_to(8, 15); cr.line_to(-8, 15)
    cr.fill()
    cr.restore()

# 20. Utilities: Dark calculator
def cat_utilities(cr):
    cr.set_source_rgb(0.38, 0.42, 0.48)
    draw_squircle(cr, 11, 10, 26, 30, 5)
    cr.fill()
    # Screen
    cr.set_source_rgb(0.85, 0.90, 0.85)
    cr.rectangle(15, 14, 18, 6)
    cr.fill()
    # Keypad grid
    colors = [(0.98, 0.58, 0.15), (0.75, 0.78, 0.82), (0.75, 0.78, 0.82)]
    for r in range(3):
        for c in range(3):
            cr.set_source_rgb(*colors[c])
            cr.arc(16 + c * 8, 24 + r * 5.5, 1.8, 0, 2*math.pi)
            cr.fill()

# 21. Weather: Golden sun behind cloud
def cat_weather(cr):
    # Sun
    cr.set_source_rgb(0.98, 0.75, 0.15)
    cr.arc(30, 18, 8, 0, 2*math.pi)
    cr.fill()
    # Cloud
    cr.set_source_rgb(0.20, 0.65, 0.98)
    cr.arc(18, 28, 7, 0, 2*math.pi)
    cr.arc(26, 25, 9, 0, 2*math.pi)
    cr.arc(33, 29, 6, 0, 2*math.pi)
    cr.fill()
    cr.rectangle(18, 28, 16, 7)
    cr.fill()

# Run all generators
if __name__ == "__main__":
    print("Generating featured app icons...")
    generate_viator()
    generate_omnifocus()
    generate_headspace()
    generate_planta()
    generate_trello()
    generate_noted()

    print("Generating category icons...")
    create_cat_icon("business.png", cat_business)
    create_cat_icon("developer_tools.png", cat_developer)
    create_cat_icon("education.png", cat_education)
    create_cat_icon("entertainment.png", cat_entertainment)
    create_cat_icon("finance.png", cat_finance)
    create_cat_icon("games.png", cat_games)
    create_cat_icon("graphics_design.png", cat_graphics)
    create_cat_icon("health_fitness.png", cat_health)
    create_cat_icon("lifestyle.png", cat_lifestyle)
    create_cat_icon("medical.png", cat_medical)
    create_cat_icon("music.png", cat_music)
    create_cat_icon("news.png", cat_news)
    create_cat_icon("photo_video.png", cat_photo)
    create_cat_icon("productivity.png", cat_productivity)
    create_cat_icon("reference.png", cat_reference)
    create_cat_icon("safari_extensions.png", cat_safari)
    create_cat_icon("social_networking.png", cat_social)
    create_cat_icon("sports.png", cat_sports)
    create_cat_icon("travel.png", cat_travel)
    create_cat_icon("utilities.png", cat_utilities)
    create_cat_icon("weather.png", cat_weather)

    print("Successfully generated all macOS App Store assets!")
