#!/usr/bin/env python3
"""
Captures screenshots of DesktopWeatherWidget and MacOSPhotoBoothWindow in Japanese.
"""

import sys
import os
import cairo

sys.path.insert(0, "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX")

from src.utils.i18n import set_language
from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow
from gi.repository import Gtk, Gdk

def capture_widget(widget, filename):
    widget.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    
    alloc = widget.get_allocation()
    w = max(alloc.width, widget.get_size()[0], 100)
    h = max(alloc.height, widget.get_size()[1], 100)
    
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surf)
    
    widget.draw(cr)
    surf.write_to_png(filename)
    print(f"Captured {filename} ({w}x{h})")

if __name__ == "__main__":
    set_language("ja", apply_system=False)
    
    # 1. Weather Widget in JA
    ww = DesktopWeatherWidget()
    ww.weather_mgr._on_language_changed("ja")
    capture_widget(ww, "/home/tramvo/.gemini/antigravity-ide/brain/742baac2-a101-4d72-90bc-0974431fcbbe/weather_widget_ja.png")
    
    # 2. Photo Booth in JA
    pb = MacOSPhotoBoothWindow.get_instance()
    pb._retranslate_ui()
    capture_widget(pb, "/home/tramvo/.gemini/antigravity-ide/brain/742baac2-a101-4d72-90bc-0974431fcbbe/photobooth_ja.png")
    
    print("Done capturing artifacts!")
