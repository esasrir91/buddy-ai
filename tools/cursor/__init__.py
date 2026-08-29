"""
CursorTools – Cursor-parity toolkit for the Aura / Buddy Code agent.

All file operations are sandboxed to the workspace root.
PascalCase tool names match the Cursor IDE tool surface.
"""

from buddy.tools.cursor.toolkit import CursorTools

__all__ = ["CursorTools"]
