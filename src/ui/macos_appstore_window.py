"""
macOS App Store for Ubuntu Linux.
An authentic, pixel-perfect replica of Apple macOS Sequoia App Store:
- Window: Frosted glass aesthetics, rounded squircle corners, macOS traffic lights (🔴 🟡 🟢).
- Sidebar: Discover, Arcade, Create, Work, Play, Develop, Categories, Updates + Real User Profile Card.
- User Profile: Real Linux avatar synchronization (~/.face, AccountsService) with perfect circular crop.
- Categories Tab: 3-column table of all 21 Apple categories with crisp icons and hairline dividers.
- Editors' Choice Section: Top apps matching macOS App Store (Viator, OmniFocus4, Headspace, Planta, Trello, Noted).
- App Cards: 56x56 squircle icons, clean typography, pill "Get" / "Open" buttons with "In-App Purchases" caption.
- Real System Integration:
  * Dynamic detection of installed apps (Snap / APT / binaries).
  * Launches apps directly via subprocess.
  * Real background installation via pkexec with progress indicators.
  * System updates check & "Update All" functionality.
- Search: Instant live filtering across catalog and featured apps.
- App Detail Sheet: Full info, developer badge, description, features and specs.
- Dynamic Dark / Light theme synchronization with GNOME.
"""

import os
import sys
import pwd
import time
import math
import shutil
import threading
import subprocess
from typing import Dict, List, Optional, Any

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf, Pango
import cairo

from src.utils.theme import is_system_dark_mode
from src.utils.icons import get_image, get_pixbuf
from src.utils.i18n import t, add_language_listener

_appstore_instance = None
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_ICONS_DIR = os.path.join(BASE_DIR, "assets", "app_icons")
CAT_ICONS_DIR = os.path.join(BASE_DIR, "assets", "category_icons")
CACHE_ICONS_DIR = os.path.expanduser("~/.cache/macos-appstore/icons")
os.makedirs(CACHE_ICONS_DIR, exist_ok=True)


def _privileged_run(args, timeout=900):
    """Run package operations without hanging on interactive apt prompts."""
    env = os.environ.copy()
    env.update({
        "DEBIAN_FRONTEND": "noninteractive",
        "APT_LISTCHANGES_FRONTEND": "none",
        "NEEDRESTART_MODE": "a",
    })
    prefix = [] if os.geteuid() == 0 else ["pkexec"]
    return subprocess.run(prefix + list(args), capture_output=True, text=True,
                          env=env, timeout=timeout)

try:
    GLib.set_prgname("snap-store")
    if not GLib.get_application_name():
        GLib.set_application_name("App Store")
except Exception:
    pass

# =========================================================================
# SYSTEM PROFILE HELPERS
# =========================================================================

