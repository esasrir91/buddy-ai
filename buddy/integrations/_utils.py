"""Shared helpers for Buddy integration adapters."""

from __future__ import annotations

from typing import Any


def require(package: str, extra: str) -> Any:
    """Import an optional integration dependency or raise a helpful error.

    Args:
        package: The importable module name (e.g. ``"langchain_core"``).
        extra: The pip extra that installs it (e.g. ``"langchain"``).

    Returns:
        The imported module.

    Raises:
        ImportError: If the package is not installed, with install guidance.
    """
    import importlib

    try:
        return importlib.import_module(package)
    except ImportError as exc:  # pragma: no cover - exercised only without dep
        raise ImportError(
            f"The '{package}' package is required for this Buddy integration. "
            f"Install it with: pip install 'buddy-ai[{extra}]'"
        ) from exc
