#!/usr/bin/env bash
# Runner script for Dynamic Island on Ubuntu GNOME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GDK_BACKEND=x11
export PYTHONUNBUFFERED=1

echo "✨ Launching Dynamic Island GNOME..."
python3 "${SCRIPT_DIR}/main.py" "$@"
