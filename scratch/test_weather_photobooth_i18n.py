#!/usr/bin/env python3
"""
Comprehensive automated test suite for Weather Widget & Photo Booth Multilingual (i18n) Support.
"""

import sys
import os

sys.path.insert(0, "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX")

from src.utils.i18n import set_language, get_current_language, t, TRANSLATIONS
from src.modules.weather import WeatherManager, WMO_WEATHER_MAP
from src.ui.desktop_widgets.weather_widget import DesktopWeatherWidget
from src.ui.macos_photobooth_window import MacOSPhotoBoothWindow

def test_i18n_keys():
    print("=== Test 1: Translation Keys Integrity across all 9 languages ===")
    languages = ["vi", "en", "ja", "fr", "es", "de", "zh", "ko", "ru"]
    required_keys = [
        "weather_title", "weather_precipitation", "weather_wind",
        "weather_high_short", "weather_low_short", "weather_hl_format",
        "weather_code_0", "weather_code_51", "weather_code_95",
        "photobooth_title", "photobooth_connect_phone", "photobooth_effects",
        "photobooth_mode_4up", "photobooth_mode_single", "photobooth_mode_video",
        "photobooth_filter_normal", "photobooth_filter_mirror", "photobooth_filter_comic"
    ]
    for lang in languages:
        assert lang in TRANSLATIONS, f"Missing language '{lang}' in TRANSLATIONS"
        dict_l = TRANSLATIONS[lang]
        for key in required_keys:
            assert key in dict_l, f"Missing key '{key}' in language '{lang}'"
    print(f"✓ All {len(required_keys)} test keys exist in all {len(languages)} languages!")

def test_weather_manager_dynamic_translations():
    print("=== Test 2: WeatherManager Dynamic Multilingual Translation ===")
    wm = WeatherManager()
    
    # 1. Japanese
    set_language("ja", apply_system=False)
    assert wm.desc == "弱い霧雨", f"Expected '弱い霧雨', got '{wm.desc}'"
    assert wm.wind_dir_name == "北西", f"Expected '北西', got '{wm.wind_dir_name}'"
    
    # 2. English
    set_language("en", apply_system=False)
    assert wm.desc == "Light drizzle", f"Expected 'Light drizzle', got '{wm.desc}'"
    assert wm.wind_dir_name == "North-West", f"Expected 'North-West', got '{wm.wind_dir_name}'"
    
    # 3. Vietnamese
    set_language("vi", apply_system=False)
    assert wm.desc == "Mưa phùn nhẹ", f"Expected 'Mưa phùn nhẹ', got '{wm.desc}'"
    assert wm.wind_dir_name == "Tây Bắc", f"Expected 'Tây Bắc', got '{wm.wind_dir_name}'"
    print("✓ WeatherManager transitions smoothly and updates descriptions in real-time!")

def test_photobooth_window_translations():
    print("=== Test 3: Photo Booth UI Dynamic Translation ===")
    pb = MacOSPhotoBoothWindow.get_instance()
    
    # 1. Japanese
    set_language("ja", apply_system=False)
    assert pb.lbl_phone_status.get_text() == "iPhone / Android を接続", f"Unexpected phone status: {pb.lbl_phone_status.get_text()}"
    assert pb.btn_live_preview.get_label() == "エフェクト", f"Unexpected effects label: {pb.btn_live_preview.get_label()}"
    assert pb.btn_mode_4up.get_tooltip_text() == "4コマ連写モード", f"Unexpected tooltip: {pb.btn_mode_4up.get_tooltip_text()}"
    
    # 2. English
    set_language("en", apply_system=False)
    assert pb.lbl_phone_status.get_text() == "Connect Phone", f"Unexpected phone status: {pb.lbl_phone_status.get_text()}"
    assert pb.btn_live_preview.get_label() == "Effects", f"Unexpected effects label: {pb.btn_live_preview.get_label()}"
    assert pb.btn_mode_4up.get_tooltip_text() == "4-Up Burst Mode", f"Unexpected tooltip: {pb.btn_mode_4up.get_tooltip_text()}"
    
    # 3. Vietnamese
    set_language("vi", apply_system=False)
    assert pb.lbl_phone_status.get_text() == "Kết nối điện thoại", f"Unexpected phone status: {pb.lbl_phone_status.get_text()}"
    assert pb.btn_live_preview.get_label() == "Hiệu ứng", f"Unexpected effects label: {pb.btn_live_preview.get_label()}"
    assert pb.btn_mode_4up.get_tooltip_text() == "Chụp 4 ô liên hoàn", f"Unexpected tooltip: {pb.btn_mode_4up.get_tooltip_text()}"
    print("✓ Photo Booth UI retranslates immediately on language switch!")

def test_weather_widget_drawing():
    print("=== Test 4: Desktop Weather Widget Cairo Drawing in Active Language ===")
    import cairo
    ww = DesktopWeatherWidget()
    set_language("ja", apply_system=False)
    
    # Create surface and context to simulate draw
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, ww.total_w, ww.total_h)
    cr = cairo.Context(surf)
    res = ww._on_draw(ww, cr)
    assert res is False, "Expected _on_draw to return False (standard GTK convention)"
    print("✓ DesktopWeatherWidget drew frame cleanly in Japanese without exceptions!")

if __name__ == "__main__":
    test_i18n_keys()
    test_weather_manager_dynamic_translations()
    test_photobooth_window_translations()
    test_weather_widget_drawing()
    # Restore user preference to 'ja'
    set_language("ja", apply_system=False)
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
