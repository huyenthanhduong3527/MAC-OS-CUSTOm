"""
macOS Spotlight Search for Ubuntu Linux.
Features:
- Authentic macOS Sequoia floating frosted glass pill interface.
- Instant App Launcher: Indexed from .desktop files with fuzzy search and high-res icons.
- Instant Math Calculator: Safe AST evaluation for expressions, functions, percentages.
- macOS System Quick Actions: Lock, Sleep, Restart, Shutdown, Dark/Light Mode, Settings, Widgets.
- Web Search fallback to default browser.
- Smooth keyboard navigation (Arrow Up/Down, Enter to launch, Escape to close).
- Dynamic Dark / Light theme synchronization.
"""

import os
import sys
import glob
import ast
import math
import operator
import subprocess
import urllib.parse
import time
from configparser import ConfigParser

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, GdkPixbuf
import cairo

from src.utils.theme import is_system_dark_mode
from src.utils.i18n import t

# Safe Math Operations
SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
}

SAFE_CONSTS = {
    "pi": math.pi,
    "e": math.e,
}

def eval_safe_math(expr: str):
    """Safely evaluates a math expression. Returns formatted string or None."""
    cleaned = expr.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    if not cleaned or not any(c in cleaned for c in "+-*/%^0123456789"):
        return None
    try:
        node = ast.parse(cleaned, mode="eval")
    except Exception:
        return None

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        elif isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return n.value
            return None
        elif isinstance(n, ast.BinOp):
            left = _eval(n.left)
            right = _eval(n.right)
            if left is None or right is None:
                return None
            op_type = type(n.op)
            if op_type in SAFE_OPS:
                return SAFE_OPS[op_type](left, right)
        elif isinstance(n, ast.UnaryOp):
            operand = _eval(n.operand)
            if operand is None:
                return None
            op_type = type(n.op)
            if op_type in SAFE_OPS:
                return SAFE_OPS[op_type](operand)
        elif isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name) and n.func.id in SAFE_FUNCS:
                args = [_eval(a) for a in n.args]
                if None in args:
                    return None
                return SAFE_FUNCS[n.func.id](*args)
        elif isinstance(n, ast.Name) and n.id in SAFE_CONSTS:
            return SAFE_CONSTS[n.id]
        return None

    try:
        res = _eval(node)
        if isinstance(res, (int, float)):
            if isinstance(res, float) and res.is_integer():
                res = int(res)
            elif isinstance(res, float):
                res = round(res, 6)
            return str(res)
    except Exception:
        return None
    return None


class SpotlightMagnifierIcon(Gtk.DrawingArea):
    """Draws authentic Apple SF Symbol magnifying glass."""
    def __init__(self, size=20):
        super().__init__()
        self.size = size
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._on_draw)

    def _on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0

        toplevel = widget.get_toplevel()
        is_dark = getattr(toplevel, "is_dark", False)

        if is_dark:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.70)
        else:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.60)

        cr.set_line_width(2.0)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        r = self.size * 0.32
        lens_cx = cx - self.size * 0.10
        lens_cy = cy - self.size * 0.10

        cr.arc(lens_cx, lens_cy, r, 0, 2 * math.pi)
        cr.stroke()

        h_start_x = lens_cx + r * math.cos(math.pi / 4)
        h_start_y = lens_cy + r * math.sin(math.pi / 4)
        h_end_x = h_start_x + self.size * 0.30
        h_end_y = h_start_y + self.size * 0.30

        cr.move_to(h_start_x, h_start_y)
        cr.line_to(h_end_x, h_end_y)
        cr.stroke()
        return False


