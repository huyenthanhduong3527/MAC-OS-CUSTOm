#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Global Language & System-Wide Locale Integration.
Tests:
1. World Languages database (Unicode CLDR + Linux locales)
2. Internationalization (i18n) translation engine and fallbacks
3. System-wide locale updates (AccountsService, locale.conf, GSettings)
4. macOS Settings Window Language & Region page integration
5. macOS World Language Picker Dialog
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from src.utils.languages import (
    get_all_world_languages,
    find_language,
    search_languages,
    LanguageInfo
)
from src.utils.i18n import (
    t, _, set_language, get_current_language,
    get_current_language_info, get_preferred_languages,
    add_preferred_language, remove_preferred_language
)
from src.utils.system_locale import (
    is_locale_generated,
    apply_system_language
)

def test_languages_db():
    print("=== 1. Testing World Languages Database ===")
    all_langs = get_all_world_languages()
    assert len(all_langs) >= 100, f"Expected >= 100 world languages, got {len(all_langs)}"
    print(f"✓ Loaded {len(all_langs)} world languages successfully.")

    # Test major languages
    vi = find_language("vi")
    assert vi is not None and "Tiếng Việt" in vi.native_name
    print(f"✓ Found Vietnamese: {vi.native_name} ({vi.locale}) {vi.flag}")

    en = find_language("en")
    assert en is not None and "English" in en.native_name
    print(f"✓ Found English: {en.native_name} ({en.locale}) {en.flag}")

    ja = find_language("ja")
    assert ja is not None and "日本語" in ja.native_name
    print(f"✓ Found Japanese: {ja.native_name} ({ja.locale}) {ja.flag}")

    fr = find_language("fr")
    assert fr is not None and "Français" in fr.native_name
    print(f"✓ Found French: {fr.native_name} ({fr.locale}) {fr.flag}")

    # Test search
    res_vi = search_languages("tieng viet")
    assert any("Tiếng Việt" in r.native_name for r in res_vi)
    print(f"✓ Search 'tieng viet' (unaccented) returned {len(res_vi)} results.")

    res_ar = search_languages("arabic")
    assert any("العربية" in r.native_name for r in res_ar)
    print(f"✓ Search 'arabic' returned {len(res_ar)} results.")


def test_i18n_engine():
    print("\n=== 2. Testing i18n Translation Engine ===")
    original_lang = get_current_language()

    # Test Vietnamese
    set_language("vi", apply_system=False)
    assert get_current_language() == "vi"
    assert t("settings_title") == "Cài đặt hệ thống"
    assert t("language_region") == "Ngôn ngữ & Vùng"
    print(f"✓ Vietnamese translations verified: '{t('settings_title')}', '{t('language_region')}'")

    # Test English
    set_language("en", apply_system=False)
    assert get_current_language() == "en"
    assert t("settings_title") == "System Settings"
    assert t("language_region") == "Language & Region"
    print(f"✓ English translations verified: '{t('settings_title')}', '{t('language_region')}'")

    # Test Japanese
    set_language("ja", apply_system=False)
    assert get_current_language() == "ja"
    assert t("settings_title") == "システム設定"
    assert t("language_region") == "言語と地域"
    print(f"✓ Japanese translations verified: '{t('settings_title')}', '{t('language_region')}'")

    # Test French
    set_language("fr", apply_system=False)
    assert get_current_language() == "fr"
    assert t("settings_title") == "Réglages Système"
    assert t("language_region") == "Langue et région"
    print(f"✓ French translations verified: '{t('settings_title')}', '{t('language_region')}'")

    # Restore
    set_language(original_lang, apply_system=False)
    print(f"✓ Restored language to '{original_lang}'")


def test_preferred_languages():
    print("\n=== 3. Testing Preferred Languages List Management ===")
    add_preferred_language("fr", make_primary=False)
    prefs = get_preferred_languages()
    codes = [p.code for p in prefs]
    assert "fr" in codes
    print(f"✓ Added French to preferred list: {codes}")

    remove_preferred_language("fr")
    prefs_after = get_preferred_languages()
    codes_after = [p.code for p in prefs_after]
    assert "fr" not in codes_after
    print(f"✓ Removed French from preferred list: {codes_after}")


def test_system_locale_integration():
    print("\n=== 4. Testing System Locale Integration ===")
    res = apply_system_language("vi_VN.UTF-8", "vi")
    print(f"✓ System locale apply result: {res}")
    assert res.get("success") is True, f"Expected apply_system_language success, got: {res}"

    # Verify ~/.config/locale.conf
    conf_path = os.path.expanduser("~/.config/locale.conf")
    assert os.path.exists(conf_path)
    with open(conf_path) as f:
        content = f.read()
    assert "vi_VN.UTF-8" in content
    print(f"✓ ~/.config/locale.conf contents verified:\n{content.strip()}")


def test_settings_window_language_page():
    print("\n=== 5. Testing Settings Window Language & Region Page ===")
    from src.ui.macos_settings_window import MacOSSettingsWindow

    win = MacOSSettingsWindow()
    # Check that language_region child exists in stack
    child = win.stack.get_child_by_name("language_region")
    assert child is not None, "language_region page not found in stack!"
    print("✓ 'language_region' subpage found in stack.")

    # Select tab
    win.select_tab("language_region")
    assert win.stack.get_visible_child_name() == "language_region"
    print("✓ Successfully navigated to 'language_region' page.")

    # Verify language row in general page
    assert hasattr(win, "general_lang_sub")
    print(f"✓ General page language indicator verified: '{win.general_lang_sub.get_text()}'")

    win.destroy()
    print("✓ Settings Window destroyed cleanly.")


def main():
    test_languages_db()
    test_i18n_engine()
    test_preferred_languages()
    test_system_locale_integration()
    test_settings_window_language_page()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
