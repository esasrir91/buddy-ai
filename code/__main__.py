"""Launch the Aura IDE backend — and optionally open a desktop window.

Usage:
    python -m buddy.code                         # backend only (http://127.0.0.1:8600)
    python -m buddy.code --desktop               # opens a native app window (pywebview)
    python -m buddy.code --browser               # opens in default browser (like Pulse)
    python -m buddy.code --workspace /path/to/project
    python -m buddy.code --port 9001
    python -m buddy.code --host 0.0.0.0          # allow network access (mobile clients)
"""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aura",
        description="Aura — AI coding IDE",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8600)
    parser.add_argument("--workspace", default=None, help="Folder the agent operates on (default: cwd)")
    parser.add_argument("--reload", action="store_true", help="Hot-reload backend on file changes (dev)")
    parser.add_argument("--desktop", action="store_true", help="Open in a native desktop window (pywebview)")
    parser.add_argument("--browser", action="store_true", help="Open in the default system browser")
    args = parser.parse_args()

    if args.workspace:
        os.environ["BUDDY_CODE_WORKSPACE"] = args.workspace

    from buddy.code.server import serve

    serve(
        host=args.host,
        port=args.port,
        reload=args.reload,
        desktop=args.desktop,
        browser=args.browser,
    )


if __name__ == "__main__":
    main()
