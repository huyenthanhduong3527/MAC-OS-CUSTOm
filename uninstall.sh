#!/usr/bin/env bash
# ==============================================================================
# 🗑️ UNINSTALL SCRIPT FOR DYNAMIC ISLAND & MACOS SYSTEM ON UBUNTU LINUX
# Cho phép người dùng gỡ bỏ từng thành phần riêng lẻ hoặc gỡ bỏ toàn bộ sạch sẽ.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/share/applications"
AUTOSTART_DIR="${HOME}/.config/autostart"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
EXT_DIR="${HOME}/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam"
BIN_DIR="${HOME}/.local/bin"

# ------------------------------------------------------------------------------
# 1. Gỡ bỏ Dynamic Island
# ------------------------------------------------------------------------------
uninstall_island() {
    echo "🏝️  Đang gỡ bỏ Dynamic Island..."
    
    # Dừng tiến trình
    "${SCRIPT_DIR}/main.py" quit 2>/dev/null || true
    pkill -f "python3.*main.py" 2>/dev/null || true

    # Xóa file launcher và autostart
    rm -f "${APP_DIR}/dynamic-island.desktop"
    rm -f "${AUTOSTART_DIR}/dynamic-island.desktop"
    rm -f "${ICON_DIR}/dynamic-island.svg"

    # Khôi phục kiểm tra treo của GNOME Mutter về mặc định
    if command -v gsettings >/dev/null 2>&1; then
        gsettings set org.gnome.mutter check-alive-timeout 5000 2>/dev/null || true
    fi

    # Cập nhật cache
    update-desktop-database "${APP_DIR}" 2>/dev/null || true
    gtk-update-icon-cache "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true

    echo "✅ Đã gỡ bỏ Dynamic Island thành công!"
}

# ------------------------------------------------------------------------------
# 2. Gỡ bỏ macOS Menu Bar (GNOME Shell Extension)
# ------------------------------------------------------------------------------
uninstall_menubar() {
    echo "🍏 Đang gỡ bỏ macOS Menu Bar Extension..."

    # Tắt extension
    if command -v gnome-extensions >/dev/null 2>&1; then
        gnome-extensions disable macos-menu-bar@Nguyenthanhtam 2>/dev/null || true
    fi

    # Xóa khỏi danh sách enabled-extensions của gsettings
    if command -v gsettings >/dev/null 2>&1; then
        CURRENT_EXTS=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "[]")
        if [[ "$CURRENT_EXTS" == *"macos-menu-bar@Nguyenthanhtam"* ]]; then
            NEW_EXTS=$(echo "$CURRENT_EXTS" | sed "s/'macos-menu-bar@Nguyenthanhtam'//g; s/, ,/,/g; s/\[, /[/g; s/, \]/]/g")
            gsettings set org.gnome.shell enabled-extensions "$NEW_EXTS" 2>/dev/null || true
        fi
    fi

    # Xóa thư mục extension và symlink
    rm -rf "${EXT_DIR}"
    rm -f "${HOME}/.local/share/dynamic-island"

    echo "✅ Đã gỡ bỏ macOS Menu Bar Extension!"
    echo "💡 Mẹo: Hãy Đăng xuất (Log Out) và Đăng nhập lại để Top Bar GNOME trở về mặc định hoàn toàn."
}

# ------------------------------------------------------------------------------
# 3. Gỡ bỏ Widgets Desktop
# ------------------------------------------------------------------------------
uninstall_widgets() {
    echo "🖥️  Đang tắt và gỡ bỏ Widgets Desktop..."

    # Tắt tiến trình widget độc lập
    pkill -f "desktop_widgets" 2>/dev/null || true

    # Xóa launcher widget nếu có
    rm -f "${APP_DIR}/macos-widgets.desktop"

    # Tắt cờ bật widget trong cấu hình dynamic_island
    if [ -f "${HOME}/.config/dynamic_island/config.json" ]; then
        python3 -c "
import json, os
p = os.path.expanduser('~/.config/dynamic_island/config.json')
try:
    with open(p, 'r') as f: d = json.load(f)
    for k in ['enable_desktop_calendar', 'enable_desktop_weather', 'enable_desktop_battery', 'enable_desktop_clock', 'enable_desktop_music', 'enable_desktop_photo', 'enable_desktop_weekday', 'enable_desktop_macbook']:
        d[k] = False
    with open(p, 'w') as f: json.dump(d, f, indent=4)
except Exception: pass
" 2>/dev/null || true
    fi

    echo "✅ Đã tắt và gỡ bỏ Desktop Widgets thành công!"
}

# ------------------------------------------------------------------------------
# 4. Gỡ bỏ Các App macOS
# ------------------------------------------------------------------------------
uninstall_apps() {
    echo "📦 Đang gỡ bỏ các ứng dụng macOS (Notes, Photos, Settings, App Store, AirDrop, Photo Booth)..."

    # Xóa launcher các app
    rm -f "${APP_DIR}/macos-notes.desktop"
    rm -f "${APP_DIR}/macos-photos.desktop"
    rm -f "${APP_DIR}/macos-settings.desktop"
    rm -f "${APP_DIR}/macos-airdrop.desktop"
    rm -f "${APP_DIR}/macos-photobooth.desktop"
    rm -f "${APP_DIR}/snap-store_snap-store.desktop"
    rm -f "${APP_DIR}/macos-deb-installer.desktop"

    # Khôi phục mime default nếu cần
    if command -v xdg-mime >/dev/null 2>&1; then
        xdg-mime default org.gnome.Software.desktop application/vnd.debian.binary-package 2>/dev/null || true
    fi

    # Cập nhật cache
    update-desktop-database "${APP_DIR}" 2>/dev/null || true

    echo "✅ Đã gỡ bỏ toàn bộ lối tắt các App macOS khỏi hệ thống!"
}

# ------------------------------------------------------------------------------
# 5. Gỡ bỏ Hình Nền Động (Live Wallpaper)
# ------------------------------------------------------------------------------
uninstall_wallpaper() {
    echo "🎬 Đang dừng và gỡ bỏ Hình nền động (Live Wallpaper)..."

    # Dừng tiến trình
    python3 "${SCRIPT_DIR}/scripts/live_wallpaper.py" stop 2>/dev/null || true
    pkill -f "live_wallpaper.py" 2>/dev/null || true
    pkill -f "live_wallpaper --run" 2>/dev/null || true

    # Xóa file runtime và cấu hình
    rm -f "/tmp/live_wallpaper.pid" "/tmp/live_wallpaper.log"
    rm -f "${AUTOSTART_DIR}/live-wallpaper.desktop"
    rm -f "${APP_DIR}/live-wallpaper.desktop"
    rm -f "${BIN_DIR}/live-wallpaper"
    rm -f "${HOME}/.config/dynamic_island/live_wallpaper.path"

    # Khôi phục hình nền mặc định GNOME nếu cần
    if command -v gsettings >/dev/null 2>&1; then
        gsettings reset org.gnome.desktop.background picture-uri 2>/dev/null || true
        gsettings reset org.gnome.desktop.background picture-uri-dark 2>/dev/null || true
    fi

    echo "✅ Đã dừng và gỡ bỏ Live Wallpaper!"
}

# ------------------------------------------------------------------------------
# 6. Gỡ bỏ Terminal Effects & Khôi phục Shell mặc định
# ------------------------------------------------------------------------------
uninstall_terminal() {
    echo "⚡ Đang gỡ bỏ hiệu ứng Terminal và khôi phục Shell..."

    # Xóa file hiệu ứng typing
    rm -f "${HOME}/.oh-my-zsh/custom/typing_effects.zsh"
    rm -f "${BIN_DIR}/hacker_splash"

    # Tắt pwfeedback sudo nếu có quyền
    if [ -f /etc/sudoers.d/pwfeedback ]; then
        if command -v sudo >/dev/null 2>&1; then
            sudo rm -f /etc/sudoers.d/pwfeedback 2>/dev/null || true
        fi
    fi

    # Khôi phục shell sang Bash nếu đang là Zsh
    local BASH_BIN
    BASH_BIN=$(which bash 2>/dev/null || echo "/bin/bash")
    local CURRENT_SHELL
    CURRENT_SHELL=$(getent passwd "$USER" | cut -d: -f7)
    if [ "$CURRENT_SHELL" != "$BASH_BIN" ]; then
        chsh -s "$BASH_BIN" "$USER" 2>/dev/null || sudo chsh -s "$BASH_BIN" "$USER" 2>/dev/null || true
        echo "   - Đã khôi phục shell mặc định sang Bash ($BASH_BIN)"
    fi

    echo "✅ Đã gỡ bỏ hiệu ứng Terminal thành công!"
}

