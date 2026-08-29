"""In-process diagnostics store (Monaco → backend → ReadLints)."""
from __future__ import annotations

import threading
from typing import Any, Dict, List

_lock = threading.Lock()
_diags: List[Dict[str, Any]] = []


def set_diagnostics(markers: List[Dict[str, Any]]) -> None:
    with _lock:
        global _diags
        _diags = list(markers)


def get_diagnostics() -> List[Dict[str, Any]]:
    with _lock:
        return list(_diags)
