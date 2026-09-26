#!/usr/bin/env bash
# ==============================================================================
# 🏝️ MODULAR INSTALLER FOR DYNAMIC ISLAND & MACOS SYSTEM ON UBUNTU LINUX
# Cho phép người dùng cài đặt toàn bộ hoặc tùy chọn từng thành phần riêng lẻ:
#  - macOS Menu Bar (GNOME Shell Extension)
#  - Dynamic Island (Core App + MPRIS2 + OSD suppression + autostart)
#  - Desktop Widgets (Lịch âm, Thời tiết, Pin 4 vòng, Đồng hồ, Nhạc...)
#  - Các App chuẩn macOS (App Store, Notes, Photos, Settings, AirDrop, Photo Booth)
#  - Hình Nền Động (Live Wallpaper Video Engine 4K/1080p 60FPS)
#  - Terminal macOS & Hiệu Ứng Gõ Phím (Ptyxis Tokyo Night, Zsh, Typing FX, Fastfetch)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
AUTOSTART_DIR="${HOME}/.config/autostart"
EXT_DIR="${HOME}/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "${APP_DIR}" "${ICON_DIR}" "${AUTOSTART_DIR}" "${EXT_DIR}" "${BIN_DIR}" "${HOME}/.local/share/icons/hicolor/512x512/apps"

chmod +x "${SCRIPT_DIR}/run.sh" "${SCRIPT_DIR}/main.py" "${SCRIPT_DIR}/install.sh" "${SCRIPT_DIR}/uninstall.sh" "${SCRIPT_DIR}/rm.sh" "${SCRIPT_DIR}/install_theme.sh" "${SCRIPT_DIR}/scripts/"*.sh "${SCRIPT_DIR}/scripts/"*.py 2>/dev/null || true

# ------------------------------------------------------------------------------
# Hàm kiểm tra và cài đặt gói phụ thuộc apt
# ------------------------------------------------------------------------------
install_system_packages() {
    local pkgs=("$@")
    local missing=()
    for pkg in "${pkgs[@]}"; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        echo "📦 Đang cài đặt các thư viện hệ thống còn thiếu: ${missing[*]}..."
        if command -v sudo >/dev/null 2>&1; then
            sudo apt update && sudo apt install -y "${missing[@]}"
        else
            echo "⚠️  Vui lòng tự cài bằng lệnh: sudo apt install -y ${missing[*]}"
        fi
    else
        echo "✅ Thư viện hệ thống đã đầy đủ (${pkgs[*]})."
    fi
}

# ------------------------------------------------------------------------------
# 1. Cài đặt Dynamic Island (Đảo thông minh)
# ------------------------------------------------------------------------------
install_island() {
    echo ""
    echo "========================================================"
    echo "🏝️  CÀI ĐẶT DYNAMIC ISLAND (ĐẢO THÔNG MINH)"
    echo "========================================================"

    # Kiểm tra dependencies
    install_system_packages python3-gi python3-gi-cairo python3-cairo gir1.2-gtk-3.0 python3-psutil python3-dbus x11-xserver-utils python3-pil

    # Tạo icon SVG độ phân giải cao
    echo "🎨 Đang cài icon vector Dynamic Island..."
    cat << 'SVG_EOF' > "${ICON_DIR}/dynamic-island.svg"
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#818cf8"/>
      <stop offset="100%" stop-color="#c084fc"/>
    </linearGradient>
  </defs>
  <rect width="128" height="128" rx="28" fill="url(#bg)"/>
  <rect x="20" y="46" width="88" height="36" rx="18" fill="#000000" stroke="url(#glow)" stroke-width="2.5"/>
  <circle cx="38" cy="64" r="6" fill="#38bdf8"/>
  <rect x="52" y="61" width="36" height="6" rx="3" fill="#ffffff" opacity="0.8"/>
  <circle cx="98" cy="64" r="3" fill="#22c55e"/>
</svg>
SVG_EOF

    # Tạo launcher menu ứng dụng và autostart khi đăng nhập
    echo "🖥️  Đăng ký launcher & kích hoạt tự khởi động khi bật máy..."
    sed "s|Exec=.*|Exec=${SCRIPT_DIR}/run.sh|g" "${SCRIPT_DIR}/dynamic-island.desktop" > "${APP_DIR}/dynamic-island.desktop"
    chmod +x "${APP_DIR}/dynamic-island.desktop"
    cp -f "${APP_DIR}/dynamic-island.desktop" "${AUTOSTART_DIR}/dynamic-island.desktop"

    # Tối ưu hóa GNOME Mutter (vô hiệu ping modal "Main.py Is Not Responding")
    if command -v gsettings >/dev/null 2>&1; then
        gsettings set org.gnome.mutter check-alive-timeout 0 2>/dev/null || true
    fi

    # Ẩn thanh OSD âm lượng mặc định của GNOME để chỉ hiển thị độc quyền trên Dynamic Island
    if [ -d "${HOME}/.themes" ]; then
        for css in "${HOME}/.themes"/*/gnome-shell/gnome-shell.css; do
            if [ -f "$css" ] && ! grep -q "Suppress Native GNOME OSD" "$css"; then
                cat << 'CSS_EOF' >> "$css"

/* Suppress Native GNOME OSD (Volume & Brightness HUD Popups) */
.osd-window, .osd-window * {
    opacity: 0 !important;
    min-width: 0px !important;
    min-height: 0px !important;
    width: 0px !important;
    height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    border: none !important;
    background-color: transparent !important;
    box-shadow: none !important;
    color: transparent !important;
}
CSS_EOF
            fi
        done
    fi

    # Cập nhật cache
    update-desktop-database "${APP_DIR}" 2>/dev/null || true
    gtk-update-icon-cache "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true

    echo "✅ Cài đặt Dynamic Island hoàn tất!"
    echo "👉 Khởi chạy ngay: ./run.sh (hoặc tìm trong menu ứng dụng)"
}

