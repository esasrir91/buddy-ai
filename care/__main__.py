"""Run the Buddy Care server:  python -m buddy.care [--host H] [--port P] [--reload]"""

from __future__ import annotations

import argparse

from buddy.care.server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Buddy Care - customer-care server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8700)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
