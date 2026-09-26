import os
import sys
import time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

sys.path.insert(0, "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX")
from src.ui.macos_photos_window import MacOSPhotosWindow
from src.modules.photos_scanner import PhotoItem

ARTIFACTS_DIR = "/home/tramvo/.gemini/antigravity-ide/brain/5c8b0e90-4565-4787-8bdd-54594301fbfc"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

app = MacOSPhotosWindow.get_instance()
app.set_size_request(1180, 780)
app.resize(1180, 780)
app.show_all()
app.lightbox.hide()
app.inspector_panel.hide()

# Find target photo
target_path = "/home/tramvo/Pictures/Screenshots/Screenshot From 2026-09-21 09-18-50.png"
if not os.path.exists(target_path):
    # fallback to first available
    sc_dir = "/home/tramvo/Pictures/Screenshots"
    files = [os.path.join(sc_dir, f) for f in os.listdir(sc_dir) if f.endswith(".png")]
    target_path = files[0] if files else ""

print(f"Target photo: {target_path}")
photo_item = PhotoItem(
    path=target_path,
    size=os.path.getsize(target_path),
    mtime=os.path.getmtime(target_path),
    is_favorite=False
)

import cairo

def capture_window_to_file(window, filename):
    window.check_resize()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    alloc = window.get_allocation()
    w, h = max(100, alloc.width), max(100, alloc.height)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    window.draw(cr)
    out_path = os.path.join(ARTIFACTS_DIR, filename)
    surface.write_to_png(out_path)
    print(f"Saved screenshot: {out_path} ({w}x{h})")

step = 0

def on_step():
    global step
    step += 1
    
    if step == 1:
        # Step 1: Open lightbox with photo
        app.lightbox.open_photo(photo_item, [photo_item])
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        GLib.timeout_add(300, on_step)
        return False

    elif step == 2:
        # Capture lightbox before editing (showing "Sửa" button in top bar and pill bar)
        capture_window_to_file(app, "macos_photo_lightbox_before_edit.png")
        # Enter edit mode
        app.lightbox.enter_edit_mode()
        GLib.timeout_add(300, on_step)
        return False

    elif step == 3:
        # Step 3: Adjustments tab
        app.lightbox._on_editor_tab_switched("adjust")
        app.lightbox.editor_header._highlight_tab("adjust")
        app.lightbox.editor_inspector.slider_scales["exposure"].set_value(25)
        app.lightbox.editor_inspector.slider_scales["brilliance"].set_value(20)
        app.lightbox.editor_inspector.slider_scales["saturation"].set_value(30)
        capture_window_to_file(app, "macos_photo_editor_adjust.png")
        GLib.timeout_add(300, on_step)
        return False

    elif step == 4:
        # Step 4: Crop & Straighten tab
        app.lightbox._on_editor_tab_switched("crop")
        app.lightbox.editor_header._highlight_tab("crop")
        app.lightbox.editor_inspector._on_aspect_ratio_clicked("16:9")
        app.lightbox.editor_inspector.st_scale.set_value(3.5)
        capture_window_to_file(app, "macos_photo_editor_crop.png")
        GLib.timeout_add(300, on_step)
        return False

    elif step == 5:
        # Step 5: Filters tab
        app.lightbox._on_editor_tab_switched("filters")
        app.lightbox.editor_header._highlight_tab("filters")
        app.lightbox.editor_inspector._on_filter_chosen("vivid_warm")
        capture_window_to_file(app, "macos_photo_editor_filters.png")
        GLib.timeout_add(300, on_step)
        return False

    elif step == 6:
        # Step 6: Markup tab
        app.lightbox._on_editor_tab_switched("markup")
        app.lightbox.editor_header._highlight_tab("markup")
        app.lightbox.editor_engine.add_markup({
            "type": "arrow",
            "p1": (0.3, 0.4),
            "p2": (0.6, 0.6),
            "color": (255, 59, 48, 255),
            "width": 6
        })
        app.lightbox.editor_engine.add_markup({
            "type": "text",
            "pos": (0.35, 0.35),
            "text": "Audio Message 01:54.26",
            "color": (255, 204, 0, 255)
        })
        app.lightbox._refresh_editor_preview()
        capture_window_to_file(app, "macos_photo_editor_markup.png")
        GLib.timeout_add(200, on_step)
        return False

    elif step == 7:
        print("Done capturing all screenshots!")
        Gtk.main_quit()
        return False

    return False

GLib.timeout_add(200, on_step)
Gtk.main()
