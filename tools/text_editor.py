"""TextEditorTool – file viewing and editing client tool.

Mirrors Anthropic's ``text_editor_20250728`` / ``text_editor_20250124`` client
tools but works with **any LLM**.  Provides four operations:

* ``view``       – read a file or list directory contents
* ``str_replace`` – replace an exact string in a file (requires unique match)
* ``create``     – write a new file (or overwrite)
* ``insert``     – insert lines after a given line number

Usage::

    from buddy.tools.text_editor import TextEditorTool

    agent = Agent(model=..., tools=[TextEditorTool(base_dir="/workspace")])
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List, Optional

from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

ANTHROPIC_TOOL_TYPE = "text_editor_20250728"  # for Claude 4+


class TextEditorTool(Toolkit):
    """Read and edit files with view / str_replace / create / insert operations.

    Equivalent to Anthropic's ``text_editor_20250728`` client tool, but
    provider-agnostic.  All file paths are resolved relative to ``base_dir``
    (defaults to ``os.getcwd()``).

    Parameters
    ----------
    base_dir:
        Root directory.  All file operations are sandboxed to this path.
    max_view_lines:
        Maximum number of lines returned by ``view`` (avoids flooding context).
    backup:
        If ``True``, create ``.bak`` backup files before edits.
    """

    ANTHROPIC_TOOL_TYPE = ANTHROPIC_TOOL_TYPE

    def __init__(
        self,
        base_dir: Optional[str] = None,
        max_view_lines: int = 500,
        backup: bool = False,
        **kwargs: Any,
    ):
        import os
        self._base = Path(base_dir or os.getcwd()).resolve()
        self._max_view_lines = max_view_lines
        self._backup = backup

        super().__init__(
            name="str_replace_based_edit_tool",
            tools=[self.view, self.str_replace, self.create, self.insert],
            instructions=(
                "Use the text editor tools to read and modify files. "
                "Always view a file before editing to understand its current contents. "
                "Use str_replace for precise edits; create to write new files; "
                "insert to add lines at a specific position."
            ),
            **kwargs,
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        """Resolve a user-supplied path against base_dir, preventing escapes."""
        p = (self._base / path).resolve()
        if not str(p).startswith(str(self._base)):
            raise PermissionError(f"Path '{path}' escapes the base directory.")
        return p

    @staticmethod
    def _line_numbers(text: str, start: int = 1) -> str:
        lines = text.splitlines()
        width = len(str(start + len(lines) - 1))
        return "\n".join(f"{str(start + i).rjust(width)}│{line}" for i, line in enumerate(lines))

    # ── tool methods ─────────────────────────────────────────────────────────

    def view(self, path: str, view_range: Optional[List[int]] = None) -> str:
        """View the contents of a file or list files in a directory.

        If ``path`` is a directory, lists its contents.  If it is a file,
        returns its contents with line numbers.  Use ``view_range`` to see a
        specific range of lines.

        Args:
            path: Relative path to the file or directory to view.
            view_range: Optional [start_line, end_line] (1-indexed, inclusive).

        Returns:
            str: File contents with line numbers, or directory listing.
        """
        try:
            p = self._resolve(path)
        except PermissionError as exc:
            return json.dumps({"error": str(exc)})

        if p.is_dir():
            entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name))
            listing = [f"{'[DIR] ' if e.is_dir() else '      '}{e.name}" for e in entries]
            return f"Directory: {path}\n" + "\n".join(listing)

        if not p.exists():
            return json.dumps({"error": f"File not found: {path}"})

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return json.dumps({"error": f"Could not read file: {exc}"})

        lines = text.splitlines()
        total = len(lines)

        if view_range:
            start = max(1, view_range[0]) - 1
            end = min(total, view_range[1] if len(view_range) > 1 else total)
            lines = lines[start:end]
            numbered = self._line_numbers("\n".join(lines), start + 1)
            return f"File: {path} (lines {start+1}-{end} of {total})\n{numbered}"

        if total > self._max_view_lines:
            truncated = lines[: self._max_view_lines]
            numbered = self._line_numbers("\n".join(truncated))
            return (
                f"File: {path} ({total} lines; showing first {self._max_view_lines})\n"
                f"{numbered}\n…[truncated – use view_range to see more]"
            )

        return f"File: {path} ({total} lines)\n{self._line_numbers(text)}"

    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """Replace an exact, unique string in a file with new content.

        The ``old_str`` must match exactly one location in the file (including
        whitespace and indentation).  If it matches zero or multiple locations
        the edit is rejected to avoid ambiguous changes.

        Args:
            path: Relative path to the file to edit.
            old_str: The exact string to search for (must be unique).
            new_str: The replacement string.

        Returns:
            str: Success message or error details.
        """
        try:
            p = self._resolve(path)
        except PermissionError as exc:
            return json.dumps({"error": str(exc)})

        if not p.exists():
            return json.dumps({"error": f"File not found: {path}"})

        try:
            original = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return json.dumps({"error": f"Could not read file: {exc}"})

        count = original.count(old_str)
        if count == 0:
            return json.dumps({"error": "old_str not found in file. Double-check whitespace and indentation."})
        if count > 1:
            return json.dumps({"error": f"old_str found {count} times. Provide more context to make it unique."})

        if self._backup:
            p.with_suffix(p.suffix + ".bak").write_text(original, encoding="utf-8")

        updated = original.replace(old_str, new_str, 1)
        p.write_text(updated, encoding="utf-8")

        # Report the changed region
        new_lines = updated.splitlines()
        idx = updated[:updated.index(new_str)].count("\n")
        changed = new_lines[max(0, idx - 1): idx + new_str.count("\n") + 2]
        return f"Successfully replaced in {path}.\nChanged region:\n" + "\n".join(changed)

    def create(self, path: str, file_text: str) -> str:
        """Create a new file or overwrite an existing file with the given content.

        Creates any missing parent directories automatically.  Use this for
        writing new source files, config files, or replacing file content
        wholesale.

        Args:
            path: Relative path of the file to create.
            file_text: The full content to write to the file.

        Returns:
            str: Success message with line count.
        """
        try:
            p = self._resolve(path)
        except PermissionError as exc:
            return json.dumps({"error": str(exc)})

        if self._backup and p.exists():
            p.with_suffix(p.suffix + ".bak").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.write_text(file_text, encoding="utf-8")
            lines = file_text.count("\n") + 1
            return f"File '{path}' created successfully ({lines} lines)."
        except Exception as exc:
            return json.dumps({"error": f"Could not write file: {exc}"})

    def insert(self, path: str, insert_line: int, new_str: str) -> str:
        """Insert text after a specific line number in a file.

        Lines are 1-indexed.  Use ``insert_line=0`` to insert at the very
        beginning of the file.

        Args:
            path: Relative path to the file to edit.
            insert_line: Insert the new content *after* this line (0 = before line 1).
            new_str: The text to insert.  A trailing newline is added if missing.

        Returns:
            str: Success message or error details.
        """
        try:
            p = self._resolve(path)
        except PermissionError as exc:
            return json.dumps({"error": str(exc)})

        if not p.exists():
            return json.dumps({"error": f"File not found: {path}"})

        try:
            original = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return json.dumps({"error": f"Could not read file: {exc}"})

        lines = original.splitlines(keepends=True)
        total = len(lines)
        if insert_line < 0 or insert_line > total:
            return json.dumps({"error": f"insert_line {insert_line} is out of range (file has {total} lines)."})

        if self._backup:
            p.with_suffix(p.suffix + ".bak").write_text(original, encoding="utf-8")

        insertion = new_str if new_str.endswith("\n") else new_str + "\n"
        lines.insert(insert_line, insertion)
        p.write_text("".join(lines), encoding="utf-8")
        return f"Inserted {new_str.count(chr(10)) + 1} line(s) after line {insert_line} in '{path}'."

    def to_anthropic_client_tool(self) -> dict:
        """Return the Anthropic API client-tool declaration."""
        return {"type": self.ANTHROPIC_TOOL_TYPE}
