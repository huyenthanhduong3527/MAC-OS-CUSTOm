"""
System Vitals Tab for Expanded Dynamic Island.
Displays real-time CPU, RAM, and Battery / Power status cards with progress bars.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf

class VitalsTab(Gtk.Box):
    def __init__(self, system_mon):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.get_style_context().add_class("tab-content")

        self.system_mon = system_mon

        # 3 Cards in horizontal row
        cards_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cards_box.set_homogeneous(True)

        # 1. CPU Card
        self.cpu_card = self._create_card("cpu", "CPU LOAD", "0%", "16 Cores")
        cards_box.pack_start(self.cpu_card["box"], True, True, 0)

        # 2. RAM Card
        self.ram_card = self._create_card("ram", "MEMORY", "0%", "0 / 0 GB")
        cards_box.pack_start(self.ram_card["box"], True, True, 0)

        # 3. Battery / Power Card
        self.bat_card = self._create_card("battery", "POWER", "100%", "AC Connected")
        cards_box.pack_start(self.bat_card["box"], True, True, 0)

        self.pack_start(cards_box, True, True, 0)

        self.update()

    def _create_card(self, icon_name, label_text, val_text, sub_text):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.get_style_context().add_class("vital-card")

        # Top icon + label
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon_img = Gtk.Image.new_from_pixbuf(get_pixbuf(icon_name, 14, "#38bdf8"))
        lbl = Gtk.Label(label=label_text)
        lbl.get_style_context().add_class("vital-label")
        top_row.pack_start(icon_img, False, False, 0)
        top_row.pack_start(lbl, False, False, 0)
        box.pack_start(top_row, False, False, 0)

        # Big Value
        val_lbl = Gtk.Label(label=val_text)
        val_lbl.get_style_context().add_class("vital-value")
        val_lbl.set_xalign(0.0)
        box.pack_start(val_lbl, False, False, 0)

        # Progress bar
        prog = Gtk.ProgressBar()
        prog.set_fraction(0.0)
        prog.set_show_text(False)
        box.pack_start(prog, False, False, 0)

        # Subtext
        sub_lbl = Gtk.Label(label=sub_text)
        sub_lbl.get_style_context().add_class("vital-subtext")
        sub_lbl.set_xalign(0.0)
        box.pack_start(sub_lbl, False, False, 0)

        return {
            "box": box,
            "val_lbl": val_lbl,
            "prog": prog,
            "sub_lbl": sub_lbl,
            "icon_img": icon_img
        }

    def update(self):
        metrics = self.system_mon.refresh()

        # Update CPU
        cpu_val = metrics["cpu_pct"]
        self.cpu_card["val_lbl"].set_text(f"{cpu_val:.1f}%")
        self.cpu_card["prog"].set_fraction(min(1.0, cpu_val / 100.0))

        # Update RAM
        ram_val = metrics["ram_pct"]
        self.ram_card["val_lbl"].set_text(f"{ram_val:.1f}%")
        self.ram_card["prog"].set_fraction(min(1.0, ram_val / 100.0))
        self.ram_card["sub_lbl"].set_text(f"{metrics['ram_used_gb']:.1f} / {metrics['ram_total_gb']:.1f} GB")

        # Update Battery / Power
        if metrics["has_battery"]:
            bat_pct = metrics["battery_pct"]
            status = "Charging ⚡" if metrics["is_charging"] else "Discharging"
            self.bat_card["val_lbl"].set_text(f"{bat_pct}%")
            self.bat_card["prog"].set_fraction(min(1.0, bat_pct / 100.0))
            self.bat_card["sub_lbl"].set_text(status)
        else:
            self.bat_card["val_lbl"].set_text("AC Power")
            self.bat_card["prog"].set_fraction(1.0)
            self.bat_card["sub_lbl"].set_text("Desktop Online")
