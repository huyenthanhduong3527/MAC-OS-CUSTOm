#!/usr/bin/env python3
import sys

with open("src/ui/macos_notes_window.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Imports
import_target = "from src.utils.icons import get_pixbuf, get_image"
import_replacement = """from src.utils.icons import get_pixbuf, get_image
from src.utils.i18n import t, add_language_listener"""
assert import_target in text
text = text.replace(import_target, import_replacement, 1)

storage_import_target = "from src.modules.notes_storage import ("
storage_import_replacement = """from src.modules.notes_storage import (
    get_folder_display_name,"""
assert storage_import_target in text
text = text.replace(storage_import_target, storage_import_replacement, 1)

# 2. TrafficLightsWidget tooltips
tl_target = """        self.dot_red = TrafficLightDot(
            color_normal=(1.0, 0.37, 0.34),
            color_hover=(1.0, 0.28, 0.25),
            color_border=(0.88, 0.27, 0.24, 0.8),
            tooltip="Đóng (Close)",
            symbol="✕",
            cb=on_close
        )
        self.dot_yellow = TrafficLightDot(
            color_normal=(1.0, 0.74, 0.18),
            color_hover=(1.0, 0.68, 0.10),
            color_border=(0.87, 0.63, 0.14, 0.8),
            tooltip="Thu nhỏ (Minimize)",
            symbol="—",
            cb=on_minimize
        )
        self.dot_green = TrafficLightDot(
            color_normal=(0.15, 0.79, 0.25),
            color_hover=(0.10, 0.72, 0.20),
            color_border=(0.10, 0.67, 0.16, 0.8),
            tooltip="Phóng to (Zoom)",
            symbol="⤢",
            cb=on_maximize
        )"""

tl_replacement = """        self.dot_red = TrafficLightDot(
            color_normal=(1.0, 0.37, 0.34),
            color_hover=(1.0, 0.28, 0.25),
            color_border=(0.88, 0.27, 0.24, 0.8),
            tooltip=t("tl_close", "Đóng"),
            symbol="✕",
            cb=on_close
        )
        self.dot_yellow = TrafficLightDot(
            color_normal=(1.0, 0.74, 0.18),
            color_hover=(1.0, 0.68, 0.10),
            color_border=(0.87, 0.63, 0.14, 0.8),
            tooltip=t("tl_minimize", "Thu nhỏ"),
            symbol="—",
            cb=on_minimize
        )
        self.dot_green = TrafficLightDot(
            color_normal=(0.15, 0.79, 0.25),
            color_hover=(0.10, 0.72, 0.20),
            color_border=(0.10, 0.67, 0.16, 0.8),
            tooltip=t("tl_zoom", "Phóng to"),
            symbol="⤢",
            cb=on_maximize
        )"""
assert tl_target in text
text = text.replace(tl_target, tl_replacement, 1)

# 3. AudioInspectorPanel strings
insp_target = """        self.lbl_header_title = Gtk.Label(label="Ghi âm thoại")"""
insp_replacement = """        self.lbl_header_title = Gtk.Label(label=t("notes_audio_message", "Ghi âm thoại"))"""
assert insp_target in text
text = text.replace(insp_target, insp_replacement, 1)

done_btn_target = """        self.btn_done = Gtk.Button(label="Xong")"""
done_btn_replacement = """        self.btn_done = Gtk.Button(label=t("done", "Xong"))"""
assert done_btn_target in text
text = text.replace(done_btn_target, done_btn_replacement, 1)

lbl_sec_target = """        lbl_sec = Gtk.Label(label="BẢN BÓC BĂNG THOẠI")"""
lbl_sec_replacement = """        lbl_sec = Gtk.Label(label=t("notes_transcript", "Bản ghi lời thoại").upper())
        self.lbl_transcript_sec = lbl_sec"""
assert lbl_sec_target in text
text = text.replace(lbl_sec_target, lbl_sec_replacement, 1)

# 4. Notes window init: title and language listener
init_target = """        self._load_css()
        self._setup_ui()"""
init_replacement = """        self._load_css()
        self._setup_ui()
        self.set_title(t("notes_title", "Ghi chú"))
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass"""
assert init_target in text
text = text.replace(init_target, init_replacement, 1)

# 5. Toolbar tooltips
tool_target = """        # Sidebar Toggle Button
        self.btn_sidebar_toggle = Gtk.Button()
        self.btn_sidebar_toggle.set_valign(Gtk.Align.CENTER)
        self.btn_sidebar_toggle.set_size_request(30, 30)
        self.btn_sidebar_toggle.get_style_context().add_class("mac-tool-btn")
        self.btn_sidebar_toggle.set_tooltip_text("Ẩn / Hiện thanh bên")
        self.btn_sidebar_toggle.add(get_image("sidebar", 16, "#6e6e73"))
        self.btn_sidebar_toggle.connect("clicked", lambda _: self.toggle_sidebar())
        self.toolbar.pack_start(self.btn_sidebar_toggle, False, False, 0)

        # Center Title: Note title
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        center_box.set_valign(Gtk.Align.CENTER)
        self.lbl_window_title = Gtk.Label(label="Call with Rigo Rangel")
        self.lbl_window_title.get_style_context().add_class("mac-window-title")
        self.lbl_window_title.set_halign(Gtk.Align.CENTER)
        center_box.pack_start(self.lbl_window_title, False, False, 0)

        self.lbl_window_subtitle = Gtk.Label(label="iCloud - May 2, 2024 at 7:34 PM")
        self.lbl_window_subtitle.get_style_context().add_class("mac-window-subtitle")
        self.lbl_window_subtitle.set_halign(Gtk.Align.CENTER)
        center_box.pack_start(self.lbl_window_subtitle, False, False, 0)
        self.toolbar.pack_start(center_box, True, True, 0)

        # Right Action Icons: Aa, Checklist, Table, Paperclip, Pen, Lock, Share, Mic, More
        right_tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        right_tools.set_valign(Gtk.Align.CENTER)

        def make_tool_btn(icon_name, tooltip, cb):
            btn = Gtk.Button()
            btn.set_size_request(28, 28)
            btn.get_style_context().add_class("mac-tool-btn")
            btn.set_tooltip_text(tooltip)
            btn.add(get_image(icon_name, 16, "#6e6e73"))
            btn.connect("clicked", lambda _: cb())
            return btn

        # Format Aa
        self.btn_format = make_tool_btn("format_aa", "Định dạng chữ (Format)", self._show_format_popover)
        right_tools.pack_start(self.btn_format, False, False, 0)

        # Checklist
        self.btn_toolbar_checklist = make_tool_btn("checklist", "Chèn danh sách việc cần làm", self._insert_checklist)
        right_tools.pack_start(self.btn_toolbar_checklist, False, False, 0)

        # Table
        self.btn_toolbar_table = make_tool_btn("table", "Chèn bảng", self._insert_table)
        right_tools.pack_start(self.btn_toolbar_table, False, False, 0)

        # Paperclip / Attachment
        self.btn_toolbar_paperclip = make_tool_btn("paperclip", "Đính kèm tệp / hình ảnh", self._attach_file)
        right_tools.pack_start(self.btn_toolbar_paperclip, False, False, 0)

        # Pen / Markup
        self.btn_toolbar_markup = make_tool_btn("pen_markup", "Bút vẽ & phác thảo", self._toggle_markup)
        right_tools.pack_start(self.btn_toolbar_markup, False, False, 0)

        # Lock
        self.btn_toolbar_lock = make_tool_btn("lock", "Khóa ghi chú", self._toggle_lock)
        right_tools.pack_start(self.btn_toolbar_lock, False, False, 0)

        # Share / AirDrop
        self.btn_toolbar_share = make_tool_btn("share", "Chia sẻ qua AirDrop / Email", self._share_note)
        right_tools.pack_start(self.btn_toolbar_share, False, False, 0)

        # Audio Recording / Mic
        self.btn_toolbar_mic = make_tool_btn("mic", "Ghi âm & bóc băng thoại", self.toggle_audio_inspector)
        right_tools.pack_start(self.btn_toolbar_mic, False, False, 0)

        # Delete / Trash Can Button
        self.btn_toolbar_trash = make_tool_btn("trash", "Xóa ghi chú này (Delete hoặc Ctrl+Delete)", self._delete_current)
        self.btn_toolbar_trash.get_style_context().add_class("mac-trash-btn")
        right_tools.pack_start(self.btn_toolbar_trash, False, False, 0)

        # More (...)
        self.btn_more_toolbar = make_tool_btn("dots_horizontal", "Tùy chọn khác", self._show_more_menu)"""

tool_replacement = """        # Sidebar Toggle Button
        self.btn_sidebar_toggle = Gtk.Button()
        self.btn_sidebar_toggle.set_valign(Gtk.Align.CENTER)
        self.btn_sidebar_toggle.set_size_request(30, 30)
        self.btn_sidebar_toggle.get_style_context().add_class("mac-tool-btn")
        self.btn_sidebar_toggle.set_tooltip_text(t("notes_toggle_sidebar", "Ẩn / Hiện thanh bên"))
        self.btn_sidebar_toggle.add(get_image("sidebar", 16, "#6e6e73"))
        self.btn_sidebar_toggle.connect("clicked", lambda _: self.toggle_sidebar())
        self.toolbar.pack_start(self.btn_sidebar_toggle, False, False, 0)

        # Center Title: Note title
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        center_box.set_valign(Gtk.Align.CENTER)
        self.lbl_window_title = Gtk.Label(label=t("notes_title", "Ghi chú"))
        self.lbl_window_title.get_style_context().add_class("mac-window-title")
        self.lbl_window_title.set_halign(Gtk.Align.CENTER)
        center_box.pack_start(self.lbl_window_title, False, False, 0)

        self.lbl_window_subtitle = Gtk.Label(label=t("notes_no_notes", "Không có ghi chú nào"))
        self.lbl_window_subtitle.get_style_context().add_class("mac-window-subtitle")
        self.lbl_window_subtitle.set_halign(Gtk.Align.CENTER)
        center_box.pack_start(self.lbl_window_subtitle, False, False, 0)
        self.toolbar.pack_start(center_box, True, True, 0)

        # Right Action Icons: Aa, Checklist, Table, Paperclip, Pen, Lock, Share, Mic, More
        right_tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        right_tools.set_valign(Gtk.Align.CENTER)

        def make_tool_btn(icon_name, tooltip, cb):
            btn = Gtk.Button()
            btn.set_size_request(28, 28)
            btn.get_style_context().add_class("mac-tool-btn")
            btn.set_tooltip_text(tooltip)
            btn.add(get_image(icon_name, 16, "#6e6e73"))
            btn.connect("clicked", lambda _: cb())
            return btn

        # Format Aa
        self.btn_format = make_tool_btn("format_aa", t("notes_format_tooltip", "Định dạng chữ (Format)"), self._show_format_popover)
        right_tools.pack_start(self.btn_format, False, False, 0)

        # Checklist
        self.btn_toolbar_checklist = make_tool_btn("checklist", t("notes_checklist_tooltip", "Chèn danh sách việc cần làm"), self._insert_checklist)
        right_tools.pack_start(self.btn_toolbar_checklist, False, False, 0)

        # Table
        self.btn_toolbar_table = make_tool_btn("table", t("notes_table_tooltip", "Chèn bảng"), self._insert_table)
        right_tools.pack_start(self.btn_toolbar_table, False, False, 0)

        # Paperclip / Attachment
        self.btn_toolbar_paperclip = make_tool_btn("paperclip", t("notes_attach_tooltip", "Đính kèm tệp / hình ảnh"), self._attach_file)
        right_tools.pack_start(self.btn_toolbar_paperclip, False, False, 0)

        # Pen / Markup
        self.btn_toolbar_markup = make_tool_btn("pen_markup", t("notes_markup_tooltip", "Bút vẽ & phác thảo"), self._toggle_markup)
        right_tools.pack_start(self.btn_toolbar_markup, False, False, 0)

        # Lock
        self.btn_toolbar_lock = make_tool_btn("lock", t("notes_lock_tooltip", "Khóa ghi chú"), self._toggle_lock)
        right_tools.pack_start(self.btn_toolbar_lock, False, False, 0)

        # Share / AirDrop
        self.btn_toolbar_share = make_tool_btn("share", t("notes_share_tooltip", "Chia sẻ qua AirDrop / Email"), self._share_note)
        right_tools.pack_start(self.btn_toolbar_share, False, False, 0)

        # Audio Recording / Mic
        self.btn_toolbar_mic = make_tool_btn("mic", t("notes_audio_tooltip", "Ghi âm & bóc băng thoại"), self.toggle_audio_inspector)
        right_tools.pack_start(self.btn_toolbar_mic, False, False, 0)

        # Delete / Trash Can Button
        self.btn_toolbar_trash = make_tool_btn("trash", t("notes_delete_tooltip", "Xóa ghi chú này"), self._delete_current)
        self.btn_toolbar_trash.get_style_context().add_class("mac-trash-btn")
        right_tools.pack_start(self.btn_toolbar_trash, False, False, 0)

        # More (...)
        self.btn_more_toolbar = make_tool_btn("dots_horizontal", t("notes_more_tooltip", "Tùy chọn khác"), self._show_more_menu)"""
assert tool_target in text
text = text.replace(tool_target, tool_replacement, 1)

# 6. Folder refresh localized
folder_loop_target = """        for folder in self.notes_mgr.folders:
            f_id = folder["id"]
            f_name = folder["name"]"""
folder_loop_replacement = """        for folder in self.notes_mgr.folders:
            f_id = folder["id"]
            f_name = get_folder_display_name(f_id, folder.get("name", ""))"""
assert folder_loop_target in text
text = text.replace(folder_loop_target, folder_loop_replacement, 1)

# 7. Notes search and compose
search_compose_target = """        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Tìm kiếm...")
        self.search_entry.get_style_context().add_class("mac-notes-search")
        self.search_entry.connect("search-changed", self._on_search_changed)
        top_bar.pack_start(self.search_entry, True, True, 0)

        # Apple Notes signature Yellow Compose button
        self.btn_new_note = Gtk.Button()
        self.btn_new_note.set_size_request(28, 28)
        self.btn_new_note.get_style_context().add_class("mac-notes-compose-btn")
        self.btn_new_note.add(get_image("plus", 14, "#ffffff"))
        self.btn_new_note.set_tooltip_text("Soạn ghi chú mới")"""

search_compose_replacement = """        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(t("notes_search_placeholder", "Tìm kiếm…"))
        self.search_entry.get_style_context().add_class("mac-notes-search")
        self.search_entry.connect("search-changed", self._on_search_changed)
        top_bar.pack_start(self.search_entry, True, True, 0)

        # Apple Notes signature Yellow Compose button
        self.btn_new_note = Gtk.Button()
        self.btn_new_note.set_size_request(28, 28)
        self.btn_new_note.get_style_context().add_class("mac-notes-compose-btn")
        self.btn_new_note.add(get_image("plus", 14, "#ffffff"))
        self.btn_new_note.set_tooltip_text(t("notes_new_note", "Soạn ghi chú mới"))"""
assert search_compose_target in text
text = text.replace(search_compose_target, search_compose_replacement, 1)

# 8. Untitled note
untitled_target = """n_title = note.get("title", "Không có tiêu đề")"""
untitled_replacement = """n_title = note.get("title", t("notes_untitled", "Không có tiêu đề"))"""
assert untitled_target in text
text = text.replace(untitled_target, untitled_replacement, 1)

# 9. Clear editor empty
clear_empty_target = """        try:
            self.lbl_window_title.set_text("Ghi chú")
            self.lbl_window_subtitle.set_text("Không có ghi chú nào")
            self.lbl_note_date.set_text("")
            self.title_entry.set_text("")
            self.title_entry.set_placeholder_text("Không có ghi chú")"""

clear_empty_replacement = """        try:
            self.lbl_window_title.set_text(t("notes_title", "Ghi chú"))
            self.lbl_window_subtitle.set_text(t("notes_no_notes", "Không có ghi chú nào"))
            self.lbl_note_date.set_text("")
            self.title_entry.set_text("")
            self.title_entry.set_placeholder_text(t("notes_empty_placeholder", "Không có ghi chú"))"""
assert clear_empty_target in text
text = text.replace(clear_empty_target, clear_empty_replacement, 1)

# 10. Create note default title
create_note_target = """new_n = self.notes_mgr.create_note(title="Ghi chú mới", folder=self.current_folder)"""
create_note_replacement = """new_n = self.notes_mgr.create_note(title=t("notes_new", "Ghi chú mới"), folder=self.current_folder)"""
assert create_note_target in text
text = text.replace(create_note_target, create_note_replacement, 1)

# 11. Format popover
popover_target = """        formats = [
            ("Tiêu đề lớn (Title)", lambda: self._apply_format("title")),
            ("Đầu đề (Heading)", lambda: self._apply_format("heading")),
            ("Đầu đề phụ (Subheading)", lambda: self._apply_format("subheading")),
            ("Thân bài (Body)", lambda: self._apply_format("body")),
            ("Đơn cách (Monospaced)", lambda: self._apply_format("mono")),
            ("Danh sách dấu chấm (Bullet List)", lambda: self._apply_format("bullet")),
            ("Danh sách số (Numbered List)", lambda: self._apply_format("number")),
        ]"""

popover_replacement = """        formats = [
            (t("format_title", "Tiêu đề lớn (Title)"), lambda: self._apply_format("title")),
            (t("format_heading", "Đầu đề (Heading)"), lambda: self._apply_format("heading")),
            (t("format_subheading", "Đầu đề phụ (Subheading)"), lambda: self._apply_format("subheading")),
            (t("format_body", "Thân bài (Body)"), lambda: self._apply_format("body")),
            (t("format_mono", "Đơn cách (Monospaced)"), lambda: self._apply_format("mono")),
            (t("format_bullet", "Danh sách dấu chấm (Bullet List)"), lambda: self._apply_format("bullet")),
            (t("format_number", "Danh sách số (Numbered List)"), lambda: self._apply_format("number")),
        ]"""
assert popover_target in text
text = text.replace(popover_target, popover_replacement, 1)

# 12. Context menu
ctx_target = """        is_trash = note.get("in_trash", False)
        if is_trash:
            menu.append(make_menu_item("restore", "Khôi phục ghi chú", lambda: self._restore_note_by_id(note["id"])))
            menu.append(make_menu_item("trash", "Xóa vĩnh viễn", lambda: self._delete_note_by_id(note["id"]), is_destructive=True))
        else:
            is_pinned = note.get("pinned", False)
            menu.append(make_menu_item("pin_slash" if is_pinned else "pin", "Bỏ ghim" if is_pinned else "Ghim ghi chú", lambda: [self.notes_mgr.toggle_pin(note["id"]), self._refresh_notes_list()]))
            menu.append(make_menu_item("duplicate", "Tạo bản sao (Duplicate)", lambda: [self.notes_mgr.duplicate_note(note["id"]), self._refresh_notes_list()]))

            sep = Gtk.SeparatorMenuItem()
            menu.append(sep)

            menu.append(make_menu_item("trash", "Xóa ghi chú (Delete)", lambda: self._delete_note_by_id(note["id"]), is_destructive=True))"""

ctx_replacement = """        is_trash = note.get("in_trash", False)
        if is_trash:
            menu.append(make_menu_item("restore", t("notes_restore", "Khôi phục ghi chú"), lambda: self._restore_note_by_id(note["id"])))
            menu.append(make_menu_item("trash", t("notes_delete_forever", "Xóa vĩnh viễn"), lambda: self._delete_note_by_id(note["id"]), is_destructive=True))
        else:
            is_pinned = note.get("pinned", False)
            pin_text = t("notes_unpin", "Bỏ ghim") if is_pinned else t("notes_pin", "Ghim ghi chú")
            menu.append(make_menu_item("pin_slash" if is_pinned else "pin", pin_text, lambda: [self.notes_mgr.toggle_pin(note["id"]), self._refresh_notes_list()]))
            menu.append(make_menu_item("duplicate", t("notes_duplicate", "Tạo bản sao (Duplicate)"), lambda: [self.notes_mgr.duplicate_note(note["id"]), self._refresh_notes_list()]))

            sep = Gtk.SeparatorMenuItem()
            menu.append(sep)

            menu.append(make_menu_item("trash", t("notes_delete", "Xóa ghi chú (Delete)"), lambda: self._delete_note_by_id(note["id"]), is_destructive=True))"""
assert ctx_target in text
text = text.replace(ctx_target, ctx_replacement, 1)

# 13. Add _on_language_changed and _retranslate_ui methods
method_to_add = """    def _on_language_changed(self, lang_code: str):
        GLib.idle_add(self._retranslate_ui)

    def _retranslate_ui(self):
        try:
            self.set_title(t("notes_title", "Ghi chú"))
            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("notes_search_placeholder", "Tìm kiếm…"))
            if hasattr(self, "btn_new_note"):
                self.btn_new_note.set_tooltip_text(t("notes_new_note", "Soạn ghi chú mới"))
            if hasattr(self, "btn_sidebar_toggle"):
                self.btn_sidebar_toggle.set_tooltip_text(t("notes_toggle_sidebar", "Ẩn / Hiện thanh bên"))
            if hasattr(self, "btn_format"):
                self.btn_format.set_tooltip_text(t("notes_format_tooltip", "Định dạng chữ (Format)"))
            if hasattr(self, "btn_toolbar_checklist"):
                self.btn_toolbar_checklist.set_tooltip_text(t("notes_checklist_tooltip", "Chèn danh sách việc cần làm"))
            if hasattr(self, "btn_toolbar_table"):
                self.btn_toolbar_table.set_tooltip_text(t("notes_table_tooltip", "Chèn bảng"))
            if hasattr(self, "btn_toolbar_paperclip"):
                self.btn_toolbar_paperclip.set_tooltip_text(t("notes_attach_tooltip", "Đính kèm tệp / hình ảnh"))
            if hasattr(self, "btn_toolbar_markup"):
                self.btn_toolbar_markup.set_tooltip_text(t("notes_markup_tooltip", "Bút vẽ & phác thảo"))
            if hasattr(self, "btn_toolbar_lock"):
                self.btn_toolbar_lock.set_tooltip_text(t("notes_lock_tooltip", "Khóa ghi chú"))
            if hasattr(self, "btn_toolbar_share"):
                self.btn_toolbar_share.set_tooltip_text(t("notes_share_tooltip", "Chia sẻ qua AirDrop / Email"))
            if hasattr(self, "btn_toolbar_mic"):
                self.btn_toolbar_mic.set_tooltip_text(t("notes_audio_tooltip", "Ghi âm & bóc băng thoại"))
            if hasattr(self, "btn_toolbar_trash"):
                self.btn_toolbar_trash.set_tooltip_text(t("notes_delete_tooltip", "Xóa ghi chú này"))
            if hasattr(self, "btn_more_toolbar"):
                self.btn_more_toolbar.set_tooltip_text(t("notes_more_tooltip", "Tùy chọn khác"))

            if hasattr(self, "audio_inspector"):
                self.audio_inspector.btn_done.set_label(t("done", "Xong"))
                self.audio_inspector.btn_skip_back.set_tooltip_text(t("notes_rewind_15", "Tua lùi 15 giây"))
                self.audio_inspector.btn_skip_fwd.set_tooltip_text(t("notes_forward_15", "Tua tới 15 giây"))
                self.audio_inspector.btn_play_pause.set_tooltip_text(t("notes_play_pause", "Phát / Tạm dừng"))
                self.audio_inspector.btn_trans_toggle.set_tooltip_text(t("notes_transcript_toggle", "Bật / Tắt hiển thị bóc băng"))
                self.audio_inspector.btn_record.set_tooltip_text(t("notes_record", "Ghi âm"))
                self.audio_inspector.btn_more.set_tooltip_text(t("notes_more_tooltip", "Tùy chọn khác"))
                if hasattr(self.audio_inspector, "lbl_transcript_sec"):
                    self.audio_inspector.lbl_transcript_sec.set_text(t("notes_transcript", "Bản ghi lời thoại").upper())
                if not self.current_note or not self.current_note.get("audio"):
                    self.audio_inspector.lbl_header_title.set_text(t("notes_audio_message", "Ghi âm thoại"))

            self._refresh_folders_list()
            self._refresh_notes_list()

            if not self.current_note:
                self._clear_editor_empty()
        except Exception as e:
            print(f"[Notes] Error retranslating UI: {e}")
"""

# Add before `def get_instance` or at end of MacOSNotesWindow
target_end = "    def _on_window_state_event(self, widget, event):"
assert target_end in text
text = text.replace(target_end, method_to_add + "\n" + target_end, 1)

with open("src/ui/macos_notes_window.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched src/ui/macos_notes_window.py")
