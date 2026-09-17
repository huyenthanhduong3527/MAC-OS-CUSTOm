"""
Notifications Tab for Dynamic Island.
Displays notification history captured from desktop apps with Apple glassmorphism styling.
Allows clearing notifications and shows unread badges.
"""

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf
from src.utils.artwork import load_artwork_pixbuf

class NotificationsTab(Gtk.Box):
    def __init__(self, notif_mgr):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.get_style_context().add_class("tab-content")
        self.notif_mgr = notif_mgr

        # Header Bar: Title, Count Badge, Clear All
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        bell_img = Gtk.Image.new_from_pixbuf(get_pixbuf("bell", 14, "#f43f5e"))
        header.pack_start(bell_img, False, False, 0)

        title = Gtk.Label(label="Notifications")
        title.get_style_context().add_class("media-title")
        header.pack_start(title, False, False, 0)

        self.badge_label = Gtk.Label(label="")
        self.badge_label.get_style_context().add_class("compact-subtitle")
        header.pack_start(self.badge_label, False, False, 4)

        # Clear All Button
        clear_btn = Gtk.Button(label="Clear All")
        clear_btn.get_style_context().add_class("ctrl-btn")
        clear_btn.connect("clicked", self._on_clear_clicked)
        header.pack_end(clear_btn, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Scrolled Window for notification cards
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_size_request(-1, 140)

        self.card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.scroll.add(self.card_box)

        self.pack_start(self.scroll, True, True, 0)

        self.update()

    def _on_clear_clicked(self, widget):
        self.notif_mgr.clear_all()
        self.update()

    def update(self):
        """Rebuild notification list based on history."""
        # Clear existing cards
        for child in self.card_box.get_children():
            self.card_box.remove(child)

        items = list(self.notif_mgr.history)
        count = len(items)

        if count > 0:
            self.badge_label.set_text(f"({count})")
            self.badge_label.show()
        else:
            self.badge_label.set_text("")
            self.badge_label.hide()

        if not items:
            # Apple-style empty state
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_margin_top(28)

            empty_lbl = Gtk.Label(label="No Notifications")
            empty_lbl.get_style_context().add_class("media-title")

            sub_lbl = Gtk.Label(label="All notifications appear here & on Dynamic Island")
            sub_lbl.get_style_context().add_class("vital-subtext")

            empty_box.pack_start(empty_lbl, False, False, 0)
            empty_box.pack_start(sub_lbl, False, False, 0)
            self.card_box.pack_start(empty_box, True, True, 0)
        else:
            for item in items:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                card.get_style_context().add_class("vital-card")

                # Header row inside card: App Name + Time
                top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

                app_lbl = Gtk.Label(label=item["app"].upper())
                app_lbl.get_style_context().add_class("event-app")
                top_row.pack_start(app_lbl, False, False, 0)

                time_lbl = Gtk.Label(label=item["time_str"])
                time_lbl.get_style_context().add_class("vital-subtext")
                top_row.pack_end(time_lbl, False, False, 0)

                card.pack_start(top_row, False, False, 0)

                # Content row: text on left, optional screenshot preview on right
                content_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

                # Title row
                title_lbl = Gtk.Label(label=item["title"])
                title_lbl.get_style_context().add_class("event-title")
                title_lbl.set_halign(Gtk.Align.START)
                title_lbl.set_line_wrap(True)
                text_col.pack_start(title_lbl, False, False, 0)

                # Body row if present
                if item["body"]:
                    body_lbl = Gtk.Label(label=item["body"])
                    body_lbl.get_style_context().add_class("event-subtitle")
                    body_lbl.set_halign(Gtk.Align.START)
                    body_lbl.set_line_wrap(True)
                    text_col.pack_start(body_lbl, False, False, 0)

                content_row.pack_start(text_col, True, True, 0)

                if item.get("image_path") and os.path.exists(item["image_path"]):
                    thumb = load_artwork_pixbuf(item["image_path"], size=36, radius=6)
                    if thumb:
                        thumb_img = Gtk.Image.new_from_pixbuf(thumb)
                        thumb_img.set_valign(Gtk.Align.CENTER)
                        content_row.pack_end(thumb_img, False, False, 0)

                card.pack_start(content_row, False, False, 0)
                self.card_box.pack_start(card, False, False, 0)

        self.card_box.show_all()
