# ==============================================================================
#  ⚡ TERMINAL DYNAMIC TYPING & DELETING EFFECTS (ZSH + PTYXIS / GNOME TERMINAL)
# ==============================================================================

typeset -g _FX_ACTIVE=1
typeset -g _FX_CURSOR_TYPE=$'\033]12;#00f0ff\007\033[5 q'
typeset -g _FX_CURSOR_DELETE=$'\033]12;#ff2a6d\007\033[2 q'
typeset -g _FX_CURSOR_NORMAL=$'\033]12;#7aa2f7\007\033[5 q'

# High-Definition Tokyo Night / Cyberpunk Real-time Syntax Highlighting
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[command]='fg=#50fa7b,bold'
ZSH_HIGHLIGHT_STYLES[alias]='fg=#00f0ff,bold'
ZSH_HIGHLIGHT_STYLES[builtin]='fg=#bd93f9,bold'
ZSH_HIGHLIGHT_STYLES[function]='fg=#ff79c6,bold'
ZSH_HIGHLIGHT_STYLES[precommand]='fg=#bd93f9,italic'
ZSH_HIGHLIGHT_STYLES[commandseparator]='fg=#ff79c6,bold'
ZSH_HIGHLIGHT_STYLES[hashed-command]='fg=#50fa7b,bold'
ZSH_HIGHLIGHT_STYLES[path]='fg=#8be9fd,underline'
ZSH_HIGHLIGHT_STYLES[globbing]='fg=#f1fa8c'
ZSH_HIGHLIGHT_STYLES[history-expansion]='fg=#bd93f9'
ZSH_HIGHLIGHT_STYLES[single-hyphen-option]='fg=#ffb86c,bold'
ZSH_HIGHLIGHT_STYLES[double-hyphen-option]='fg=#ffb86c,bold'
ZSH_HIGHLIGHT_STYLES[back-quoted-argument]='fg=#f1fa8c'
ZSH_HIGHLIGHT_STYLES[single-quoted-argument]='fg=#f1fa8c'
ZSH_HIGHLIGHT_STYLES[double-quoted-argument]='fg=#f1fa8c'
ZSH_HIGHLIGHT_STYLES[dollar-quoted-argument]='fg=#f1fa8c'
ZSH_HIGHLIGHT_STYLES[redirection]='fg=#ff79c6,bold'
ZSH_HIGHLIGHT_STYLES[comment]='fg=#565f89,italic'
ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=#ff5555,bold,underline'

# 1. Widget khi gõ ký tự (Typing Effect: Neon Cyan glow + I-beam cursor)
function _zle_fx_typing() {
    if [[ $_FX_ACTIVE -eq 1 ]]; then
        builtin printf "%s" "$_FX_CURSOR_TYPE"
        zle .self-insert
        RPROMPT="%F{#00f0ff}⚡ typing%f"
        zle reset-prompt
    else
        zle .self-insert
    fi
}

# 2. Widget khi xóa lùi (Backspace / Backward Delete Effect: Ruby Red flash + Block pulse)
function _zle_fx_backward_delete() {
    if [[ $_FX_ACTIVE -eq 1 ]]; then
        builtin printf "%s" "$_FX_CURSOR_DELETE"
        zle .backward-delete-char
        if [[ -z "$BUFFER" ]]; then
            RPROMPT="%F{#565f89}● ready%f"
        else
            RPROMPT="%F{#ff2a6d}⌫ delete%f"
        fi
        zle reset-prompt
    else
        zle .backward-delete-char
    fi
}

# 3. Widget khi xóa tới (Delete key)
function _zle_fx_delete_char() {
    if [[ $_FX_ACTIVE -eq 1 ]]; then
        builtin printf "%s" "$_FX_CURSOR_DELETE"
        zle .delete-char
        if [[ -z "$BUFFER" ]]; then
            RPROMPT="%F{#565f89}● ready%f"
        else
            RPROMPT="%F{#ff2a6d}⌫ delete%f"
        fi
        zle reset-prompt
    else
        zle .delete-char
    fi
}

