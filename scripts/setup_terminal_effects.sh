#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  ⚡ CÀI ĐẶT HIỆU ỨNG NHẬP / XÓA TERMINAL & SUDO PASSWORD"
echo "=========================================================="

# 1. Bật hiển thị dấu sao * khi gõ/xóa mật khẩu sudo
if [ ! -f /etc/sudoers.d/pwfeedback ]; then
    echo "🔑 Bật hiệu ứng dấu sao (*) khi gõ hoặc xóa mật khẩu sudo..."
    echo 'Defaults pwfeedback' | sudo tee /etc/sudoers.d/pwfeedback >/dev/null
    sudo chmod 0440 /etc/sudoers.d/pwfeedback
    echo "✅ Đã bật hiệu ứng pwfeedback cho sudo!"
else
    echo "✅ Hiệu ứng pwfeedback cho sudo đã được bật từ trước."
fi

echo ""
echo "🎉 HOÀN TẤT!"
echo "• Khi gõ lệnh bình thường: Con trỏ Neon Cyan (#00f0ff) + RPROMPT '⚡ typing' + Tô màu cú pháp thời gian thực."
echo "• Khi xóa (Backspace/Del/Ctrl+W): Con trỏ Ruby Red (#ff2a6d) nhấp nháy khối + RPROMPT '⌫ delete'."
echo "• Khi nhập mật khẩu sudo: Hiển thị các dấu sao (****) động khi gõ hoặc xóa."
echo "=========================================================="
