#!/usr/bin/env bash
# Aura — AI Coding IDE launcher (Mac / Linux)
# Usage:   ./start-aura.sh [/path/to/workspace]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ████████████████████████████████"
echo "   A U R A  —  AI Coding IDE"
echo "  ████████████████████████████████"
echo ""

# Pick Python 3 (prefer python3, fall back to python)
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "  [ERROR] Python not found. Install Python 3.10+ first."
    exit 1
fi

# Optional workspace argument
WORKSPACE_ARG=""
if [ -n "$1" ]; then
    WORKSPACE_ARG="--workspace $1"
fi

echo "  Starting Aura…"
$PY -m buddy.code --desktop $WORKSPACE_ARG
