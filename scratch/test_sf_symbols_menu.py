import cairo
import math
import gi
import os
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

# Cache for rendered SF Symbols
_SYMBOL_CACHE = {}

def get_sf_symbol_pixbuf(symbol_name: str, size: int = 16, color: tuple = None) -> GdkPixbuf.Pixbuf:
    """
    Renders vector Apple SF Symbols in Cairo with 2x supersampling for retina sharpness.
    """
    if color is None:
        if symbol_name in ("xmark", "hide", "trash", "delete"):
            color = (1.0, 0.27, 0.23) # Apple Red #ff453a
        elif symbol_name in ("sparkles",):
            color = (1.0, 0.84, 0.04) # Apple Gold #ffd60a
        elif symbol_name in ("check", "checkmark"):
            color = (0.04, 0.52, 1.00) # Apple Blue #0a84ff
        else:
            color = (0.92, 0.94, 0.98) # Crisp Silver/White #f1f5f9

    cache_key = (symbol_name, size, color)
    if cache_key in _SYMBOL_CACHE:
        return _SYMBOL_CACHE[cache_key]

    scale = 2
    px = size * scale
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, px, px)
    cr = cairo.Context(surface)
    cr.scale(scale, scale)

    cr.set_source_rgb(*color)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    s = size
    # -------------------------------------------------------------
    # 1. LOCK / UNLOCK
    # -------------------------------------------------------------
    if symbol_name in ("lock.open", "unlock"):
        # Apple SF Symbol: lock.open
        # Body
        bw, bh = s * 0.65, s * 0.44
        bx = (s - bw) / 2.0
        by = s - bh - 1.8
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
        cr.arc(s * 0.42, by - 0.2, s * 0.26, math.pi * 0.9, math.pi * 2.1)
        cr.stroke()

    elif symbol_name in ("lock", "lock.fill"):
        # Apple SF Symbol: lock.fill
        bw, bh = s * 0.65, s * 0.46
        bx = (s - bw) / 2.0
        by = s - bh - 1.8
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
        cr.arc(s / 2.0, by + 0.2, s * 0.24, math.pi, 0)
        cr.line_to(s / 2.0 + s * 0.24, by + 1.2)
        cr.stroke()
        # Keyhole dot in center
        cr.arc(s / 2.0, by + bh * 0.45, 1.2, 0, 2*math.pi)
        cr.set_source_rgba(0.12, 0.14, 0.18, 0.9)
        cr.fill()

    elif symbol_name in ("lock.all", "lock.stack"):
        # Apple SF Symbol: Dual locks
        cr.set_line_width(1.4)
        # Back lock
        cr.rectangle(s * 0.38, s * 0.38, s * 0.48, s * 0.40)
        cr.stroke()
        cr.arc(s * 0.62, s * 0.38, s * 0.16, math.pi, 0)
        cr.stroke()
        # Front lock
        cr.rectangle(s * 0.14, s * 0.50, s * 0.48, s * 0.40)
        cr.fill()
        cr.arc(s * 0.38, s * 0.50, s * 0.16, math.pi, 0)
        cr.stroke()

    # -------------------------------------------------------------
    # 2. LAYOUT & DISPLAY
    # -------------------------------------------------------------
    elif symbol_name in ("layout", "square.grid.2x2", "rectangle.split.2x1"):
        # Apple SF Symbol: rectangle.split.2x1
        rw, rh = s * 0.78, s * 0.70
        rx = (s - rw) / 2.0
        ry = (s - rh) / 2.0
        cr.set_line_width(1.4)
        r = 2.2
        cr.new_sub_path()
        cr.arc(rx + rw - r, ry + r, r, -math.pi/2, 0)
        cr.arc(rx + rw - r, ry + rh - r, r, 0, math.pi/2)
        cr.arc(rx + r, ry + rh - r, r, math.pi/2, math.pi)
        cr.arc(rx + r, ry + r, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        # Vertical split divider
        cr.move_to(rx + rw * 0.46, ry + 1.2)
        cr.line_to(rx + rw * 0.46, ry + rh - 1.2)
        cr.stroke()

    elif symbol_name in ("iphone", "phone"):
        # Apple SF Symbol: iphone
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
        # Home bar at bottom
        cr.set_line_width(1.2)
        cr.move_to(px + pw * 0.32, py + ph - 2.5)
        cr.line_to(px + pw * 0.68, py + ph - 2.5)
        cr.stroke()

    elif symbol_name in ("macbook", "laptop"):
        # Apple SF Symbol: macbook
        # Screen
        sw, sh = s * 0.68, s * 0.48
        sx = (s - sw) / 2.0
        sy = s * 0.22
        cr.set_line_width(1.3)
        cr.rectangle(sx, sy, sw, sh)
        cr.stroke()
        # Base
        cr.move_to(s * 0.08, sy + sh + 2.2)
        cr.line_to(s * 0.92, sy + sh + 2.2)
        cr.stroke()

    # -------------------------------------------------------------
    # 3. SIZE & RESIZE
    # -------------------------------------------------------------
    elif symbol_name in ("size", "arrow.up.left.and.arrow.down.right"):
        # Apple SF Symbol: arrow.up.left.and.arrow.down.right
        cr.set_line_width(1.4)
        # Top-left arrow
        cr.move_to(s * 0.20, s * 0.48)
        cr.line_to(s * 0.20, s * 0.20)
        cr.line_to(s * 0.48, s * 0.20)
        cr.stroke()
        cr.move_to(s * 0.20, s * 0.20)
        cr.line_to(s * 0.50, s * 0.50)
        cr.stroke()
        # Bottom-right arrow
        cr.move_to(s * 0.80, s * 0.52)
        cr.line_to(s * 0.80, s * 0.80)
        cr.line_to(s * 0.52, s * 0.80)
        cr.stroke()
        cr.move_to(s * 0.80, s * 0.80)
        cr.line_to(s * 0.50, s * 0.50)
        cr.stroke()

    # -------------------------------------------------------------
    # 4. THEME & PALETTE
    # -------------------------------------------------------------
    elif symbol_name in ("theme", "paintpalette"):
        # Apple SF Symbol: paintpalette
        cr.set_line_width(1.4)
        cx, cy = s / 2.0, s / 2.0
        # Smooth palette contour
        cr.arc(cx, cy, s * 0.38, 0, 2 * math.pi)
        cr.stroke()
        # Palette pigment dots
        cr.arc(cx - s * 0.16, cy - s * 0.16, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(cx + s * 0.14, cy - s * 0.18, 1.3, 0, 2*math.pi)
        cr.fill()
        cr.arc(cx + s * 0.20, cy + s * 0.10, 1.3, 0, 2*math.pi)
        cr.fill()
        # Thumb hole
        cr.arc(cx - s * 0.10, cy + s * 0.14, 1.6, 0, 2*math.pi)
        cr.stroke()

    elif symbol_name in ("sun.max", "sun"):
        # Apple SF Symbol: sun.max
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
        # Apple SF Symbol: moon.fill
        cx, cy = s * 0.48, s * 0.50
        cr.arc(cx, cy, s * 0.34, math.pi * 0.25, math.pi * 1.75)
        cr.arc_negative(cx + s * 0.18, cy, s * 0.28, math.pi * 1.6, math.pi * 0.4)
        cr.close_path()
        cr.fill()

    elif symbol_name in ("circle.lefthalf.filled", "auto"):
        # Apple SF Symbol: circle.lefthalf.filled (Auto theme)
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        cr.set_line_width(1.4)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()
        # Fill left half
        cr.arc(cx, cy, r - 0.7, math.pi / 2, 3 * math.pi / 2)
        cr.close_path()
        cr.fill()

    # -------------------------------------------------------------
    # 5. SPARKLES & EFFECTS
    # -------------------------------------------------------------
    elif symbol_name in ("sparkles", "sparkle"):
        # Apple SF Symbol: sparkles
        # Center main star
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
        # Small companion star top-right
        c2x, c2y = s * 0.80, s * 0.24
        cr.arc(c2x, c2y, 1.2, 0, 2*math.pi)
        cr.fill()
        # Small companion star bottom-left
        c3x, c3y = s * 0.18, s * 0.78
        cr.arc(c3x, c3y, 0.9, 0, 2*math.pi)
        cr.fill()

    # -------------------------------------------------------------
    # 6. PIN & KEEP ON TOP
    # -------------------------------------------------------------
    elif symbol_name in ("pin", "pin.fill"):
        # Apple SF Symbol: pin.fill
        cr.save()
        cr.translate(s * 0.5, s * 0.5)
        cr.rotate(-math.pi / 4)
        cr.set_line_width(1.4)
        # Pin head
        cr.rectangle(-2.5, -6.0, 5.0, 3.0)
        cr.fill()
        cr.rectangle(-4.0, -3.0, 8.0, 2.0)
        cr.fill()
        # Pin body taper
        cr.move_to(-2.0, -1.0)
        cr.line_to(-1.2, 3.5)
        cr.line_to(1.2, 3.5)
        cr.line_to(2.0, -1.0)
        cr.close_path()
        cr.fill()
        # Needle
        cr.move_to(0, 3.5)
        cr.line_to(0, 7.0)
        cr.stroke()
        cr.restore()

    # -------------------------------------------------------------
    # 7. RESET / RELOAD
    # -------------------------------------------------------------
    elif symbol_name in ("reset", "arrow.counterclockwise"):
        # Apple SF Symbol: arrow.counterclockwise
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.32
        cr.set_line_width(1.5)
        cr.arc(cx, cy, r, -math.pi * 0.4, math.pi * 0.95)
        cr.stroke()
        # Arrowhead
        ax = cx + math.cos(-math.pi * 0.4) * r
        ay = cy + math.sin(-math.pi * 0.4) * r
        cr.move_to(ax - 2.8, ay - 1.2)
        cr.line_to(ax, ay)
        cr.line_to(ax + 0.8, ay + 3.0)
        cr.stroke()

    # -------------------------------------------------------------
    # 8. HIDE / DELETE / CLOSE
    # -------------------------------------------------------------
    elif symbol_name in ("xmark", "hide", "close"):
        # Apple SF Symbol: xmark
        cr.set_line_width(1.8)
        pad = s * 0.24
        cr.move_to(pad, pad)
        cr.line_to(s - pad, s - pad)
        cr.stroke()
        cr.move_to(s - pad, pad)
        cr.line_to(pad, s - pad)
        cr.stroke()

    elif symbol_name in ("check", "checkmark"):
        # Apple SF Symbol: checkmark
        cr.set_line_width(1.8)
        cr.move_to(s * 0.20, s * 0.52)
        cr.line_to(s * 0.42, s * 0.74)
        cr.line_to(s * 0.82, s * 0.26)
        cr.stroke()

    else:
        # Generic dot
        cr.arc(s / 2.0, s / 2.0, s * 0.25, 0, 2*math.pi)
        cr.fill()

    # Convert cairo surface to GdkPixbuf
    pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, px, px)
    if scale > 1:
        pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)

    _SYMBOL_CACHE[cache_key] = pixbuf
    return pixbuf


