#!/usr/bin/env bash
# Quick wrapper for uninstall.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/uninstall.sh" "$@"