# 4. Widget khi xóa nguyên từ (Ctrl+W hoặc Alt+Backspace)
function _zle_fx_backward_kill_word() {
    if [[ $_FX_ACTIVE -eq 1 ]]; then
        builtin printf "%s" "$_FX_CURSOR_DELETE"
        zle .backward-kill-word
        RPROMPT="%F{#ff2a6d}✂ cut%f"
        zle reset-prompt
    else
        zle .backward-kill-word
    fi
}

# 5. Khởi tạo dòng lệnh mới (Prompt ready)
function _zle_fx_line_init() {
    if [[ $_FX_ACTIVE -eq 1 ]]; then
        builtin printf "%s" "$_FX_CURSOR_NORMAL"
        RPROMPT="%F{#565f89}●%f"
        zle reset-prompt 2>/dev/null || true
    fi
}

# 6. Khi ấn Enter thực thi lệnh (Line accepted)
function _zle_fx_line_finish() {
    if [[ $_FX_ACTIVE -eq 1 ]]; then
        builtin printf "%s" "$_FX_CURSOR_NORMAL"
        RPROMPT="%F{#565f89}%D{%H:%M:%S}%f"
        zle reset-prompt 2>/dev/null || true
    fi
}

# Đăng ký ZLE widgets
zle -N self-insert _zle_fx_typing
zle -N backward-delete-char _zle_fx_backward_delete
zle -N delete-char _zle_fx_delete_char
zle -N backward-kill-word _zle_fx_backward_kill_word
zle -N zle-line-init _zle_fx_line_init
zle -N zle-line-finish _zle_fx_line_finish

# Lệnh quản lý hiệu ứng gõ phím
function typing-fx() {
    case "$1" in
        off)
            _FX_ACTIVE=0
            builtin printf "%s" "$_FX_CURSOR_NORMAL"
            RPROMPT=""
            echo "⚡ Hiệu ứng nhập/xóa Terminal: ĐÃ TẮT"
            ;;
        on)
            _FX_ACTIVE=1
            echo "⚡ Hiệu ứng nhập/xóa Terminal: ĐÃ BẬT"
            ;;
        test)
            echo "🎨 Đang kiểm tra hiệu ứng con trỏ:"
            echo "1. Hiệu ứng nhập (Neon Cyan):"
            builtin printf "%s" "$_FX_CURSOR_TYPE"
            sleep 0.8
            echo "2. Hiệu ứng xóa (Ruby Red Flash):"
            builtin printf "%s" "$_FX_CURSOR_DELETE"
            sleep 0.8
            echo "3. Trạng thái nghỉ (Tokyo Night):"
            builtin printf "%s" "$_FX_CURSOR_NORMAL"
            echo "✅ Kiểm tra hoàn tất! Hãy thử gõ phím và xóa (Backspace) trên Terminal."
            ;;
        status|*)
            echo "=========================================================="
            echo "  ⚡ TERMINAL DYNAMIC TYPING & DELETING FX"
            echo "=========================================================="
            echo "  • Trạng thái hiệu ứng : $([[ $_FX_ACTIVE -eq 1 ]] && echo 'ĐANG BẬT (Active)' || echo 'ĐÃ TẮT (Disabled)')"
            echo "  • Màu khi gõ (Type)   : #00f0ff (Neon Cyan Beam)"
            echo "  • Màu khi xóa (Delete): #ff2a6d (Ruby Red Block Pulse)"
            echo "  • Màu khi nghỉ (Idle) : #7aa2f7 (Tokyo Night Blue)"
            echo "  • Chỉ báo động HUD    : Bật (RPROMPT real-time feedback)"
            echo ""
            echo "  Cách dùng:"
            echo "    typing-fx on    - Bật hiệu ứng"
            echo "    typing-fx off   - Tắt hiệu ứng"
            echo "    typing-fx test  - Thử nghiệm các màu hiệu ứng"
            echo "=========================================================="
            ;;
    esac
}
