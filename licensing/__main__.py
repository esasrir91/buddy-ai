"""Run the Varam AI license server:  python -m buddy.licensing [--host H] [--port P] [--reload]"""

from __future__ import annotations

import argparse

from buddy.licensing.server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Varam AI License & Entitlement API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
