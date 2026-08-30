#!/usr/bin/env bash
# Aura — AI Coding IDE (macOS .command — double-click in Finder)
cd "$(dirname "$0")"
if command -v python3 &>/dev/null; then
    python3 -m buddy.code --desktop
elif command -v python &>/dev/null; then
    python -m buddy.code --desktop
else
    osascript -e 'display dialog "Python not found. Install Python 3.10+ first." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi
