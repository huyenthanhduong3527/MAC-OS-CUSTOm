#!/usr/bin/env bash
# macOS Photo Booth & Virtual Camera Setup Script
# Configures PipeWire and optional v4l2loopback for Ubuntu Linux

set -e

echo "========================================================"
echo " 📷 macOS Photo Booth & Virtual Camera Setup"
echo "========================================================"

# 1. Check PipeWire support (Native, zero sudo needed)
echo "🔍 Kiểm tra PipeWire GStreamer Video Source..."
if gst-inspect-1.0 pipewiresink >/dev/null 2>&1; then
    echo "✅ PipeWire pipewiresink đã sẵn sàng!"
    echo "   -> Virtual Camera có thể phát trực tiếp cho Chrome, Google Meet, Discord, Zoom."
else
    echo "⚠️ Đang cài đặt gstreamer1.0-pipewire..."
    sudo apt-get update && sudo apt-get install -y gstreamer1.0-pipewire
fi

# 2. Optional: v4l2loopback kernel module (for legacy V4L2 apps)
echo ""
echo "🔍 Kiểm tra module kernel v4l2loopback (cho ứng dụng V4L2 truyền thống)..."
if lsmod | grep -q v4l2loopback; then
    echo "✅ Module v4l2loopback đã được nạp!"
else
    echo "💡 Muốn nạp module v4l2loopback để tạo thiết bị /dev/video10? (Chạy lệnh dưới nếu cần):"
    echo "   sudo modprobe v4l2loopback devices=1 video_nr=10 card_label=\"macOS Photo Booth Cam\" exclusive_caps=1"
fi

# 3. Create Photo Booth folder in Pictures
mkdir -p "$HOME/Pictures/Photo Booth"
echo "✅ Đã tạo thư mục lưu ảnh: $HOME/Pictures/Photo Booth"

# 4. Install Desktop Entry
DESKTOP_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/macos-photobooth.desktop"
if [ -f "$DESKTOP_SRC" ]; then
    mkdir -p "$HOME/.local/share/applications"
    cp "$DESKTOP_SRC" "$HOME/.local/share/applications/"
    chmod +x "$HOME/.local/share/applications/macos-photobooth.desktop"
    echo "✅ Đã cài đặt lối tắt Photo Booth vào Menu Ứng dụng & Spotlight!"
fi

echo ""
echo "🎉 Thiết lập hoàn tất! Bạn có thể khởi động Photo Booth bằng lệnh:"
echo "   ./run.sh --photobooth"
echo "========================================================"