# ------------------------------------------------------------------------------
# 2. Cài đặt macOS Menu Bar (GNOME Shell Extension)
# ------------------------------------------------------------------------------
install_menubar() {
    echo ""
    echo "========================================================"
    echo "🍏 CÀI ĐẶT MACOS MENU BAR (GNOME SHELL EXTENSION)"
    echo "========================================================"

    # Tạo symlink
    ln -sfn "${SCRIPT_DIR}" "${HOME}/.local/share/dynamic-island"

    if [ -d "${SCRIPT_DIR}/extensions/macos-menu-bar@Nguyenthanhtam" ]; then
        echo "📂 Đang sao chép mã nguồn extension..."
        mkdir -p "${EXT_DIR}"
        cp -rf "${SCRIPT_DIR}/extensions/macos-menu-bar@Nguyenthanhtam/"* "${EXT_DIR}/"

        # Kích hoạt qua gsettings
        if command -v gsettings >/dev/null 2>&1; then
            CURRENT_EXTS=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "[]")
            if [[ "$CURRENT_EXTS" != *"macos-menu-bar@Nguyenthanhtam"* ]]; then
                NEW_EXTS=$(echo "$CURRENT_EXTS" | sed "s/]/, 'macos-menu-bar@Nguyenthanhtam']/")
                gsettings set org.gnome.shell enabled-extensions "$NEW_EXTS" 2>/dev/null || true
                echo "   - Đã thêm vào danh sách gsettings enabled-extensions"
            fi
        fi

        # Kích hoạt qua gnome-extensions CLI
        if command -v gnome-extensions >/dev/null 2>&1; then
            gnome-extensions enable macos-menu-bar@Nguyenthanhtam 2>/dev/null || true
            echo "   - Đã gửi lệnh bật extension qua gnome-extensions"
        fi
    fi

    echo "✅ Cài đặt macOS Menu Bar hoàn tất!"
    echo "💡 Lưu ý: Trên Wayland/GNOME mới, bạn hãy Đăng xuất (Log Out) và Đăng nhập lại để thanh menu xuất hiện đẹp nhất!"
}

