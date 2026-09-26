"""
Authentic Apple macOS Sequoia Language Picker Modal Dialog.
Allows selecting from all 500+ world languages and dialects with:
- Instant unaccented search across native names, English names, and countries
- Country flag emojis and locale badges
- macOS Bento list presentation with hover highlights
- Primary language assignment confirmation prompt
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from src.utils.theme import is_dark_mode
from src.utils.languages import get_all_world_languages, search_languages, find_language, LanguageInfo
from src.utils.i18n import t, _, get_current_language_info

class MacOSLanguagePickerDialog(Gtk.Dialog):
    """macOS Sequoia World Language Chooser Modal Dialog."""
    def __init__(self, parent_window=None, on_select_language=None):
        super().__init__(
            title=t("select_language_title"),
            transient_for=parent_window,
            modal=True,
            destroy_with_parent=True
        )
        self.on_select_language = on_select_language
        self.selected_lang: LanguageInfo = None
        self.all_langs = get_all_world_languages()

        self.set_default_size(520, 560)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT if parent_window else Gtk.WindowPosition.CENTER)

        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(12)

        # Title & Subtitle Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_lbl = Gtk.Label(label=t("select_language_title"))
        title_lbl.get_style_context().add_class("mac-general-title")
        title_lbl.set_xalign(0.0)

        sub_lbl = Gtk.Label(label="Hỗ trợ đầy đủ tất cả các ngôn ngữ và vùng lãnh thổ trên thế giới.")
        sub_lbl.get_style_context().add_class("mac-general-desc")
        sub_lbl.set_xalign(0.0)

        header_box.pack_start(title_lbl, False, False, 0)
        header_box.pack_start(sub_lbl, False, False, 0)
        content.pack_start(header_box, False, False, 0)

        # Search Bar
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Tìm kiếm ngôn ngữ, quốc gia, mã locale…")
        self.search_entry.get_style_context().add_class("mac-search-entry")
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        content.pack_start(search_box, False, False, 0)

        # Scrolled List Box
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.NONE)
        scroll.get_style_context().add_class("mac-bento-card")

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_row_selected)
        self.listbox.connect("row-activated", self._on_row_activated)
        scroll.add(self.listbox)
        content.pack_start(scroll, True, True, 0)

        # Action Buttons
        action_area = self.get_action_area()
        action_area.set_layout(Gtk.ButtonBoxStyle.END)
        action_area.set_spacing(10)

        self.btn_cancel = Gtk.Button(label=t("cancel"))
        self.btn_cancel.get_style_context().add_class("mac-action-btn")
        self.btn_cancel.connect("clicked", lambda _: self.destroy())
        action_area.pack_end(self.btn_cancel, False, False, 0)

        self.btn_add = Gtk.Button(label=t("add"))
        self.btn_add.get_style_context().add_class("mac-action-btn")
        self.btn_add.get_style_context().add_class("primary")
        self.btn_add.set_sensitive(False)
        self.btn_add.connect("clicked", lambda _: self._confirm_selection())
        action_area.pack_end(self.btn_add, False, False, 0)

        self._populate_list(self.all_langs)
        self.show_all()

    def _populate_list(self, langs):
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        for lang in langs:
            row = Gtk.ListBoxRow()
            row.lang_info = lang
            row.get_style_context().add_class("mac-lang-row")

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            row_box.set_margin_start(14)
            row_box.set_margin_end(14)
            row_box.set_margin_top(10)
            row_box.set_margin_bottom(10)

            # Flag
            flag_lbl = Gtk.Label(label=lang.flag)
            flag_lbl.get_style_context().add_class("mac-lang-flag")
            flag_lbl.set_valign(Gtk.Align.CENTER)
            row_box.pack_start(flag_lbl, False, False, 0)

            # Text
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=lang.native_name)
            name_lbl.set_xalign(0.0)
            name_lbl.get_style_context().add_class("mac-lang-name")

            sub_text = f"{lang.english_name}"
            sub_lbl = Gtk.Label(label=sub_text)
            sub_lbl.set_xalign(0.0)
            sub_lbl.get_style_context().add_class("mac-label-sub")

            text_box.pack_start(name_lbl, False, False, 0)
            text_box.pack_start(sub_lbl, False, False, 0)
            row_box.pack_start(text_box, True, True, 0)

            # Locale tag badge
            locale_badge = Gtk.Label(label=lang.raw_locale)
            locale_badge.get_style_context().add_class("mac-badge-admin")
            locale_badge.set_valign(Gtk.Align.CENTER)
            row_box.pack_start(locale_badge, False, False, 0)

            row.add(row_box)
            self.listbox.add(row)

        self.listbox.show_all()

    def _on_search_changed(self, entry):
        q = entry.get_text().strip()
        matched = search_languages(q)
        self._populate_list(matched)

    def _on_row_selected(self, listbox, row):
        if row and hasattr(row, "lang_info"):
            self.selected_lang = row.lang_info
            self.btn_add.set_sensitive(True)
        else:
            self.btn_add.set_sensitive(False)

    def _on_row_activated(self, listbox, row):
        if row and hasattr(row, "lang_info"):
            self.selected_lang = row.lang_info
            self._confirm_selection()

    def _confirm_selection(self):
        if not self.selected_lang:
            return

        curr_info = get_current_language_info()
        chosen = self.selected_lang

        # Prompt: Use as primary or keep current
        confirm_dialog = Gtk.Dialog(
            title="Ngôn ngữ chính",
            transient_for=self,
            modal=True,
            destroy_with_parent=True
        )
        confirm_dialog.set_default_size(420, 190)
        confirm_dialog.set_resizable(False)
        confirm_dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        box = confirm_dialog.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(12)

        prompt_lbl = Gtk.Label(
            label=f"Bạn có muốn sử dụng {chosen.native_name} làm ngôn ngữ chính không?"
        )
        prompt_lbl.get_style_context().add_class("mac-general-title")
        prompt_lbl.set_line_wrap(True)
        prompt_lbl.set_xalign(0.0)
        box.pack_start(prompt_lbl, False, False, 0)

        sub_prompt = Gtk.Label(
            label=(
                f"Các ứng dụng macOS và hệ thống sẽ hiển thị bằng {chosen.native_name}. "
                f"Bạn có thể chọn giữ {curr_info.native_name} làm ngôn ngữ chính và thêm {chosen.native_name} vào danh sách dự phòng."
            )
        )
        sub_prompt.get_style_context().add_class("mac-general-desc")
        sub_prompt.set_line_wrap(True)
        sub_prompt.set_xalign(0.0)
        box.pack_start(sub_prompt, False, False, 0)

        actions = confirm_dialog.get_action_area()
        actions.set_layout(Gtk.ButtonBoxStyle.END)
        actions.set_spacing(8)

        btn_cancel = Gtk.Button(label="Hủy")
        btn_cancel.get_style_context().add_class("mac-action-btn")
        confirm_dialog.add_action_widget(btn_cancel, Gtk.ResponseType.CANCEL)

        btn_keep = Gtk.Button(label=f"Giữ {curr_info.native_name}")
        btn_keep.get_style_context().add_class("mac-action-btn")
        confirm_dialog.add_action_widget(btn_keep, Gtk.ResponseType.NO)

        btn_primary = Gtk.Button(label=f"Dùng {chosen.native_name}")
        btn_primary.get_style_context().add_class("mac-action-btn")
        btn_primary.get_style_context().add_class("primary")
        confirm_dialog.add_action_widget(btn_primary, Gtk.ResponseType.YES)

        confirm_dialog.show_all()
        resp = confirm_dialog.run()
        confirm_dialog.destroy()

        if resp == Gtk.ResponseType.YES:
            # Selected as Primary
            self.destroy()
            if self.on_select_language:
                self.on_select_language(chosen, make_primary=True)
        elif resp == Gtk.ResponseType.NO:
            # Added as Secondary
            self.destroy()
            if self.on_select_language:
                self.on_select_language(chosen, make_primary=False)