# ------------------------------------------------------------------------------
# 7. Gỡ bỏ TOÀN BỘ sạch sẽ (Uninstall All)
# ------------------------------------------------------------------------------
uninstall_all() {
    echo "========================================================"
    echo "🗑️  BẮT ĐẦU GỠ BỎ TOÀN BỘ DYNAMIC ISLAND & MACOS SYSTEM"
    echo "========================================================"

    uninstall_island
    uninstall_menubar
    uninstall_widgets
    uninstall_apps
    uninstall_wallpaper
    uninstall_terminal

    # Dọn dẹp thư mục cấu hình nếu người dùng muốn sạch hoàn toàn
    echo "🧹 Dọn dẹp dữ liệu cấu hình..."
    rm -rf "${HOME}/.config/dynamic_island"

    echo ""
    echo "========================================================"
    echo "✨ ĐÃ GỠ BỎ TOÀN BỘ SẠCH SẼ KHỎI MÁY CỦA BẠN!"
    echo "👉 Mọi cài đặt đã được khôi phục về trạng thái Ubuntu gốc."
    echo "👉 Hãy Đăng xuất (Log Out) và Đăng nhập lại để cập nhật."
    echo "========================================================"
}

# ------------------------------------------------------------------------------
# Xử lý tham số dòng lệnh CLI hoặc Menu tương tác
# ------------------------------------------------------------------------------
TARGET="${1:-}"

case "${TARGET,,}" in
    island|dynamic-island|pill)
        uninstall_island
        ;;
    menubar|menu|topbar|bar|extension)
        uninstall_menubar
        ;;
    widgets|widget|desktop-widgets)
        uninstall_widgets
        ;;
    apps|app|applications)
        uninstall_apps
        ;;
    wallpaper|live-wallpaper|video)
        uninstall_wallpaper
        ;;
    terminal|term|zsh|ptyxis|theme)
        uninstall_terminal
        ;;
    all|full|clean)
        uninstall_all
        ;;
    "")
        # Kiểm tra xem có đang chạy trong terminal tương tác không
        if [ -t 0 ]; then
            echo "========================================================"
            echo "🗑️  TRÌNH GỠ BỎ (UNINSTALL) DYNAMIC ISLAND & MACOS"
            echo "========================================================"
            echo "Vui lòng chọn thành phần bạn muốn gỡ bỏ:"
            echo ""
            echo "  1) Gỡ TẤT CẢ sạch sẽ (Gỡ sạch mọi thứ, khôi phục gốc)"
            echo "  2) Gỡ riêng Dynamic Island (Đảo thông minh)"
            echo "  3) Gỡ riêng macOS Menu Bar (Thanh menu trên cùng)"
            echo "  4) Tắt & Gỡ Widgets Desktop (Lịch, Thời tiết, Pin...)"
            echo "  5) Gỡ riêng Các App macOS (Notes, Photos, Settings...)"
            echo "  6) Dừng & Gỡ Hình Nền Động (Live Wallpaper)"
            echo "  7) Gỡ Terminal & Hiệu ứng gõ phím (Khôi phục Bash)"
            echo "  0) Thoát (Không làm gì)"
            echo ""
            read -r -p "👉 Nhập số lựa chọn của bạn [0-7]: " choice

            case "$choice" in
                1) uninstall_all ;;
                2) uninstall_island ;;
                3) uninstall_menubar ;;
                4) uninstall_widgets ;;
                5) uninstall_apps ;;
                6) uninstall_wallpaper ;;
                7) uninstall_terminal ;;
                0) echo "Đã hủy bỏ."; exit 0 ;;
                *) echo "❌ Lựa chọn không hợp lệ!"; exit 1 ;;
            esac
        else
            uninstall_all
        fi
        ;;
    *)
        echo "❌ Lựa chọn không hợp lệ: $TARGET"
        echo ""
        echo "Cú pháp sử dụng:"
        echo "  ./uninstall.sh all        # Gỡ toàn bộ sạch sẽ"
        echo "  ./uninstall.sh island     # Chỉ gỡ Dynamic Island"
        echo "  ./uninstall.sh menubar    # Chỉ gỡ macOS Menu Bar"
        echo "  ./uninstall.sh widgets    # Chỉ tắt và gỡ Widgets"
        echo "  ./uninstall.sh apps       # Chỉ gỡ các App macOS"
        echo "  ./uninstall.sh wallpaper  # Chỉ dừng và gỡ Hình nền động"
        echo "  ./uninstall.sh terminal   # Chỉ gỡ Terminal & Hiệu ứng gõ phím"
        exit 1
        ;;
esac
