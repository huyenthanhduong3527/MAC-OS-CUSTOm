"""
macOS Notes Data & Storage Manager for Ubuntu Linux.
Handles persistent storage of notes, folders, audio recordings,
and synchronized transcripts in ~/.local/share/macos-notes/.
"""

import os
import json
import time
import uuid
import shutil
from typing import List, Dict, Optional, Any

DATA_DIR = os.path.expanduser("~/.local/share/macos-notes")
RECORDINGS_DIR = os.path.join(DATA_DIR, "recordings")
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLE_AUDIO_PATH = os.path.join(_base_dir, "assets", "sample_audio_call.wav")


DEFAULT_FOLDERS = [
    {"id": "all", "name": "Tất cả iCloud", "icon": "notes_app", "count": 0},
    {"id": "quick", "name": "Ghi chú nhanh", "icon": "sparkles", "count": 0},
    {"id": "audio", "name": "Ghi âm thoại", "icon": "mic", "count": 0},
    {"id": "work", "name": "Công việc", "icon": "briefcase", "count": 0},
    {"id": "personal", "name": "Cá nhân", "icon": "heart", "count": 0},
    {"id": "trash", "name": "Đã xóa gần đây", "icon": "trash", "count": 0},
]


def get_folder_display_name(folder_id: str, default_name: str = "") -> str:
    """Returns localized display name for standard macOS Notes folders."""
    try:
        from src.utils.i18n import t
        key = f"notes_folder_{folder_id}"
        return t(key, default_name or folder_id.capitalize())
    except Exception:
        return default_name or folder_id.capitalize()