# ------------------------------------------------------------------------------
# 3. Cài đặt Widgets Desktop (Bộ Widgets Màn Hình)
# ------------------------------------------------------------------------------
install_widgets() {
    echo ""
    echo "========================================================"
    echo "🖥️  CÀI ĐẶT BỘ WIDGETS DESKTOP CHUẨN MACOS"
    echo "========================================================"

    # Kiểm tra thư viện
    install_system_packages python3-gi python3-gi-cairo python3-cairo gir1.2-gtk-3.0 python3-psutil python3-pil

    # Dọn dẹp blur-my-shell để tránh viền mờ vuông quanh các widget bo tròn
    local BLUR_SCHEMA_DIR="${HOME}/.local/share/gnome-shell/extensions/blur-my-shell@aunetx/schemas"
    if [ -d "$BLUR_SCHEMA_DIR" ] && command -v gsettings >/dev/null 2>&1; then
        gsettings --schemadir "$BLUR_SCHEMA_DIR" set org.gnome.shell.extensions.blur-my-shell.applications blur false 2>/dev/null || true
        gsettings --schemadir "$BLUR_SCHEMA_DIR" set org.gnome.shell.extensions.blur-my-shell.applications whitelist "[]" 2>/dev/null || true
    fi

    # Tạo launcher mở widget
    cat << WIDGET_EOF > "${APP_DIR}/macos-widgets.desktop"
[Desktop Entry]
Type=Application
Version=1.0
Name=macOS Desktop Widgets
Name[vi]=Bộ Widget Màn Hình macOS
GenericName=Desktop Widgets
Comment=Widget Lịch Âm Dương, Thời Tiết, Vòng Pin 4 thiết bị, Đồng hồ chuẩn Apple
Exec=${SCRIPT_DIR}/run.sh --widgets
Icon=${SCRIPT_DIR}/assets/category_icons/productivity.png
Terminal=false
Categories=Utility;Desktop;System;
StartupWMClass=desktop-widgets
StartupNotify=true
WIDGET_EOF
    chmod +x "${APP_DIR}/macos-widgets.desktop"

    # Bật các widget trong file cấu hình JSON
    mkdir -p "${HOME}/.config/dynamic_island"
    python3 -c "
import json, os
p = os.path.expanduser('~/.config/dynamic_island/config.json')
data = {}
if os.path.exists(p):
    try:
        with open(p, 'r') as f: data = json.load(f)
    except Exception: data = {}
for k in ['enable_desktop_calendar', 'enable_desktop_weather', 'enable_desktop_battery']:
    data[k] = True
with open(p, 'w') as f: json.dump(data, f, indent=4)
" 2>/dev/null || true

    update-desktop-database "${APP_DIR}" 2>/dev/null || true

    echo "✅ Cài đặt Widgets Desktop hoàn tất!"
    echo "👉 Khởi chạy thử: ./run.sh --widgets (hoặc ./run.sh --calendar, ./run.sh --weather, ./run.sh --battery)"
}

