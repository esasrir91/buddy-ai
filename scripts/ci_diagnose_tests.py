"""Import each unit test module explicitly — used in CI diagnostics."""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

UNIT_TEST_DIR = Path(__file__).resolve().parent.parent / "tests" / "unit"
MODULES = [
    "test_package",
    "test_cli",
    "test_planning",
    "test_pulse",
    "test_pyproject",
]


def main() -> None:
    sys.path.insert(0, str(UNIT_TEST_DIR))
    for name in MODULES:
        path = UNIT_TEST_DIR / f"{name}.py"
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load spec for {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"{name} OK")
        except Exception:
            print(f"{name} FAILED", file=sys.stderr)
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
