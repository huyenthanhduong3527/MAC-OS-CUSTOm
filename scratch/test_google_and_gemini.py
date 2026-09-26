#!/usr/bin/env python3
"""
Automated Test Suite for Google Account, Cloud Storage (Google Drive),
and Google Gemini AI Siri Assistant.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from src.modules.google_account import google_account_mgr
from src.modules.gemini_assistant import gemini_assistant
from src.ui.tabs.gemini_tab import GeminiTab, SiriOrbWidget
from src.ui.macos_settings_window import MacOSSettingsWindow

def test_google_account_module():
    print("=== 1. Testing Google Account & Google Drive Module ===")
    info = google_account_mgr.get_info()
    assert "used_gb" in info
    assert "total_gb" in info
    assert "percent" in info
    print(f"✓ Initial Google Account info: {info}")

    # Test toggles
    google_account_mgr.set_sync_option("sync_photos", False)
    assert google_account_mgr.data["sync_photos"] is False
    google_account_mgr.set_sync_option("sync_photos", True)
    assert google_account_mgr.data["sync_photos"] is True
    print("✓ Google Drive sync options verified.")


def test_gemini_assistant_module():
    print("\n=== 2. Testing Gemini AI Siri Assistant Module ===")
    gemini_assistant.load_config()
    print(f"✓ Current model: {gemini_assistant.model}, Voice: {gemini_assistant.voice_enabled}")

    # Test system actions (Weather, Timer, Drive, Apps)
    res_weather = gemini_assistant.check_system_action("thời tiết hôm nay")
    assert res_weather is not None and res_weather["success"] is True
    print(f"✓ Weather action: '{res_weather['text']}'")

    res_timer = gemini_assistant.check_system_action("hẹn giờ 10 phút")
    assert res_timer is not None and res_timer["seconds"] == 600
    print(f"✓ Timer action: '{res_timer['text']}'")

    res_drive = gemini_assistant.check_system_action("kiểm tra dung lượng google drive")
    assert res_drive is not None and res_drive["action"] == "google_drive"
    print(f"✓ Drive action: '{res_drive['text']}'")

    # Test query with offline/smart assistant
    res_query = gemini_assistant.query("Bạn là ai?")
    assert len(res_query) > 0
    print(f"✓ Query response: '{res_query[:80]}…'")


def test_gemini_tab_ui():
    print("\n=== 3. Testing Dynamic Island Gemini Siri Tab UI ===")
    tab = GeminiTab()
    assert tab.siri_orb is not None
    assert tab.entry is not None
    assert tab.response_lbl is not None
    print("✓ GeminiTab widgets initialized successfully.")

    # Test prompt submission
    tab._submit_prompt("thời tiết")
    assert "thời tiết" in tab.response_lbl.get_text().lower() or "đang xử lý" in tab.response_lbl.get_text().lower()
    print("✓ Gemini prompt submission verified.")


def test_settings_window_internet_accounts():
    print("\n=== 4. Testing Settings Window Internet Accounts Page ===")
    win = MacOSSettingsWindow()
    child = win.stack.get_child_by_name("internet_accounts")
    assert child is not None, "internet_accounts subpage not found in stack!"
    print("✓ 'internet_accounts' subpage verified in stack.")

    win.select_tab("internet_accounts")
    assert win.stack.get_visible_child_name() == "internet_accounts"
    print("✓ Successfully navigated to 'internet_accounts' page.")

    assert hasattr(win, "google_name_lbl")
    assert hasattr(win, "quota_bar")
    assert hasattr(win, "gemini_key_entry")
    print(f"✓ Google & Gemini UI elements verified on settings page.")

    win.destroy()
    print("✓ Settings Window cleanly closed.")


def main():
    test_google_account_module()
    test_gemini_assistant_module()
    test_gemini_tab_ui()
    test_settings_window_internet_accounts()
    print("\n🎉 ALL GOOGLE & GEMINI TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