# ------------------------------------------------------------------------------
# 4. Cài đặt Các App macOS (Notes, Photos, Settings, App Store, AirDrop...)
# ------------------------------------------------------------------------------
install_apps() {
    echo ""
    echo "========================================================"
    echo "📦 CÀI ĐẶT CÁC APP CHUẨN MACOS"
    echo "========================================================"

    # Kiểm tra thư viện
    install_system_packages python3-gi python3-gi-cairo gir1.2-gtk-3.0 openssl python3-pil python3-opencv

    # Copy icons
    if [ -f "${SCRIPT_DIR}/assets/appstore_icon.png" ]; then
        cp -f "${SCRIPT_DIR}/assets/appstore_icon.png" "${HOME}/.local/share/icons/hicolor/512x512/apps/appstore.png"
    fi
    if [ -f "${SCRIPT_DIR}/assets/appstore_icon.svg" ]; then
        cp -f "${SCRIPT_DIR}/assets/appstore_icon.svg" "${ICON_DIR}/appstore.svg"
    fi

    # 1. Notes (Ghi chú)
    if [ -f "${SCRIPT_DIR}/macos-notes.desktop" ]; then
        sed "s|Exec=.*|Exec=${SCRIPT_DIR}/run.sh --notes|g" "${SCRIPT_DIR}/macos-notes.desktop" > "${APP_DIR}/macos-notes.desktop"
        chmod +x "${APP_DIR}/macos-notes.desktop"
    fi

    # 2. Photos (Ảnh)
    if [ -f "${SCRIPT_DIR}/macos-photos.desktop" ]; then
        sed "s|Exec=.*|Exec=${SCRIPT_DIR}/run.sh --photos|g" "${SCRIPT_DIR}/macos-photos.desktop" > "${APP_DIR}/macos-photos.desktop"
        chmod +x "${APP_DIR}/macos-photos.desktop"
    fi

    # 3. Settings (Cài đặt hệ thống)
    if [ -f "${SCRIPT_DIR}/macos-settings.desktop" ]; then
        sed "s|Exec=.*|Exec=${SCRIPT_DIR}/run.sh --settings|g" "${SCRIPT_DIR}/macos-settings.desktop" > "${APP_DIR}/macos-settings.desktop"
        chmod +x "${APP_DIR}/macos-settings.desktop"
    fi

    # 4. AirDrop
    if [ -f "${SCRIPT_DIR}/macos-airdrop.desktop" ]; then
        sed "s|Exec=.*|Exec=${SCRIPT_DIR}/run.sh --airdrop|g" "${SCRIPT_DIR}/macos-airdrop.desktop" > "${APP_DIR}/macos-airdrop.desktop"
        chmod +x "${APP_DIR}/macos-airdrop.desktop"
    fi

    # 5. Photo Booth
    if [ -f "${SCRIPT_DIR}/macos-photobooth.desktop" ]; then
        sed "s|Exec=.*|Exec=${SCRIPT_DIR}/run.sh --photobooth|g" "${SCRIPT_DIR}/macos-photobooth.desktop" > "${APP_DIR}/macos-photobooth.desktop"
        chmod +x "${APP_DIR}/macos-photobooth.desktop"
    fi

    # 6. macOS App Store
    rm -f "${APP_DIR}/macos-appstore.desktop"
    cat << STORE_EOF > "${APP_DIR}/snap-store_snap-store.desktop"
[Desktop Entry]
X-SnapInstanceName=snap-store
Type=Application
Version=1.0
X-SnapAppName=snap-store
Exec=${SCRIPT_DIR}/run.sh --appstore %F
Icon=${SCRIPT_DIR}/assets/appstore_icon.png
Terminal=false
Categories=System;Utility;PackageManager;SoftwareManagement;Network;Settings;
Keywords=Ubuntu;Applications;Apps;Store;Software;Snaps;App Store;App Center;AppCenter;Snap Store;Cửa hàng ứng dụng;Trung tâm ứng dụng;kho ứng dụng;cài app;cài phần mềm;
MimeType=x-scheme-handler/snap;
StartupWMClass=snap-store
StartupNotify=true
Name=App Store
Name[vi]=App Store
GenericName=App Center (macOS App Store)
GenericName[vi]=Trung tâm ứng dụng (App Center)
X-GNOME-FullName=App Store (Ubuntu App Center)
X-GNOME-FullName[vi]=App Store (Trung tâm ứng dụng Ubuntu App Center)
Comment=Apple macOS App Store (Ubuntu App Center)
Comment[vi]=Kho ứng dụng Apple macOS App Store (Trung tâm ứng dụng Ubuntu App Center)
STORE_EOF
    chmod +x "${APP_DIR}/snap-store_snap-store.desktop"

    # 7. Trình cài gói macOS (.deb)
    if [ -f "${SCRIPT_DIR}/src/ui/macos_deb_installer.py" ]; then
        cat << DEB_EOF > "${APP_DIR}/macos-deb-installer.desktop"
[Desktop Entry]
Type=Application
Version=1.0
Name=Trình cài đặt macOS (.deb)
Name[en]=macOS Package Installer (.deb)
GenericName=Package Installer
Comment=Cài đặt gói ứng dụng Debian (.deb) theo chuẩn Apple macOS
Exec=${SCRIPT_DIR}/run.sh --install-deb %F
Icon=${SCRIPT_DIR}/assets/app_icons/installer.png
Terminal=false
Categories=System;Settings;PackageManager;
MimeType=application/vnd.debian.binary-package;
StartupWMClass=macos-deb-installer
StartupNotify=true
DEB_EOF
        chmod +x "${APP_DIR}/macos-deb-installer.desktop"

        if command -v xdg-mime >/dev/null 2>&1; then
            xdg-mime default macos-deb-installer.desktop application/vnd.debian.binary-package 2>/dev/null || true
        fi
    fi

    update-desktop-database "${APP_DIR}" 2>/dev/null || true
    gtk-update-icon-cache "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true

    echo "✅ Đã đăng ký tất cả các App macOS vào menu ứng dụng Ubuntu!"
    echo "👉 Bạn có thể tìm thấy: App Store, Ghi chú, Ảnh, Cài đặt macOS, AirDrop, Photo Booth."
}

