import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import os
import sys

sys.path.insert(0, "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX")

from src.config import config
from src.ui.macos_settings_window import MacOSSettingsWindow
from src.modules.airdrop import get_machine_name

def run_tests():
    print("[TEST] Initializing MacOSSettingsWindow...")
    orig_device_name = config.get("device_name", "")
    
    win = MacOSSettingsWindow()
    win.show_all()
    
    # Process pending events
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
        
    print(f"[TEST] Default tab: {win._current_tab}, stack: {win.stack.get_visible_child_name()}")
    print(f"[TEST] Nav history: {win._nav_history}, index: {win._nav_index}")
    print(f"[TEST] Back button sensitive: {win.back_btn.is_sensitive()}, Fwd button sensitive: {win.fwd_btn.is_sensitive()}")
    assert not win.back_btn.is_sensitive(), "Back button should initially be disabled"
    assert not win.fwd_btn.is_sensitive(), "Forward button should initially be disabled"

    # Navigate to subpage About (Giới thiệu)
    print("\n[TEST] Navigating to 'about' (Giới thiệu)...")
    win.select_tab("about")
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print(f"[TEST] Current page: {win.stack.get_visible_child_name()}, title: '{win.page_title_lbl.get_text()}'")
    print(f"[TEST] Nav history: {win._nav_history}, index: {win._nav_index}")
    print(f"[TEST] Back button sensitive: {win.back_btn.is_sensitive()}, Fwd button sensitive: {win.fwd_btn.is_sensitive()}")
    assert win.back_btn.is_sensitive(), "Back button MUST be sensitive after entering About subpage!"
    assert not win.fwd_btn.is_sensitive(), "Forward button should be disabled at end of history"
    assert win.stack.get_visible_child_name() == "about", "Visible stack child should be 'about'"

    # Click Back navigation arrow
    print("\n[TEST] Clicking Back arrow (_nav_back)...")
    win._nav_back()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print(f"[TEST] After Back: stack: {win.stack.get_visible_child_name()}, title: '{win.page_title_lbl.get_text()}'")
    print(f"[TEST] Back button sensitive: {win.back_btn.is_sensitive()}, Fwd button sensitive: {win.fwd_btn.is_sensitive()}")
    assert win.stack.get_visible_child_name() == "general", "Visible child should be 'general'"
    assert not win.back_btn.is_sensitive(), "Back button should now be disabled"
    assert win.fwd_btn.is_sensitive(), "Forward button MUST be sensitive after going back!"

    # Click Forward navigation arrow
    print("\n[TEST] Clicking Forward arrow (_nav_forward)...")
    win._nav_forward()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print(f"[TEST] After Forward: stack: {win.stack.get_visible_child_name()}, title: '{win.page_title_lbl.get_text()}'")
    print(f"[TEST] Back button sensitive: {win.back_btn.is_sensitive()}, Fwd button sensitive: {win.fwd_btn.is_sensitive()}")
    assert win.stack.get_visible_child_name() == "about"
    assert win.back_btn.is_sensitive()
    assert not win.fwd_btn.is_sensitive()

    # Test Breadcrumb button back
    print("\n[TEST] Testing breadcrumb back (_on_breadcrumb_back)...")
    win._on_breadcrumb_back("general")
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print(f"[TEST] After Breadcrumb Back: stack: {win.stack.get_visible_child_name()}, title: '{win.page_title_lbl.get_text()}'")
    print(f"[TEST] Back button sensitive: {win.back_btn.is_sensitive()}, Fwd button sensitive: {win.fwd_btn.is_sensitive()}")
    assert win.stack.get_visible_child_name() == "general"
    assert win.fwd_btn.is_sensitive()

    # Forward back to About to test renaming
    win._nav_forward()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print(f"\n[TEST] Current model label: '{win.model_lbl.get_text()}'")
    print(f"[TEST] Current name val label: '{win.name_val_lbl.get_text()}'")
    
    test_new_name = "MacBook Pro của Tâm"
    print(f"\n[TEST] Saving new device name: '{test_new_name}'...")
    win._save_new_device_name(test_new_name)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print(f"[TEST] New model label: '{win.model_lbl.get_text()}'")
    print(f"[TEST] New name val label: '{win.name_val_lbl.get_text()}'")
    print(f"[TEST] AirDrop machine name: '{get_machine_name()}'")
    assert win.model_lbl.get_text() == f"{test_new_name} (Mac Edition)"
    assert win.name_val_lbl.get_text() == test_new_name
    assert get_machine_name() == test_new_name

    # Restore original device name
    print(f"\n[TEST] Restoring device name to '{orig_device_name}'...")
    win._save_new_device_name(orig_device_name if orig_device_name else os.uname().nodename)
    config.set("device_name", orig_device_name)
    
    win.destroy()
    print("\n[SUCCESS] ALL NAVIGATION ARROW AND DEVICE RENAMING TESTS PASSED 100%!")

if __name__ == "__main__":
    run_tests()
