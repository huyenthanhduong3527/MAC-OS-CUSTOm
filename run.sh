#!/usr/bin/env bash
# Runner script for Dynamic Island on Ubuntu GNOME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONUNBUFFERED=1

# Only force X11 backend for the top Dynamic Island overlay daemon.
# Standalone apps (Notes, Photo Booth, Settings, Photos, AppStore, AirDrop, etc.)
# run smoothly with native Wayland/X11 compositor integration and fluid Dash to Dock animations.
if [ $# -eq 0 ] || [ "$1" = "island" ]; then
    export GDK_BACKEND=x11
fi

echo "✨ Launching Dynamic Island GNOME..."
python3 "${SCRIPT_DIR}/main.py" "$@"
