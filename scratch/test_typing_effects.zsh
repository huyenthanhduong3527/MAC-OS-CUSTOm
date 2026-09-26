#!/usr/bin/env zsh

# Test ZLE typing & deleting widget hooks
typeset -g _FX_CURSOR_TYPING="\033]12;#00f0ff\007\033[5 q"
typeset -g _FX_CURSOR_DELETING="\033]12;#ff2a6d\007\033[2 q"
typeset -g _FX_CURSOR_NORMAL="\033]12;#7aa2f7\007\033[5 q"

function zle-typing-fx() {
    builtin printf "$_FX_CURSOR_TYPING"
    zle .self-insert
}

function zle-backward-delete-fx() {
    builtin printf "$_FX_CURSOR_DELETING"
    zle .backward-delete-char
}

function zle-delete-char-fx() {
    builtin printf "$_FX_CURSOR_DELETING"
    zle .delete-char
}

function zle-line-init-fx() {
    builtin printf "$_FX_CURSOR_NORMAL"
}

function zle-line-finish-fx() {
    builtin printf "$_FX_CURSOR_NORMAL"
}

zle -N self-insert zle-typing-fx
zle -N backward-delete-char zle-backward-delete-fx
zle -N delete-char zle-delete-char-fx
zle -N zle-line-init zle-line-init-fx
zle -N zle-line-finish zle-line-finish-fx

echo "ZLE Typing and Deleting effects loaded successfully!"
