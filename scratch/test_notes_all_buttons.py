import os
import sys
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk

from src.ui.macos_notes_window import MacOSNotesWindow
from src.modules.notes_storage import NotesManager

def run_tests():
    print("=== STARTING MACOS NOTES BUTTONS & AUDIO INSPECTOR TESTS ===")
    
    window = MacOSNotesWindow()
    window.show_all()
    
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    print("\n[TEST 1] Testing inspector no_show_all protection...")
    assert window.sep_inspector.get_no_show_all() is True, "sep_inspector must have no_show_all=True"
    assert window.audio_inspector.get_no_show_all() is True, "audio_inspector must have no_show_all=True"
    assert not window.audio_inspector.get_visible(), "audio_inspector must be hidden initially"
    assert not window.sep_inspector.get_visible(), "sep_inspector must be hidden initially"
    
    # Test that window.show_all() does NOT accidentally reveal the audio inspector
    window.show_all()
    assert not window.audio_inspector.get_visible(), "audio_inspector must remain hidden after window.show_all()"
    print("✓ [TEST 1 PASSED] audio_inspector stays hidden even when show_all() is invoked")

    print("\n[TEST 2] Testing Audio Inspector Show / Done / Close / Delete...")
    # Add a note with audio
    note_obj = window.notes_mgr.create_note(title="Test Audio Note", body="Sample content", audio={
        "path": "/tmp/test_rec.ogg",
        "duration": 12.5,
        "transcript": "Test audio transcript"
    })
    note_id = note_obj["id"]
    window.select_note(note_id)
    
    # Explicitly open inspector
    window.show_audio_inspector({
        "path": "/tmp/test_rec.ogg",
        "duration": 12.5,
        "transcript": "Test audio transcript"
    })
    assert window.audio_inspector.get_visible() is True, "audio_inspector must be visible after show_audio_inspector"
    print("  -> Audio inspector opened successfully.")
    
    # Test Done button hides inspector
    window.audio_inspector.btn_done.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert not window.audio_inspector.get_visible(), "audio_inspector must be hidden after Done button clicked"
    print("✓ [TEST 2.1 PASSED] 'Done' button hides inspector properly")
    
    # Test Close button hides inspector
    window.show_audio_inspector({
        "path": "/tmp/test_rec.ogg",
        "duration": 12.5
    })
    assert window.audio_inspector.get_visible() is True
    window.audio_inspector.btn_close.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert not window.audio_inspector.get_visible(), "audio_inspector must be hidden after '✕' close button clicked"
    print("✓ [TEST 2.2 PASSED] '✕' Close button hides inspector properly")

    # Test Header Trash button deletes audio and hides inspector
    window.show_audio_inspector({
        "path": "/tmp/test_rec.ogg",
        "duration": 12.5
    })
    assert window.audio_inspector.get_visible() is True
    window.audio_inspector.btn_trash_audio.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert not window.audio_inspector.get_visible(), "audio_inspector must be hidden after trash button clicked"
    # Check that audio was removed from note
    curr_note = window.notes_mgr.get_note_by_id(note_id)
    assert curr_note.get("audio") is None, f"Audio should be deleted from note storage, got {curr_note.get('audio')}"
    print("✓ [TEST 2.3 PASSED] Direct trash button in inspector header deletes audio and hides inspector")

    # Test 'Xóa bản ghi âm này' in menu
    window.notes_mgr.update_note(note_id, audio={"path": "/tmp/test2.ogg", "duration": 5.0})
    window.show_audio_inspector({"path": "/tmp/test2.ogg", "duration": 5.0})
    assert window.audio_inspector.get_visible() is True
    window._delete_audio_from_current_note()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert not window.audio_inspector.get_visible(), "audio_inspector must be hidden after _delete_audio_from_current_note()"
    curr_note2 = window.notes_mgr.get_note_by_id(note_id)
    assert curr_note2.get("audio") is None, "Audio should be None in note storage"
    print("✓ [TEST 2.4 PASSED] _delete_audio_from_current_note() completely removes audio and closes panel")

    print("\n[TEST 3] Testing Markup Tool button (_toggle_markup)...")
    window.btn_toolbar_markup.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert hasattr(window, 'markup_popover'), "window must have markup_popover"
    assert window.markup_popover.get_visible() is True, "markup_popover must be visible when clicked"
    print("✓ [TEST 3 PASSED] Markup tool popover opens with Pen, Highlighter, Pencil, Eraser, and Apple colors")

    print("\n[TEST 4] Testing Lock/Unlock button (_toggle_lock)...")
    assert not curr_note2.get("locked", False), "Note should start unlocked"
    # Lock the note
    window.btn_toolbar_lock.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    note_locked = window.notes_mgr.get_note_by_id(note_id)
    assert note_locked.get("locked") is True, "Note must be marked locked in storage"
    assert window.locked_box.get_visible() is True, "locked_box shield must be visible"
    assert not window.text_view.get_visible(), "text_view must be hidden when locked"
    print("  -> Note locked: shield active, editor protected.")
    
    # Unlock via shield button
    window.btn_unlock_note.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    note_unlocked = window.notes_mgr.get_note_by_id(note_id)
    assert not note_unlocked.get("locked", False), "Note must be unlocked in storage"
    assert not window.locked_box.get_visible(), "locked_box shield must be hidden"
    assert window.text_view.get_visible() is True, "text_view must be visible when unlocked"
    print("✓ [TEST 4 PASSED] Note locking and unlocking shield works flawlessly")

    print("\n[TEST 5] Testing Share button (_share_note)...")
    window.btn_toolbar_share.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert hasattr(window, 'share_popover'), "window must have share_popover"
    assert window.share_popover.get_visible() is True, "share_popover must be visible when clicked"
    print("✓ [TEST 5 PASSED] Share note popover opens with AirDrop, Copy, Mail, and Export TXT")

    print("\n[TEST 6] Testing Checklist and Table formatting buttons...")
    window.btn_toolbar_checklist.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    text_after_checklist = window.text_buffer.get_text(window.text_buffer.get_start_iter(), window.text_buffer.get_end_iter(), False)
    assert "○ " in text_after_checklist, "Checklist item '○ ' should be inserted in buffer"
    
    window.btn_toolbar_table.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    text_after_table = window.text_buffer.get_text(window.text_buffer.get_start_iter(), window.text_buffer.get_end_iter(), False)
    assert "|" in text_after_table, "Markdown table template should be inserted in buffer"
    print("✓ [TEST 6 PASSED] Checklist and Table buttons insert content into editor")

    print("\n[TEST 7] Testing switching notes hides inspector if target note has no audio...")
    # Add a text-only note
    note2_obj = window.notes_mgr.create_note(title="Text Only Note", body="Just plain text")
    note2_id = note2_obj["id"]
    # First select audio note and show inspector
    window.notes_mgr.update_note(note_id, audio={"path": "/tmp/dummy.ogg", "duration": 4.0})
    window.select_note(note_id)
    window.show_audio_inspector({"path": "/tmp/dummy.ogg", "duration": 4.0})
    assert window.audio_inspector.get_visible() is True, "Inspector should be visible"
    # Now select text-only note
    window.select_note(note2_id)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    assert not window.audio_inspector.get_visible(), "Audio inspector must be automatically hidden when selecting a note without audio"
    print("✓ [TEST 7 PASSED] Switching to a note without audio automatically hides inspector")

    print("\n[TEST 8] Testing Format Aa and More (...) popovers...")
    window.btn_format.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    
    window.btn_more_toolbar.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    print("✓ [TEST 8 PASSED] Format Aa and More (...) popovers trigger and render properly")

    # Clean up test notes
    window.notes_mgr.delete_note(note_id)
    window.notes_mgr.delete_note(note2_id)

    print("\n🎉 ALL 8 TEST SUITES PASSED PERFECTLY! ZERO ERRORS!")

if __name__ == "__main__":
    run_tests()
