"""Buddy Code - a Cursor-like AI coding assistant built on the Buddy framework.

A workspace-scoped coding agent (file read/write/edit/search + shell), a settings
store for API keys / model / tools, and a FastAPI backend that powers a web UI
and cross-platform (Windows / macOS) desktop builds.
"""

import buddy.models as _models  # noqa: F401  initialise models first (avoids a framework circular import)

from buddy.code.settings import CodeSettings, load_settings, save_settings
from buddy.code.tools import WorkspaceTools

__all__ = ["WorkspaceTools", "CodeSettings", "load_settings", "save_settings"]
