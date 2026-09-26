"""
Apple Intelligence Siri Tab for Dynamic Island Expanded View.
Powered by Local AI Model Qwen 2.5 1.5B with complete OS Automation and Multilingual Neural Voice.

Features:
- Animated Cairo-drawn Apple Intelligence Siri Orb with organic dynamic breathing glow
- Multi-turn conversation with local Qwen 2.5 1.5B (100% offline & private)
- System & OS Action execution: Open Apps, Open Files, Create Files/Documents, Weather, Timers
- Natural Multilingual Voice output with anti-repetition & anti-stutter
"""

import math
import time
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from src.utils.icons import get_pixbuf
from src.modules.siri_assistant import siri_assistant

class SiriOrbWidget(Gtk.DrawingArea):
    """Animated Apple Intelligence Siri Orb with vibrant organic glow."""
    def __init__(self, size=40):
        super().__init__()
        self.size = size
        self.set_size_request(size, size)
        self.phase = 0.0
        self.is_active = True
        self.connect("draw", self.on_draw)
        GLib.timeout_add(50, self._on_tick)

    def _on_tick(self):
        if self.is_active and self.get_visible():
            self.phase += 0.08
            if self.phase > 2 * math.pi:
                self.phase -= 2 * math.pi
            self.queue_draw()
        return True

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0
        base_r = min(w, h) / 2.0 - 4

        # Breathing radius oscillation
        r = base_r + math.sin(self.phase * 2.0) * 2.0

        # 1. Outer Glow
        glow = cairo.RadialGradient(cx, cy, r * 0.2, cx, cy, r * 1.3)
        glow.add_color_stop_rgba(0.0, 0.0, 0.95, 1.0, 0.45) # Cyan
        glow.add_color_stop_rgba(0.5, 0.6, 0.2, 0.95, 0.35) # Purple
        glow.add_color_stop_rgba(1.0, 0.95, 0.4, 0.8, 0.0)  # Pink fade
        cr.set_source(glow)
        cr.arc(cx, cy, r * 1.3, 0, 2 * math.pi)
        cr.fill()

        # 2. Main Fluid Orb
        orb = cairo.RadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.1, cx, cy, r)
        t_col = (math.sin(self.phase) + 1.0) / 2.0
        orb.add_color_stop_rgba(0.0, 0.2 + 0.5 * t_col, 0.8, 1.0, 0.95)
        orb.add_color_stop_rgba(0.4, 0.8, 0.2, 0.9, 0.85)
        orb.add_color_stop_rgba(0.8, 0.1, 0.4, 0.95, 0.90)
        orb.add_color_stop_rgba(1.0, 0.0, 0.1, 0.4, 0.80)

        cr.set_source(orb)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.fill()

        # 3. Inner Pulsating Core Ring
        cr.set_line_width(1.8)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.5 + 0.3 * math.sin(self.phase * 3.0))
        cr.arc(cx, cy, r * 0.55 + math.cos(self.phase * 2.0) * 2.0, 0, 2 * math.pi)
        cr.stroke()

        return False


