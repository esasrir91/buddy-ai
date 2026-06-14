"""CI import smoke test — prints tracebacks on failure."""

from __future__ import annotations

import sys
import traceback


def main() -> None:
    try:
        import buddy

        print("buddy", buddy.__version__)
    except Exception:
        print("buddy import FAILED", file=sys.stderr)
        traceback.print_exc()
        raise

    try:
        from buddy.cli.entrypoint import BUDDY_cli

        _ = BUDDY_cli
        print("cli ok")
    except Exception:
        print("cli import FAILED", file=sys.stderr)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