def get_user_profile():
    """Fetches real Linux username, display full name, and avatar image path."""
    try:
        username = os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USER', 'user')
    except Exception:
        username = os.environ.get('USER', 'user')

    fullname = username
    try:
        pw = pwd.getpwnam(username)
        if pw.pw_gecos:
            parts = pw.pw_gecos.split(',')
            if parts[0].strip():
                fullname = parts[0].strip()
    except Exception:
        pass

    avatar_path = None
    candidates = [
        f"/var/lib/AccountsService/icons/{username}",
        os.path.expanduser("~/.face"),
        os.path.expanduser("~/.face.icon"),
        os.path.expanduser("~/.avatar"),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            avatar_path = p
            break

    return username, fullname, avatar_path


# =========================================================================
# 21 MACOS APP STORE CATEGORIES (3 EQUAL COLUMNS)
# =========================================================================

CATEGORY_COLUMNS = [
    # Column 1
    [
        ("business", "Kinh doanh", "business.png"),
        ("entertainment", "Giải trí", "entertainment.png"),
        ("graphics_design", "Đồ họa & Thiết kế", "graphics_design.png"),
        ("medical", "Y tế", "medical.png"),
        ("photo_video", "Ảnh & Video", "photo_video.png"),
        ("safari_extensions", "Tiện ích mở rộng Safari", "safari_extensions.png"),
        ("travel", "Du lịch", "travel.png"),
    ],
    # Column 2
    [
        ("develop", "Công cụ cho Nhà phát triển", "developer_tools.png"),
        ("finance", "Tài chính", "finance.png"),
        ("health_fitness", "Sức khỏe & Thể chất", "health_fitness.png"),
        ("music", "Âm nhạc", "music.png"),
        ("productivity", "Năng suất", "productivity.png"),
        ("social_networking", "Mạng xã hội", "social_networking.png"),
        ("utilities", "Tiện ích", "utilities.png"),
    ],
    # Column 3
    [
        ("education", "Giáo dục", "education.png"),
        ("games", "Trò chơi", "games.png"),
        ("lifestyle", "Phong cách sống", "lifestyle.png"),
        ("news", "Tin tức", "news.png"),
        ("reference", "Tra cứu", "reference.png"),
        ("sports", "Thể thao", "sports.png"),
        ("weather", "Thời tiết", "weather.png"),
    ]
]


# =========================================================================
# EDITORS' CHOICE: TOP APPS FOR EVERY TASK (MATCHING REFERENCE)
# =========================================================================

EDITORS_CHOICE_APPS: List[Dict[str, Any]] = [
    # Row 1, Col 1
    {
        "id": "viator",
        "name": "Viator Tours & Attractions",
        "subtitle": "Plan travel experiences",
        "category": "travel",
        "category_name": "Travel",
        "developer": "Tripadvisor LLC",
        "rating": 4.8,
        "reviews": "128K",
        "size": "85 MB",
        "version": "12.4.1",
        "in_app_purchases": False,
        "web_url": "https://www.viator.com",
        "desc": "Discover and book unforgettable travel experiences, day trips, and curated tours worldwide with Viator, a Tripadvisor company.",
        "features": [
            "Access to thousands of top-rated tours and exclusive activities",
            "Flexible cancellation policy and instant mobile ticketing",
            "Millions of verified traveler reviews and travel guides"
        ]
    },
    # Row 1, Col 2
    {
        "id": "omnifocus",
        "name": "OmniFocus4",
        "subtitle": "Accomplish More Every Day",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "The Omni Group",
        "rating": 4.7,
        "reviews": "42K",
        "size": "64 MB",
        "version": "4.3.1",
        "in_app_purchases": True,
        "web_url": "https://web.omnifocus.com",
        "desc": "OmniFocus is a powerful, flexible task manager designed for busy professionals. Keep projects on track with custom perspectives, tags, and reviews.",
        "features": [
            "Custom perspectives and powerful priority filtering",
            "Interactive desktop widgets and instant synchronization",
            "Quick Entry shortcuts and deep keyboard navigation"
        ]
    },
    # Row 2, Col 1
    {
        "id": "headspace",
        "name": "Headspace: Sleep & Meditation",
        "subtitle": "Sleep, Calm Anxiety & Stress",
        "category": "health_fitness",
        "category_name": "Health & Fitness",
        "developer": "Headspace Inc.",
        "rating": 4.9,
        "reviews": "380K",
        "size": "112 MB",
        "version": "4.28.0",
        "in_app_purchases": True,
        "web_url": "https://www.headspace.com",
        "desc": "Headspace is your guide to everyday mindfulness in just a few minutes a day. Choose from hundreds of guided meditations on stress, sleep, focus, and mind-body health.",
        "features": [
            "Daily guided meditations and mindfulness breathing exercises",
            "Sleepcasts, relaxing music soundtracks, and evening wind downs",
            "Focus music and energized mind-body workout sessions"
        ]
    },
    # Row 2, Col 2
    {
        "id": "planta",
        "name": "Planta: Plant & Garden Care",
        "subtitle": "Happy Plants, Happy Life!",
        "category": "lifestyle",
        "category_name": "Lifestyle",
        "developer": "Strömbergs & Co",
        "rating": 4.8,
        "reviews": "95K",
        "size": "78 MB",
        "version": "3.15.2",
        "in_app_purchases": True,
        "web_url": "https://getplanta.com",
        "desc": "Join over 8 million plant lovers and keep your house plants thriving! Individual care schedules, watering reminders, light meter, and step-by-step guides.",
        "features": [
            "Intelligent watering, misting, and fertilization schedule",
            "Built-in light meter to find the best spot in your room",
            "Instant AI plant identification and disease diagnostic assistant"
        ]
    },
    # Row 3, Col 1
    {
        "id": "trello",
        "name": "Trello",
        "subtitle": "Organize anything, together",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "Atlassian Pty Ltd",
        "rating": 4.7,
        "reviews": "115K",
        "size": "90 MB",
        "version": "2.11.0",
        "snap": "trello",
        "web_url": "https://trello.com",
        "in_app_purchases": False,
        "desc": "Whether it’s for work, a side project, or a family trip, Trello helps your team stay organized, manage Kanban boards, and track progress effortlessly.",
        "features": [
            "Flexible boards, lists, cards, and custom workflows",
            "Automated actions and workflow rules with Butler",
            "Real-time team collaboration with attachments and checklists"
        ]
    },
    # Row 3, Col 2
    {
        "id": "noted",
        "name": "Noted: Record & AI Transcribe",
        "subtitle": "Take meeting notes and audio",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "Digital Workroom Ltd.",
        "rating": 4.8,
        "reviews": "31K",
        "size": "55 MB",
        "version": "3.8.0",
        "in_app_purchases": True,
        "web_url": "https://www.notedapp.io",
        "desc": "Noted is a beautiful audio recording and note-taking app that pairs your voice notes with timestamps and high-accuracy automatic AI transcriptions.",
        "features": [
            "Timestamped audio playback paired with typed notes",
            "High-accuracy AI voice transcription in 50+ languages",
            "Rich text formatting, attachments, dictation, and cloud export"
        ]
    }
]


# =========================================================================
# APP STORE EXTENDED CATALOG DATABASE
# =========================================================================

APP_CATALOG: List[Dict[str, Any]] = [
    # --- DEVELOPER TOOLS ---
    {
        "id": "code",
        "name": "Visual Studio Code",
        "subtitle": "Code editing redefined by Microsoft",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Microsoft Corporation",
        "rating": 4.9,
        "reviews": "142K",
        "hero": True,
        "hero_tag": "EDITORS' CHOICE",
        "hero_title": "Visual Studio Code: Code Anywhere",
        "hero_sub": "Built-in Git, terminal, endless extensions, and GitHub Copilot intelligence.",
        "size": "95 MB",
        "version": "1.93.1",
        "snap": "code",
        "apt": "code",
        "bin": "code",
        "in_app_purchases": False,
        "desc": "Visual Studio Code combines the simplicity of a source code editor with powerful developer tooling like IntelliSense code completion and debugging.",
        "features": [
            "IntelliSense context-aware syntax completion",
            "Interactive graphical debugging with breakpoints",
            "Seamless Git source control integration",
            "Thousands of extensions for Python, JS, C++, Rust, Go, etc."
        ]
    },
    {
        "id": "cursor",
        "name": "Cursor AI",
        "subtitle": "The AI-first code editor",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Anysphere Inc.",
        "rating": 4.9,
        "reviews": "35K",
        "size": "110 MB",
        "version": "0.40.4",
        "snap": "cursor",
        "bin": "cursor",
        "in_app_purchases": True,
        "desc": "Built to make you extraordinarily productive, Cursor is the best way to code with AI. Multi-line completions, smart codebase chat, and instant bug fixes.",
        "features": [
            "Multi-line autonomous code generation",
            "Natural language conversations with your codebase",
            "Full compatibility with all VS Code extensions"
        ]
    },
    {
        "id": "pycharm-community",
        "name": "PyCharm Community",
        "subtitle": "Professional Python IDE",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "JetBrains s.r.o.",
        "rating": 4.8,
        "reviews": "41K",
        "size": "450 MB",
        "version": "2024.2",
        "snap": "pycharm-community",
        "bin": "pycharm-community",
        "in_app_purchases": False,
        "desc": "Smart Python IDE with code analysis, graphical debugger, and seamless virtual environment management.",
        "features": [
            "Support for Python 3.12+, venv, conda, and poetry",
            "Real-time static code analysis and safe refactoring",
            "Integrated terminal and visual Git tools"
        ]
    },
    {
        "id": "postman",
        "name": "Postman",
        "subtitle": "API platform for building and using APIs",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Postman Inc.",
        "rating": 4.7,
        "reviews": "53K",
        "size": "140 MB",
        "version": "11.10",
        "snap": "postman",
        "bin": "postman",
        "in_app_purchases": False,
        "desc": "An API platform for building and using APIs. Postman simplifies each step of the API lifecycle and streamlines collaboration.",
        "features": [
            "HTTP, REST, GraphQL, WebSocket, and gRPC requests",
            "Automated API testing and OpenAPI documentation",
            "Collaborative team workspaces"
        ]
    },
    {
        "id": "docker",
        "name": "Docker Desktop",
        "subtitle": "Securely build and share containerized apps",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Docker Inc.",
        "rating": 4.8,
        "reviews": "85K",
        "size": "180 MB",
        "version": "27.2",
        "snap": "docker",
        "bin": "docker",
        "in_app_purchases": False,
        "desc": "Accelerate how you build, share, and run applications. The developer’s container toolkit of choice.",
        "features": [
            "One-click container engine and Kubernetes setup",
            "Visual container inspection and log streaming",
            "Docker Compose multi-container coordination"
        ]
    },
    {
        "id": "dbeaver-ce",
        "name": "DBeaver Community",
        "subtitle": "Universal database manager",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "DBeaver Corp",
        "rating": 4.7,
        "reviews": "29K",
        "size": "120 MB",
        "version": "24.2.0",
        "snap": "dbeaver-ce",
        "bin": "dbeaver-ce",
        "in_app_purchases": False,
        "desc": "Free multi-platform database tool for developers, database administrators, analysts, and anyone who needs to work with databases.",
        "features": [
            "Supports MySQL, PostgreSQL, SQLite, Oracle, Redis",
            "Visual query builder and ER diagrams",
            "Data export to CSV, JSON, XML, and SQL scripts"
        ]
    },

    # --- GRAPHICS & DESIGN / CREATE ---
    {
        "id": "blender",
        "name": "Blender 3D",
        "subtitle": "Open-source 3D creation suite",
        "category": "graphics_design",
        "category_name": "Graphics & Design",
        "developer": "Blender Foundation",
        "rating": 4.9,
        "reviews": "92K",
        "size": "310 MB",
        "version": "4.2.1",
        "snap": "blender",
        "apt": "blender",
        "bin": "blender",
        "in_app_purchases": False,
        "desc": "Blender is the free and open source 3D creation suite supporting modeling, rigging, animation, simulation, rendering, compositing, and motion tracking.",
        "features": [
            "Cycles photorealistic ray-tracing render engine",
            "Advanced digital sculpting with dynamic topology",
            "VFX pipeline and 2D Grease Pencil animation"
        ]
    },
    {
        "id": "gimp",
        "name": "GIMP",
        "subtitle": "GNU Image Manipulation Program",
        "category": "graphics_design",
        "category_name": "Graphics & Design",
        "developer": "GIMP Team",
        "rating": 4.6,
        "reviews": "48K",
        "size": "85 MB",
        "version": "2.10.38",
        "snap": "gimp",
        "apt": "gimp",
        "bin": "gimp",
        "in_app_purchases": False,
        "desc": "GIMP is a cross-platform image editor available for GNU/Linux, macOS, Windows, and more. High-quality photo retouching and graphic design.",
        "features": [
            "Layer masks, channel mixer, and blend modes",
            "Extensive plugin ecosystem with Python integration",
            "Color management with sRGB and Adobe RGB"
        ]
    },
    {
        "id": "inkscape",
        "name": "Inkscape",
        "subtitle": "Vector graphics editor",
        "category": "graphics_design",
        "category_name": "Graphics & Design",
        "developer": "Inkscape Community",
        "rating": 4.7,
        "reviews": "36K",
        "size": "95 MB",
        "version": "1.3.2",
        "snap": "inkscape",
        "apt": "inkscape",
        "bin": "inkscape",
        "in_app_purchases": False,
        "desc": "A powerful, free design tool for vector illustrations, SVG graphics, logos, typography, and diagram drafting.",
        "features": [
            "Compliant with W3C standard SVG format",
            "Bézier curve drawing and advanced node sculpting",
            "Live path effects and boolean operations"
        ]
    },
    {
        "id": "kdenlive",
        "name": "Kdenlive",
        "subtitle": "Non-linear video editor",
        "category": "photo_video",
        "category_name": "Photo & Video",
        "developer": "KDE Community",
        "rating": 4.6,
        "reviews": "22K",
        "size": "130 MB",
        "version": "24.08",
        "snap": "kdenlive",
        "apt": "kdenlive",
        "bin": "kdenlive",
        "in_app_purchases": False,
        "desc": "A multi-track video editor that supports almost all audio and video formats using the FFmpeg backend with GPU timeline acceleration.",
        "features": [
            "Multi-track timeline with audio waveforms",
            "Hardware-accelerated rendering up to 4K 60fps",
            "Keyframeable audio/video effects and color grading"
        ]
    },

    # --- MUSIC & ENTERTAINMENT ---
    {
        "id": "spotify",
        "name": "Spotify",
        "subtitle": "Music and podcasts for everyone",
        "category": "music",
        "category_name": "Music",
        "developer": "Spotify AB",
        "rating": 4.8,
        "reviews": "210K",
        "size": "95 MB",
        "version": "1.2.45",
        "snap": "spotify",
        "bin": "spotify",
        "in_app_purchases": True,
        "desc": "Play millions of songs and podcasts on your device with high-fidelity audio, personalized playlists, and offline playback.",
        "features": [
            "Stream over 100 million songs and podcasts",
            "Personalized Release Radar and Discover Weekly",
            "Connect playback across desktop, mobile, and speakers"
        ]
    },
    {
        "id": "vlc",
        "name": "VLC Media Player",
        "subtitle": "The ultimate multimedia player",
        "category": "entertainment",
        "category_name": "Entertainment",
        "developer": "VideoLAN Organization",
        "rating": 4.9,
        "reviews": "340K",
        "size": "45 MB",
        "version": "3.0.21",
        "snap": "vlc",
        "apt": "vlc",
        "bin": "vlc",
        "in_app_purchases": False,
        "desc": "VLC is a free and open source cross-platform multimedia player and framework that plays most multimedia files, discs, and streaming protocols.",
        "features": [
            "Plays all formats (MKV, MP4, AVI, FLAC, OGG, etc.)",
            "Hardware decoding for smooth 4K/8K playback",
            "Automatic online subtitle searching and synchronization"
        ]
    },
    {
        "id": "steam",
        "name": "Steam",
        "subtitle": "The ultimate gaming platform",
        "category": "games",
        "category_name": "Games",
        "developer": "Valve Corporation",
        "rating": 4.9,
        "reviews": "520K",
        "size": "75 MB",
        "version": "1.0.0.79",
        "snap": "steam",
        "apt": "steam-installer",
        "bin": "steam",
        "in_app_purchases": True,
        "desc": "Steam is the ultimate destination for playing, discussing, and creating games with Proton compatibility layer for thousands of titles.",
        "features": [
            "Play thousands of Windows games on Linux via Proton",
            "Cloud save synchronization and Steam Community",
            "Full controller support including DualSense & Xbox"
        ]
    },

    # --- SOCIAL & PRODUCTIVITY ---
    {
        "id": "discord",
        "name": "Discord",
        "subtitle": "Talk, chat, and hang out",
        "category": "social_networking",
        "category_name": "Social Networking",
        "developer": "Discord Inc.",
        "rating": 4.8,
        "reviews": "190K",
        "size": "115 MB",
        "version": "0.0.65",
        "snap": "discord",
        "bin": "discord",
        "in_app_purchases": True,
        "desc": "Discord is great for playing games and chilling with friends, or even building a worldwide community. Low-latency voice and HD screen sharing.",
        "features": [
            "Crystal clear low-latency voice and video channels",
            "HD 60fps screen sharing and game streaming",
            "Rich bot integration and customizable server roles"
        ]
    },
    {
        "id": "slack",
        "name": "Slack",
        "subtitle": "Team communication for the modern workplace",
        "category": "business",
        "category_name": "Business",
        "developer": "Slack Technologies",
        "rating": 4.6,
        "reviews": "68K",
        "size": "120 MB",
        "version": "4.39.95",
        "snap": "slack",
        "bin": "slack",
        "in_app_purchases": True,
        "desc": "Slack is a new way to communicate with your team. It’s faster, better organized, and more secure than email.",
        "features": [
            "Organized channels for projects, topics, and teams",
            "Audio Huddles with real-time screen sharing",
            "Deep integration with Google Drive, Jira, and GitHub"
        ]
    },
    {
        "id": "telegram-desktop",
        "name": "Telegram",
        "subtitle": "Fast and secure cloud messaging",
        "category": "social_networking",
        "category_name": "Social Networking",
        "developer": "Telegram FZ-LLC",
        "rating": 4.9,
        "reviews": "150K",
        "size": "80 MB",
        "version": "5.4.1",
        "snap": "telegram-desktop",
        "bin": "telegram-desktop",
        "in_app_purchases": True,
        "desc": "Pure instant messaging — simple, fast, secure, and synced across all your devices.",
        "features": [
            "Send media and files up to 2GB each",
            "Groups of up to 200,000 members",
            "Secret chats with client-to-client encryption"
        ]
    },
    {
        "id": "obsidian",
        "name": "Obsidian",
        "subtitle": "Sharpen your thinking with linked notes",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "Dynalist Inc.",
        "rating": 4.9,
        "reviews": "74K",
        "size": "90 MB",
        "version": "1.6.7",
        "snap": "obsidian",
        "bin": "obsidian",
        "in_app_purchases": True,
        "desc": "Obsidian is a powerful knowledge base on top of a local folder of plain text Markdown files.",
        "features": [
            "Interactive graph view of linked ideas",
            "100% private local Markdown storage",
            "Huge community plugin and canvas system"
        ]
    },

    # --- UTILITIES ---
    {
        "id": "gnome-tweaks",
        "name": "GNOME Tweaks",
        "subtitle": "Advanced desktop customization",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "GNOME Project",
        "rating": 4.8,
        "reviews": "45K",
        "size": "8 MB",
        "version": "46.1",
        "apt": "gnome-tweaks",
        "bin": "gnome-tweaks",
        "in_app_purchases": False,
        "desc": "Customize fonts, themes, mouse behavior, titlebar buttons, and startup applications in GNOME desktop.",
        "features": [
            "Toggle macOS left titlebar traffic lights",
            "Change system fonts and interface scaling",
            "Manage startup applications and shell settings"
        ]
    },
    {
        "id": "extension-manager",
        "name": "Extension Manager",
        "subtitle": "Browse and manage GNOME Shell extensions",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "Matthew Jakeman",
        "rating": 4.9,
        "reviews": "35K",
        "size": "12 MB",
        "version": "0.5.1",
        "apt": "gnome-shell-extension-manager",
        "bin": "extension-manager",
        "in_app_purchases": False,
        "desc": "Discover, install, and manage GNOME Shell extensions directly from your desktop without a web browser.",
        "features": [
            "Search and install from extensions.gnome.org",
            "Toggle and configure each extension easily",
            "Automatic upgrade notifications"
        ]
    },
    {
        "id": "timeshift",
        "name": "Timeshift",
        "subtitle": "Time Machine backup for Linux",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "Linux Mint Team",
        "rating": 4.9,
        "reviews": "58K",
        "size": "25 MB",
        "version": "24.06",
        "apt": "timeshift",
        "bin": "timeshift-gtk",
        "in_app_purchases": False,
        "desc": "System restore tool for Linux similar to Apple Time Machine on macOS. Create incremental snapshots to safely restore your machine.",
        "features": [
            "Supports RSYNC and BTRFS snapshot formats",
            "Automated hourly, daily, and weekly schedules",
            "One-click complete operating system restore"
        ]
    },
    {
        "id": "bitwarden",
        "name": "Bitwarden",
        "subtitle": "Secure password and credential manager",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "Bitwarden Inc.",
        "rating": 4.9,
        "reviews": "85K",
        "size": "80 MB",
        "version": "2024.8",
        "snap": "bitwarden",
        "bin": "bitwarden",
        "in_app_purchases": True,
        "desc": "End-to-end encrypted AES-256 password vault for storing credentials, secure notes, credit cards, and two-factor authentication codes.",
        "features": [
            "Zero-knowledge end-to-end encryption",
            "Secure password generator and auto-fill",
            "Seamless synchronization across mobile and browser"
        ]
    },
    {
        "id": "android-studio",
        "name": "Android Studio",
        "subtitle": "Official IDE for Android development",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Google LLC",
        "rating": 4.8,
        "reviews": "68K",
        "size": "950 MB",
        "version": "2024.1",
        "snap": "android-studio",
        "classic": True,
        "desc": "Android Studio provides the fastest tools for building apps on every type of Android device.",
        "features": ["Intelligent code editor with Kotlin & Java support", "Visual Layout Editor & APK analyzer", "Fast Android Virtual Device emulator"]
    },
    {
        "id": "sublime-text",
        "name": "Sublime Text",
        "subtitle": "Sophisticated text editor for code & prose",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Sublime HQ Pty Ltd",
        "rating": 4.8,
        "reviews": "92K",
        "size": "45 MB",
        "version": "4.0",
        "snap": "sublime-text",
        "classic": True,
        "desc": "Sublime Text is a sophisticated text editor for code, markup and prose with slick user interface and extraordinary performance.",
        "features": ["GPU rendering on Linux and macOS", "Supercharged auto-complete engine", "Split editing and multiple selections"]
    },
    {
        "id": "beekeeper-studio",
        "name": "Beekeeper Studio",
        "subtitle": "Modern SQL editor and database manager",
        "category": "develop",
        "category_name": "Developer Tools",
        "developer": "Beekeeper Studio Team",
        "rating": 4.8,
        "reviews": "18K",
        "size": "85 MB",
        "version": "4.4",
        "snap": "beekeeper-studio",
        "desc": "Open source SQL editor and database manager for MySQL, PostgreSQL, SQLite, SQL Server, and Redis.",
        "features": ["Smooth tabbed SQL editor with syntax highlight", "Secure SSH tunneling for remote connections", "Visual table data viewer and editor"]
    },
    {
        "id": "google-chrome",
        "name": "Google Chrome",
        "subtitle": "Fast, secure, and personal web browser",
        "category": "utilities",
        "category_name": "Web Browsers",
        "developer": "Google LLC",
        "rating": 4.9,
        "reviews": "500K+",
        "size": "105 MB",
        "version": "130.0",
        "apt": "google-chrome-stable",
        "bin": "google-chrome",
        "desc": "Browse fast and safely with Google Chrome across all your computers and phones. Sync bookmarks, history, and passwords seamlessly.",
        "features": ["Built-in Google Translate and smart search", "Advanced sandboxed tab security", "Extensive Chrome Web Store extension ecosystem"]
    },
    {
        "id": "brave",
        "name": "Brave Browser",
        "subtitle": "Secure, fast, and private web browsing",
        "category": "utilities",
        "category_name": "Web Browsers",
        "developer": "Brave Software Inc.",
        "rating": 4.8,
        "reviews": "110K",
        "size": "120 MB",
        "version": "1.70",
        "snap": "brave",
        "desc": "Brave blocks trackers and intrusive ads by default, giving you 3x faster page loads and unmatched privacy protection.",
        "features": ["Automatic ad and tracker blocking Shields", "Built-in private Tor browsing windows", "Native Web3 crypto wallet and IPFS integration"]
    },
    {
        "id": "firefox",
        "name": "Mozilla Firefox",
        "subtitle": "Fast, private, and independent browser",
        "category": "utilities",
        "category_name": "Web Browsers",
        "developer": "Mozilla Foundation",
        "rating": 4.8,
        "reviews": "250K",
        "size": "90 MB",
        "version": "130.0",
        "snap": "firefox",
        "bin": "firefox",
        "desc": "Firefox puts you in control of your digital life. Open-source, privacy-first web browser with lightning-fast Gecko engine.",
        "features": ["Enhanced Tracking Protection", "Multi-account containers for separating work & personal life", "Picture-in-picture video floating player"]
    },
    {
        "id": "zoom-client",
        "name": "Zoom Meetings",
        "subtitle": "HD video conferencing & team messaging",
        "category": "social_networking",
        "category_name": "Social Networking",
        "developer": "Zoom Video Communications",
        "rating": 4.7,
        "reviews": "180K",
        "size": "190 MB",
        "version": "6.2",
        "snap": "zoom-client",
        "desc": "Connect, collaborate, and communicate with high-definition video meetings, team chat, screen sharing, and interactive whiteboards.",
        "features": ["Crystal clear HD audio and video calling", "Real-time interactive screen sharing & recording", "Breakout rooms and encrypted meeting rooms"]
    },
    {
        "id": "krita",
        "name": "Krita Digital Painting",
        "subtitle": "Professional digital sketching & painting",
        "category": "graphics_design",
        "category_name": "Graphics & Design",
        "developer": "Krita Foundation",
        "rating": 4.9,
        "reviews": "75K",
        "size": "180 MB",
        "version": "5.2.3",
        "snap": "krita",
        "desc": "Krita is a professional FREE and open source painting program made by artists that want to see affordable art tools for everyone.",
        "features": ["100+ professionally made brushes", "Brush stabilizers for smooth hand-drawn lines", "Full vector art & 2D frame-by-frame animation"]
    },
    {
        "id": "obs-studio",
        "name": "OBS Studio",
        "subtitle": "Live streaming and video recording studio",
        "category": "photo_video",
        "category_name": "Photo & Video",
        "developer": "OBS Project",
        "rating": 4.9,
        "reviews": "140K",
        "size": "130 MB",
        "version": "30.2",
        "snap": "obs-studio",
        "desc": "Free and open source software for video recording and live streaming. Stream directly to YouTube, Twitch, Facebook, and more.",
        "features": ["High performance real-time video/audio capturing and mixing", "Intuitive audio mixer with per-source filters", "Powerful and easy-to-use configuration options"]
    },
    {
        "id": "shotcut",
        "name": "Shotcut Video Editor",
        "subtitle": "Free, open-source, cross-platform video editor",
        "category": "photo_video",
        "category_name": "Photo & Video",
        "developer": "Meltytech LLC",
        "rating": 4.7,
        "reviews": "40K",
        "size": "110 MB",
        "version": "24.08",
        "snap": "shotcut",
        "classic": True,
        "desc": "Shotcut is a free, open-source, cross-platform video editor with support for wide format codecs and 4K resolutions.",
        "features": ["Native timeline editing with no import required", "Supports 4K UHD resolutions and wide color gamuts", "Video effects, color grading, transitions, and audio filters"]
    },
    {
        "id": "freecad",
        "name": "FreeCAD",
        "subtitle": "Parametric 3D CAD modeler for engineers",
        "category": "graphics_design",
        "category_name": "Graphics & Design",
        "developer": "FreeCAD Community",
        "rating": 4.7,
        "reviews": "30K",
        "size": "380 MB",
        "version": "0.21.2",
        "snap": "freecad",
        "desc": "FreeCAD is a general-purpose parametric 3D CAD modeler. The modeling is completely parametric, allowing effortless design modifications.",
        "features": ["Parametric modeling for mechanical parts", "BIM architecture and FEA simulation workbenches", "Export to STEP, IGES, STL, SVG, and DXF"]
    },
    {
        "id": "darktable",
        "name": "Darktable",
        "subtitle": "Open source photography workflow & RAW developer",
        "category": "photo_video",
        "category_name": "Photo & Video",
        "developer": "Darktable Team",
        "rating": 4.8,
        "reviews": "22K",
        "size": "110 MB",
        "version": "4.8",
        "snap": "darktable",
        "desc": "Darktable is an open source photography workflow application and raw developer. A virtual lighttable and darkroom for photographers.",
        "features": ["Non-destructive editing workflow", "GPU accelerated image processing via OpenCL", "Professional color management and tethered shooting"]
    },
    {
        "id": "audacity",
        "name": "Audacity",
        "subtitle": "Multi-track audio recorder & editor",
        "category": "music",
        "category_name": "Music & Audio",
        "developer": "Muse Group",
        "rating": 4.8,
        "reviews": "160K",
        "size": "70 MB",
        "version": "3.6",
        "snap": "audacity",
        "desc": "Audacity is the world's most popular free, open-source audio recording and editing software. Record live audio, cut, and mix tracks.",
        "features": ["Multi-track audio recording and editing", "Extensive library of digital effects and filters", "High-fidelity 16-bit, 24-bit, and 32-bit sound processing"]
    },
    {
        "id": "clementine",
        "name": "Clementine Music Player",
        "subtitle": "Modern music player and library organizer",
        "category": "music",
        "category_name": "Music & Audio",
        "developer": "David Sansome & John Maguire",
        "rating": 4.8,
        "reviews": "25K",
        "size": "45 MB",
        "version": "1.4",
        "snap": "clementine",
        "desc": "Clementine is a modern music player and library organizer inspired by Amarok 1.4, focusing on a fast and easy-to-use interface.",
        "features": ["Search and play your local music library", "Internet radio support for Spotify, Soundcloud, Jamendo", "Create dynamic and smart playlists"]
    },
    {
        "id": "libreoffice",
        "name": "LibreOffice",
        "subtitle": "Free and powerful office productivity suite",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "The Document Foundation",
        "rating": 4.8,
        "reviews": "200K+",
        "size": "600 MB",
        "version": "24.8",
        "snap": "libreoffice",
        "desc": "LibreOffice is a powerful and free office suite. Clean interface and feature-rich tools help you unleash your creativity and grow productivity.",
        "features": ["Writer (Word processor), Calc (Spreadsheets), Impress (Slides)", "Full compatibility with Microsoft Office .docx, .xlsx, .pptx", "Export to PDF and open document formats"]
    },
    {
        "id": "notion-snap-reborn",
        "name": "Notion",
        "subtitle": "The all-in-one connected workspace",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "Notion Labs Inc. (Wrapper)",
        "rating": 4.9,
        "reviews": "120K",
        "size": "95 MB",
        "version": "2.0.1",
        "snap": "notion-snap-reborn",
        "web_url": "https://www.notion.so",
        "desc": "Write, plan, and organize in one place. Notion is the connected workspace where better, faster work happens.",
        "features": ["Wikis, docs, notes, and task project management", "Kanban boards, calendars, tables, and lists", "Real-time sync across computers, mobile, and web"]
    },
    {
        "id": "joplin-desktop",
        "name": "Joplin",
        "subtitle": "Open source secure note-taking application",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "Laurent Cozic",
        "rating": 4.8,
        "reviews": "35K",
        "size": "90 MB",
        "version": "3.0.1",
        "snap": "joplin-desktop",
        "desc": "An open source note taking and to-do application with synchronisation capabilities for Windows, macOS, Linux, Android and iOS.",
        "features": ["Markdown note-taking with math formula support", "End-to-end encryption (E2EE)", "Sync via Dropbox, OneDrive, Nextcloud, or WebDAV"]
    },
    {
        "id": "thunderbird",
        "name": "Mozilla Thunderbird",
        "subtitle": "Full-featured email, news, and chat client",
        "category": "productivity",
        "category_name": "Productivity",
        "developer": "MZLA Technologies Corporation",
        "rating": 4.7,
        "reviews": "90K",
        "size": "110 MB",
        "version": "128.0",
        "snap": "thunderbird",
        "bin": "thunderbird",
        "desc": "Thunderbird is a free email application that's easy to set up and customize - and it's loaded with great features!",
        "features": ["One-click address book and message archiving", "Smart tabbed email interface", "Built-in calendar, reminders, and RSS reader"]
    },
    {
        "id": "0ad",
        "name": "0 A.D. Empires Ascendant",
        "subtitle": "Historical real-time strategy game",
        "category": "games",
        "category_name": "Games",
        "developer": "Wildfire Games",
        "rating": 4.9,
        "reviews": "45K",
        "size": "1.2 GB",
        "version": "0.0.26",
        "snap": "0ad",
        "desc": "0 A.D. is a free, open-source, historical Real Time Strategy (RTS) game currently under development by Wildfire Games.",
        "features": ["Command ancient civilizations from Romans to Persians", "Stunning 3D graphics and detailed historical units", "Single-player skirmish and online multiplayer battles"]
    },
    {
        "id": "supertuxkart",
        "name": "SuperTuxKart",
        "subtitle": "High-octane 3D arcade kart racing game",
        "category": "games",
        "category_name": "Games",
        "developer": "SuperTuxKart Team",
        "rating": 4.9,
        "reviews": "60K",
        "size": "650 MB",
        "version": "1.4",
        "snap": "supertuxkart",
        "desc": "Karts. Nitro. Action! SuperTuxKart is a 3D open-source arcade racer with a variety characters, tracks, and modes to play.",
        "features": ["Over 20 distinct tracks and battle arenas", "Story campaign, grand prix, time trials, and online battles", "Split-screen local multiplayer for up to 4 players"]
    },
    {
        "id": "retroarch",
        "name": "RetroArch",
        "subtitle": "Universal frontend for retro game emulators",
        "category": "games",
        "category_name": "Games",
        "developer": "Libretro Team",
        "rating": 4.8,
        "reviews": "80K",
        "size": "220 MB",
        "version": "1.19.1",
        "snap": "retroarch",
        "desc": "RetroArch is a frontend for emulators, game engines and media players. It enables you to run classic games on a wide range of computers.",
        "features": ["Slick cross-platform PlayStation/macOS XMB interface", "Next-frame response time with RunAhead", "Advanced shaders, netplay, and automatic controller mapping"]
    },
    {
        "id": "keepassxc",
        "name": "KeePassXC",
        "subtitle": "Secure cross-platform password manager",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "KeePassXC Team",
        "rating": 4.9,
        "reviews": "50K",
        "size": "45 MB",
        "version": "2.7.9",
        "snap": "keepassxc",
        "desc": "KeePassXC is a community fork of KeePassX, the cross-platform port of KeePass for Windows. 100% offline, private, and secure.",
        "features": ["256-bit AES encryption with Argon2 key derivation", "Built-in Time-based One-Time Password (TOTP) generator", "Browser integration for Chrome, Firefox, and Brave"]
    },
    {
        "id": "remmina",
        "name": "Remmina",
        "subtitle": "Remote desktop client for RDP, VNC, SSH, and SPICE",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "Remmina Community",
        "rating": 4.8,
        "reviews": "35K",
        "size": "65 MB",
        "version": "1.4.35",
        "snap": "remmina",
        "desc": "Remmina is a remote desktop client written in GTK+, aiming to be especially useful for system administrators and travelers.",
        "features": ["Supports RDP, VNC, SSH, SFTP, and SPICE protocols", "Tabbed multi-monitor remote desktop sessions", "Secure encrypted profile storage"]
    },
    {
        "id": "htop",
        "name": "Htop",
        "subtitle": "Interactive system process monitor & viewer",
        "category": "utilities",
        "category_name": "Utilities",
        "developer": "Htop Community",
        "rating": 4.9,
        "reviews": "40K",
        "size": "8 MB",
        "version": "3.3.0",
        "snap": "htop",
        "desc": "An interactive process viewer for Unix systems. It is a text-mode application and requires ncurses.",
        "features": ["Colorized visual graphs for CPU, RAM, and Swap", "Kill, renice, and filter processes instantly", "Tree view of parent and child process hierarchies"]
    }
]


# =========================================================================
# SYSTEM DETECTOR & EXECUTOR
# =========================================================================

def is_app_installed(app: Dict[str, Any]) -> bool:
    """Check if app is currently installed on the system."""
    bin_name = app.get("bin")
    if bin_name and shutil.which(bin_name):
        return True

    snap_name = app.get("snap")
    if snap_name:
        snap_path = f"/snap/{snap_name}"
        if os.path.exists(snap_path) or os.path.exists(f"/var/lib/snapd/snaps/{snap_name}_*.snap"):
            return True

    app_id = app.get("id")
    if app_id:
        user_desktop = os.path.expanduser(f"~/.local/share/applications/{app_id}.desktop")
        sys_desktop = f"/usr/share/applications/{app_id}.desktop"
        snap_desktop = f"/var/lib/snapd/desktop/applications/{app_id}_{app_id}.desktop"
        if os.path.exists(user_desktop) or os.path.exists(sys_desktop) or os.path.exists(snap_desktop):
            return True

    return False


def launch_installed_app(app: Dict[str, Any]) -> bool:
    """Launch the application using system binary, desktop file, or web runner."""
    bin_name = app.get("bin")
    if bin_name and shutil.which(bin_name):
        try:
            subprocess.Popen([bin_name], start_new_session=True)
            return True
        except Exception:
            pass

    snap_name = app.get("snap")
    if snap_name:
        for cmd in [f"/snap/bin/{snap_name}", snap_name]:
            if os.path.exists(cmd) or shutil.which(cmd):
                try:
                    subprocess.Popen([cmd], start_new_session=True)
                    return True
                except Exception:
                    pass

    app_id = app.get("id")
    if app_id:
        user_desktop = os.path.expanduser(f"~/.local/share/applications/{app_id}.desktop")
        if os.path.exists(user_desktop):
            try:
                subprocess.Popen(["gtk-launch", f"{app_id}.desktop"], start_new_session=True)
                return True
            except Exception:
                pass

    if app.get("web_url"):
        try:
            if shutil.which("google-chrome"):
                subprocess.Popen(["google-chrome", f"--app={app['web_url']}"], start_new_session=True)
            else:
                subprocess.Popen(["xdg-open", app["web_url"]], start_new_session=True)
            return True
        except Exception:
            pass

    return False


def generate_fallback_app_icon(app_name: str, size: int = 56) -> Optional[GdkPixbuf.Pixbuf]:
    """Generate on-the-fly Apple-style squircle icon with gradient and initials."""
    try:
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surf)
        cr.set_antialias(cairo.Antialias.SUBPIXEL)

        r = size * 0.22
        # Squircle shape
        cr.new_sub_path()
        cr.arc(size - r, r, r, -math.pi/2, 0)
        cr.arc(size - r, size - r, r, 0, math.pi/2)
        cr.arc(r, size - r, r, math.pi/2, math.pi)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.close_path()

        import hashlib
        h = int(hashlib.md5(app_name.encode('utf-8')).hexdigest()[:6], 16)
        r1 = ((h >> 16) & 0xFF) / 255.0 * 0.5 + 0.2
        g1 = ((h >> 8) & 0xFF) / 255.0 * 0.5 + 0.2
        b1 = (h & 0xFF) / 255.0 * 0.5 + 0.3

        pat = cairo.LinearGradient(0, 0, size, size)
        pat.add_color_stop_rgb(0.0, r1, g1, b1)
        pat.add_color_stop_rgb(1.0, max(0.05, r1 - 0.15), max(0.05, g1 - 0.15), max(0.05, b1 - 0.15))
        cr.set_source(pat)
        cr.fill()

        # Initials
        initials = "".join([w[0].upper() for w in app_name.split()[:2] if w.isalnum()]) or app_name[:2].upper()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.select_font_face("-apple-system, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(size * 0.38)
        xb, yb, w, h, _, _ = cr.text_extents(initials)
        cr.move_to(size / 2.0 - w / 2.0 - xb, size / 2.0 + h / 2.0)
        cr.show_text(initials)

        import io
        bio = io.BytesIO()
        surf.write_to_png(bio)
        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(bio.getvalue())
        loader.close()
        return loader.get_pixbuf()
    except Exception:
        return None


def get_app_icon_pixbuf(app_id: str, size: int = 56, app_name: Optional[str] = None) -> Optional[GdkPixbuf.Pixbuf]:
    """Load authentic high-resolution app squircle icon from assets/app_icons, themes, or generated fallback."""
    # 1. Custom app icons in assets/app_icons/
    png_path = os.path.join(APP_ICONS_DIR, f"{app_id}.png")
    if os.path.exists(png_path):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(png_path, size, size, True)
        except Exception:
            pass

    # 2. Check normalized name (e.g. telegram-desktop -> telegram)
    clean_id = app_id.lower().replace("-desktop", "").replace("_", "-")
    png_path2 = os.path.join(APP_ICONS_DIR, f"{clean_id}.png")
    if os.path.exists(png_path2):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(png_path2, size, size, True)
        except Exception:
            pass

    # 2.5 Check dynamic online cache in ~/.cache/macos-appstore/icons/
    for cid in [clean_id, app_id, app_id.lower(), clean_id.lower()]:
        cached_p = os.path.join(CACHE_ICONS_DIR, f"{cid}.png")
        if os.path.exists(cached_p):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(cached_p, size, size, True)
            except Exception:
                pass

    # 3. Direct absolute path if provided
    if os.path.isabs(app_id) and os.path.exists(app_id):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(app_id, size, size, True)
        except Exception:
            pass

    # 4. System icon search paths
    search_dirs = [
        "/home/tramvo/.local/share/icons/MacTahoe/apps/scalable",
        "/usr/share/icons/hicolor/scalable/apps",
        "/usr/share/icons/hicolor/48x48/apps",
        "/usr/share/pixmaps"
    ]
    for d in search_dirs:
        for ext in [".svg", ".png"]:
            cand = os.path.join(d, f"{app_id}{ext}")
            if os.path.exists(cand):
                try:
                    return GdkPixbuf.Pixbuf.new_from_file_at_scale(cand, size, size, True)
                except Exception:
                    pass
            cand2 = os.path.join(d, f"{clean_id}{ext}")
            if os.path.exists(cand2):
                try:
                    return GdkPixbuf.Pixbuf.new_from_file_at_scale(cand2, size, size, True)
                except Exception:
                    pass

    # 5. GTK IconTheme lookup
    theme = Gtk.IconTheme.get_default()
    if theme:
        for iname in [app_id, clean_id, f"{app_id}-symbolic", f"{clean_id}-symbolic"]:
            if theme.has_icon(iname):
                try:
                    return theme.load_icon(iname, size, Gtk.IconLookupFlags.FORCE_SIZE)
                except Exception:
                    pass

    # 6. High quality on-the-fly squircle fallback with initials
    if app_name:
        return generate_fallback_app_icon(app_name, size)

    return None


_system_apps_cache = None


CAT_TO_SNAPD_SECTION = {
    "business": "productivity",
    "developer_tools": "development",
    "develop": "development",
    "education": "education",
    "entertainment": "entertainment",
    "finance": "finance",
    "games": "games",
    "arcade": "games",
    "graphics_design": "art-and-design",
    "create": "art-and-design",
    "health_fitness": "health-and-fitness",
    "lifestyle": "personalisation",
    "medical": "science",
    "music": "music-and-audio",
    "news": "news-and-weather",
    "photo_video": "photo-and-video",
    "productivity": "productivity",
    "work": "productivity",
    "reference": "books-and-reference",
    "social_networking": "social",
    "play": "entertainment",
    "sports": "games",
    "travel": "utilities",
    "utilities": "utilities",
    "weather": "news-and-weather",
}

def query_snapd_apps(section: Optional[str] = None, query: Optional[str] = None, limit: int = 24) -> List[Dict[str, Any]]:
    """Query real packages directly from the local snapd daemon unix socket."""
    socket_path = "/run/snapd.socket"
    if not os.path.exists(socket_path):
        return []
    try:
        import socket, http.client, json, urllib.parse
        conn = http.client.HTTPConnection("localhost", timeout=3)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(socket_path)
        conn.sock = sock

        endpoint = "/v2/find"
        if section:
            endpoint += f"?section={section}"
        elif query:
            endpoint += f"?q={urllib.parse.quote(query)}"
        else:
            endpoint += "?select=featured"

        conn.request("GET", endpoint)
        resp = conn.getresponse()
        if resp.status != 200:
            return []

        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        results = data.get("result", [])
        apps = []
        for item in results[:limit]:
            s_name = item.get("name")
            if not s_name:
                continue
            title = item.get("title") or s_name.replace("-", " ").title()
            summary = item.get("summary") or "Linux Application"
            dsize = item.get("download-size") or 0
            size_str = f"{int(dsize / (1024 * 1024))} MB" if dsize else "50 MB"
            apps.append({
                "id": s_name,
                "name": title,
                "subtitle": summary,
                "category": section or "utilities",
                "category_name": (section or "Software").replace("-", " ").title(),
                "developer": item.get("publisher", {}).get("display-name", "Canonical"),
                "rating": 4.8,
                "reviews": "10K+",
                "size": size_str,
                "version": item.get("version", "1.0"),
                "snap": s_name,
                "classic": item.get("confinement") == "classic",
                "icon_url": item.get("icon"),
                "in_app_purchases": False,
                "desc": item.get("description", summary),
                "features": [
                    f"Official Ubuntu Snap package: {s_name}",
                    f"Maintained by {item.get('publisher', {}).get('display-name', 'Developer')}",
                    "One-click sandboxed installation on Ubuntu Linux"
                ]
            })
        return apps
    except Exception:
        return []


def load_system_desktop_apps() -> List[Dict[str, Any]]:
    """Loads all installed desktop applications on the system."""
    global _system_apps_cache
    if _system_apps_cache is not None:
        return _system_apps_cache

    apps = []
    seen = set()
    dirs = [
        os.path.expanduser('~/.local/share/applications'),
        '/usr/share/applications'
    ]
    for d in dirs:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if not f.endswith('.desktop'):
                continue
            fpath = os.path.join(d, f)
            try:
                name, comment, icon, exec_cmd, nodisplay = None, "", None, None, False
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                    in_main = False
                    for line in fp:
                        line = line.strip()
                        if line == '[Desktop Entry]':
                            in_main = True
                        elif line.startswith('[') and line.endswith(']'):
                            in_main = False
                        if in_main:
                            if line.startswith('Name=') and not name:
                                name = line.split('=', 1)[1].strip()
                            elif line.startswith('Comment=') and not comment:
                                comment = line.split('=', 1)[1].strip()
                            elif line.startswith('Icon=') and not icon:
                                icon = line.split('=', 1)[1].strip()
                            elif line.startswith('Exec=') and not exec_cmd:
                                exec_cmd = line.split('=', 1)[1].strip()
                            elif line.startswith('NoDisplay=true'):
                                nodisplay = True
                if name and exec_cmd and not nodisplay and name.lower() not in seen:
                    seen.add(name.lower())
                    cmd_clean = exec_cmd.split()[0].replace('%U', '').replace('%u', '').replace('%F', '').replace('%f', '')
                    app_id = icon if (icon and not os.path.isabs(icon)) else f.replace('.desktop', '')
                    apps.append({
                        "id": app_id,
                        "name": name,
                        "subtitle": comment or "Installed System Application",
                        "category": "utilities",
                        "category_name": "Installed",
                        "developer": "System Application",
                        "rating": 4.8,
                        "reviews": "10K",
                        "size": "Local",
                        "version": "1.0",
                        "bin": cmd_clean,
                        "in_app_purchases": False,
                        "desc": comment or f"{name} application installed on your system.",
                        "features": [f"Launch {name} directly from App Store"]
                    })
            except Exception:
                pass
    _system_apps_cache = apps
    return apps


def query_snap_store(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Query Canonical Snap Store online for apps with strict relevance ranking."""
    if not shutil.which("snap"):
        return []
    try:
        proc = subprocess.run(
            ["snap", "find", query],
            capture_output=True,
            text=True,
            timeout=2.5
        )
        if proc.returncode != 0:
            return []
        lines = proc.stdout.strip().splitlines()
        if len(lines) <= 1:
            return []

        q_clean = query.lower().strip()
        q_words = [w for w in q_clean.replace("-", " ").replace("_", " ").split() if len(w) > 1]

        # Related search keywords dictionary for popular queries
        related_aliases = {
            "facebook": ["messenger", "caprine", "fb", "meta", "facebook"],
            "messenger": ["facebook", "caprine", "chat"],
            "chrome": ["google", "chromium", "browser"],
            "edge": ["microsoft", "browser"],
            "office": ["libreoffice", "onlyoffice", "wps"],
            "video": ["vlc", "kdenlive", "obs", "player", "editor"],
            "music": ["spotify", "audacity", "player", "sound"],
        }
        aliases = related_aliases.get(q_clean, [])

        scored_results = []
        for line in lines[1:]:
            parts = line.split(None, 4)
            if len(parts) >= 5:
                s_name, s_ver, s_pub, s_notes, s_summary = parts
            elif len(parts) == 4:
                s_name, s_ver, s_pub, s_summary = parts[0], parts[1], parts[2], parts[3]
            else:
                continue

            name_lower = s_name.lower()
            summary_lower = s_summary.lower()

            # Relevance Scoring
            score = 0
            # 1. Exact or prefix match in package name
            if name_lower == q_clean:
                score += 1000
            elif name_lower.startswith(q_clean):
                score += 600
            elif q_clean in name_lower:
                score += 400
            else:
                matched_words = sum(1 for w in q_words if w in name_lower)
                if matched_words:
                    score += 200 * matched_words

            # 2. Check aliases (e.g. caprine for facebook)
            for alias in aliases:
                if alias in name_lower:
                    score += 350
                elif alias in summary_lower:
                    score += 150

            # 3. Query in summary
            if q_clean in summary_lower:
                score += 100

            # Filter out completely irrelevant noise when query has at least 3 chars
            if len(q_clean) >= 3 and score < 80:
                continue

            disp_name = s_name.replace('-', ' ').title()
            # Custom polished display names
            if s_name == "facebook-messenger-desktop":
                disp_name = "Facebook Messenger Desktop"
            elif s_name == "caprine":
                disp_name = "Caprine (Facebook Messenger)"
            elif s_name == "facebook-webapp":
                disp_name = "Facebook Web App"
            elif s_name == "facebook-auto-utility-tool":
                disp_name = "Facebook Auto Utility Tool"

            scored_results.append((score, {
                "id": s_name,
                "name": disp_name,
                "subtitle": s_summary,
                "category": "utilities",
                "category_name": "Snap Store",
                "developer": s_pub.replace('✓', '').replace('✪', '').strip(),
                "rating": 4.8,
                "reviews": "20K",
                "size": "Snap Store",
                "version": s_ver,
                "snap": s_name,
                "bin": s_name,
                "in_app_purchases": False,
                "desc": f"{s_summary}\n\nPackage: {s_name}\nVersion: {s_ver}\nPublisher: {s_pub}",
                "features": [
                    f"Official Snap package: {s_name}",
                    f"Maintained by {s_pub}",
                    "One-click sandboxed installation"
                ]
            }))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:max_results]]
    except Exception as e:
        print(f"[SnapSearch] Error: {e}")
        return []


# =========================================================================
# WIDGETS: CIRCULAR AVATAR, TRAFFIC LIGHTS, APP CARD
# =========================================================================

class CircularAvatarWidget(Gtk.DrawingArea):
    """Draws real user profile picture inside a perfect circle with specular border ring."""
    def __init__(self, avatar_path: Optional[str], fullname: str = "User", size: int = 36):
        super().__init__()
        self.size = size
        self.avatar_path = avatar_path
        self.fullname = fullname
        self.set_size_request(size, size)
        self.pixbuf = None
        self._load_pixbuf()
        self.connect("draw", self._on_draw)

    def _load_pixbuf(self):
        self.pixbuf = None
        if self.avatar_path and os.path.exists(self.avatar_path):
            try:
                self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.avatar_path, self.size * 2, self.size * 2, True)
            except Exception as e:
                print(f"[AppStore] Error loading user avatar: {e}")

    def update_profile(self, new_avatar_path: Optional[str], new_fullname: Optional[str] = None):
        self.avatar_path = new_avatar_path
        if new_fullname:
            self.fullname = new_fullname
        self._load_pixbuf()
        self.queue_draw()

    def _on_draw(self, widget, cr: cairo.Context):
        s = self.size
        r = s / 2.0

        cr.save()
        cr.set_antialias(cairo.Antialias.SUBPIXEL)
        cr.arc(r, r, r - 0.5, 0, 2 * math.pi)
        cr.clip()

        if self.pixbuf:
            scale_x = s / float(self.pixbuf.get_width())
            scale_y = s / float(self.pixbuf.get_height())
            cr.scale(scale_x, scale_y)
            Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
            cr.paint()
        else:
            # Fallback Apple Memoji / Monogram gradient with user's real initials
            pat = cairo.LinearGradient(0, 0, s, s)
            pat.add_color_stop_rgb(0.0, 0.20, 0.55, 0.95)
            pat.add_color_stop_rgb(1.0, 0.05, 0.35, 0.85)
            cr.set_source(pat)
            cr.paint()

            initials = "".join([w[0].upper() for w in self.fullname.split()[:2]]) or "U"
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.select_font_face("-apple-system, Inter, sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(s * 0.40)
            xb, yb, w, h, _, _ = cr.text_extents(initials)
            cr.move_to(r - w / 2 - xb, r + h / 2)
            cr.show_text(initials)

        cr.restore()

        # Specular outer ring
        cr.save()
        cr.set_antialias(cairo.Antialias.SUBPIXEL)
        cr.arc(r, r, r - 0.75, 0, 2 * math.pi)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.14)
        cr.set_line_width(1.0)
        cr.stroke()
        cr.restore()
        return False


class TrafficLightsWidget(Gtk.Box):
    """Authentic Apple macOS Traffic Lights: 🔴 Red, 🟡 Yellow, 🟢 Green."""
    def __init__(self, on_close, on_minimize, on_maximize):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_start(16)
        self.set_margin_top(14)
        self.set_margin_bottom(12)

        def make_light(color_class, tooltip, symbol, cb):
            btn = Gtk.Button()
            btn.get_style_context().add_class("mac-traffic-light")
            btn.get_style_context().add_class(color_class)
            btn.set_tooltip_text(tooltip)
            lbl = Gtk.Label(label="")
            lbl.get_style_context().add_class("tl-symbol")
            btn.add(lbl)

            btn.connect("enter-notify-event", lambda b, e: [lbl.set_text(symbol), False][1])
            btn.connect("leave-notify-event", lambda b, e: [lbl.set_text(""), False][1])
            btn.connect("clicked", lambda _: cb())
            return btn

        self.pack_start(make_light("tl-red", "Close", "✕", on_close), False, False, 0)
        self.pack_start(make_light("tl-yellow", "Minimize", "—", on_minimize), False, False, 0)
        self.pack_start(make_light("tl-green", "Zoom", "⤢", on_maximize), False, False, 0)


class AppCardWidget(Gtk.Box):
    """Authentic Apple macOS App Store Card matching reference layout."""
    def __init__(self, app: Dict[str, Any], on_open_detail, on_install_or_launch, window=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.app = app
        self.on_open_detail = on_open_detail
        self.on_install_or_launch = on_install_or_launch
        self.window = window
        self._pulse_id = None
        self.is_installing = False

        self.get_style_context().add_class("mac-app-card")
        self.set_margin_start(2)
        self.set_margin_end(2)
        self.set_margin_top(2)
        self.set_margin_bottom(2)

        if self.window and hasattr(self.window, "_register_card"):
            self.window._register_card(self)
            self.connect("destroy", lambda *_: self.window._unregister_card(self) if self.window and hasattr(self.window, "_unregister_card") else None)

        # Clickable event box for detail view
        ev_box = Gtk.EventBox()
        ev_box.set_visible_window(False)
        ev_box.connect("button-press-event", lambda *_: [self.on_open_detail(self.app), True][1])

        inner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        ev_box.add(inner_box)

        # 56x56 High-Resolution Squircle Icon
        self.icon_img = Gtk.Image()
        pb = get_app_icon_pixbuf(app["id"], 56, app.get("name"))
        if pb:
            self.icon_img.set_from_pixbuf(pb)
        else:
            self.icon_img.set_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)

        inner_box.pack_start(self.icon_img, False, False, 0)

        # App Info Box
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_valign(Gtk.Align.CENTER)

        lbl_title = Gtk.Label(label=app["name"])
        lbl_title.get_style_context().add_class("mac-app-title")
        lbl_title.set_xalign(0.0)
        lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label=app.get("subtitle", ""))
        lbl_sub.get_style_context().add_class("mac-app-subtitle")
        lbl_sub.set_xalign(0.0)
        lbl_sub.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.pack_start(lbl_sub, False, False, 0)

        inner_box.pack_start(info_box, True, True, 0)
        self.pack_start(ev_box, True, True, 0)

        # Right Action Box: [ Get / Open ] pill + progress bar + caption
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        action_box.set_valign(Gtk.Align.CENTER)
        action_box.set_halign(Gtk.Align.END)

        self.btn_action = Gtk.Button()
        self.btn_action.get_style_context().add_class("mac-pill-btn")
        self.btn_action.connect("clicked", self._on_action_clicked)
        action_box.pack_start(self.btn_action, False, False, 0)

        # Slim macOS Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.get_style_context().add_class("mac-store-progress")
        self.progress_bar.set_size_request(68, 4)
        self.progress_bar.set_no_show_all(True)
        action_box.pack_start(self.progress_bar, False, False, 1)

        # Card action status label
        self.lbl_card_status = Gtk.Label(label="")
        self.lbl_card_status.get_style_context().add_class("mac-update-status")
        self.lbl_card_status.set_no_show_all(True)
        action_box.pack_start(self.lbl_card_status, False, False, 0)

        if self.app.get("in_app_purchases", False):
            self.lbl_iap = Gtk.Label(label="Mua trong ứng dụng")
            self.lbl_iap.set_xalign(0.5)
            self.lbl_iap.get_style_context().add_class("mac-iap-label")
            action_box.pack_start(self.lbl_iap, False, False, 0)
        else:
            self.lbl_iap = Gtk.Label(label="")
            self.lbl_iap.set_xalign(0.5)
            self.lbl_iap.get_style_context().add_class("mac-iap-spacer")
            action_box.pack_start(self.lbl_iap, False, False, 0)

        self.pack_end(action_box, False, False, 6)
        self.update_state()

        # Check if local icon was found or if remote snap icon should be fetched
        snap_name = app.get("snap")
        if snap_name:
            local_png = os.path.join(APP_ICONS_DIR, f"{snap_name}.png")
            cached_png = os.path.join(CACHE_ICONS_DIR, f"{snap_name}.png")
            if not os.path.exists(local_png) and not os.path.exists(cached_png):
                self._fetch_remote_icon_async(snap_name)

    def _fetch_remote_icon_async(self, snap_name: str):
        def _fetch():
            try:
                import urllib.request, json
                req = urllib.request.Request(
                    f"https://api.snapcraft.io/api/v1/snaps/details/{snap_name}",
                    headers={"X-Ubuntu-Series": "16", "User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    icon_url = data.get("icon_url")
                if icon_url:
                    dest = os.path.join(CACHE_ICONS_DIR, f"{snap_name}.png")
                    with urllib.request.urlopen(icon_url, timeout=5) as img_resp:
                        with open(dest, "wb") as f:
                            f.write(img_resp.read())
                    if os.path.exists(dest):
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(dest, 56, 56, True)
                        if pb:
                            GLib.idle_add(self._update_remote_icon, pb)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_remote_icon(self, pb: GdkPixbuf.Pixbuf):
        if hasattr(self, 'icon_img') and pb:
            self.icon_img.set_from_pixbuf(pb)

    def set_installing(self, is_installing: bool, success: Optional[bool] = None):
        self.is_installing = is_installing
        ctx = self.btn_action.get_style_context()
        if is_installing:
            self.btn_action.set_label(t("appstore_installing", "Installing…"))
            self.btn_action.set_sensitive(False)
            ctx.remove_class("pill-get")
            ctx.remove_class("pill-open")
            ctx.add_class("pill-installing")
            self.progress_bar.show()
            self.lbl_card_status.set_text("Đang cài...")
            self.lbl_card_status.show()
            if not self._pulse_id:
                def _pulse():
                    if hasattr(self, 'progress_bar') and self.progress_bar.get_visible():
                        self.progress_bar.pulse()
                        return True
                    return False
                self._pulse_id = GLib.timeout_add(80, _pulse)
        else:
            if self._pulse_id:
                GLib.source_remove(self._pulse_id)
                self._pulse_id = None
            ctx.remove_class("pill-installing")
            self.btn_action.set_sensitive(True)
            if success or is_app_installed(self.app):
                self.progress_bar.set_fraction(1.0)
                self.btn_action.set_label(t("appstore_open", "Open"))
                ctx.remove_class("pill-get")
                ctx.add_class("pill-open")
                self.lbl_card_status.set_text("✓ Đã cài đặt")
                self.lbl_card_status.get_style_context().remove_class("mac-update-status-err")
                self.lbl_card_status.get_style_context().add_class("mac-update-status-ok")
                self.lbl_card_status.show()
                GLib.timeout_add(2500, lambda: [self.progress_bar.hide(), self.lbl_card_status.hide()] if hasattr(self, 'progress_bar') else None)
            else:
                self.progress_bar.hide()
                self.btn_action.set_label(t("appstore_get", "Get"))
                ctx.remove_class("pill-open")
                ctx.add_class("pill-get")
                self.lbl_card_status.set_text("⚠ Lỗi cài đặt")
                self.lbl_card_status.get_style_context().remove_class("mac-update-status-ok")
                self.lbl_card_status.get_style_context().add_class("mac-update-status-err")
                self.lbl_card_status.show()
                GLib.timeout_add(3500, lambda: self.lbl_card_status.hide() if hasattr(self, 'lbl_card_status') else None)

    def update_state(self):
        if self.is_installing:
            return
        installed = is_app_installed(self.app)
        ctx = self.btn_action.get_style_context()
        self.btn_action.set_sensitive(True)
        if installed:
            self.btn_action.set_label(t("appstore_open", "Open"))
            ctx.remove_class("pill-get")
            ctx.remove_class("pill-installing")
            ctx.add_class("pill-open")
        else:
            self.btn_action.set_label(t("appstore_get", "Get"))
            ctx.remove_class("pill-open")
            ctx.remove_class("pill-installing")
            ctx.add_class("pill-get")

    def _on_action_clicked(self, btn):
        self.on_install_or_launch(self.app, self)


# =========================================================================
# MAIN APP STORE WINDOW
# =========================================================================

class MacOSAppStoreWindow(Gtk.Window):
    """
    Main macOS Sequoia App Store Desktop Window for Ubuntu GNOME.
    Fully native GTK3 + Cairo with authentic frosted glass aesthetics.
    """
    _instance = None
    _css_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MacOSAppStoreWindow()
        return cls._instance

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        GLib.set_prgname("macos-appstore")
        if not GLib.get_application_name():
            GLib.set_application_name(t("appstore_title", "App Store"))
        self.set_title("App Store")
        self.set_wmclass("macos-appstore", "MacOSAppStore")
        self.set_role("appstore")
        self._is_iconified = False

        # Official App Store Icon
        icon_path = os.path.join(BASE_DIR, "assets", "appstore_icon.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        self.set_default_size(1020, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_resizable(True)

        geom = Gdk.Geometry()
        geom.min_width = 800
        geom.min_height = 550
        self.set_geometry_hints(None, geom, Gdk.WindowHints.MIN_SIZE)

        self._is_maximized = False
        self.is_standalone = False
        self.is_dark = is_system_dark_mode()
        self.current_tab = "categories"
        self._history_stack = ["categories"]

        # Track active cards & live install/update states
        self._active_cards = {}  # app_id -> list of AppCardWidget
        self._installing_apps = set()  # set of app_ids currently installing
        self.update_rows = {}  # pkg_id -> dict of row widgets for updates

        # RGBA visual for rounded window
        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

        self._load_css()
        self._setup_ui()
        add_language_listener(lambda *_: GLib.idle_add(self._refresh_language))

        # Connect window events
        self.connect("draw", self._on_window_draw)
        self.connect_after("draw", self._on_window_draw_after)
        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_key_press)
        self.connect("button-press-event", self._on_window_button_press)
        self.connect("focus-in-event", self._on_window_focus_in)
        self.connect("window-state-event", self._on_window_state_event)

        # Dynamic System Theme Listener
        try:
            self._gnome_settings = Gio.Settings.new("org.gnome.desktop.interface")
            self._gnome_settings.connect("changed::color-scheme", lambda *_: GLib.idle_add(self.apply_theme))
            self._gnome_settings.connect("changed::gtk-theme", lambda *_: GLib.idle_add(self.apply_theme))
        except Exception:
            pass

        self.apply_theme()

    def _refresh_language(self):
        """Refresh all persistent App Store chrome after a language change."""
        try:
            self.set_title(t("app_store_title", "App Store"))
            if hasattr(self, "search_entry"):
                self.search_entry.set_placeholder_text(t("search_short", "Search"))
            labels = {
                "discover": t("appstore_discover", "Discover"),
                "arcade": t("appstore_arcade", "Arcade"),
                "create": t("appstore_create", "Create"),
                "work": t("appstore_work", "Work"),
                "play": t("appstore_play", "Play"),
                "develop": t("appstore_develop", "Develop"),
                "categories": t("appstore_categories", "Categories"),
                "updates": t("appstore_updates", "Updates"),
            }
            for key, item in getattr(self, "_nav_buttons", {}).items():
                item[3].set_text(labels.get(key, key))
            if hasattr(self, "current_tab"):
                self.select_tab(self.current_tab)
        except Exception as e:
            print(f"[AppStore] language refresh error: {e}")
        return False

    def _register_card(self, card: AppCardWidget):
        app_id = card.app.get("id")
        if not app_id:
            return
        if app_id not in self._active_cards:
            self._active_cards[app_id] = []
        if card not in self._active_cards[app_id]:
            self._active_cards[app_id].append(card)
        if app_id in self._installing_apps:
            card.set_installing(True)

    def _unregister_card(self, card: AppCardWidget):
        app_id = card.app.get("id")
        if app_id and app_id in self._active_cards and card in self._active_cards[app_id]:
            self._active_cards[app_id].remove(card)

    def _setup_ui(self):
        self.master_overlay = Gtk.Overlay()
        self.add(self.master_overlay)

        self.root_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root_card.get_style_context().add_class("mac-appstore-window")
        self.master_overlay.add(self.root_card)

        self._setup_resize_handles()

        # Split: Sidebar (left) + Canvas (right)
        self.main_split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.root_card.pack_start(self.main_split, True, True, 0)

        # -----------------------------------------------------------------
        # 1. LEFT SIDEBAR
        # -----------------------------------------------------------------
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_box.set_size_request(210, -1)
        self.sidebar_box.get_style_context().add_class("mac-store-sidebar")
        self.main_split.pack_start(self.sidebar_box, False, False, 0)

        # Traffic Lights
        tl = TrafficLightsWidget(
            on_close=self.close_window,
            on_minimize=self.iconify,
            on_maximize=self.toggle_maximize
        )
        self.sidebar_box.pack_start(tl, False, False, 0)

        # Search Bar in sidebar: pill with "Search" placeholder
        search_wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_wrap.get_style_context().add_class("mac-store-search-wrap")
        search_wrap.set_margin_start(14)
        search_wrap.set_margin_end(14)
        search_wrap.set_margin_bottom(12)

        search_icon = get_image("search", 13, "#8e8e93")
        search_wrap.pack_start(search_icon, False, False, 4)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(t("search_short", "Search"))
        self.search_entry.get_style_context().add_class("mac-store-search-input")
        self.search_entry.connect("changed", self._on_search_text_changed)
        self.search_entry.connect("activate", self._on_search_enter)
        search_wrap.pack_start(self.search_entry, True, True, 0)
        self.sidebar_box.pack_start(search_wrap, False, False, 0)

        # Navigation Scroll
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar_box.pack_start(nav_scroll, True, True, 0)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.nav_box.set_margin_start(10)
        self.nav_box.set_margin_end(10)
        nav_scroll.add(self.nav_box)

        # 8 Authentic macOS App Store items in exact order
        self._nav_buttons = {}
        self._add_nav_item("discover", t("appstore_discover", "Discover"), "star")
        self._add_nav_item("arcade", t("appstore_arcade", "Arcade"), "gamepad")
        self._add_nav_item("create", t("appstore_create", "Create"), "palette")
        self._add_nav_item("work", t("appstore_work", "Work"), "paperplane")
        self._add_nav_item("play", t("appstore_play", "Play"), "rocket")
        self._add_nav_item("develop", t("appstore_develop", "Develop"), "hammer")
        self._add_nav_item("categories", t("appstore_categories", "Categories"), "grid")
        self._add_nav_item("updates", t("appstore_updates", "Updates"), "tray_down")

        # Bottom Profile Card (Real User Avatar + Full Name Sync)
        self._build_sidebar_user_profile()

        # -----------------------------------------------------------------
        # 2. MAIN CONTENT AREA
        # -----------------------------------------------------------------
        self.content_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.content_container.get_style_context().add_class("mac-store-content")
        self.main_split.pack_start(self.content_container, True, True, 0)

        # Top Header Bar (Back button + dynamic title, hidden on Categories overview)
        self._build_top_header()

        # Stack Pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(160)
        self.content_container.pack_start(self.stack, True, True, 0)

        # Build pages
        self._build_categories_overview_page()
        self._build_category_subpage()
        self._build_search_page()
        self._build_discover_page()
        self._build_category_pages()
        self._build_updates_page()
        self._build_detail_page()

        # Default to "Discover" tab on launch
        self.select_tab("discover")

    def _build_sidebar_user_profile(self):
        """Builds bottom profile card with circular user avatar and real name."""
        self.profile_btn = Gtk.Button()
        self.profile_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.profile_btn.get_style_context().add_class("mac-sidebar-profile-btn")
        self.profile_btn.connect("clicked", lambda _: self._on_profile_clicked())

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(8)
        row.set_margin_bottom(12)

        username, fullname, avatar_path = get_user_profile()
        self.user_fullname = fullname or username or "User"
        self.user_avatar_path = avatar_path

        # Circular Avatar widget
        self.avatar_widget = CircularAvatarWidget(avatar_path, self.user_fullname, size=36)
        row.pack_start(self.avatar_widget, False, False, 0)

        # User's Full Name (Bold text vertically centered with avatar, matching macOS)
        self.lbl_profile_name = Gtk.Label(label=self.user_fullname)
        self.lbl_profile_name.get_style_context().add_class("profile-name")
        self.lbl_profile_name.set_xalign(0.0)
        self.lbl_profile_name.set_valign(Gtk.Align.CENTER)
        self.lbl_profile_name.set_ellipsize(Pango.EllipsizeMode.END)
        row.pack_start(self.lbl_profile_name, True, True, 0)

        self.profile_btn.add(row)
        self.sidebar_box.pack_end(self.profile_btn, False, False, 0)

    def _refresh_user_profile(self):
        """Dynamically reload user profile picture and name."""
        username, fullname, avatar_path = get_user_profile()
        self.user_fullname = fullname or username or "User"
        self.user_avatar_path = avatar_path
        if hasattr(self, 'avatar_widget'):
            self.avatar_widget.update_profile(avatar_path, self.user_fullname)
        if hasattr(self, 'lbl_profile_name'):
            self.lbl_profile_name.set_text(self.user_fullname)

    def _on_profile_clicked(self):
        """Open Avatar / Profile editor when user clicks profile card."""
        try:
            from src.ui.macos_avatar_dialog import MacOSAvatarDialog
            dialog = MacOSAvatarDialog(
                parent=self,
                current_avatar=self.user_avatar_path,
                fullname=self.user_fullname,
                on_save=lambda _: self._refresh_user_profile()
            )
            dialog.show_all()
        except Exception as e:
            print(f"[StoreWindow] Error opening avatar dialog: {e}")

    def _on_window_focus_in(self, widget, event):
        self._refresh_user_profile()
        return False

    def _build_top_header(self):
        self.top_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.top_header.get_style_context().add_class("mac-store-header-bar")
        self.top_header.set_size_request(-1, 52)
        self.top_header.set_margin_start(28)
        self.top_header.set_margin_end(28)
        self.top_header.set_no_show_all(True)

        # Back button
        self.btn_back = Gtk.Button()
        self.btn_back.get_style_context().add_class("mac-header-nav-btn")
        self.btn_back.add(Gtk.Label(label="‹"))
        self.btn_back.set_tooltip_text("Quay lại")
        self.btn_back.connect("clicked", lambda _: self._navigate_back())
        self.top_header.pack_start(self.btn_back, False, False, 0)

        # Page Title
        self.header_title = Gtk.Label(label="Danh mục")
        self.header_title.get_style_context().add_class("mac-page-header-title")
        self.header_title.set_xalign(0.0)
        self.top_header.pack_start(self.header_title, False, False, 4)

        # Status spinner
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status_box.set_valign(Gtk.Align.CENTER)
        self.spinner = Gtk.Spinner()
        self.status_lbl = Gtk.Label(label="")
        self.status_lbl.get_style_context().add_class("mac-header-status-lbl")
        self.status_box.pack_start(self.spinner, False, False, 0)
        self.status_box.pack_start(self.status_lbl, False, False, 0)
        self.top_header.pack_end(self.status_box, False, False, 0)

        self.content_container.pack_start(self.top_header, False, False, 0)

    def _add_nav_item(self, tab_key: str, title: str, icon_name: str, badge: Optional[str] = None):
        btn = Gtk.Button()
        btn.get_style_context().add_class("mac-nav-item")
        btn.set_relief(Gtk.ReliefStyle.NONE)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(6)
        row.set_margin_bottom(6)

        # Vector Icon
        icon_img = get_image(icon_name, 16, "#8e8e93")
        row.pack_start(icon_img, False, False, 0)

        lbl = Gtk.Label(label=title)
        lbl.get_style_context().add_class("mac-nav-label")
        lbl.set_xalign(0.0)
        row.pack_start(lbl, True, True, 0)

        if badge:
            badge_lbl = Gtk.Label(label=badge)
            badge_lbl.get_style_context().add_class("mac-nav-badge")
            row.pack_end(badge_lbl, False, False, 0)

        btn.add(row)
        btn.connect("clicked", lambda _: self.select_tab(tab_key))
        self.nav_box.pack_start(btn, False, False, 0)
        self._nav_buttons[tab_key] = (btn, icon_img, icon_name, lbl)

    # -----------------------------------------------------------------
    # CATEGORIES OVERVIEW PAGE (AUTHENTIC MACOS REPLICA)
    # -----------------------------------------------------------------
    def _build_categories_overview_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_start(32)
        main_box.set_margin_end(32)
        main_box.set_margin_top(14)
        main_box.set_margin_bottom(36)
        scrolled.add(main_box)

        # Centered "Categories" Header
        header_lbl = Gtk.Label(label="Danh mục")
        header_lbl.get_style_context().add_class("mac-categories-page-title")
        header_lbl.set_halign(Gtk.Align.CENTER)
        header_lbl.set_margin_top(14)
        header_lbl.set_margin_bottom(12)
        main_box.pack_start(header_lbl, False, False, 0)

        # 3-Column Categories Grid / Columns
        cols_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        cols_container.set_homogeneous(True)

        for col_items in CATEGORY_COLUMNS:
            col_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for cat_id, cat_name, icon_filename in col_items:
                row_eb = Gtk.EventBox()
                row_eb.get_style_context().add_class("mac-cat-item-row")
                row_eb.connect("button-press-event", lambda _w, _e, cid=cat_id, cname=cat_name: self._on_category_clicked(cid, cname))

                row_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

                row_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_hbox.set_margin_top(7)
                row_hbox.set_margin_bottom(7)
                row_hbox.set_margin_start(6)
                row_hbox.set_margin_end(6)

                # Icon
                icon_path = os.path.join(CAT_ICONS_DIR, icon_filename)
                icon_img = Gtk.Image()
                if os.path.exists(icon_path):
                    try:
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 22, 22, True)
                        icon_img.set_from_pixbuf(pb)
                    except Exception:
                        icon_img.set_from_icon_name("folder", Gtk.IconSize.MENU)
                else:
                    icon_img.set_from_icon_name("folder", Gtk.IconSize.MENU)
                row_hbox.pack_start(icon_img, False, False, 0)

                # Name
                name_lbl = Gtk.Label(label=cat_name)
                name_lbl.get_style_context().add_class("mac-cat-item-label")
                name_lbl.set_xalign(0.0)
                row_hbox.pack_start(name_lbl, True, True, 0)

                row_vbox.pack_start(row_hbox, False, False, 0)

                # Hairline Separator Divider
                divider = Gtk.Box()
                divider.get_style_context().add_class("mac-cat-hairline-divider")
                divider.set_size_request(-1, 1)
                row_vbox.pack_start(divider, False, False, 0)

                row_eb.add(row_vbox)
                col_box.pack_start(row_eb, False, False, 0)

            cols_container.pack_start(col_box, True, True, 0)

        main_box.pack_start(cols_container, False, False, 0)

        # Section: "Editors' Choice: Top Apps for Every Task"
        sec_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sec_header.set_margin_top(22)
        sec_header.set_margin_bottom(8)

        sec_title = Gtk.Label(label="Lựa chọn của biên tập viên: Ứng dụng hàng đầu")
        sec_title.get_style_context().add_class("mac-section-title")
        sec_title.set_xalign(0.0)
        sec_header.pack_start(sec_title, False, False, 0)

        btn_see_all = Gtk.Button(label="Xem tất cả")
        btn_see_all.get_style_context().add_class("mac-see-all-btn")
        btn_see_all.connect("clicked", lambda _: self.select_tab("discover"))
        sec_header.pack_end(btn_see_all, False, False, 0)

        main_box.pack_start(sec_header, False, False, 0)

        # 2-Column Grid for Editors' Choice Apps
        grid = Gtk.Grid()
        grid.set_column_spacing(28)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        for i, app in enumerate(EDITORS_CHOICE_APPS):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
            grid.attach(card, i % 2, i // 2, 1, 1)

        main_box.pack_start(grid, False, False, 0)
        self.stack.add_named(scrolled, "categories")

    def _build_category_subpage(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.category_subpage_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.category_subpage_box.set_margin_start(32)
        self.category_subpage_box.set_margin_end(32)
        self.category_subpage_box.set_margin_top(16)
        self.category_subpage_box.set_margin_bottom(36)
        scrolled.add(self.category_subpage_box)
        self.stack.add_named(scrolled, "category_subpage")

    def _on_category_clicked(self, cat_id: str, cat_name: str):
        matched = [a for a in EDITORS_CHOICE_APPS + APP_CATALOG if a.get("category") == cat_id or cat_id in a.get("category", "")]
        if not matched:
            matched = [a for a in APP_CATALOG if a.get("category") == cat_id]
        if not matched:
            matched = [a for a in APP_CATALOG if cat_id in a.get("category_name", "").lower() or cat_id in a.get("subtitle", "").lower()]
        if not matched:
            matched = APP_CATALOG[:8]
        self._show_filtered_category_view(cat_id, cat_name, matched)

        # Asynchronously fetch real packages from local snapd socket
        snapd_sec = CAT_TO_SNAPD_SECTION.get(cat_id)
        if snapd_sec:
            def _fetch():
                extra_apps = query_snapd_apps(section=snapd_sec, limit=16)
                if extra_apps:
                    GLib.idle_add(self._append_category_apps, cat_id, extra_apps)
            threading.Thread(target=_fetch, daemon=True).start()

    def _append_category_apps(self, cat_id: str, extra_apps: List[Dict[str, Any]]):
        if not hasattr(self, "category_subpage_grid"):
            return
        existing_ids = {a.get("id") for a in self.current_category_apps}
        idx = len(self.current_category_apps)
        for app in extra_apps:
            if app["id"] in existing_ids:
                continue
            existing_ids.add(app["id"])
            self.current_category_apps.append(app)
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
            card.show_all()
            self.category_subpage_grid.attach(card, idx % 2, idx // 2, 1, 1)
            idx += 1

    def _show_filtered_category_view(self, cat_id: str, cat_name: str, apps: List[Dict[str, Any]]):
        for child in self.category_subpage_box.get_children():
            self.category_subpage_box.remove(child)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_back_cat = Gtk.Button(label="‹ Danh mục")
        btn_back_cat.get_style_context().add_class("mac-see-all-btn")
        btn_back_cat.connect("clicked", lambda _: self.select_tab("categories"))
        header_box.pack_start(btn_back_cat, False, False, 0)

        title_lbl = Gtk.Label(label=f"  |  {cat_name}")
        title_lbl.get_style_context().add_class("mac-section-title")
        title_lbl.set_xalign(0.0)
        header_box.pack_start(title_lbl, False, False, 0)
        self.category_subpage_box.pack_start(header_box, False, False, 8)

        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        self.category_subpage_grid = grid
        self.current_category_apps = list(apps)

        for i, app in enumerate(apps):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
            grid.attach(card, i % 2, i // 2, 1, 1)

        self.category_subpage_box.pack_start(grid, False, False, 0)
        self.category_subpage_box.show_all()
        self.top_header.show()
        self.header_title.set_text(cat_name)
        self.btn_back.set_sensitive(True)
        self._history_stack.append("categories")
        self.stack.set_visible_child_name("category_subpage")

    def _build_search_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.search_results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.search_results_box.set_margin_start(32)
        self.search_results_box.set_margin_end(32)
        self.search_results_box.set_margin_top(16)
        self.search_results_box.set_margin_bottom(36)
        scrolled.add(self.search_results_box)
        self.stack.add_named(scrolled, "search_results")

    # -----------------------------------------------------------------
    # OTHER STORE PAGES (DISCOVER, DEVELOP, CREATE, WORK, PLAY, UPDATES)
    # -----------------------------------------------------------------
    def _create_app_grid_section(self, title: str, subtitle: Optional[str], app_list: List[Dict[str, Any]]) -> Gtk.Box:
        sec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sec_box.set_margin_top(8)

        lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sec_title = Gtk.Label(label=title)
        sec_title.get_style_context().add_class("mac-section-title")
        sec_title.set_xalign(0.0)
        lbl_box.pack_start(sec_title, False, False, 0)

        if subtitle:
            sec_sub = Gtk.Label(label=subtitle)
            sec_sub.get_style_context().add_class("mac-app-subtitle")
            sec_sub.set_xalign(0.0)
            lbl_box.pack_start(sec_sub, False, False, 0)

        sec_box.pack_start(lbl_box, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        for i, app in enumerate(app_list):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
            grid.attach(card, i % 2, i // 2, 1, 1)

        sec_box.pack_start(grid, False, False, 0)
        return sec_box

    def _build_discover_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_start(28)
        box.set_margin_end(28)
        box.set_margin_bottom(48)
        scrolled.add(box)

        # 1. Hero Banner
        hero_apps = [a for a in APP_CATALOG if a.get("hero")]
        if hero_apps:
            hero_card = self._create_hero_card(hero_apps[0])
            box.pack_start(hero_card, False, False, 4)

        # Helper mapping by ID
        app_map = {a["id"]: a for a in APP_CATALOG}

        # 2. Essential Mac Apps (8 apps)
        essential_ids = ["code", "google-chrome", "telegram-desktop", "spotify", "discord", "vlc", "obsidian", "postman"]
        essential_apps = [app_map[aid] for aid in essential_ids if aid in app_map]
        if essential_apps:
            box.pack_start(self._create_app_grid_section("Ứng dụng Mac thiết yếu", "Các ứng dụng cần thiết cho quy trình làm việc hàng ngày của bạn", essential_apps), False, False, 0)

        # 3. Trending & Popular (8 apps)
        trending_ids = ["blender", "gimp", "steam", "inkscape", "kdenlive", "audacity", "brave", "beekeeper-studio"]
        trending_apps = [app_map[aid] for aid in trending_ids if aid in app_map]
        if trending_apps:
            box.pack_start(self._create_app_grid_section("Thịnh hành & Phổ biến", "Các ứng dụng tuyệt vời được người dùng toàn cầu yêu thích", trending_apps), False, False, 0)

        # 4. Creative Studio & Design (6 apps)
        creative_ids = ["blender", "krita", "inkscape", "darktable", "shotcut", "freecad"]
        creative_apps = [app_map[aid] for aid in creative_ids if aid in app_map]
        if creative_apps:
            box.pack_start(self._create_app_grid_section("Xưởng sáng tạo & Thiết kế", "Công cụ chuyên nghiệp cho nghệ thuật số, mô hình 3D và dựng video", creative_apps), False, False, 0)

        # 5. Developer Power Tools (6 apps)
        dev_ids = ["cursor", "pycharm-community", "docker", "android-studio", "sublime-text", "dbeaver-ce"]
        dev_apps = [app_map[aid] for aid in dev_ids if aid in app_map]
        if dev_apps:
            box.pack_start(self._create_app_grid_section("Công cụ phát triển", "Viết mã nhanh hơn, gỡ lỗi thông minh hơn với các IDE hàng đầu", dev_apps), False, False, 0)

        # 6. Productivity & Collaboration (6 apps)
        prod_ids = ["libreoffice", "notion-snap-reborn", "slack", "zoom-client", "bitwarden", "keepassxc"]
        prod_apps = [app_map[aid] for aid in prod_ids if aid in app_map]
        if prod_apps:
            box.pack_start(self._create_app_grid_section("Năng suất & Cộng tác", "Tổ chức công việc khoa học, tập trung và cộng tác cùng đội ngũ", prod_apps), False, False, 0)

        # 7. Games & Entertainment (6 apps)
        game_ids = ["steam", "0ad", "supertuxkart", "retroarch", "clementine", "vlc"]
        game_apps = [app_map[aid] for aid in game_ids if aid in app_map]
        if game_apps:
            box.pack_start(self._create_app_grid_section("Trò chơi & Giải trí", "Thư giãn cùng các tựa game tốc độ cao, chiến thuật hoặc tận hưởng âm nhạc", game_apps), False, False, 0)

        self.stack.add_named(scrolled, "discover")

    def _create_hero_card(self, app: Dict[str, Any]) -> Gtk.Widget:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        card.get_style_context().add_class("mac-hero-banner")
        card.set_size_request(-1, 210)

        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_valign(Gtk.Align.CENTER)

        raw_tag = app.get("hero_tag", "LỰA CHỌN CỦA BIÊN TẬP VIÊN")
        if raw_tag == "EDITORS' CHOICE":
            raw_tag = "LỰA CHỌN CỦA BIÊN TẬP VIÊN"
        lbl_tag = Gtk.Label(label=raw_tag)
        lbl_tag.get_style_context().add_class("mac-hero-tag")
        lbl_tag.set_xalign(0.0)
        left_col.pack_start(lbl_tag, False, False, 0)

        lbl_title = Gtk.Label(label=app.get("hero_title", app["name"]))
        lbl_title.get_style_context().add_class("mac-hero-title")
        lbl_title.set_xalign(0.0)
        left_col.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label=app.get("hero_sub", app["subtitle"]))
        lbl_sub.get_style_context().add_class("mac-hero-sub")
        lbl_sub.set_xalign(0.0)
        lbl_sub.set_line_wrap(True)
        left_col.pack_start(lbl_sub, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        btn_row.set_margin_top(10)

        btn_action = Gtk.Button()
        installed = is_app_installed(app)
        btn_action.set_label(t("appstore_open", "Open") if installed else t("appstore_get", "Get"))
        btn_action.get_style_context().add_class("mac-hero-pill-btn")
        btn_action.connect("clicked", lambda _: self.handle_install_or_launch(app, None))
        self.hero_btn_action = btn_action
        self.hero_app = app
        btn_row.pack_start(btn_action, False, False, 0)

        btn_more = Gtk.Button(label="Xem chi tiết →")
        btn_more.get_style_context().add_class("mac-hero-link-btn")
        btn_more.connect("clicked", lambda _: self.show_app_detail(app))
        btn_row.pack_start(btn_more, False, False, 0)

        left_col.pack_start(btn_row, False, False, 0)
        card.pack_start(left_col, True, True, 0)

        hero_art = os.path.join(BASE_DIR, "assets", "hero_vscode.png")
        if os.path.exists(hero_art):
            art_img = Gtk.Image.new_from_file(hero_art)
            art_img.set_valign(Gtk.Align.CENTER)
            card.pack_end(art_img, False, False, 0)

        return card

    def _build_category_pages(self):
        categories = [
            ("arcade", "Trò chơi Arcade", ["steam", "0ad", "supertuxkart", "retroarch"]),
            ("create", "Sáng tạo", ["blender", "gimp", "inkscape", "krita", "kdenlive", "audacity", "shotcut", "freecad", "darktable"]),
            ("work", "Làm việc", ["libreoffice", "obsidian", "notion-snap-reborn", "slack", "zoom-client", "trello", "joplin-desktop", "thunderbird", "postman"]),
            ("develop", "Phát triển", ["code", "cursor", "pycharm-community", "docker", "postman", "dbeaver-ce", "android-studio", "sublime-text", "beekeeper-studio"]),
            ("play", "Giải trí", ["spotify", "vlc", "discord", "steam", "clementine", "audacity"]),
        ]
        for cat_key, cat_title, app_ids in categories:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            box.set_margin_start(28)
            box.set_margin_end(28)
            box.set_margin_bottom(36)
            scrolled.add(box)

            header_lbl = Gtk.Label(label=f"Ứng dụng {cat_title}")
            header_lbl.get_style_context().add_class("mac-section-title")
            header_lbl.set_xalign(0.0)
            box.pack_start(header_lbl, False, False, 4)

            grid = Gtk.Grid()
            grid.set_column_spacing(20)
            grid.set_row_spacing(10)
            grid.set_column_homogeneous(True)

            all_pool = EDITORS_CHOICE_APPS + APP_CATALOG
            cat_apps = [a for a in all_pool if a["id"] in app_ids or a.get("category") == cat_key]
            for i, app in enumerate(cat_apps):
                card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
                grid.attach(card, i % 2, i // 2, 1, 1)

            box.pack_start(grid, False, False, 0)
            self.stack.add_named(scrolled, cat_key)

    def _build_updates_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.updates_main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.updates_main_box.set_margin_start(28)
        self.updates_main_box.set_margin_end(28)
        self.updates_main_box.set_margin_top(10)
        self.updates_main_box.set_margin_bottom(36)
        scrolled.add(self.updates_main_box)

        # Summary Card
        self.updates_summary_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.updates_summary_card.get_style_context().add_class("mac-updates-summary-card")

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_valign(Gtk.Align.CENTER)
        self.lbl_updates_title = Gtk.Label(label="Cập nhật phần mềm")
        self.lbl_updates_title.get_style_context().add_class("mac-section-title")
        self.lbl_updates_title.set_xalign(0.0)
        self.lbl_updates_sub = Gtk.Label(label="Đang kiểm tra các bản cập nhật hệ thống và ứng dụng...")
        self.lbl_updates_sub.get_style_context().add_class("mac-app-subtitle")
        self.lbl_updates_sub.set_xalign(0.0)
        info_box.pack_start(self.lbl_updates_title, False, False, 0)
        info_box.pack_start(self.lbl_updates_sub, False, False, 0)

        # Summary Progress Bar for "Update All"
        self.updates_summary_progress = Gtk.ProgressBar()
        self.updates_summary_progress.get_style_context().add_class("mac-store-progress")
        self.updates_summary_progress.set_size_request(-1, 5)
        self.updates_summary_progress.set_no_show_all(True)
        info_box.pack_start(self.updates_summary_progress, False, False, 2)

        self.updates_summary_card.pack_start(info_box, True, True, 0)

        self.btn_update_all = Gtk.Button(label="Cập nhật tất cả")
        self.btn_update_all.get_style_context().add_class("mac-btn-update-all")
        self.btn_update_all.set_valign(Gtk.Align.CENTER)
        self.btn_update_all.connect("clicked", lambda _: self._run_system_update())
        self.updates_summary_card.pack_end(self.btn_update_all, False, False, 8)

        self.updates_main_box.pack_start(self.updates_summary_card, False, False, 0)

        # Dynamic Container for Updates List
        self.updates_list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.updates_main_box.pack_start(self.updates_list_container, True, True, 0)

        self.stack.add_named(scrolled, "updates")

        # Initial background scan
        GLib.timeout_add(1000, self._refresh_updates_list)

    # -----------------------------------------------------------------
    # APP DETAIL PAGE
    # -----------------------------------------------------------------
    def _build_detail_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.detail_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.detail_content.set_margin_start(32)
        self.detail_content.set_margin_end(32)
        self.detail_content.set_margin_top(16)
        self.detail_content.set_margin_bottom(36)
        scrolled.add(self.detail_content)

        self.stack.add_named(scrolled, "detail")

    def show_app_detail(self, app: Dict[str, Any]):
        for child in self.detail_content.get_children():
            self.detail_content.remove(child)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        icon_img = Gtk.Image()
        pb = get_app_icon_pixbuf(app["id"], 96, app.get("name"))
        if pb:
            icon_img.set_from_pixbuf(pb)
        else:
            icon_img.set_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
        top_row.pack_start(icon_img, False, False, 0)

        meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        meta_box.set_valign(Gtk.Align.CENTER)

        lbl_name = Gtk.Label(label=app["name"])
        lbl_name.get_style_context().add_class("mac-detail-title")
        lbl_name.set_xalign(0.0)
        meta_box.pack_start(lbl_name, False, False, 0)

        lbl_dev = Gtk.Label(label=app.get("developer", "Apple Inc."))
        lbl_dev.get_style_context().add_class("mac-detail-dev")
        lbl_dev.set_xalign(0.0)
        meta_box.pack_start(lbl_dev, False, False, 0)

        lbl_sub = Gtk.Label(label=app.get("subtitle", ""))
        lbl_sub.get_style_context().add_class("mac-app-subtitle")
        lbl_sub.set_xalign(0.0)
        meta_box.pack_start(lbl_sub, False, False, 0)

        self.detail_app = app
        top_row.pack_start(meta_box, True, True, 0)

        # Right Action Column in Detail View
        detail_act_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        detail_act_box.set_valign(Gtk.Align.CENTER)
        detail_act_box.set_halign(Gtk.Align.END)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        detail_act_box.pack_start(btn_box, False, False, 0)

        btn_act = Gtk.Button()
        installed = is_app_installed(app)
        btn_act.set_label(t("appstore_open", "Open") if installed else t("appstore_get", "Get"))
        btn_act.get_style_context().add_class("mac-pill-btn")
        btn_act.get_style_context().add_class("pill-open" if installed else "pill-get")
        btn_act.set_valign(Gtk.Align.CENTER)
        btn_act.connect("clicked", lambda _: self.handle_install_or_launch(app, None))
        btn_box.pack_start(btn_act, False, False, 0)
        self.detail_btn_act = btn_act

        if installed:
            btn_uninstall = Gtk.Button(label="Gỡ cài đặt")
            btn_uninstall.get_style_context().add_class("mac-pill-btn")
            btn_uninstall.get_style_context().add_class("pill-uninstall")
            btn_uninstall.set_valign(Gtk.Align.CENTER)
            btn_uninstall.set_tooltip_text(f"Gỡ cài đặt {app.get('name')}")
            btn_uninstall.connect("clicked", lambda _: self.handle_uninstall(app))
            btn_box.pack_start(btn_uninstall, False, False, 0)
            self.detail_btn_uninstall = btn_uninstall
        else:
            self.detail_btn_uninstall = None

        self.detail_progress_bar = Gtk.ProgressBar()
        self.detail_progress_bar.get_style_context().add_class("mac-store-progress")
        self.detail_progress_bar.set_size_request(90, 4)
        self.detail_progress_bar.set_no_show_all(True)
        detail_act_box.pack_start(self.detail_progress_bar, False, False, 1)

        self.detail_lbl_status = Gtk.Label(label="")
        self.detail_lbl_status.get_style_context().add_class("mac-update-status")
        self.detail_lbl_status.set_no_show_all(True)
        detail_act_box.pack_start(self.detail_lbl_status, False, False, 0)

        if app.get("id") in self._installing_apps:
            btn_act.set_label(t("appstore_installing", "Installing…"))
            btn_act.set_sensitive(False)
            btn_act.get_style_context().remove_class("pill-get")
            btn_act.get_style_context().add_class("pill-installing")
            self.detail_progress_bar.show()
            self.detail_lbl_status.set_text("Đang tải & cài đặt...")
            self.detail_lbl_status.show()
            def _pulse_detail():
                if hasattr(self, 'detail_progress_bar') and self.detail_progress_bar.get_visible():
                    self.detail_progress_bar.pulse()
                    return True
                return False
            self._detail_pulse_id = GLib.timeout_add(80, _pulse_detail)

        top_row.pack_end(detail_act_box, False, False, 8)
        self.detail_content.pack_start(top_row, False, False, 0)

        # Metric Strip
        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        strip.get_style_context().add_class("mac-specs-strip")
        strip.set_homogeneous(True)

        def add_metric(val, tag):
            b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            v = Gtk.Label(label=str(val))
            v.get_style_context().add_class("mac-metric-val")
            t = Gtk.Label(label=tag)
            t.get_style_context().add_class("mac-metric-tag")
            b.pack_start(v, False, False, 0)
            b.pack_start(t, False, False, 0)
            strip.pack_start(b, True, True, 0)

        add_metric(f"{app.get('rating', 4.8)} ★", f"{app.get('reviews', '10K')} ĐÁNH GIÁ")
        add_metric("4+", "ĐỘ TUỔI")
        add_metric(app.get("category_name", "App"), "BẢNG XẾP HẠNG")
        add_metric(app.get("developer", "Team").split()[0], "NHÀ PHÁT TRIỂN")
        add_metric(app.get("size", "80 MB"), "DUNG LƯỢNG")

        self.detail_content.pack_start(strip, False, False, 4)

        # Description
        lbl_desc_title = Gtk.Label(label="Mô tả")
        lbl_desc_title.get_style_context().add_class("mac-section-title")
        lbl_desc_title.set_xalign(0.0)
        self.detail_content.pack_start(lbl_desc_title, False, False, 0)

        lbl_desc = Gtk.Label(label=app.get("desc", app.get("subtitle", "")))
        lbl_desc.get_style_context().add_class("mac-detail-body")
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_xalign(0.0)
        self.detail_content.pack_start(lbl_desc, False, False, 0)

        # Features
        features = app.get("features", [])
        if features:
            lbl_feat_title = Gtk.Label(label="Tính năng nổi bật")
            lbl_feat_title.get_style_context().add_class("mac-section-title")
            lbl_feat_title.set_xalign(0.0)
            lbl_feat_title.set_margin_top(8)
            self.detail_content.pack_start(lbl_feat_title, False, False, 0)

            for feat in features:
                f_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                f_dot = Gtk.Label(label="•")
                f_dot.get_style_context().add_class("mac-blue-dot")
                f_lbl = Gtk.Label(label=feat)
                f_lbl.get_style_context().add_class("mac-detail-body")
                f_lbl.set_xalign(0.0)
                f_row.pack_start(f_dot, False, False, 0)
                f_row.pack_start(f_lbl, True, True, 0)
                self.detail_content.pack_start(f_row, False, False, 0)

        self.detail_content.show_all()
        self._history_stack.append(self.current_tab)
        self.stack.set_visible_child_name("detail")
        self.top_header.show()
        self.header_title.set_text(app["name"])
        self.btn_back.set_sensitive(True)

    # -----------------------------------------------------------------
    # NAVIGATION & TABS
    # -----------------------------------------------------------------
    def select_tab(self, tab_key: str):
        self.current_tab = tab_key
        for k, (btn, icon_img, icon_name, lbl) in self._nav_buttons.items():
            if k == tab_key:
                btn.get_style_context().add_class("active")
                # Active: Apple Blue icon
                new_img = get_image(icon_name, 16, "#007aff")
                if new_img and new_img.get_pixbuf():
                    icon_img.set_from_pixbuf(new_img.get_pixbuf())
            else:
                btn.get_style_context().remove_class("active")
                # Inactive: Neutral icon
                icon_col = "#8e8e93" if self.is_dark else "#48484a"
                new_img = get_image(icon_name, 16, icon_col)
                if new_img and new_img.get_pixbuf():
                    icon_img.set_from_pixbuf(new_img.get_pixbuf())

        # On "categories" overview page, hide top header to match exact macOS reference!
        if tab_key == "categories":
            self.top_header.hide()
        else:
            self.top_header.show()

        titles = {
            "categories": t("appstore_categories", "Categories"),
            "discover": t("appstore_discover", "Discover"),
            "arcade": t("appstore_arcade", "Arcade"),
            "create": t("appstore_create", "Create"),
            "work": t("appstore_work", "Work"),
            "develop": t("appstore_develop", "Develop"),
            "play": t("appstore_play", "Play"),
            "updates": t("appstore_updates", "Updates")
        }
        self.header_title.set_text(titles.get(tab_key, ""))
        child = self.stack.get_child_by_name(tab_key)
        if child:
            child.show_all()
            self.stack.set_visible_child(child)
        else:
            self.stack.set_visible_child_name(tab_key)
        self.btn_back.set_sensitive(False)

        if tab_key == "updates" and hasattr(self, "_refresh_updates_list"):
            self._refresh_updates_list()

    def _navigate_back(self):
        if self._history_stack:
            prev = self._history_stack.pop()
            self.select_tab(prev)
        else:
            self.select_tab("categories")

    def _on_search_enter(self, entry):
        query = entry.get_text().strip().lower()
        if not query:
            return
        if hasattr(self, '_search_timer') and self._search_timer:
            GLib.source_remove(self._search_timer)
            self._search_timer = None
        self._trigger_online_search(query)

    def _on_search_text_changed(self, entry):
        query = entry.get_text().strip().lower()
        if not query:
            if hasattr(self, '_search_timer') and self._search_timer:
                GLib.source_remove(self._search_timer)
                self._search_timer = None
            if hasattr(self, '_prev_tab_before_search'):
                self.select_tab(self._prev_tab_before_search)
            else:
                self.select_tab("categories")
            return

        if self.current_tab != "search_results":
            self._prev_tab_before_search = self.current_tab

        if hasattr(self, '_search_timer') and self._search_timer:
            GLib.source_remove(self._search_timer)
            self._search_timer = None

        self._current_search_query = query
        self._render_local_search_results(query)

        # Debounce online Snap Store search (350ms)
        self._search_timer = GLib.timeout_add(350, self._trigger_online_search, query)

    def _render_local_search_results(self, query: str):
        for child in self.search_results_box.get_children():
            self.search_results_box.remove(child)

        all_pool = EDITORS_CHOICE_APPS + APP_CATALOG + load_system_desktop_apps()
        seen = set()
        matches = []
        for a in all_pool:
            aid = a["id"].lower()
            aname = a["name"].lower()
            if aid in seen or aname in seen:
                continue
            if query in aname or query in a.get("subtitle", "").lower() or query in a.get("category_name", "").lower():
                seen.add(aid)
                seen.add(aname)
                matches.append(a)

        self._current_search_matches = matches
        self._search_seen_ids = seen

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label=f"Kết quả cho \"{self.search_entry.get_text().strip()}\"")
        title.get_style_context().add_class("mac-section-title")
        title.set_xalign(0.0)
        header_box.pack_start(title, False, False, 0)

        self.search_spinner = Gtk.Spinner()
        self.search_spinner.start()
        header_box.pack_start(self.search_spinner, False, False, 0)

        self.search_status_lbl = Gtk.Label(label="Đang tìm kiếm kho ứng dụng...")
        self.search_status_lbl.get_style_context().add_class("mac-header-status-lbl")
        header_box.pack_start(self.search_status_lbl, False, False, 0)

        self.search_results_box.pack_start(header_box, False, False, 4)

        if not matches:
            self.search_empty_lbl = Gtk.Label(label="Đang tìm kiếm trực tuyến các ứng dụng phù hợp...")
            self.search_empty_lbl.get_style_context().add_class("mac-app-subtitle")
            self.search_empty_lbl.set_xalign(0.0)
            self.search_results_box.pack_start(self.search_empty_lbl, False, False, 8)
        else:
            self.search_empty_lbl = None

        self.search_grid = Gtk.Grid()
        self.search_grid.set_column_spacing(24)
        self.search_grid.set_row_spacing(10)
        self.search_grid.set_column_homogeneous(True)

        for i, app in enumerate(matches):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
            self.search_grid.attach(card, i % 2, i // 2, 1, 1)

        self.search_results_box.pack_start(self.search_grid, False, False, 0)
        self.search_results_box.show_all()
        self.top_header.show()
        self.header_title.set_text("Tìm kiếm")
        self.stack.set_visible_child_name("search_results")

    def _trigger_online_search(self, query: str):
        self._search_timer = None
        if not query or query != getattr(self, '_current_search_query', ''):
            return False

        def _worker():
            snap_results = query_snap_store(query, max_results=20)
            GLib.idle_add(self._on_online_search_finished, query, snap_results)

        threading.Thread(target=_worker, daemon=True).start()
        return False

    def _on_online_search_finished(self, query: str, snap_results: List[Dict[str, Any]]):
        if query != getattr(self, '_current_search_query', ''):
            return

        if hasattr(self, 'search_spinner'):
            self.search_spinner.stop()
            self.search_spinner.hide()

        seen = getattr(self, '_search_seen_ids', set())
        matches = getattr(self, '_current_search_matches', [])
        start_idx = len(matches)

        for app in snap_results:
            aid = app["id"].lower()
            aname = app["name"].lower()
            if aid not in seen and aname not in seen:
                seen.add(aid)
                seen.add(aname)
                matches.append(app)
                card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch, window=self)
                self.search_grid.attach(card, start_idx % 2, start_idx // 2, 1, 1)
                start_idx += 1

        if getattr(self, 'search_empty_lbl', None) is not None:
            if matches:
                self.search_results_box.remove(self.search_empty_lbl)
                self.search_empty_lbl = None
            else:
                self.search_empty_lbl.set_text("Không tìm thấy ứng dụng phù hợp với tìm kiếm của bạn.")

        if hasattr(self, 'search_status_lbl'):
            if not matches:
                self.search_status_lbl.set_text("Không tìm thấy")
            else:
                self.search_status_lbl.set_text(f"(Tìm thấy {len(matches)} ứng dụng)")

        self.search_results_box.show_all()
        if hasattr(self, 'search_spinner'):
            self.search_spinner.hide()

    # -----------------------------------------------------------------
    # INSTALL / LAUNCH HANDLERS
    # -----------------------------------------------------------------
    def handle_install_or_launch(self, app: Dict[str, Any], card_widget: Optional[AppCardWidget] = None):
        if is_app_installed(app):
            success = launch_installed_app(app)
            if success:
                self.set_status(f"Đang mở {app['name']}...")
            else:
                self.set_status(f"Không thể khởi chạy {app['name']}")
            GLib.timeout_add(3000, lambda: self.set_status(""))
            return

        app_id = app.get("id")
        if app_id in self._installing_apps:
            self.set_status(f"{app['name']} đang được tải & cài đặt...")
            return

        self._installing_apps.add(app_id)
        if card_widget:
            card_widget.set_installing(True)
        for c in self._active_cards.get(app_id, []):
            c.set_installing(True)

        if hasattr(self, 'detail_app') and self.detail_app and self.detail_app.get("id") == app_id:
            if hasattr(self, 'detail_btn_act'):
                self.detail_btn_act.set_label(t("appstore_installing", "Installing…"))
                self.detail_btn_act.set_sensitive(False)
                self.detail_btn_act.get_style_context().remove_class("pill-get")
                self.detail_btn_act.get_style_context().add_class("pill-installing")
            if hasattr(self, 'detail_progress_bar'):
                self.detail_progress_bar.show()
            if hasattr(self, 'detail_lbl_status'):
                self.detail_lbl_status.set_text("Đang tải & cài đặt...")
                self.detail_lbl_status.show()
            def _pulse_detail():
                if hasattr(self, 'detail_progress_bar') and self.detail_progress_bar.get_visible():
                    self.detail_progress_bar.pulse()
                    return True
                return False
            self._detail_pulse_id = GLib.timeout_add(80, _pulse_detail)

        if hasattr(self, 'hero_app') and self.hero_app and self.hero_app.get("id") == app_id:
            if hasattr(self, 'hero_btn_action'):
                self.hero_btn_action.set_label(t("appstore_installing", "Installing…"))
                self.hero_btn_action.set_sensitive(False)

        self.spinner.start()
        self.set_status(f"Đang tải & cài đặt {app['name']}...")

        def _do_install():
            success = False
            err_msg = ""
            snap_name = app.get("snap")
            apt_name = app.get("apt")
            web_url = app.get("web_url")

            if snap_name:
                try:
                    cmd = ["snap", "install"]
                    if app.get("classic") or app.get("confinement") == "classic":
                        cmd.append("--classic")
                    cmd.append(snap_name)
                    res = _privileged_run(cmd)
                    if res.returncode == 0:
                        success = True
                    elif "--classic" in res.stderr and "--classic" not in cmd:
                        res2 = _privileged_run(["snap", "install", "--classic", snap_name])
                        if res2.returncode == 0:
                            success = True
                        else:
                            err_msg = res2.stderr
                    else:
                        err_msg = res.stderr
                except Exception as e:
                    err_msg = str(e)

            if not success and apt_name:
                try:
                    res = _privileged_run(["apt-get", "install", "-y", apt_name])
                    if res.returncode == 0:
                        success = True
                    else:
                        err_msg = res.stderr
                except Exception as e:
                    err_msg = str(e)

            if not success and web_url:
                try:
                    app_id = app.get("id")
                    name = app.get("name")
                    icon_path = os.path.join(APP_ICONS_DIR, f"{app_id}.png")
                    desktop_path = os.path.expanduser(f"~/.local/share/applications/{app_id}.desktop")
                    exec_str = f"google-chrome --app={web_url}" if shutil.which("google-chrome") else f"xdg-open {web_url}"
                    desktop_content = f"""[Desktop Entry]
Name={name}
Comment={app.get('subtitle', name)}
Exec={exec_str}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Network;WebBrowser;
StartupWMClass={app_id}
"""
                    with open(desktop_path, "w") as f:
                        f.write(desktop_content)
                    os.chmod(desktop_path, 0o755)
                    subprocess.run(["update-desktop-database", os.path.expanduser("~/.local/share/applications/")], capture_output=True)
                    success = True
                except Exception as e:
                    err_msg = str(e)

            GLib.idle_add(self._on_install_finished, app, card_widget, success, err_msg)

        threading.Thread(target=_do_install, daemon=True).start()

    def _on_install_finished(self, app: Dict[str, Any], card_widget: Optional[AppCardWidget], success: bool, err_msg: str = ""):
        self.spinner.stop()
        app_id = app.get("id")
        self._installing_apps.discard(app_id)

        installed = success or is_app_installed(app)
        if card_widget:
            card_widget.set_installing(False, installed)
        for c in self._active_cards.get(app_id, []):
            c.set_installing(False, installed)

        if hasattr(self, 'detail_app') and self.detail_app and self.detail_app.get("id") == app_id:
            if hasattr(self, '_detail_pulse_id') and self._detail_pulse_id:
                GLib.source_remove(self._detail_pulse_id)
                self._detail_pulse_id = None
            if hasattr(self, 'detail_btn_act'):
                self.detail_btn_act.set_sensitive(True)
                self.detail_btn_act.get_style_context().remove_class("pill-installing")
                if installed:
                    self.detail_btn_act.set_label(t("appstore_open", "Open"))
                    self.detail_btn_act.get_style_context().remove_class("pill-get")
                    self.detail_btn_act.get_style_context().add_class("pill-open")
                else:
                    self.detail_btn_act.set_label(t("appstore_get", "Get"))
                    self.detail_btn_act.get_style_context().remove_class("pill-open")
                    self.detail_btn_act.get_style_context().add_class("pill-get")

            if hasattr(self, 'detail_progress_bar'):
                if installed:
                    self.detail_progress_bar.set_fraction(1.0)
                    GLib.timeout_add(1500, lambda: self.detail_progress_bar.hide() if hasattr(self, 'detail_progress_bar') else None)
                else:
                    self.detail_progress_bar.hide()

            if hasattr(self, 'detail_lbl_status'):
                if installed:
                    self.detail_lbl_status.set_text("✓ Đã cài đặt thành công!")
                    self.detail_lbl_status.get_style_context().remove_class("mac-update-status-err")
                    self.detail_lbl_status.get_style_context().add_class("mac-update-status-ok")
                    self.detail_lbl_status.show()
                    GLib.timeout_add(2500, lambda: self.detail_lbl_status.hide() if hasattr(self, 'detail_lbl_status') else None)
                else:
                    msg = "⚠ Cài đặt thất bại"
                    if "cancel" in err_msg.lower() or "auth" in err_msg.lower():
                        msg = "⚠ Đã hủy xác thực mật khẩu"
                    self.detail_lbl_status.set_text(msg)
                    self.detail_lbl_status.get_style_context().remove_class("mac-update-status-ok")
                    self.detail_lbl_status.get_style_context().add_class("mac-update-status-err")
                    self.detail_lbl_status.show()
                    GLib.timeout_add(3500, lambda: self.detail_lbl_status.hide() if hasattr(self, 'detail_lbl_status') else None)

            if installed and (not hasattr(self, 'detail_btn_uninstall') or self.detail_btn_uninstall is None):
                self.show_app_detail(app)

        if hasattr(self, 'hero_app') and self.hero_app and self.hero_app.get("id") == app_id:
            if hasattr(self, 'hero_btn_action'):
                self.hero_btn_action.set_sensitive(True)
                self.hero_btn_action.set_label(t("appstore_open", "Open") if installed else t("appstore_get", "Get"))

        if installed:
            self.set_status(f"Đã cài đặt {app['name']} thành công!")
        else:
            self.set_status(f"Không thể cài đặt {app['name']}")
        GLib.timeout_add(4000, lambda: self.set_status(""))

    def handle_uninstall(self, app: Dict[str, Any]):
        snap_name = app.get("snap")
        apt_name = app.get("apt")
        name = app.get("name", "ứng dụng")

        self.spinner.start()
        self.set_status(f"Đang gỡ cài đặt {name}...")

        def _do_uninstall():
            success = False
            if snap_name:
                try:
                    res = _privileged_run(["snap", "remove", snap_name])
                    if res.returncode == 0:
                        success = True
                except Exception:
                    pass

            if not success and apt_name:
                try:
                    res = _privileged_run(["apt-get", "remove", "-y", apt_name])
                    if res.returncode == 0:
                        success = True
                except Exception:
                    pass

            desktop_path = os.path.expanduser(f"~/.local/share/applications/{app.get('id')}.desktop")
            if os.path.exists(desktop_path):
                try:
                    os.remove(desktop_path)
                    subprocess.run(["update-desktop-database", os.path.expanduser("~/.local/share/applications/")], capture_output=True)
                    success = True
                except Exception:
                    pass

            GLib.idle_add(self._on_uninstall_finished, app, success)

        threading.Thread(target=_do_uninstall, daemon=True).start()

    def _on_uninstall_finished(self, app: Dict[str, Any], success: bool):
        self.spinner.stop()
        if success or not is_app_installed(app):
            self.set_status(f"Đã gỡ cài đặt {app.get('name')} thành công.")
            self.show_app_detail(app)
        else:
            self.set_status(f"Không thể gỡ cài đặt {app.get('name')}.")
        GLib.timeout_add(4000, lambda: self.set_status(""))

    def _refresh_updates_list(self):
        if hasattr(self, 'spinner'):
            self.spinner.start()
        self.set_status("Đang quét các bản cập nhật hệ thống...")

        def _worker():
            updates = []
            # 1. Snap updates
            try:
                proc = subprocess.run(["snap", "refresh", "--list"], capture_output=True, text=True, timeout=6)
                if proc.returncode == 0:
                    lines = proc.stdout.strip().splitlines()
                    if len(lines) > 1:
                        for line in lines[1:]:
                            parts = line.split()
                            if len(parts) >= 3:
                                s_name = parts[0]
                                s_ver = parts[1]
                                updates.append({
                                    "id": s_name,
                                    "name": s_name.replace("-", " ").title(),
                                    "version": s_ver,
                                    "type": "snap",
                                    "desc": f"Bản cập nhật chính thức gói Snap Store ({parts[2]})"
                                })
            except Exception:
                pass

            # 2. APT updates
            try:
                proc = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True, timeout=6)
                if proc.returncode == 0:
                    lines = proc.stdout.strip().splitlines()
                    apt_gui = []
                    apt_sys = []
                    nice_names = {
                        "google-chrome-stable": ("Google Chrome", "Trình duyệt web nhanh và bảo mật của Google"),
                        "google-chrome": ("Google Chrome", "Trình duyệt web nhanh và bảo mật của Google"),
                        "firefox": ("Mozilla Firefox", "Trình duyệt web mã nguồn mở tự do"),
                        "code": ("Visual Studio Code", "Trình biên tập mã nguồn của Microsoft"),
                        "discord": ("Discord", "Dịch vụ trò chuyện âm thanh, video và văn bản"),
                        "slack-desktop": ("Slack", "Nền tảng năng suất và nhắn tin cộng tác"),
                        "spotify-client": ("Spotify", "Dịch vụ phát nhạc kỹ thuật số"),
                    }
                    for line in lines:
                        if "/" in line and "[" in line:
                            parts = line.split()
                            pkg_name = parts[0].split("/")[0]
                            new_ver = parts[1]
                            if pkg_name in nice_names:
                                d_name, d_desc = nice_names[pkg_name]
                                apt_gui.append({
                                    "id": pkg_name,
                                    "name": d_name,
                                    "version": new_ver,
                                    "type": "apt",
                                    "desc": d_desc
                                })
                            else:
                                apt_sys.append((pkg_name, new_ver))

                    updates.extend(apt_gui)
                    if apt_sys:
                        first_three = ", ".join(p[0] for p in apt_sys[:3])
                        updates.append({
                            "id": "ubuntu-system",
                            "name": "Bản vá Bảo mật & Hệ thống Ubuntu",
                            "version": f"{len(apt_sys)} gói",
                            "type": "apt-system",
                            "desc": f"Bản cập nhật độ ổn định cốt lõi, bảo mật và tương thích phần cứng ({first_three}...)"
                        })
            except Exception:
                pass

            GLib.idle_add(self._on_updates_scan_finished, updates)

        threading.Thread(target=_worker, daemon=True).start()
        return False

    def _on_updates_scan_finished(self, updates: List[Dict[str, Any]]):
        if hasattr(self, 'spinner'):
            self.spinner.stop()
        self.set_status("")
        self._render_updates_ui(updates)

    def _render_updates_ui(self, updates: List[Dict[str, Any]]):
        if not hasattr(self, 'updates_list_container'):
            return
        for child in self.updates_list_container.get_children():
            self.updates_list_container.remove(child)

        self.update_rows = {}

        if updates:
            self.lbl_updates_sub.set_text(f"Có {len(updates)} bản cập nhật ứng dụng và hệ thống khả dụng.")
            self.btn_update_all.set_sensitive(True)

            lbl_list = Gtk.Label(label="Bản cập nhật đang chờ")
            lbl_list.get_style_context().add_class("mac-section-title")
            lbl_list.set_xalign(0.0)
            self.updates_list_container.pack_start(lbl_list, False, False, 4)

            for u in updates:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
                row.get_style_context().add_class("mac-app-card")

                icon_img = Gtk.Image()
                pb = get_app_icon_pixbuf(u["id"], 48, u["name"])
                if pb:
                    icon_img.set_from_pixbuf(pb)
                else:
                    icon_img.set_from_icon_name("software-update-available", Gtk.IconSize.DIALOG)
                row.pack_start(icon_img, False, False, 0)

                t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                t_box.set_valign(Gtk.Align.CENTER)
                lbl_name = Gtk.Label(label=f"{u['name']}  •  v{u.get('version', '')}")
                lbl_name.get_style_context().add_class("mac-app-title")
                lbl_name.set_xalign(0.0)
                lbl_notes = Gtk.Label(label=u.get("desc", "Cải thiện bảo mật và hiệu năng."))
                lbl_notes.get_style_context().add_class("mac-app-subtitle")
                lbl_notes.set_xalign(0.0)
                lbl_notes.set_ellipsize(Pango.EllipsizeMode.END)

                pbar = Gtk.ProgressBar()
                pbar.get_style_context().add_class("mac-store-progress")
                pbar.set_size_request(240, 4)
                pbar.set_no_show_all(True)

                lbl_status = Gtk.Label(label="")
                lbl_status.get_style_context().add_class("mac-update-status")
                lbl_status.set_xalign(0.0)
                lbl_status.set_no_show_all(True)

                t_box.pack_start(lbl_name, False, False, 0)
                t_box.pack_start(lbl_notes, False, False, 0)
                t_box.pack_start(pbar, False, False, 2)
                t_box.pack_start(lbl_status, False, False, 0)
                row.pack_start(t_box, True, True, 0)

                btn_up = Gtk.Button(label="CẬP NHẬT")
                btn_up.get_style_context().add_class("mac-pill-btn")
                btn_up.get_style_context().add_class("pill-open")
                btn_up.set_valign(Gtk.Align.CENTER)
                btn_up.connect("clicked", lambda _, pkg=u: self._update_single_package(pkg))
                row.pack_end(btn_up, False, False, 8)

                self.update_rows[u["id"]] = {
                    "btn": btn_up,
                    "pbar": pbar,
                    "lbl_status": lbl_status,
                    "pulse_id": None
                }

                self.updates_list_container.pack_start(row, False, False, 0)
        else:
            self.lbl_updates_sub.set_text("Tất cả ứng dụng và gói hệ thống đều đã được cập nhật.")
            self.btn_update_all.set_sensitive(False)

            empty_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            empty_card.set_valign(Gtk.Align.CENTER)
            empty_card.set_margin_top(40)
            empty_card.set_margin_bottom(40)

            shield_img = get_image("tray_down", 48, "#34c759")
            empty_card.pack_start(shield_img, False, False, 0)

            title_lbl = Gtk.Label(label="Hệ thống của bạn đã được cập nhật")
            title_lbl.get_style_context().add_class("mac-section-title")
            empty_card.pack_start(title_lbl, False, False, 0)

            sub_lbl = Gtk.Label(label="Hiện không có bản cập nhật nào. Tất cả gói đã cài đặt đều đang ở phiên bản mới nhất.")
            sub_lbl.get_style_context().add_class("mac-app-subtitle")
            empty_card.pack_start(sub_lbl, False, False, 0)

            btn_check = Gtk.Button(label="Kiểm tra lại")
            btn_check.get_style_context().add_class("mac-pill-btn")
            btn_check.get_style_context().add_class("pill-open")
            btn_check.set_halign(Gtk.Align.CENTER)
            btn_check.connect("clicked", lambda _: self._refresh_updates_list())
            empty_card.pack_start(btn_check, False, False, 8)

            self.updates_list_container.pack_start(empty_card, True, True, 0)

        self.updates_list_container.show_all()

    def _update_single_package(self, pkg: Dict[str, Any]):
        pkg_id = pkg["id"]
        row_data = self.update_rows.get(pkg_id)
        if row_data:
            row_data["btn"].set_label("UPDATING...")
            row_data["btn"].set_sensitive(False)
            row_data["btn"].get_style_context().remove_class("pill-open")
            row_data["btn"].get_style_context().add_class("pill-updating")
            row_data["lbl_status"].set_text("Đang cập nhật... (Nhập mật khẩu nếu có hộp thoại)")
            row_data["lbl_status"].get_style_context().remove_class("mac-update-status-err")
            row_data["lbl_status"].get_style_context().remove_class("mac-update-status-ok")
            row_data["lbl_status"].show()
            row_data["pbar"].show()

            def _pulse():
                if row_data.get("pulse_id") and row_data["pbar"].get_visible():
                    row_data["pbar"].pulse()
                    return True
                return False
            row_data["pulse_id"] = GLib.timeout_add(80, _pulse)

        self.spinner.start()
        self.set_status(f"Updating {pkg['name']}...")

        def _worker():
            success = False
            err_msg = ""
            pkg_id = pkg["id"]
            pkg_type = pkg.get("type", "apt")

            try:
                if pkg_type == "snap":
                    res = _privileged_run(["snap", "refresh", pkg_id])
                    success = (res.returncode == 0)
                    if not success:
                        err_msg = res.stderr or res.stdout
                elif pkg_type == "apt":
                    res = _privileged_run(["apt-get", "install", "--only-upgrade", "-y", pkg_id])
                    success = (res.returncode == 0)
                    if not success:
                        err_msg = res.stderr or res.stdout
                else:
                    res = _privileged_run(["apt-get", "upgrade", "-y"])
                    success = (res.returncode == 0)
                    if not success:
                        err_msg = res.stderr or res.stdout
            except Exception as e:
                err_msg = str(e)

            GLib.idle_add(self._on_package_updated, pkg, success, err_msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_package_updated(self, pkg: Dict[str, Any], success: bool, err_msg: str = ""):
        self.spinner.stop()
        pkg_id = pkg["id"]
        row_data = self.update_rows.get(pkg_id)
        if row_data:
            if row_data.get("pulse_id"):
                GLib.source_remove(row_data["pulse_id"])
                row_data["pulse_id"] = None

            if success:
                row_data["pbar"].set_fraction(1.0)
                row_data["btn"].set_label("ĐÃ CẬP NHẬT")
                row_data["btn"].get_style_context().remove_class("pill-updating")
                row_data["btn"].get_style_context().add_class("pill-updated")
                row_data["lbl_status"].set_text("✓ Đã cập nhật thành công!")
                row_data["lbl_status"].get_style_context().remove_class("mac-update-status-err")
                row_data["lbl_status"].get_style_context().add_class("mac-update-status-ok")
                self.set_status(f"Đã cập nhật {pkg['name']} thành công!")
                GLib.timeout_add(2500, self._refresh_updates_list)
            else:
                row_data["pbar"].hide()
                row_data["btn"].set_label("THỬ LẠI")
                row_data["btn"].set_sensitive(True)
                row_data["btn"].get_style_context().remove_class("pill-updating")
                row_data["btn"].get_style_context().add_class("pill-open")
                msg = "⚠ Cập nhật thất bại"
                if "cancel" in err_msg.lower() or "auth" in err_msg.lower() or "not authorized" in err_msg.lower():
                    msg = "⚠ Đã hủy xác thực mật khẩu"
                elif "lock" in err_msg.lower():
                    msg = "⚠ Hệ thống đang bận cập nhật ngầm"
                row_data["lbl_status"].set_text(msg)
                row_data["lbl_status"].get_style_context().remove_class("mac-update-status-ok")
                row_data["lbl_status"].get_style_context().add_class("mac-update-status-err")
                self.set_status(f"Không thể cập nhật {pkg['name']}")
                GLib.timeout_add(4000, lambda: self.set_status(""))

    def _run_system_update(self):
        self.spinner.start()
        self.set_status("Đang cài đặt tất cả bản cập nhật phần mềm...")
        if hasattr(self, 'btn_update_all'):
            self.btn_update_all.set_label(t("appstore_installing", "Installing…"))
            self.btn_update_all.set_sensitive(False)
        if hasattr(self, 'updates_summary_progress'):
            self.updates_summary_progress.show()
            def _pulse_sum():
                if hasattr(self, 'updates_summary_progress') and self.updates_summary_progress.get_visible():
                    self.updates_summary_progress.pulse()
                    return True
                return False
            self.summary_pulse_id = GLib.timeout_add(80, _pulse_sum)

        for pkg_id, row_data in self.update_rows.items():
            row_data["btn"].set_label("ĐANG CẬP NHẬT...")
            row_data["btn"].set_sensitive(False)
            row_data["btn"].get_style_context().remove_class("pill-open")
            row_data["btn"].get_style_context().add_class("pill-updating")
            row_data["lbl_status"].set_text("Đang cập nhật...")
            row_data["lbl_status"].show()
            row_data["pbar"].show()
            def _pulse_row(p=row_data["pbar"]):
                if p.get_visible():
                    p.pulse()
                    return True
                return False
            row_data["pulse_id"] = GLib.timeout_add(80, _pulse_row)

        def _do_update():
            success = True
            try:
                r1 = _privileged_run(["apt-get", "upgrade", "-y"])
                if r1.returncode != 0:
                    success = False
            except Exception:
                success = False
            try:
                r2 = _privileged_run(["snap", "refresh"])
                if r2.returncode != 0:
                    success = False
            except Exception:
                pass
            GLib.idle_add(self._on_update_all_finished, success)

        threading.Thread(target=_do_update, daemon=True).start()

    def _on_update_all_finished(self, success: bool = True):
        self.spinner.stop()
        if hasattr(self, 'summary_pulse_id') and self.summary_pulse_id:
            GLib.source_remove(self.summary_pulse_id)
            self.summary_pulse_id = None
        if hasattr(self, 'updates_summary_progress'):
            if success:
                self.updates_summary_progress.set_fraction(1.0)
            else:
                self.updates_summary_progress.hide()
        if hasattr(self, 'btn_update_all'):
            self.btn_update_all.set_label(t("appstore_update_all", "Update All"))
            self.btn_update_all.set_sensitive(True)
        self.set_status("Đã hoàn tất tất cả bản cập nhật phần mềm." if success else "Một số bản cập nhật không thể hoàn thành.")
        GLib.timeout_add(3000, self._refresh_updates_list)

    def set_status(self, text: str):
        if hasattr(self, 'status_lbl'):
            self.status_lbl.set_text(text)
        if hasattr(self, 'status_box'):
            if text:
                self.status_box.show_all()
            else:
                self.status_box.hide()

    # -----------------------------------------------------------------
    # WINDOW CONTROLS & DRAWING
    # -----------------------------------------------------------------
    def _setup_resize_handles(self):
        """Add 8 edge and corner resize handles around the window overlay."""
        def make_handle(cursor_name, edge, width, height, halign, valign):
            eb = Gtk.EventBox()
            eb.set_visible_window(True)
            eb.set_opacity(0.0)
            eb.set_size_request(width, height)
            eb.set_halign(halign)
            eb.set_valign(valign)

            def on_realize(widget):
                win = widget.get_window()
                if win:
                    cursor = Gdk.Cursor.new_from_name(widget.get_display(), cursor_name)
                    win.set_cursor(cursor)

            def on_button_press(widget, event):
                if event.button == 1 and not getattr(self, "_is_maximized", False):
                    self.begin_resize_drag(
                        edge,
                        event.button,
                        int(event.x_root),
                        int(event.y_root),
                        event.time
                    )
                    return True
                return False

            eb.connect("realize", on_realize)
            eb.connect("button-press-event", on_button_press)
            self.master_overlay.add_overlay(eb)
            return eb

        # 4 Edges (thickness: 6px)
        make_handle("ns-resize", Gdk.WindowEdge.NORTH, -1, 6, Gtk.Align.FILL, Gtk.Align.START)
        make_handle("ns-resize", Gdk.WindowEdge.SOUTH, -1, 6, Gtk.Align.FILL, Gtk.Align.END)
        make_handle("ew-resize", Gdk.WindowEdge.WEST, 6, -1, Gtk.Align.START, Gtk.Align.FILL)
        make_handle("ew-resize", Gdk.WindowEdge.EAST, 6, -1, Gtk.Align.END, Gtk.Align.FILL)

        # 4 Corners (thickness: 14x14px)
        make_handle("nwse-resize", Gdk.WindowEdge.NORTH_WEST, 14, 14, Gtk.Align.START, Gtk.Align.START)
        make_handle("nesw-resize", Gdk.WindowEdge.NORTH_EAST, 14, 14, Gtk.Align.END, Gtk.Align.START)
        make_handle("nesw-resize", Gdk.WindowEdge.SOUTH_WEST, 14, 14, Gtk.Align.START, Gtk.Align.END)
        make_handle("nwse-resize", Gdk.WindowEdge.SOUTH_EAST, 16, 16, Gtk.Align.END, Gtk.Align.END)

    def _on_window_button_press(self, widget, event):
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            if event.y < 50 or event.x < 210:
                self.toggle_maximize()
                return True
        elif event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            if event.y < 50 or event.x < 210:
                if not getattr(self, "_is_maximized", False):
                    self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                    return True
        return False

    def _on_window_state_event(self, widget, event):
        is_max = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        is_icon = bool(event.new_window_state & Gdk.WindowState.ICONIFIED)
        was_icon = getattr(self, "_is_iconified", False)
        self._is_iconified = is_icon

        if is_icon:
            return False

        if was_icon and not is_icon:
            self.queue_draw()
        elif self._is_maximized != is_max:
            self._is_maximized = is_max
            self.queue_draw()
        return False

    def toggle_maximize(self):
        if self._is_maximized:
            self.unmaximize()
            self._is_maximized = False
        else:
            self.maximize()
            self._is_maximized = True

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_window()
            return True
        if (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval in (Gdk.KEY_w, Gdk.KEY_W):
            self.close_window()
            return True
        return False

    def close_window(self):
        self.hide()
        if getattr(self, "is_standalone", False):
            Gtk.main_quit()

    def _on_delete_event(self, widget, event):
        self.close_window()
        return True

    def _on_window_draw(self, widget, cr: cairo.Context):
        if getattr(self, "_is_iconified", False):
            return False
        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height
        r = 0.0 if self._is_maximized else 18.0

        if r > 0:
            cr.save()
            cr.set_operator(cairo.Operator.CLEAR)
            cr.paint()
            cr.restore()

            cr.new_sub_path()
            cr.arc(w - r, r, r, -math.pi/2, 0)
            cr.arc(w - r, h - r, r, 0, math.pi/2)
            cr.arc(r, h - r, r, math.pi/2, math.pi)
            cr.arc(r, r, r, math.pi, 3*math.pi/2)
            cr.close_path()
            cr.clip()

        return False

    def _on_window_draw_after(self, widget, cr: cairo.Context):
        if getattr(self, "_is_iconified", False) or self._is_maximized:
            return False

        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height
        r = 18.0

        cr.save()
        cr.new_sub_path()
        cr.arc(w - r - 0.5, r + 0.5, r, -math.pi/2, 0)
        cr.arc(w - r - 0.5, h - r - 0.5, r, 0, math.pi/2)
        cr.arc(r + 0.5, h - r - 0.5, r, math.pi/2, math.pi)
        cr.arc(r + 0.5, r + 0.5, r, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.set_line_width(1.0)
        if self.is_dark:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        else:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.14)
        cr.stroke()
        cr.restore()
        return False

    def apply_theme(self):
        self.is_dark = is_system_dark_mode()
        ctx = self.root_card.get_style_context()
        if self.is_dark:
            ctx.add_class("mac-dark")
            ctx.remove_class("mac-light")
        else:
            ctx.add_class("mac-light")
            ctx.remove_class("mac-dark")
        self.queue_draw()

    # -----------------------------------------------------------------
    # CSS STYLESHEET
    # -----------------------------------------------------------------
    def _load_css(self):
        if MacOSAppStoreWindow._css_loaded:
            return

        css_data = """
        * {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", Roboto, sans-serif;
        }

        window {
            background-color: transparent;
        }

        .mac-appstore-window {
            background-color: transparent;
            border-radius: 18px;
        }

        /* Sidebar */
        .mac-store-sidebar {
            border-top-left-radius: 18px;
            border-bottom-left-radius: 18px;
        }
        .mac-dark .mac-store-sidebar {
            background-color: rgba(30, 30, 32, 0.96);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        .mac-light .mac-store-sidebar {
            background-color: rgba(246, 246, 248, 0.98);
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }

        /* Main Content */
        .mac-store-content {
            border-top-right-radius: 18px;
            border-bottom-right-radius: 18px;
        }
        .mac-dark .mac-store-content {
            background-color: #1a1a1c;
        }
        .mac-light .mac-store-content {
            background-color: #ffffff;
        }

        .mac-store-content scrolledwindow,
        .mac-store-content viewport,
        .mac-store-content stack {
            background-color: transparent;
            background: transparent;
            border-top-right-radius: 18px;
            border-bottom-right-radius: 18px;
        }

        /* Navigation Items */
        .mac-nav-item {
            background: transparent;
            border: none;
            border-radius: 8px;
            padding: 2px 4px;
            margin: 1px 0px;
        }
        .mac-dark .mac-nav-item:hover {
            background-color: rgba(255, 255, 255, 0.06);
        }
        .mac-light .mac-nav-item:hover {
            background-color: rgba(0, 0, 0, 0.04);
        }
        .mac-light .mac-nav-item.active {
            background-color: rgba(0, 0, 0, 0.06);
        }
        .mac-dark .mac-nav-item.active {
            background-color: rgba(255, 255, 255, 0.10);
        }
        .mac-nav-item.active .mac-nav-label {
            color: #007aff;
            font-weight: 600;
        }

        .mac-dark .mac-nav-label {
            color: #f2f2f7;
            font-size: 13.5px;
            font-weight: 500;
        }
        .mac-light .mac-nav-label {
            color: #1c1c1e;
            font-size: 13.5px;
            font-weight: 500;
        }

        .mac-nav-badge {
            background-color: #007aff;
            color: white;
            font-size: 10px;
            font-weight: 700;
            border-radius: 10px;
            padding: 1px 6px;
        }

        /* Search Wrap */
        .mac-store-search-wrap {
            background-color: rgba(120, 120, 128, 0.12);
            border-radius: 8px;
            padding: 2px 8px;
        }
        .mac-store-search-input {
            background: transparent;
            border: none;
            box-shadow: none;
            font-size: 13px;
            color: inherit;
        }

        /* Traffic Lights */
        .mac-traffic-light {
            border-radius: 50%;
            min-width: 12px;
            min-height: 12px;
            padding: 0;
            border: none;
            box-shadow: none;
        }
        .tl-red { background-color: #ff5f56; border: 0.5px solid #e0443e; }
        .tl-yellow { background-color: #ffbd2e; border: 0.5px solid #dea123; }
        .tl-green { background-color: #27c93f; border: 0.5px solid #1aab29; }
        .tl-symbol {
            font-size: 8px;
            font-weight: bold;
            color: rgba(0, 0, 0, 0.6);
        }

        /* Top Header */
        .mac-page-header-title {
            font-size: 22px;
            font-weight: 700;
        }
        .mac-dark .mac-page-header-title { color: #ffffff; }
        .mac-light .mac-page-header-title { color: #1c1c1e; }

        .mac-header-nav-btn {
            background: transparent;
            border: none;
            border-radius: 6px;
            font-size: 22px;
            font-weight: 300;
            color: #007aff;
            min-width: 28px;
            min-height: 28px;
            padding: 0;
        }
        .mac-header-status-lbl {
            font-size: 12px;
            font-weight: 500;
            color: #007aff;
        }

        /* Categories Page */
        .mac-categories-page-title {
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .mac-dark .mac-categories-page-title {
            color: #ffffff;
        }
        .mac-light .mac-categories-page-title {
            color: #1c1c1e;
        }

        /* Category Item Rows */
        .mac-cat-item-row {
            border-radius: 6px;
            padding: 1px 2px;
        }
        .mac-dark .mac-cat-item-row:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }
        .mac-light .mac-cat-item-row:hover {
            background-color: rgba(0, 0, 0, 0.035);
        }

        .mac-cat-item-label {
            font-size: 13.5px;
            font-weight: 500;
        }
        .mac-dark .mac-cat-item-label {
            color: #f2f2f7;
        }
        .mac-light .mac-cat-item-label {
            color: #1c1c1e;
        }

        /* Hairline Divider */
        .mac-dark .mac-cat-hairline-divider {
            background-color: rgba(255, 255, 255, 0.08);
        }
        .mac-light .mac-cat-hairline-divider {
            background-color: rgba(0, 0, 0, 0.07);
        }

        /* See All Link */
        .mac-see-all-btn {
            background: transparent;
            border: none;
            box-shadow: none;
            color: #007aff;
            font-size: 14px;
            font-weight: 500;
            padding: 0;
        }
        .mac-see-all-btn:hover {
            opacity: 0.8;
        }

        /* Hero Banner Card */
        .mac-hero-banner {
            border-radius: 18px;
            padding: 24px 30px;
            background: linear-gradient(135deg, #0d2847 0%, #15457a 50%, #007acc 100%);
            box-shadow: 0 10px 28px rgba(0, 122, 255, 0.25);
        }
        .mac-hero-tag {
            font-size: 11px;
            font-weight: 700;
            color: rgba(255, 255, 255, 0.75);
        }
        .mac-hero-title {
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
        }
        .mac-hero-sub {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.9);
        }
        .mac-hero-pill-btn {
            background-color: #ffffff;
            color: #007aff;
            font-weight: 700;
            font-size: 12.5px;
            border-radius: 18px;
            padding: 7px 22px;
            border: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
        }
        .mac-hero-pill-btn:hover {
            background-color: #f2f2f7;
        }
        .mac-hero-link-btn {
            background: transparent;
            border: none;
            color: #ffffff;
            font-weight: 600;
            font-size: 13px;
        }

        /* Section Titles */
        .mac-section-title {
            font-size: 18.5px;
            font-weight: 700;
        }
        .mac-dark .mac-section-title { color: #f2f2f7; }
        .mac-light .mac-section-title { color: #1c1c1e; }

        /* App Cards (Row Style) */
        .mac-app-card {
            border-radius: 10px;
            padding: 8px 10px;
        }
        .mac-dark .mac-app-card:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }
        .mac-light .mac-app-card:hover {
            background-color: rgba(0, 0, 0, 0.035);
        }

        .mac-app-title {
            font-size: 14px;
            font-weight: 600;
        }
        .mac-dark .mac-app-title { color: #ffffff; }
        .mac-light .mac-app-title { color: #1c1c1e; }

        .mac-app-subtitle {
            font-size: 12px;
            color: #8e8e93;
        }

        /* Pill Buttons: Get / Open */
        .mac-pill-btn {
            border-radius: 16px;
            padding: 4px 18px;
            font-size: 12.5px;
            font-weight: 700;
            border: none;
            box-shadow: none;
            min-width: 64px;
            min-height: 26px;
        }
        .mac-light .mac-pill-btn {
            background-color: #f0f1f5;
            color: #007aff;
        }
        .mac-light .mac-pill-btn:hover {
            background-color: #e5e5ea;
        }
        .mac-dark .mac-pill-btn {
            background-color: rgba(255, 255, 255, 0.12);
            color: #0a84ff;
        }
        .mac-dark .mac-pill-btn:hover {
            background-color: rgba(255, 255, 255, 0.18);
        }

        .pill-uninstall {
            background-color: rgba(255, 59, 48, 0.12);
            color: #ff3b30;
            border: 1px solid rgba(255, 59, 48, 0.25);
        }
        .pill-uninstall:hover {
            background-color: rgba(255, 59, 48, 0.22);
        }

        .pill-installing, .pill-updating {
            background-color: rgba(0, 122, 255, 0.14);
            color: #007aff;
            font-weight: 600;
        }
        .pill-updated {
            background-color: rgba(52, 199, 89, 0.16);
            color: #34c759;
            font-weight: 700;
        }

        /* Progress Bar */
        .mac-store-progress,
        progressbar.mac-store-progress,
        .mac-store-progress progressbar {
            min-height: 4px;
            border-radius: 4px;
            background-color: rgba(120, 120, 128, 0.2);
            border: none;
            padding: 0;
            margin: 2px 0;
        }
        .mac-store-progress trough {
            min-height: 4px;
            border-radius: 4px;
            background-color: rgba(120, 120, 128, 0.18);
            border: none;
        }
        .mac-store-progress progress {
            min-height: 4px;
            border-radius: 4px;
            background-color: #007aff;
            border: none;
        }

        /* Update & Action Status Labels */
        .mac-update-status {
            font-size: 11px;
            color: #007aff;
            font-weight: 500;
        }
        .mac-update-status-ok {
            font-size: 11px;
            color: #34c759;
            font-weight: 600;
        }
        .mac-update-status-err {
            font-size: 11px;
            color: #ff3b30;
            font-weight: 500;
        }

        /* In-App Purchases Caption */
        .mac-iap-label {
            font-size: 8.5px;
            font-weight: 500;
            color: #8e8e93;
            margin-top: 1px;
        }
        .mac-iap-spacer {
            font-size: 8.5px;
            min-height: 10px;
        }

        /* Detail View */
        .mac-detail-title {
            font-size: 26px;
            font-weight: 800;
            color: inherit;
        }
        .mac-detail-dev {
            font-size: 13.5px;
            color: #007aff;
            font-weight: 500;
        }
        .mac-detail-body {
            font-size: 14px;
            color: #8e8e93;
        }
        .mac-blue-dot {
            color: #007aff;
            font-weight: bold;
            font-size: 16px;
        }
        .mac-specs-strip {
            border-radius: 12px;
            padding: 12px 16px;
            margin: 6px 0px;
        }
        .mac-dark .mac-specs-strip {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .mac-light .mac-specs-strip {
            background-color: #f2f2f7;
            border: 1px solid rgba(0, 0, 0, 0.06);
        }
        .mac-metric-val {
            font-size: 18px;
            font-weight: 700;
            color: inherit;
        }
        .mac-metric-tag {
            font-size: 10px;
            font-weight: 600;
            color: #8e8e93;
        }

        /* Updates Summary */
        .mac-updates-summary-card {
            border-radius: 14px;
            padding: 16px 20px;
            background: linear-gradient(135deg, rgba(0, 122, 255, 0.12) 0%, rgba(88, 86, 214, 0.12) 100%);
            border: 1px solid rgba(0, 122, 255, 0.2);
        }
        .mac-btn-update-all {
            background-color: #007aff;
            color: white;
            font-weight: 700;
            border-radius: 16px;
            padding: 7px 18px;
            border: none;
        }

        /* Profile Button in Sidebar */
        .mac-sidebar-profile-btn {
            background: transparent;
            border: none;
            box-shadow: none;
            border-radius: 10px;
            padding: 0;
            margin: 0 4px 6px 4px;
        }
        .mac-dark .mac-sidebar-profile-btn:hover {
            background-color: rgba(255, 255, 255, 0.07);
        }
        .mac-light .mac-sidebar-profile-btn:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        .profile-name {
            font-size: 13.5px;
            font-weight: 600;
            color: inherit;
        }
        """

        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(css_data.encode("utf-8"))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            MacOSAppStoreWindow._css_loaded = True
        except Exception as e:
            print(f"⚠️ [AppStore] Error loading CSS: {e}")


# =========================================================================
# LAUNCHER
# =========================================================================

def open_appstore():
    win = MacOSAppStoreWindow.get_instance()
    win.show_all()
    win.present()
    return win


if __name__ == "__main__":
    win = open_appstore()
    Gtk.main()