class GeminiTab(Gtk.Box):
    """Siri AI Tab in Dynamic Island Expanded View (Powered by Local Qwen 2.5 1.5B)."""
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.get_style_context().add_class("tab-content")
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.set_margin_top(6)
        self.set_margin_bottom(8)

        # 1. Header: Siri Orb + Title + Voice Speaker Button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_valign(Gtk.Align.CENTER)

        self.siri_orb = SiriOrbWidget(size=32)
        header_box.pack_start(self.siri_orb, False, False, 0)

        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.title_lbl = Gtk.Label(label="Apple Intelligence • Qwen 2.5")
        self.title_lbl.get_style_context().add_class("gemini-title")
        self.title_lbl.set_xalign(0.0)

        self.status_lbl = Gtk.Label(label="Mô hình AI Local Qwen 2.5 1.5B • Sẵn sàng")
        self.status_lbl.get_style_context().add_class("gemini-sub")
        self.status_lbl.set_xalign(0.0)

        title_col.pack_start(self.title_lbl, False, False, 0)
        title_col.pack_start(self.status_lbl, False, False, 0)
        header_box.pack_start(title_col, True, True, 0)

        # Voice Speaker Icon Button
        self.speaker_btn = Gtk.Button()
        self.speaker_btn.get_style_context().add_class("mac-icon-btn")
        color = "#00f2fe" if siri_assistant.voice_enabled else "#64748b"
        self.speaker_icon = Gtk.Image.new_from_pixbuf(get_pixbuf("volume_high", 14, color))
        self.speaker_btn.set_image(self.speaker_icon)
        self.speaker_btn.set_tooltip_text("Bật / Tắt giọng đọc Siri Neural")
        self.speaker_btn.connect("clicked", self._on_toggle_voice)
        header_box.pack_end(self.speaker_btn, False, False, 0)

        self.pack_start(header_box, False, False, 0)

        # 2. Conversation Display Card
        self.response_scroll = Gtk.ScrolledWindow()
        self.response_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.response_scroll.set_size_request(-1, 74)
        self.response_scroll.get_style_context().add_class("gemini-response-card")

        self.response_lbl = Gtk.Label(
            label="Xin chào! Tôi là trợ lý AI Qwen 2.5 (Local 1.5B). Tôi có thể mở app, tạo văn bản/file, tìm kiếm tệp tin hoặc giải đáp mọi câu hỏi…"
        )
        self.response_lbl.get_style_context().add_class("gemini-response-text")
        self.response_lbl.set_line_wrap(True)
        self.response_lbl.set_xalign(0.0)
        self.response_lbl.set_yalign(0.0)
        self.response_lbl.set_margin_start(10)
        self.response_lbl.set_margin_end(10)
        self.response_lbl.set_margin_top(8)
        self.response_lbl.set_margin_bottom(8)

        self.response_scroll.add(self.response_lbl)
        self.pack_start(self.response_scroll, True, True, 0)

        # 3. Quick Suggestions Pills (OS Automation & Siri Features)
        self.suggestions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.suggestions_box.set_halign(Gtk.Align.START)

        suggestions = [
            ("🌤️ Thời tiết", "Thời tiết hôm nay thế nào?"),
            ("⏱️ Hẹn giờ 5p", "Đặt hẹn giờ 5 phút"),
            ("📝 Tạo file", "Tạo file ghi_chu.txt trên desktop với nội dung Cuộc họp lúc 9h sáng"),
            ("🚀 Mở Ghi chú", "Mở ghi chú"),
            ("📂 Mở Tệp", "Mở thư mục tệp"),
        ]
        for label, full_query in suggestions:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("gemini-chip")
            btn.connect("clicked", lambda b, q=full_query: self._submit_prompt(q))
            self.suggestions_box.pack_start(btn, False, False, 0)

        self.pack_start(self.suggestions_box, False, False, 0)

        # 4. Input Bar (Pill Entry + Send Button)
        input_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_bar.get_style_context().add_class("gemini-input-pill")

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Hỏi Qwen 2.5 hoặc ra lệnh: mở app, tạo file, mở tệp…")
        self.entry.get_style_context().add_class("gemini-entry")
        self.entry.connect("activate", lambda e: self._submit_prompt(e.get_text()))
        input_bar.pack_start(self.entry, True, True, 0)

        # Send Action Button
        self.mic_btn = Gtk.Button()
        self.mic_btn.get_style_context().add_class("gemini-send-btn")
        self.mic_icon = Gtk.Image.new_from_pixbuf(get_pixbuf("sparkles", 14, "#4facfe"))
        self.mic_btn.set_image(self.mic_icon)
        self.mic_btn.connect("clicked", lambda _: self._submit_prompt(self.entry.get_text()))
        input_bar.pack_end(self.mic_btn, False, False, 0)

        self.pack_start(input_bar, False, False, 0)

    def _on_toggle_voice(self, btn):
        curr = siri_assistant.voice_enabled
        siri_assistant.set_voice_enabled(not curr)
        color = "#00f2fe" if not curr else "#64748b"
        self.speaker_icon.set_from_pixbuf(get_pixbuf("volume_high", 14, color))

    def _submit_prompt(self, text: str):
        query = text.strip()
        if not query:
            return
        self.entry.set_text("")
        self.status_lbl.set_text("Qwen 2.5 đang suy nghĩ & xử lý…")
        self.response_lbl.set_text(f"Đang xử lý: \"{query}\"…")

        def _on_reply(reply_text: str, success: bool):
            def _update():
                self.status_lbl.set_text("Apple Intelligence • Qwen 2.5 1.5B")
                self.response_lbl.set_text(reply_text)
                return False
            GLib.idle_add(_update)

        siri_assistant.query(query, callback=_on_reply)

# Alias for SiriTab
SiriTab = GeminiTab