class SpotlightSearchWindow(Gtk.Window):
    """macOS Sequoia Spotlight Search Window."""
    _instance = None

    @classmethod
    def get_instance(cls, parent_app=None):
        if cls._instance is None:
            cls._instance = SpotlightSearchWindow(parent_app)
        elif parent_app is not None:
            cls._instance.parent_app = parent_app
        return cls._instance

    def __init__(self, parent_app=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.parent_app = parent_app
        self.set_title("Spotlight Search")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_position(Gtk.WindowPosition.CENTER)

        screen = Gdk.Screen.get_default()
        if screen and screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())
        self.set_app_paintable(True)

        self.is_dark = is_system_dark_mode()
        self.results_data = []

        # Desktop app index
        self.apps_index = []
        self._index_desktop_apps()

        # Build UI
        self._build_ui()
        self._load_css()

        # Signals
        self.connect("draw", self._on_window_draw)
        self.connect("key-press-event", self._on_key_press)
        self.connect("focus-out-event", self._on_focus_out)

        # Dynamic System Theme Listener
        try:
            self._gnome_settings = Gio.Settings.new("org.gnome.desktop.interface")
            self._gnome_settings.connect("changed::color-scheme", lambda *_: GLib.idle_add(self._on_theme_changed))
            self._gnome_settings.connect("changed::gtk-theme", lambda *_: GLib.idle_add(self._on_theme_changed))
        except Exception:
            pass

    def _index_desktop_apps(self):
        """Index installed desktop applications."""
        dirs = [
            os.path.expanduser("~/.local/share/applications"),
            "/usr/share/applications",
            "/usr/local/share/applications",
            "/var/lib/snapd/desktop/applications",
            "/snap/share/applications"
        ]
        self.apps_index.clear()
        seen_names = set()
        seen_desktop_ids = set()

        for d in dirs:
            if not os.path.exists(d):
                continue
            for f in sorted(glob.glob(os.path.join(d, "*.desktop"))):
                base_id = os.path.basename(f)
                if base_id in seen_desktop_ids:
                    continue
                seen_desktop_ids.add(base_id)

                try:
                    cp = ConfigParser(interpolation=None)
                    cp.read(f, encoding="utf-8")
                    if not cp.has_section("Desktop Entry"):
                        continue
                    sec = cp["Desktop Entry"]
                    if sec.get("NoDisplay", "false").lower() == "true":
                        continue
                    if sec.get("Type", "Application") != "Application":
                        continue
                    name = sec.get("Name", "").strip()
                    if not name or name in seen_names:
                        continue
                    seen_names.add(name)

                    icon = sec.get("Icon", "application-x-executable").strip()
                    exec_cmd = sec.get("Exec", "").strip()
                    comment = sec.get("Comment", "").strip()
                    keywords = sec.get("Keywords", "").strip()

                    self.apps_index.append({
                        "name": name,
                        "icon": icon,
                        "exec": exec_cmd,
                        "comment": comment,
                        "keywords": keywords,
                        "file": f
                    })
                except Exception:
                    pass

    def _build_ui(self):
        self.root_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root_card.get_style_context().add_class("mac-spotlight-card")
        self.root_card.get_style_context().add_class("mac-dark" if self.is_dark else "mac-light")
        self.root_card.set_size_request(640, -1)
        self.add(self.root_card)

        # Header Search Bar (Height 56px)
        header_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        header_bar.get_style_context().add_class("mac-spotlight-header")
        header_bar.set_size_request(-1, 56)
        header_bar.set_margin_start(18)
        header_bar.set_margin_end(18)
        header_bar.set_margin_top(6)
        header_bar.set_margin_bottom(6)

        self.mag_icon = SpotlightMagnifierIcon(size=22)
        header_bar.pack_start(self.mag_icon, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("mac-spotlight-entry")
        self.entry.set_placeholder_text("Tìm kiếm trong Spotlight")
        self.entry.set_hexpand(True)
        self.entry.connect("changed", self._on_search_changed)
        header_bar.pack_start(self.entry, True, True, 0)

        # Esc badge
        esc_badge = Gtk.Label(label="esc")
        esc_badge.get_style_context().add_class("mac-spotlight-badge")
        esc_badge.set_valign(Gtk.Align.CENTER)
        header_bar.pack_end(esc_badge, False, False, 0)

        self.root_card.pack_start(header_bar, False, False, 0)

        # Separator line
        self.separator = Gtk.Box()
        self.separator.get_style_context().add_class("mac-spotlight-separator")
        self.separator.set_size_request(-1, 1)
        self.root_card.pack_start(self.separator, False, False, 0)
        self.separator.hide()

        # Scrolled Results with Gtk.ListBox
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_max_content_height(380)
        self.scrolled.set_propagate_natural_height(True)
        self.scrolled.get_style_context().add_class("mac-spotlight-scrolled")

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.listbox.connect("row-selected", self._on_row_selected)
        self.listbox.set_margin_top(4)
        self.listbox.set_margin_bottom(6)
        self.listbox.set_margin_start(4)
        self.listbox.set_margin_end(4)

        self.scrolled.add(self.listbox)
        self.root_card.pack_start(self.scrolled, True, True, 0)
        self.scrolled.hide()

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        .mac-spotlight-card {
            border-radius: 16px;
        }
        .mac-spotlight-entry {
            background: transparent;
            border: none;
            box-shadow: none;
            font-size: 19px;
            font-weight: 400;
            padding: 0;
            margin: 0;
        }
        .mac-dark .mac-spotlight-entry {
            color: #ffffff;
        }
        .mac-light .mac-spotlight-entry {
            color: #1d1d1f;
        }
        .mac-spotlight-badge {
            font-size: 10.5px;
            font-weight: 600;
            border-radius: 4px;
            padding: 2px 6px;
        }
        .mac-dark .mac-spotlight-badge {
            background-color: rgba(255, 255, 255, 0.12);
            color: rgba(255, 255, 255, 0.70);
            border: 0.5px solid rgba(255, 255, 255, 0.15);
        }
        .mac-light .mac-spotlight-badge {
            background-color: rgba(0, 0, 0, 0.07);
            color: rgba(0, 0, 0, 0.60);
            border: 0.5px solid rgba(0, 0, 0, 0.10);
        }
        .mac-spotlight-separator {
            min-height: 1px;
        }
        .mac-dark .mac-spotlight-separator {
            background-color: rgba(255, 255, 255, 0.10);
        }
        .mac-light .mac-spotlight-separator {
            background-color: rgba(0, 0, 0, 0.08);
        }
        listbox {
            background: transparent;
        }
        listboxrow {
            border-radius: 8px;
            padding: 6px 12px;
            margin: 2px 4px;
            background: transparent;
            transition: background-color 80ms ease;
        }
        .mac-dark listboxrow:hover {
            background-color: rgba(255, 255, 255, 0.08);
        }
        .mac-light listboxrow:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        listboxrow.mac-selected,
        listboxrow:selected,
        listboxrow:selected:backdrop,
        .mac-dark listboxrow.mac-selected,
        .mac-dark listboxrow:selected,
        .mac-dark listboxrow:selected:backdrop,
        .mac-light listboxrow.mac-selected,
        .mac-light listboxrow:selected,
        .mac-light listboxrow:selected:backdrop {
            background-color: #007aff;
        }
        listboxrow.mac-selected label,
        listboxrow:selected label,
        listboxrow:selected:backdrop label,
        .mac-dark listboxrow.mac-selected label,
        .mac-dark listboxrow:selected label,
        .mac-dark listboxrow:selected:backdrop label,
        .mac-light listboxrow.mac-selected label,
        .mac-light listboxrow:selected label,
        .mac-light listboxrow:selected:backdrop label {
            color: #ffffff;
        }
        .mac-item-title {
            font-size: 13.5px;
            font-weight: 500;
        }
        .mac-dark .mac-item-title {
            color: #ffffff;
        }
        .mac-light .mac-item-title {
            color: #1d1d1f;
        }
        .mac-item-sub {
            font-size: 11px;
            font-weight: 400;
        }
        .mac-dark .mac-item-sub {
            color: rgba(255, 255, 255, 0.55);
        }
        .mac-light .mac-item-sub {
            color: rgba(0, 0, 0, 0.50);
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _on_window_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = 16.0

        cr.save()
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw rounded card with authentic macOS glassmorphism
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi/2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi/2)
        cr.arc(r, h - r, r, math.pi/2, math.pi)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        if self.is_dark:
            cr.set_source_rgba(0.12, 0.12, 0.14, 0.96)
            cr.fill_preserve()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.14)
            cr.set_line_width(1.0)
            cr.stroke()
        else:
            cr.set_source_rgba(0.97, 0.97, 0.98, 0.97)
            cr.fill_preserve()
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.12)
            cr.set_line_width(1.0)
            cr.stroke()

        cr.restore()
        return False

    def _on_theme_changed(self, force_dark=None):
        if force_dark is not None:
            self.is_dark = bool(force_dark)
        else:
            self.is_dark = is_system_dark_mode()
        ctx = self.root_card.get_style_context()
        if self.is_dark:
            ctx.remove_class("mac-light")
            ctx.add_class("mac-dark")
        else:
            ctx.remove_class("mac-dark")
            ctx.add_class("mac-light")
        self.mag_icon.queue_draw()
        self.queue_draw()

    def _on_search_changed(self, entry):
        query = entry.get_text().strip()
        self._update_results(query)

    def _update_results(self, query):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self.results_data.clear()

        if not query:
            self.separator.hide()
            self.scrolled.hide()
            self.resize(640, 56)
            return

        # 1. Check math calculation
        math_res = eval_safe_math(query)
        if math_res is not None:
            self.results_data.append({
                "type": "calc",
                "title": f"{query} = {math_res}",
                "sub": "Máy tính nhanh • Nhấn Enter để sao chép vào bộ nhớ tạm",
                "value": math_res
            })

        # 2. Check System Actions
        q_lower = query.lower()
        system_actions = [
            ("Kho ứng dụng App Store (macOS)", "Khám phá & tải ứng dụng phần mềm máy tính", "appstore", ["appstore", "store", "app store", "app center", "snap store", "ung dung", "kho ung dung", "cai app"]),
            ("Cài đặt hệ thống (macOS Settings)", "Mở trung tâm thiết lập máy tính chuẩn Apple", "settings", ["settings", "cai dat", "he thong", "preference"]),
            ("Chuyển đổi Chế độ Sáng / Tối", "Đổi chủ đề Dark Mode hoặc Light Mode", "toggle-theme", ["dark", "light", "sang", "toi", "theme", "giao dien"]),
            ("Khóa màn hình ngay", "Khóa máy tính và màn hình làm việc", "lock", ["lock", "khoa", "khoa man hinh", "lockscreen"]),
            ("Chế độ ngủ (Suspend / Sleep)", "Tạm ngưng hệ thống để tiết kiệm điện", "sleep", ["sleep", "ngu", "tam dung", "suspend"]),
            ("Khởi động lại máy tính", "Khởi động lại hệ điều hành Ubuntu", "restart", ["restart", "khoi dong lai", "reboot"]),
            ("Tắt máy (Shut Down)", "Tắt nguồn hệ thống an toàn", "shutdown", ["shutdown", "tat may", "poweroff", "tat nguon"]),
            ("Dự báo Thời tiết", "Xem thời tiết 3 ngày & độ ẩm, lượng mưa", "weather", ["weather", "thoi tiet", "nhiet do"]),
            ("Lịch Âm Dương & Ngày lễ", "Xem lịch vạn niên & ngày tốt hoàng đạo", "calendar", ["calendar", "lich", "am lich", "lich am"]),
            ("Đảo Thông Minh Dynamic Island", "Thu phóng thanh đảo trạng thái trên đỉnh màn hình", "island", ["island", "dao", "dynamic island"]),
        ]

        for title, sub, action_id, keywords in system_actions:
            if any(kw in q_lower or q_lower in kw for kw in keywords):
                self.results_data.append({
                    "type": "system",
                    "title": title,
                    "sub": sub,
                    "action": action_id
                })

        # 3. Check Indexed Desktop Applications
        app_matches = []
        for app in self.apps_index:
            name_lower = app["name"].lower()
            exec_lower = app["exec"].lower()
            comment_lower = app["comment"].lower()
            keywords_lower = app["keywords"].lower()

            score = 0
            if name_lower.startswith(q_lower):
                score = 100
            elif q_lower in name_lower:
                score = 80
            elif q_lower in exec_lower:
                score = 60
            elif q_lower in keywords_lower:
                score = 40
            elif q_lower in comment_lower:
                score = 20

            if score > 0:
                app_matches.append((score, app))

        app_matches.sort(key=lambda x: x[0], reverse=True)
        for _, app in app_matches[:7]:
            self.results_data.append({
                "type": "app",
                "title": app["name"],
                "sub": app["comment"] or "Ứng dụng máy tính",
                "app": app
            })

        # 4. Web Search fallback
        self.results_data.append({
            "type": "web",
            "title": f'Tìm kiếm trên Google cho "{query}"',
            "sub": "Mở kết quả trên trình duyệt web mặc định",
            "query": query
        })

        # Render list rows
        for idx, item in enumerate(self.results_data):
            row = Gtk.ListBoxRow()
            row_box = self._create_row_content(item)
            row.add(row_box)
            self.listbox.add(row)
            row.show_all()

        if self.results_data:
            self.separator.show()
            self.scrolled.show()
            list_h = min(len(self.results_data) * 50 + 10, 360)
            self.scrolled.set_min_content_height(list_h)
            self.resize(640, 56 + 1 + list_h)
            first_row = self.listbox.get_row_at_index(0)
            if first_row:
                self.listbox.select_row(first_row)
        else:
            self.separator.hide()
            self.scrolled.hide()
            self.resize(640, 56)

    def _create_row_content(self, item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Icon
        icon_box = Gtk.Box()
        icon_box.set_size_request(32, 32)
        icon_box.set_valign(Gtk.Align.CENTER)

        if item["type"] == "calc":
            calc_icon = Gtk.Image.new_from_icon_name("accessories-calculator", Gtk.IconSize.LARGE_TOOLBAR)
            icon_box.pack_start(calc_icon, True, True, 0)
        elif item["type"] == "system":
            act = item.get("action", "")
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if act == "appstore":
                appstore_png = os.path.join(base_dir, "assets", "appstore_icon.png")
                if os.path.exists(appstore_png):
                    try:
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(appstore_png, 32, 32, True)
                        sys_icon = Gtk.Image.new_from_pixbuf(pb)
                    except Exception:
                        sys_icon = Gtk.Image.new_from_icon_name("softwarecenter", Gtk.IconSize.LARGE_TOOLBAR)
                else:
                    sys_icon = Gtk.Image.new_from_icon_name("softwarecenter", Gtk.IconSize.LARGE_TOOLBAR)
            elif act == "settings":
                settings_png = os.path.join(base_dir, "src", "ui", "settings_icon.png")
                if os.path.exists(settings_png):
                    try:
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(settings_png, 32, 32, True)
                        sys_icon = Gtk.Image.new_from_pixbuf(pb)
                    except Exception:
                        sys_icon = Gtk.Image.new_from_icon_name("preferences-system", Gtk.IconSize.LARGE_TOOLBAR)
                else:
                    sys_icon = Gtk.Image.new_from_icon_name("preferences-system", Gtk.IconSize.LARGE_TOOLBAR)
            else:
                sys_icon = Gtk.Image.new_from_icon_name("preferences-system", Gtk.IconSize.LARGE_TOOLBAR)
            icon_box.pack_start(sys_icon, True, True, 0)
        elif item["type"] == "app":
            app = item["app"]
            icon_name = app["icon"]
            theme = Gtk.IconTheme.get_default()
            if theme and theme.has_icon(icon_name):
                app_img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            elif os.path.exists(icon_name):
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_name, 32, 32, True)
                    app_img = Gtk.Image.new_from_pixbuf(pb)
                except Exception:
                    app_img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.LARGE_TOOLBAR)
            else:
                app_img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.LARGE_TOOLBAR)
            icon_box.pack_start(app_img, True, True, 0)
        elif item["type"] == "web":
            web_icon = Gtk.Image.new_from_icon_name("system-search", Gtk.IconSize.LARGE_TOOLBAR)
            icon_box.pack_start(web_icon, True, True, 0)

        box.pack_start(icon_box, False, False, 0)

        # Text VBox
        text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_vbox.set_valign(Gtk.Align.CENTER)

        t_lbl = Gtk.Label(label=item["title"])
        t_lbl.get_style_context().add_class("mac-item-title")
        t_lbl.set_xalign(0.0)
        t_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        text_vbox.pack_start(t_lbl, False, False, 0)

        s_lbl = Gtk.Label(label=item["sub"])
        s_lbl.get_style_context().add_class("mac-item-sub")
        s_lbl.set_xalign(0.0)
        s_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        text_vbox.pack_start(s_lbl, False, False, 0)

        box.pack_start(text_vbox, True, True, 0)

        # Return hint symbol
        ret_lbl = Gtk.Label(label="↵")
        ret_lbl.get_style_context().add_class("mac-item-sub")
        ret_lbl.set_valign(Gtk.Align.CENTER)
        box.pack_end(ret_lbl, False, False, 6)

        return box

    def _on_row_selected(self, listbox, row):
        for child in listbox.get_children():
            child.get_style_context().remove_class("mac-selected")
        if row is not None:
            row.get_style_context().add_class("mac-selected")

    def _on_row_activated(self, listbox, row):
        idx = row.get_index()
        self._activate_item(idx)

    def _activate_item(self, idx):
        if idx < 0 or idx >= len(self.results_data):
            return

        item = self.results_data[idx]
        item_type = item["type"]

        self.hide_spotlight()

        if item_type == "calc":
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.set_text(item["value"], -1)
            cb.store()
            if self.parent_app and hasattr(self.parent_app, "_on_notification_received"):
                self.parent_app._on_notification_received("Máy tính", "Đã sao chép kết quả", item["value"])

        elif item_type == "system":
            action = item["action"]
            if action == "appstore":
                run_sh = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "run.sh")
                if os.path.exists(run_sh):
                    subprocess.Popen([run_sh, "--appstore"])
                else:
                    subprocess.Popen(["python3", "main.py", "--appstore"])
            elif action == "settings":
                if self.parent_app and hasattr(self.parent_app, "open_macos_settings_window"):
                    self.parent_app.open_macos_settings_window()
                else:
                    subprocess.Popen(["python3", "main.py", "settings"])
            elif action == "toggle-theme":
                from src.utils.theme import toggle_dark_mode
                toggle_dark_mode()
            elif action == "lock":
                try:
                    subprocess.run(["gdbus", "call", "--session", "--dest", "org.gnome.ScreenSaver", "--object-path", "/org/gnome/ScreenSaver", "--method", "org.gnome.ScreenSaver.Lock"], timeout=1)
                except Exception:
                    subprocess.run(["loginctl", "lock-session"], timeout=1)
            elif action == "sleep":
                subprocess.Popen(["systemctl", "suspend"])
            elif action == "restart":
                subprocess.Popen(["gnome-session-quit", "--reboot"])
            elif action == "shutdown":
                subprocess.Popen(["gnome-session-quit", "--power-off"])
            elif action == "weather":
                if self.parent_app and hasattr(self.parent_app, "toggle_desktop_weather"):
                    self.parent_app.toggle_desktop_weather()
                else:
                    subprocess.Popen(["python3", "main.py", "weather"])
            elif action == "calendar":
                if self.parent_app and hasattr(self.parent_app, "toggle_desktop_calendar"):
                    self.parent_app.toggle_desktop_calendar()
                else:
                    subprocess.Popen(["python3", "main.py", "calendar"])
            elif action == "island":
                if self.parent_app:
                    if self.parent_app.state == "expanded":
                        self.parent_app.collapse()
                    else:
                        self.parent_app.expand()

        elif item_type == "app":
            app = item["app"]
            exec_str = app["exec"]
            clean_cmd = []
            for p in exec_str.split():
                if p in ("%u", "%U", "%f", "%F", "%i", "%c", "%k", "--sm-disable"):
                    continue
                clean_cmd.append(p)
            if clean_cmd:
                try:
                    subprocess.Popen(clean_cmd)
                except Exception as e:
                    print(f"[Spotlight] Error launching app {app['name']}: {e}")

        elif item_type == "web":
            url = f"https://www.google.com/search?q={urllib.parse.quote(item['query'])}"
            try:
                subprocess.Popen(["xdg-open", url])
            except Exception as e:
                print(f"[Spotlight] Error opening web browser: {e}")

    def _on_key_press(self, widget, event):
        key = event.keyval
        if key == Gdk.KEY_Escape:
            self.hide_spotlight()
            return True
        elif key == Gdk.KEY_Down:
            sel_row = self.listbox.get_selected_row()
            cur_idx = sel_row.get_index() if sel_row else -1
            if cur_idx < len(self.results_data) - 1:
                next_row = self.listbox.get_row_at_index(cur_idx + 1)
                if next_row:
                    self.listbox.select_row(next_row)
            return True
        elif key == Gdk.KEY_Up:
            sel_row = self.listbox.get_selected_row()
            cur_idx = sel_row.get_index() if sel_row else 0
            if cur_idx > 0:
                prev_row = self.listbox.get_row_at_index(cur_idx - 1)
                if prev_row:
                    self.listbox.select_row(prev_row)
            return True
        elif key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            sel_row = self.listbox.get_selected_row()
            if sel_row:
                self._activate_item(sel_row.get_index())
            return True
        return False

    def _on_focus_out(self, widget, event):
        GLib.timeout_add(200, self._check_focus_and_hide)
        return False

    def _check_focus_and_hide(self):
        # Ignore focus-out within 600ms of opening to avoid race conditions with GNOME Shell panel closing
        if time.time() - getattr(self, "_show_time", 0) < 0.6:
            return False
        if not self.has_toplevel_focus() and self.is_visible():
            self.hide_spotlight()
        return False

    def show_spotlight(self):
        self._on_theme_changed()
        self.entry.set_placeholder_text(t("spotlight_placeholder", "Tìm kiếm trong Spotlight"))
        self.entry.set_text("")
        self._update_results("")

        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor() if screen else 0
        geom = screen.get_monitor_geometry(monitor) if screen else Gdk.Rectangle()
        sw = geom.width if geom.width > 0 else 1920
        sh = geom.height if geom.height > 0 else 1080

        win_w = 640
        x = geom.x + (sw - win_w) // 2
        y = geom.y + int(sh * 0.18)

        self._show_time = time.time()
        self.move(x, y)
        self.show_all()
        self.separator.hide()
        self.scrolled.hide()
        self.present()
        self.entry.grab_focus()
        GLib.timeout_add(60, lambda: self.entry.grab_focus() or False)
        GLib.timeout_add(180, lambda: self.entry.grab_focus() or False)

    def hide_spotlight(self):
        self.hide()

    def toggle_spotlight(self):
        if self.is_visible():
            self.hide_spotlight()
        else:
            self.show_spotlight()
