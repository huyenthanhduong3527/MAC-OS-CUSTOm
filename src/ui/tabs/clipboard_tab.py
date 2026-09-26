"""
Clipboard History Tab for Dynamic Island.
Displays captured clipboard history with Apple-inspired cards,
search filtering, 1-tap re-copying, and category chips (All, Text, Link, Code).
"""

import time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf
from src.modules.sound import SoundManager

class ClipboardTab(Gtk.Box):
    def __init__(self, clipboard_mgr):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.get_style_context().add_class("tab-content")
        self.clipboard_mgr = clipboard_mgr
        self.active_filter = "all" # 'all', 'text', 'url', 'code'
        self.search_query = ""

        # 1. Header Bar
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        clip_img = Gtk.Image.new_from_pixbuf(get_pixbuf("clipboard", 14, "#38bdf8"))
        header.pack_start(clip_img, False, False, 0)

        title = Gtk.Label(label="Clipboard")
        title.get_style_context().add_class("media-title")
        header.pack_start(title, False, False, 0)

        self.badge_label = Gtk.Label(label="")
        self.badge_label.get_style_context().add_class("compact-subtitle")
        header.pack_start(self.badge_label, False, False, 4)

        clear_btn = Gtk.Button(label="Xóa tất cả")
        clear_btn.get_style_context().add_class("ctrl-btn")
        clear_btn.connect("clicked", self._on_clear_all_clicked)
        header.pack_end(clear_btn, False, False, 0)

        self.pack_start(header, False, False, 0)

        # 2. Search & Filter Bar
        filter_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Search Entry
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Tìm kiếm nội dung...")
        self.search_entry.get_style_context().add_class("search-entry")
        self.search_entry.set_size_request(160, 26)
        self.search_entry.connect("changed", self._on_search_changed)
        filter_bar.pack_start(self.search_entry, True, True, 0)

        # Category Buttons
        self.filter_buttons = {}
        filters = [
            ("all", "Tất cả"),
            ("text", "Chữ"),
            ("url", "Link"),
            ("code", "Code")
        ]
        for fid, flabel in filters:
            fbtn = Gtk.Button(label=flabel)
            fbtn.get_style_context().add_class("ctrl-btn")
            if fid == "all":
                fbtn.get_style_context().add_class("active")
            fbtn.connect("clicked", lambda b, f=fid: self._on_filter_clicked(f))
            filter_bar.pack_start(fbtn, False, False, 0)
            self.filter_buttons[fid] = fbtn

        self.pack_start(filter_bar, False, False, 0)

        # 3. Scrolled Window for History Cards
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_size_request(-1, 140)

        self.card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.scroll.add(self.card_box)

        self.pack_start(self.scroll, True, True, 0)

        # Register callback for live updates
        self.clipboard_mgr.add_callback(lambda history: GLib.idle_add(self._on_history_changed, history))

        self.update()

    def _on_history_changed(self, history):
        if not getattr(self.clipboard_mgr, "_is_internal_copy", False):
            self.update()

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text().strip().lower()
        self.update()

    def _on_filter_clicked(self, filter_id):
        self.active_filter = filter_id
        for fid, btn in self.filter_buttons.items():
            if fid == filter_id:
                btn.get_style_context().add_class("active")
            else:
                btn.get_style_context().remove_class("active")
        self.update()

    def _on_clear_all_clicked(self, widget):
        self.clipboard_mgr.clear_history()
        self.update()

    def _on_card_press(self, event, text, copy_btn):
        if event.button == 1:
            self._on_copy_item(text, copy_btn)
        return False

    def _on_copy_item(self, text, copy_btn):
        if not self.clipboard_mgr.copy_to_clipboard(text):
            copy_btn.set_label("Không thể chép")
            GLib.timeout_add(1200, lambda: self._reset_copy_button(copy_btn, "Sao chép"))
            return

        SoundManager.get_instance().play_pop()

        # Visual feedback: Change button label & style temporarily
        orig_label = copy_btn.get_label()
        copy_btn.set_label("✓ Đã chép!")
        copy_btn.get_style_context().add_class("active")

        GLib.timeout_add(1200, lambda: self._reset_copy_button(copy_btn, orig_label))

    def _reset_copy_button(self, copy_btn, label):
        try:
            copy_btn.set_label(label)
            copy_btn.get_style_context().remove_class("active")
        except Exception:
            pass
        # Refresh list smoothly after feedback to reflect re-prioritized order
        if not getattr(self.clipboard_mgr, "_is_internal_copy", False):
            self.update()
        return False

    def _on_delete_item(self, item_id):
        self.clipboard_mgr.remove_item(item_id)
        self.update()

    def update(self):
        """Rebuild clipboard list based on active filter and search query."""
        for child in self.card_box.get_children():
            self.card_box.remove(child)

        items = list(self.clipboard_mgr.history)
        total_count = len(items)

        if total_count > 0:
            self.badge_label.set_text(f"({total_count})")
            self.badge_label.show()
        else:
            self.badge_label.set_text("")
            self.badge_label.hide()

        # Apply Category Filter
        if self.active_filter != "all":
            items = [item for item in items if item.get("type") == self.active_filter]

        # Apply Search Filter
        if self.search_query:
            items = [item for item in items if self.search_query in item.get("text", "").lower()]

        if not items:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_margin_top(26)

            empty_lbl = Gtk.Label(label="Khay nhớ tạm trống")
            empty_lbl.get_style_context().add_class("media-title")

            sub_lbl = Gtk.Label(label="Nội dung sao chép (văn bản, link, code) sẽ lưu tại đây")
            sub_lbl.get_style_context().add_class("vital-subtext")

            empty_box.pack_start(empty_lbl, False, False, 0)
            empty_box.pack_start(sub_lbl, False, False, 0)
            self.card_box.pack_start(empty_box, True, True, 0)
        else:
            for item in items:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                card.get_style_context().add_class("vital-card")

                # Top Row: Icon + Type Badge + Char Count + Time + Delete
                top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

                icon_name = "link" if item["type"] == "url" else ("code" if item["type"] == "code" else "text")
                icon_color = "#38bdf8" if item["type"] == "url" else ("#a78bfa" if item["type"] == "code" else "#94a3b8")
                type_img = Gtk.Image.new_from_pixbuf(get_pixbuf(icon_name, 12, icon_color))
                top_row.pack_start(type_img, False, False, 0)

                type_label = Gtk.Label(label=item["type"].upper())
                type_label.get_style_context().add_class("event-app")
                top_row.pack_start(type_label, False, False, 0)

                info_str = f"{item['length']} ký tự"
                if item["lines"] > 1:
                    info_str += f" • {item['lines']} dòng"
                info_lbl = Gtk.Label(label=info_str)
                info_lbl.get_style_context().add_class("vital-subtext")
                top_row.pack_start(info_lbl, False, False, 4)

                time_lbl = Gtk.Label(label=item["time_str"])
                time_lbl.get_style_context().add_class("vital-subtext")
                top_row.pack_end(time_lbl, False, False, 0)

                # Delete single item
                del_btn = Gtk.Button(label="✕")
                del_btn.get_style_context().add_class("ctrl-btn")
                del_btn.set_tooltip_text("Xóa mục này")
                del_btn.connect("clicked", lambda b, iid=item["id"]: self._on_delete_item(iid))
                top_row.pack_end(del_btn, False, False, 2)

                card.pack_start(top_row, False, False, 0)

                # Content Row: Preview Text + Copy Button
                content_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

                preview_lbl = Gtk.Label(label=item["preview"])
                preview_lbl.get_style_context().add_class("event-title")
                preview_lbl.set_halign(Gtk.Align.START)
                preview_lbl.set_line_wrap(True)
                preview_lbl.set_xalign(0.0)

                # Monospace for code snippets
                if item["type"] == "code":
                    preview_lbl.get_style_context().add_class("code-text")

                content_row.pack_start(preview_lbl, True, True, 0)

                copy_btn = Gtk.Button(label="Sao chép")
                copy_btn.get_style_context().add_class("ctrl-btn")
                copy_btn.set_valign(Gtk.Align.CENTER)
                copy_btn.connect("clicked", lambda b, txt=item["text"]: self._on_copy_item(txt, b))
                content_row.pack_end(copy_btn, False, False, 0)

                card.pack_start(content_row, False, False, 0)

                # Keep copy as an explicit action. Wrapping the card in an EventBox
                # caused button clicks to bubble and copy/rebuild the list twice.
                self.card_box.pack_start(card, False, False, 0)

        self.card_box.show_all()