# ------------------------------------------------------------------------------
# 5. Cài đặt Hình Nền Động (Live Wallpaper)
# ------------------------------------------------------------------------------
install_wallpaper() {
    echo ""
    echo "========================================================"
    echo "🎬 CÀI ĐẶT HÌNH NỀN ĐỘNG (LIVE VIDEO WALLPAPER ENGINE)"
    echo "========================================================"

    # Kiểm tra thư viện xử lý video mượt mà
    install_system_packages python3-opencv opencv-data python3-numpy python3-pil

    # Tạo lệnh tắt trong ~/.local/bin/live-wallpaper
    cat << BIN_EOF > "${BIN_DIR}/live-wallpaper"
#!/usr/bin/env bash
python3 "${SCRIPT_DIR}/scripts/live_wallpaper.py" "\$@"
BIN_EOF
    chmod +x "${BIN_DIR}/live-wallpaper"

    # Tạo desktop launcher
    cat << WALLPAPER_EOF > "${APP_DIR}/live-wallpaper.desktop"
[Desktop Entry]
Type=Application
Version=1.0
Name=Live Wallpaper (Hình nền động)
GenericName=Live Wallpaper Manager
Comment=Quản lý và chọn video hình nền động 4K/1080p 60FPS
Exec=${SCRIPT_DIR}/scripts/live_wallpaper.py choose
Icon=${SCRIPT_DIR}/assets/category_icons/creativity.png
Terminal=false
Categories=Utility;Desktop;Settings;
StartupWMClass=live-wallpaper
StartupNotify=true
WALLPAPER_EOF
    chmod +x "${APP_DIR}/live-wallpaper.desktop"

    update-desktop-database "${APP_DIR}" 2>/dev/null || true

    echo "✅ Cài đặt Hình nền động thành công!"
    echo "👉 Khởi động hình nền động: python3 scripts/live_wallpaper.py start (hoặc live-wallpaper start)"
    echo "👉 Chọn video bằng chuột GUI: python3 scripts/live_wallpaper.py choose"
}

# ------------------------------------------------------------------------------
# 6. Cài đặt Terminal macOS & Hiệu Ứng Gõ Phím Động (Ptyxis, Zsh, Typing FX, Fastfetch)
# ------------------------------------------------------------------------------
install_terminal() {
    echo ""
    echo "========================================================"
    echo "⚡ CÀI ĐẶT MACOS TERMINAL & HIỆU ỨNG GÕ PHÍM ĐỘNG"
    echo "========================================================"

    # Kiểm tra gói cần thiết
    install_system_packages zsh curl git python3

    # Cài đặt Zsh, Oh My Zsh, Agnoster, Ptyxis & hiệu ứng gõ phím
    if [ -f "${SCRIPT_DIR}/install_theme.sh" ]; then
        bash "${SCRIPT_DIR}/install_theme.sh"
    fi

    # Cài đặt pwfeedback cho sudo
    if [ -f "${SCRIPT_DIR}/scripts/setup_terminal_effects.sh" ]; then
        bash "${SCRIPT_DIR}/scripts/setup_terminal_effects.sh" 2>/dev/null || true
    fi

    # Cài đặt Fastfetch config
    if [ -f "${SCRIPT_DIR}/scripts/setup_hacker_fetch.py" ]; then
        python3 "${SCRIPT_DIR}/scripts/setup_hacker_fetch.py" 2>/dev/null || true
    fi

    # Cài đặt hacker_splash binary
    if [ -f "${SCRIPT_DIR}/scripts/hacker_splash.py" ]; then
        cp -f "${SCRIPT_DIR}/scripts/hacker_splash.py" "${BIN_DIR}/hacker_splash"
        chmod +x "${BIN_DIR}/hacker_splash"
    fi

    echo "✅ Cài đặt Terminal macOS & Hiệu ứng gõ phím hoàn tất!"
    echo "👉 Hãy mở một cửa sổ Terminal mới (hoặc gõ: zsh) để trải nghiệm!"
}

