#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  🚀 CÀI ĐẶT ZSH + OH MY ZSH + THEME AGNOSTER (CHỮ MŨI TÊN)"
echo "=========================================================="

# 1. Cài đặt zsh nếu chưa có
if ! command -v zsh >/dev/null 2>&1; then
    echo "📦 Đang cài đặt zsh..."
    sudo apt update && sudo apt install -y zsh git curl
fi

# 2. Cài đặt Oh My Zsh (unattended - không yêu cầu nhập thủ công)
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "📦 Đang tải và cài đặt Oh My Zsh..."
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
else
    echo "✅ Oh My Zsh đã được cài đặt từ trước."
fi

# 3. Đổi theme sang agnoster
echo "🎨 Cấu hình Theme Agnoster..."
if [ -f "$HOME/.zshrc" ]; then
    sed -i 's/ZSH_THEME=".*"/ZSH_THEME="agnoster"/' "$HOME/.zshrc"
fi

# 4. Cài đặt 2 plugin siêu xịn: gợi ý lệnh tự động và tô màu cú pháp
ZSH_CUSTOM=${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}
mkdir -p "$ZSH_CUSTOM/plugins"

if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]; then
    echo "⚡ Cài đặt plugin zsh-autosuggestions..."
    git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
fi

if [ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]; then
    echo "⚡ Cài đặt plugin zsh-syntax-highlighting..."
    git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
fi

# Cập nhật danh sách plugins trong .zshrc
if [ -f "$HOME/.zshrc" ]; then
    sed -i 's/plugins=(git)/plugins=(git zsh-autosuggestions zsh-syntax-highlighting)/' "$HOME/.zshrc"
fi

# 4b. Cài đặt hiệu ứng gõ phím & xóa phím siêu đẹp (Neon Cyan & Ruby Red)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.local/bin"

if [ -f "$SCRIPT_DIR/scripts/typing_effects.zsh" ]; then
    echo "⚡ Cài đặt hiệu ứng gõ và xóa phím động cho Terminal..."
    cp "$SCRIPT_DIR/scripts/typing_effects.zsh" "$ZSH_CUSTOM/typing_effects.zsh"
fi

# 4c. Cài đặt Hacker Matrix Rain splash và Fastfetch
if [ -f "$SCRIPT_DIR/scripts/hacker_splash.py" ]; then
    echo "⚡ Đăng ký hiệu ứng mở đầu Hacker Matrix Splash..."
    cp "$SCRIPT_DIR/scripts/hacker_splash.py" "$HOME/.local/bin/hacker_splash"
    chmod +x "$HOME/.local/bin/hacker_splash"
fi

if [ -f "$SCRIPT_DIR/scripts/setup_hacker_fetch.py" ]; then
    python3 "$SCRIPT_DIR/scripts/setup_hacker_fetch.py" 2>/dev/null || true
fi

# 4d. Bật hiệu ứng dấu sao (*) cho mật khẩu sudo
if [ -f "$SCRIPT_DIR/scripts/setup_terminal_effects.sh" ]; then
    bash "$SCRIPT_DIR/scripts/setup_terminal_effects.sh" 2>/dev/null || true
fi

# 4e. Cấu hình aliases đẹp mắt trong .zshrc
if [ -f "$HOME/.zshrc" ] && ! grep -q "macOS Terminal Aesthetic Settings" "$HOME/.zshrc"; then
    cat << 'ZSH_EOF' >> "$HOME/.zshrc"

# ── macOS Terminal Aesthetic Settings ──
export DEFAULT_USER="$USER"
export PATH="$HOME/.local/bin:$PATH"

alias cls="clear"
alias c="clear"
alias ll="ls -lah --color=auto"
alias ls="ls --color=auto"
alias fetch="fastfetch"
alias apple="fastfetch"

# Hacker Matrix Rain splash & clean greeting
if [[ -o interactive ]] && [ -t 1 ] && [ -x "$HOME/.local/bin/hacker_splash" ]; then
    "$HOME/.local/bin/hacker_splash"
fi
ZSH_EOF
fi

# 5. Cấu hình giao diện Terminal Ptyxis chuẩn macOS hiện đại
echo "🎨 Tinh chỉnh Ptyxis Terminal (màu Tokyo Night, hiệu ứng mờ kính, con trỏ thanh đứng)..."
PROFILE_ID=$(gsettings get org.gnome.Ptyxis default-profile-uuid 2>/dev/null | tr -d "'")
if [ -n "$PROFILE_ID" ]; then
    gsettings set "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/${PROFILE_ID}/" palette 'Tokyo Night' || true
    gsettings set "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/${PROFILE_ID}/" opacity 0.88 || true
    gsettings set "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/${PROFILE_ID}/" use-custom-command true || true
    gsettings set "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/${PROFILE_ID}/" custom-command 'zsh' || true
fi
gsettings set org.gnome.Ptyxis font-name 'MesloLGS NF 12' || true
gsettings set org.gnome.Ptyxis cursor-shape 'ibeam' || true
gsettings set org.gnome.Ptyxis cursor-blink-mode 'on' || true

# 6. Đổi shell mặc định của user sang Zsh
echo "⚙️ Thiết lập Zsh làm shell mặc định..."
CURRENT_SHELL=$(getent passwd "$USER" | cut -d: -f7)
ZSH_BIN=$(which zsh)
if [ "$CURRENT_SHELL" != "$ZSH_BIN" ]; then
    chsh -s "$ZSH_BIN" "$USER" 2>/dev/null || sudo chsh -s "$ZSH_BIN" "$USER" 2>/dev/null || true
fi

echo ""
echo "=========================================================="
echo "  🎉 CÀI ĐẶT HOÀN TẤT!"
echo "  👉 Giao diện Terminal Ptyxis đã đổi sang Tokyo Night mờ kính."
echo "  👉 Font MesloLGS NF 12 + Zsh + Agnoster + Hacker Matrix Splash."
echo "  👉 Hiệu ứng gõ phím Neon Cyan & xóa phím Ruby Red đã kích hoạt."
echo "  👉 Bạn hãy mở một cửa sổ Terminal mới để trải nghiệm!"
echo "=========================================================="
