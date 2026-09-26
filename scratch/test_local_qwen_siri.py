"""
Comprehensive test for Local Qwen 2.5 1.5B Siri Assistant, OS Automation, and Neural Voice.
"""
import os
import sys
import time

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from src.modules.siri_assistant import siri_assistant
from src.modules.voice_synthesizer import voice_synthesizer, clean_text_for_speech, detect_language
from src.modules.gemini_assistant import gemini_assistant
from src.ui.tabs.gemini_tab import GeminiTab

def test_local_model():
    print("\n--- 1. Testing Local Qwen 2.5 1.5B Status & Query ---")
    status, msg = siri_assistant.check_local_model_status()
    print(f"Ollama Qwen Status: {status} ({msg})")
    assert status, f"Ollama model status check failed: {msg}"

    received = []
    def _cb(text, success):
        print(f"Siri Qwen Reply: {text}")
        received.append((text, success))

    siri_assistant.query("Xin chào, bạn có thể làm gì?", callback=_cb)
    for _ in range(25):
        if received:
            break
        time.sleep(0.5)

    assert len(received) > 0, "No response received from local Qwen 2.5"
    assert received[0][1] is True, "Local Qwen query failed"
    print("✓ Local Qwen 2.5 1.5B responded successfully!")

def test_file_and_app_actions():
    print("\n--- 2. Testing File & App OS Automation Actions ---")
    # Test Create File
    res_create = siri_assistant.action_create_file("test_siri_doc.txt", "Tài liệu thử nghiệm được tạo tự động bởi Siri.")
    print("Create file action:", res_create)
    assert res_create["success"], "Failed to create file"
    test_path = res_create["path"]
    assert os.path.exists(test_path), f"File {test_path} was not created"

    # Test Read File
    res_read = siri_assistant.action_read_file(test_path)
    print("Read file action:", res_read)
    assert res_read["success"], "Failed to read file"
    assert "Tài liệu thử nghiệm" in res_read["content"]

    # Test Fast System Action: Weather
    res_weather = siri_assistant.check_fast_system_action("thời tiết hôm nay")
    print("Weather action:", res_weather)
    assert res_weather is not None and res_weather["success"]

    # Test Fast System Action: Timer
    res_timer = siri_assistant.check_fast_system_action("hẹn giờ 10 phút")
    print("Timer action:", res_timer)
    assert res_timer is not None and res_timer["success"]

    # Test Fast System Action: Create File with natural prompt
    res_pattern_create = siri_assistant.check_fast_system_action("tạo file test_pattern.txt với nội dung Xin chào Siri Qwen")
    print("Natural create pattern action:", res_pattern_create)
    assert res_pattern_create is not None and res_pattern_create["success"]
    print("✓ All OS automation actions verified successfully!")

def test_voice_synthesizer():
    print("\n--- 3. Testing Multilingual Neural Voice Synthesizer ---")
    raw_md = "### Xin chào! **Tôi là Siri**, hãy xem `code` và https://apple.com 🌤️"
    cleaned = clean_text_for_speech(raw_md)
    print(f"Raw: {raw_md}")
    print(f"Cleaned: {cleaned}")
    assert "**" not in cleaned and "###" not in cleaned and "http" not in cleaned
    assert "Xin chào! Tôi là Siri" in cleaned

    # Language detection
    assert detect_language("Xin chào Việt Nam") == "vi"
    assert detect_language("Hello world, how are you?") == "en"
    assert detect_language("こんにちは、元気ですか？") == "ja"
    print("✓ Language detection accurate for vi, en, ja!")

    # Voice ID resolution
    assert "vi-VN" in voice_synthesizer.get_voice_id("Xin chào")
    assert "en-US" in voice_synthesizer.get_voice_id("Hello")
    assert "ja-JP" in voice_synthesizer.get_voice_id("こんにちは")
    print("✓ Multilingual Voice IDs resolved accurately!")

def test_backward_compatibility():
    print("\n--- 4. Testing Legacy gemini_assistant Wrapper ---")
    status, msg, models = gemini_assistant.validate_api_key()
    print("gemini_assistant validate:", status, msg, models)
    assert status is True
    assert "qwen2.5:1.5b" in models
    print("✓ Backward compatibility wrapper fully functional!")

def test_siri_tab_ui():
    print("\n--- 5. Testing Dynamic Island SiriTab UI Widget ---")
    tab = GeminiTab()
    assert tab.title_lbl.get_text() == "Apple Intelligence • Qwen 2.5"
    assert hasattr(tab, "siri_orb")
    assert hasattr(tab, "speaker_btn")
    assert hasattr(tab, "suggestions_box")
    print("✓ Dynamic Island Siri Tab initialized successfully!")

if __name__ == "__main__":
    test_local_model()
    test_file_and_app_actions()
    test_voice_synthesizer()
    test_backward_compatibility()
    test_siri_tab_ui()
    print("\n🎉 ALL LOCAL QWEN 2.5 1.5B SIRI TESTS PASSED PERFECTLY!")