# ------------------------------------------------------------------------------
# 7. Cài đặt TẤT CẢ (Full Installation)
# ------------------------------------------------------------------------------
install_all() {
    echo "========================================================"
    echo "🚀 BẮT ĐẦU CÀI ĐẶT TRỌN BỘ DYNAMIC ISLAND & MACOS SYSTEM"
    echo "========================================================"

    install_island
    install_menubar
    install_widgets
    install_apps
    install_wallpaper
    install_terminal

    echo ""
    echo "========================================================"
    echo "🎉 CHÚC MỪNG! BẠN ĐÃ CÀI ĐẶT HOÀN TẤT TOÀN BỘ HỆ THỐNG!"
    echo "========================================================"
    echo "✨ 1. Dynamic Island: Sẽ tự khởi chạy khi đăng nhập (hoặc chạy ngay: ./run.sh)"
    echo "✨ 2. macOS Menu Bar: Đăng xuất (Log Out) & Đăng nhập lại để kích hoạt."
    echo "✨ 3. Desktop Widgets: Đã sẵn sàng trên màn hình Desktop."
    echo "✨ 4. Bộ App macOS: Đã có trong App Grid (App Store, Ghi chú, Ảnh, AirDrop...)"
    echo "✨ 5. Hình nền động: Khởi chạy bằng lệnh 'live-wallpaper start' hoặc chuột trong App Grid."
    echo "✨ 6. macOS Terminal: Mở cửa sổ Terminal mới để trải nghiệm hiệu ứng gõ Neon & xóa Ruby Red."
    echo "========================================================"
}

# ------------------------------------------------------------------------------
# Xử lý tham số dòng lệnh CLI hoặc Menu tương tác
# ------------------------------------------------------------------------------
TARGET="${1:-}"

case "${TARGET,,}" in
    island|dynamic-island|pill)
        install_island
        ;;
    menubar|menu|topbar|bar|extension)
        install_menubar
        ;;
    widgets|widget|desktop-widgets)
        install_widgets
        ;;
    apps|app|applications)
        install_apps
        ;;
    wallpaper|live-wallpaper|video)
        install_wallpaper
        ;;
    terminal|term|zsh|ptyxis|theme)
        install_terminal
        ;;
    all|full)
        install_all
        ;;
    "")
        if [ -t 0 ]; then
            echo "========================================================"
            echo "🍎 BỘ CÀI ĐẶT DYNAMIC ISLAND & MACOS SYSTEM TRÊN UBUNTU"
            echo "========================================================"
            echo "Vui lòng chọn thành phần bạn muốn cài đặt:"
            echo ""
            echo "  1) Cài đặt TẤT CẢ (Khuyên dùng - Đầy đủ toàn bộ tính năng)"
            echo "  2) Cài riêng Dynamic Island (Đảo thông minh + Hub điều khiển)"
            echo "  3) Cài riêng macOS Menu Bar (Thanh menu Apple trên cùng)"
            echo "  4) Cài riêng Bộ Widgets Desktop (Lịch âm, Thời tiết, Pin 4 vòng...)"
            echo "  5) Cài riêng Các App macOS (App Store, Ghi chú, Ảnh, AirDrop...)"
            echo "  6) Cài riêng Hình Nền Động (Live Video Wallpaper Engine)"
            echo "  7) Cài riêng Terminal & Hiệu Ứng Gõ Phím (Ptyxis, Zsh, Neon FX)"
            echo "  0) Thoát"
            echo ""
            read -r -p "👉 Nhập số lựa chọn của bạn [0-7]: " choice

            case "$choice" in
                1) install_all ;;
                2) install_island ;;
                3) install_menubar ;;
                4) install_widgets ;;
                5) install_apps ;;
                6) install_wallpaper ;;
                7) install_terminal ;;
                0) echo "Đã hủy bỏ."; exit 0 ;;
                *) echo "❌ Lựa chọn không hợp lệ!"; exit 1 ;;
            esac
        else
            install_all
        fi
        ;;
    *)
        echo "❌ Lựa chọn không hợp lệ: $TARGET"
        echo ""
        echo "Cú pháp sử dụng:"
        echo "  ./install.sh all        # Cài đặt tất cả"
        echo "  ./install.sh island     # Chỉ cài Dynamic Island"
        echo "  ./install.sh menubar    # Chỉ cài macOS Menu Bar"
        echo "  ./install.sh widgets    # Chỉ cài Widgets Desktop"
        echo "  ./install.sh apps       # Chỉ cài các App macOS"
        echo "  ./install.sh wallpaper  # Chỉ cài Hình nền động"
        echo "  ./install.sh terminal   # Chỉ cài macOS Terminal & Hiệu ứng gõ phím"
        exit 1
        ;;
esac