def format_duration(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    total_sec = int(seconds)
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


def format_precise_timer(seconds: float) -> str:
    """Format seconds into MM:SS.cc format (e.g. 01:54.26)."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    cents = int((seconds - int(seconds)) * 100)
    return f"{mins:02d}:{secs:02d}.{cents:02d}"


class NotesManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = NotesManager()
        return cls._instance

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        self.notes: List[Dict[str, Any]] = []
        self.folders = list(DEFAULT_FOLDERS)
        self._load_notes()

    def _get_default_sample_notes(self) -> List[Dict[str, Any]]:
        """
        Default pre-populated notes matching the user's screenshot:
        'Call with Rigo Rangel' with full transcript and audio card.
        """
        now = time.time()
        
        # Transcript segments matching the screenshot
        call_transcript = [
            {
                "speaker": "Tonio",
                "text": "Oh, wow",
                "start_time": 0.5,
                "end_time": 2.5
            },
            {
                "speaker": "Rigo",
                "text": "I know, it's always takes longer then you think it might. But we want to make sure your belongings are treated with the utmost care, so it's important we take our time in the packing phase. You mentioned you had some particularly fragile items, right?",
                "start_time": 3.2,
                "end_time": 18.0
            },
            {
                "speaker": "Tonio",
                "text": "Yeah, that's right. I have a lot of hand-made ceramics with sentimental value, and several pieces of artwork that need to be treated very carefully.",
                "start_time": 19.2,
                "end_time": 32.2
            },
            {
                "speaker": "Rigo",
                "text": "That's right, I remember. We have lots of experience handling items like these. We can tackle these first, or make a plan to pack them while you're around so you can guide us while we're packing up your valuables.",
                "start_time": 33.5,
                "end_time": 50.8
            },
            {
                "speaker": "Tonio",
                "text": "That's great to hear; I was really nervous about moving some of my more fragile items.",
                "start_time": 52.2,
                "end_time": 61.8
            },
            {
                "speaker": "Rigo",
                "text": "Totally understand that. If you can let us know your schedule over those morning dates, we can plan to pack all of these things while you're there to be part of the process. Sound good?",
                "start_time": 63.2,
                "end_time": 80.8
            },
            {
                "speaker": "Tonio",
                "text": "That would be perfect.",
                "start_time": 82.2,
                "end_time": 86.2
            },
            {
                "speaker": "Rigo",
                "text": "And so you can guide us while we're picking up. Valuables.",
                "start_time": 87.2,
                "end_time": 94.0
            },
            {
                "speaker": "Tonio",
                "text": "Sounds good.",
                "start_time": 95.2,
                "end_time": 98.0
            },
            {
                "speaker": "Rigo",
                "text": "We'll see you on Monday morning then. Have a great weekend!",
                "start_time": 99.2,
                "end_time": 106.0
            },
            {
                "speaker": "Tonio",
                "text": "Thank you so much, you too. Bye!",
                "start_time": 107.0,
                "end_time": 114.26
            },
            {
                "speaker": "Rigo",
                "text": "Take care. Bye bye.",
                "start_time": 116.0,
                "end_time": 131.0
            }
        ]

        sample_call_note = {
            "id": "sample-call-rigo",
            "title": "Cuộc gọi với Rigo Rangel",
            "folder": "audio",
            "pinned": True,
            "created_at": "2 thg 5, 2024 lúc 19:34",
            "updated_at": "2 thg 5, 2024 lúc 19:34",
            "timestamp": now - 3600 * 24 * 3,
            "body": (
                "Tonio\nỒ, thật tuyệt vời!\n\n"
                "Rigo\nTôi biết, việc chuẩn bị luôn mất nhiều thời gian hơn dự tính. "
                "Nhưng chúng tôi muốn đảm bảo tất cả đồ đạc của bạn được chăm sóc cẩn thận nhất. "
                "Bạn có nhắc đến một số đồ thủ công đặc biệt dễ vỡ đúng không?\n\n"
                "Tonio\nĐúng vậy, tôi có nhiều đồ gốm sứ thủ công kỷ niệm và vài bức tranh nghệ thuật cần vận chuyển nhẹ nhàng.\n\n"
                "Rigo\nTôi nhớ rồi. Chúng tôi có rất nhiều kinh nghiệm đóng gói những đồ giá trị này. "
                "Chúng ta có thể đóng gói chúng trước hoặc hẹn giờ bạn có mặt để trực tiếp hướng dẫn khi chúng tôi làm việc.\n\n"
                "Tonio\nNghe vậy tôi yên tâm hẳn; lúc đầu tôi khá lo lắng cho các món đồ dễ vỡ.\n\n"
                "Rigo\nTôi hoàn toàn hiểu. Thứ Hai tới chúng tôi sẽ có mặt sớm. Chúc bạn một cuối tuần vui vẻ!\n\n"
                "Tonio\nCảm ơn bạn rất nhiều, bạn cũng vậy nhé. Tạm biệt!\n"
            ),
            "audio": {
                "id": "audio-rigo-call",
                "title": "Ghi âm thoại",
                "file_path": SAMPLE_AUDIO_PATH if os.path.exists(SAMPLE_AUDIO_PATH) else "",
                "date_str": "2 thg 5, 2024 lúc 19:34",
                "sub_date_str": "02/05/2025 lúc 19:06 • 02:12",
                "duration_sec": 132.26,
                "current_pos_sec": 114.26, # 01:54.26 as seen in screenshot!
                "preview_text": (
                    "Tonio: Ồ, thật tuyệt vời! • Rigo: Tôi biết, việc chuẩn bị luôn mất nhiều thời gian hơn dự tính..."
                ),
                "transcript": [
                    {
                        "speaker": "Tonio",
                        "text": "Ồ, thật tuyệt vời!",
                        "start_time": 0.5,
                        "end_time": 2.5
                    },
                    {
                        "speaker": "Rigo",
                        "text": "Tôi biết, việc chuẩn bị luôn mất nhiều thời gian hơn dự tính. Nhưng chúng tôi muốn đảm bảo tất cả đồ đạc của bạn được chăm sóc cẩn thận nhất. Bạn có nhắc đến một số đồ thủ công đặc biệt dễ vỡ đúng không?",
                        "start_time": 3.2,
                        "end_time": 18.0
                    },
                    {
                        "speaker": "Tonio",
                        "text": "Đúng vậy, tôi có nhiều đồ gốm sứ thủ công kỷ niệm và vài bức tranh nghệ thuật cần vận chuyển nhẹ nhàng.",
                        "start_time": 19.2,
                        "end_time": 32.2
                    },
                    {
                        "speaker": "Rigo",
                        "text": "Tôi nhớ rồi. Chúng tôi có rất nhiều kinh nghiệm đóng gói những đồ giá trị này. Chúng ta có thể đóng gói chúng trước hoặc hẹn giờ bạn có mặt để trực tiếp hướng dẫn.",
                        "start_time": 33.5,
                        "end_time": 50.8
                    },
                    {
                        "speaker": "Tonio",
                        "text": "Nghe vậy tôi yên tâm hẳn; lúc đầu tôi khá lo lắng cho các món đồ dễ vỡ.",
                        "start_time": 52.2,
                        "end_time": 61.8
                    },
                    {
                        "speaker": "Rigo",
                        "text": "Tôi hoàn toàn hiểu. Thứ Hai tới chúng tôi sẽ có mặt sớm. Chúc bạn một cuối tuần vui vẻ!",
                        "start_time": 63.2,
                        "end_time": 80.8
                    },
                    {
                        "speaker": "Tonio",
                        "text": "Cảm ơn bạn rất nhiều, bạn cũng vậy nhé. Tạm biệt!",
                        "start_time": 82.2,
                        "end_time": 86.2
                    }
                ]
            },
            "checklist": [
                {"text": "Đóng gói đồ gốm sứ thủ công có giá trị kỷ niệm", "checked": True},
                {"text": "Bảo quản các bức tranh nghệ thuật dễ trầy xước", "checked": True},
                {"text": "Gặp đội ngũ chuyển nhà sáng thứ Hai", "checked": False}
            ]
        }

        quick_ideas_note = {
            "id": "sample-quick-ideas",
            "title": "Thiết kế macOS Sequoia UI cho Linux",
            "folder": "quick",
            "pinned": False,
            "created_at": "Hôm qua lúc 15:20",
            "updated_at": "Hôm qua lúc 15:20",
            "timestamp": now - 3600 * 20,
            "body": (
                "Ý tưởng thiết kế hệ sinh thái macOS hoàn chỉnh trên Ubuntu Linux:\n\n"
                "1. Dynamic Island với hiệu ứng vật lý mượt mà.\n"
                "2. Ứng dụng Ghi chú (Notes) tích hợp bóc băng âm thanh AI trực tiếp.\n"
                "3. AirDrop kết nối mượt mà chia sẻ tệp qua mạng cục bộ.\n"
                "4. Photo Booth hỗ trợ camera ảo và Continuity Camera.\n"
                "5. App Store giao diện kính mờ với kho ứng dụng phong phú."
            ),
            "audio": None,
            "checklist": []
        }

        trip_note = {
            "id": "sample-trip-kyoto",
            "title": "Hành trình khám phá Kyoto mùa thu",
            "folder": "personal",
            "pinned": False,
            "created_at": "Tháng 4 12, 2024",
            "updated_at": "Tháng 4 12, 2024",
            "timestamp": now - 3600 * 24 * 30,
            "body": (
                "Lịch trình tham quan các ngôi đền cổ kính tại Kyoto:\n\n"
                "• Ngày 1: Đền Fushimi Inari-taisha với cổng Torii đỏ thắm rực rỡ.\n"
                "• Ngày 2: Rừng trúc Arashiyama và Chùa Vàng Kinkaku-ji.\n"
                "• Ngày 3: Thưởng thức trà đạo tại Gion và ngắm lá phong mùa thu."
            ),
            "audio": None,
            "checklist": [
                {"text": "Đặt vé tàu Shinkansen", "checked": True},
                {"text": "Thuê kimono chụp ảnh tại Arashiyama", "checked": True},
                {"text": "Mua quà lưu niệm trà xanh Uji", "checked": False}
            ]
        }

        return [sample_call_note, quick_ideas_note, trip_note]

    def _load_notes(self):
        """Load notes from JSON file or create initial notes."""
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.notes = data.get("notes", [])
                    # Check if all notes are in trash or deleted or empty
                    active_notes = [n for n in self.notes if not n.get("in_trash", False) and n.get("title")]
                    if not active_notes:
                        self.notes = self._get_default_sample_notes()
                        self.save_notes()
            except Exception as e:
                print(f"[NotesStorage] Error loading notes: {e}")
                self.notes = self._get_default_sample_notes()
                self.save_notes()
        else:
            self.notes = self._get_default_sample_notes()
            self.save_notes()

    def save_notes(self):
        """Save notes list to JSON file."""
        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump({"notes": self.notes}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[NotesStorage] Error saving notes: {e}")

    def get_notes(self, folder_id: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get filtered list of notes sorted with pinned notes on top."""
        result = []
        for n in self.notes:
            # Folder filter
            if folder_id and folder_id != "all":
                if folder_id == "trash":
                    if not n.get("in_trash", False):
                        continue
                else:
                    if n.get("in_trash", False):
                        continue
                    if folder_id == "audio":
                        if not n.get("audio"):
                            continue
                    elif n.get("folder") != folder_id:
                        continue
            else:
                if n.get("in_trash", False):
                    continue

            # Search query filter
            if query:
                q = query.lower()
                title_match = q in n.get("title", "").lower()
                body_match = q in n.get("body", "").lower()
                transcript_match = False
                if n.get("audio") and n["audio"].get("transcript"):
                    for seg in n["audio"]["transcript"]:
                        if q in seg.get("text", "").lower() or q in seg.get("speaker", "").lower():
                            transcript_match = True
                            break
                if not (title_match or body_match or transcript_match):
                    continue

            result.append(n)

        # Sort: pinned first, then by timestamp descending
        result.sort(key=lambda x: (not x.get("pinned", False), -x.get("timestamp", 0)))
        return result

    def get_note_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        for n in self.notes:
            if n.get("id") == note_id:
                return n
        return None

    def create_note(self, title: str = "Ghi chú mới", folder: str = "all", body: str = "", audio: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new note and prepend it."""
        now = time.time()
        time_str = time.strftime("%d/%m/%Y lúc %H:%M")
        note = {
            "id": f"note-{uuid.uuid4().hex[:8]}",
            "title": title or "Ghi chú mới",
            "folder": folder if folder not in ("all", "trash", "audio") else "all",
            "pinned": False,
            "created_at": time_str,
            "updated_at": time_str,
            "timestamp": now,
            "body": body,
            "audio": audio,
            "checklist": []
        }
        self.notes.insert(0, note)
        self.save_notes()
        return note

    def update_note(self, note_id: str, **kwargs):
        """Update fields of an existing note."""
        note = self.get_note_by_id(note_id)
        if note:
            for k, v in kwargs.items():
                note[k] = v
            note["updated_at"] = time.strftime("%d/%m/%Y lúc %H:%M")
            note["timestamp"] = time.time()
            self.save_notes()

    def delete_note(self, note_id: str, permanent: bool = False):
        """Move note to trash or permanently remove it."""
        note = self.get_note_by_id(note_id)
        if not note:
            return
        if permanent or note.get("in_trash", False):
            self.notes = [n for n in self.notes if n.get("id") != note_id]
        else:
            note["in_trash"] = True
        self.save_notes()

    def restore_note(self, note_id: str):
        """Restore note from trash."""
        note = self.get_note_by_id(note_id)
        if note:
            note["in_trash"] = False
            self.save_notes()

    def toggle_pin(self, note_id: str) -> bool:
        """Toggle pinned state."""
        note = self.get_note_by_id(note_id)
        if note:
            note["pinned"] = not note.get("pinned", False)
            self.save_notes()
            return note["pinned"]
        return False

    def duplicate_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Duplicate an existing note."""
        orig = self.get_note_by_id(note_id)
        if not orig:
            return None
        dup = json.loads(json.dumps(orig))
        dup["id"] = f"note-{uuid.uuid4().hex[:8]}"
        dup["title"] = f"{orig.get('title', 'Ghi chú')} (Bản sao)"
        dup["timestamp"] = time.time()
        dup["created_at"] = time.strftime("%d/%m/%Y lúc %H:%M")
        dup["updated_at"] = dup["created_at"]
        dup["pinned"] = False
        self.notes.insert(0, dup)
        self.save_notes()
        return dup

    def get_folder_count(self, folder_id: str) -> int:
        """Get number of active notes in a folder."""
        return len(self.get_notes(folder_id=folder_id))
