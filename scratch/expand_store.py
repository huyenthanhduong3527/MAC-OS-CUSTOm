import os
import sys

target_file = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/src/ui/macos_appstore_window.py"
with open(target_file, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Extra apps definition
extra_apps_code = '''    {
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
'''

# Insert extra apps right before the end of APP_CATALOG:
target_needle = '        "features": [\n            "Zero-knowledge end-to-end encryption",\n            "Secure password generator and auto-fill",\n            "Seamless synchronization across mobile and browser"\n        ]\n    }\n]'
replacement = '        "features": [\n            "Zero-knowledge end-to-end encryption",\n            "Secure password generator and auto-fill",\n            "Seamless synchronization across mobile and browser"\n        ]\n    },\n' + extra_apps_code + ']'

if target_needle in text:
    text = text.replace(target_needle, replacement, 1)
    print("1. Added EXTRA_APPS to APP_CATALOG")
else:
    print("WARNING: target_needle for APP_CATALOG not found!")

# 2. Add query_snapd_apps and CAT_TO_SNAPD_SECTION
snapd_helper_code = '''
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
'''

if "def query_snapd_apps(" not in text:
    target_pos = text.find("def load_system_desktop_apps()")
    if target_pos != -1:
        text = text[:target_pos] + snapd_helper_code + "\n\n" + text[target_pos:]
        print("2. Added query_snapd_apps and CAT_TO_SNAPD_SECTION")

with open(target_file, "w", encoding="utf-8") as f:
    f.write(text)

print("Saved intermediate updates successfully.")