def create_mac_menu_item(icon_name: str = None, text: str = "", on_activate = None,
                         is_destructive: bool = False, is_checked: bool = False,
                         submenu: Gtk.Menu = None) -> Gtk.MenuItem:
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
        color = (1.0, 0.27, 0.23) if is_destructive else (0.92, 0.94, 0.98)
        pb = get_sf_symbol_pixbuf(icon_name, size=15, color=color)
        img = Gtk.Image.new_from_pixbuf(pb)
        img.set_valign(Gtk.Align.CENTER)
        box.pack_start(img, False, False, 0)
    else:
        # Space placeholder for alignment
        spacer = Gtk.Box()
        spacer.set_size_request(15, -1)
        box.pack_start(spacer, False, False, 0)

    # 2. Text Label
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


if __name__ == "__main__":
    # Test rendering the Music widget context menu using pure SF Symbols
    menu = create_mac_context_menu()

    menu.append(create_mac_menu_item("lock.open", "Mở khóa Widget (Di chuyển & Đổi cỡ)"))
    menu.append(create_mac_menu_item("lock.all", "Mở khóa tất cả Widget trên màn hình"))
    menu.append(Gtk.SeparatorMenuItem())

    # Layout submenu
    layout_sub = create_mac_context_menu()
    layout_sub.append(create_mac_menu_item("iphone", "Thẻ dọc iOS", is_checked=True))
    layout_sub.append(create_mac_menu_item("macbook", "Thẻ vuông macOS (Cổ điển)"))
    menu.append(create_mac_menu_item("layout", "Bố cục hiển thị (Layout)", submenu=layout_sub))

    # Size submenu
    size_sub = create_mac_context_menu()
    size_sub.append(create_mac_menu_item(None, "Nhỏ (Mini - 80%)"))
    size_sub.append(create_mac_menu_item(None, "Tiêu chuẩn (100%)", is_checked=True))
    size_sub.append(create_mac_menu_item(None, "Lớn (Rộng - 125%)"))
    size_sub.append(create_mac_menu_item(None, "Cực lớn (To - 150%)"))
    size_sub.append(Gtk.SeparatorMenuItem())
    size_sub.append(create_mac_menu_item("reset", "Đặt lại kích thước mặc định"))
    menu.append(create_mac_menu_item("size", "Kích thước (Size)", submenu=size_sub))

    # Theme submenu
    theme_sub = create_mac_context_menu()
    theme_sub.append(create_mac_menu_item("auto", "Tự động theo hệ thống (Auto)", is_checked=True))
    theme_sub.append(create_mac_menu_item("sun.max", "Giao diện Sáng (Light Glass)"))
    theme_sub.append(create_mac_menu_item("moon.fill", "Giao diện Tối (Dark Glass)"))
    menu.append(create_mac_menu_item("theme", "Giao diện (Theme)", submenu=theme_sub))

    menu.append(create_mac_menu_item("sparkles", "Phát lại hiệu ứng mở"))
    menu.append(Gtk.SeparatorMenuItem())

    menu.append(create_mac_menu_item("pin", "Nổi trên cửa sổ (Keep Above)"))
    menu.append(create_mac_menu_item("reset", "Đặt lại vị trí ban đầu"))
    menu.append(Gtk.SeparatorMenuItem())

    menu.append(create_mac_menu_item("xmark", "Ẩn Widget Âm Nhạc", is_destructive=True))

    # Put in a dark window container to capture screenshot
    win = Gtk.Window()
    win.set_default_size(360, 420)
    win.set_app_paintable(True)

    def draw_bg(w, cr):
        cr.set_source_rgba(0.11, 0.12, 0.14, 0.98)
        cr.paint()
        return False
    win.connect("draw", draw_bg)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    box.set_margin_top(12)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_bottom(12)
    win.add(box)

    for child in menu.get_children():
        menu.remove(child)
        box.pack_start(child, False, False, 0)

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
            out = '/home/tramvo/.gemini/antigravity-ide/brain/67c4e8d3-62be-4941-a87e-c74568edb578/test_sf_symbols_menu.png'
            pb.savev(out, 'png', [], [])
            print('Captured SF Symbols menu test:', out)
