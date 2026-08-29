"""Launch the Buddy Builder server.

Usage:
    python -m buddy.builder            # serve on http://127.0.0.1:8500
    python -m buddy.builder --port 9000
    python -m buddy.builder --build-catalog   # pre-warm the catalog cache and exit
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="buddy-builder", description="Buddy no-code agent builder")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8500)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--build-catalog", action="store_true", help="Introspect the framework, cache, and exit")
    args = parser.parse_args()

    if args.build_catalog:
        from buddy.builder.registry import build_catalog

        cat = build_catalog(force=True)
        print(f"Catalog built: {len(cat.node_types)} node types, {len(cat.skipped)} modules skipped.")
        return

    from buddy.builder.server import serve

    serve(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
