"""WorkspaceTools - a workspace-confined coding toolkit for the Buddy Code agent.

All file operations are resolved relative to a workspace root and validated to
prevent escaping it (path traversal). This is the toolset that makes the agent
able to "work extensively well on any given task": read, search, create, edit,
and run code, just like Cursor's agent.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from buddy.tools import Toolkit

# Directories we never traverse when listing/searching (noise + performance).
_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".next", ".turbo", ".idea", ".vscode",
    "target", ".cursor", ".buddy_builder",
}
_MAX_READ_BYTES = 400_000


class WorkspaceTools(Toolkit):
    def __init__(
        self,
        base_path: str,
        enable_shell: bool = True,
        **kwargs,
    ):
        self.base = Path(base_path).expanduser().resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.enable_shell = enable_shell

        tools: List[Callable] = [
            self.list_directory,
            self.read_file,
            self.search_code,
            self.write_file,
            self.edit_file,
            self.create_file,
            self.delete_file,
        ]
        if enable_shell:
            tools.append(self.run_command)

        super().__init__(name="workspace_tools", tools=tools, **kwargs)

    # ------------------------------------------------------------------ utils
    def _resolve(self, path: str) -> Path:
        """Resolve ``path`` inside the workspace, rejecting traversal."""
        p = (self.base / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        if self.base not in p.parents and p != self.base:
            raise ValueError(f"Path '{path}' is outside the workspace")
        return p

    def _rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.base)).replace("\\", "/")
        except ValueError:
            return str(p)

    # ------------------------------------------------------------------ tools
    def list_directory(self, path: str = ".", depth: int = 2) -> str:
        """List files and folders in the workspace as a tree.

        Args:
            path (str): Directory relative to the workspace root. Defaults to root.
            depth (int): How many levels deep to recurse. Defaults to 2.

        Returns:
            str: A newline-separated tree of paths.
        """
        try:
            root = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        if not root.exists():
            return f"Error: '{path}' does not exist"

        lines: List[str] = []

        def walk(d: Path, prefix: str, level: int) -> None:
            if level > depth:
                return
            try:
                entries = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except PermissionError:
                return
            for entry in entries:
                if entry.name in _IGNORE_DIRS or entry.name.startswith("."):
                    if entry.is_dir():
                        continue
                lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
                if entry.is_dir() and entry.name not in _IGNORE_DIRS:
                    walk(entry, prefix + "  ", level + 1)

        walk(root, "", 1)
        return "\n".join(lines) if lines else "(empty)"

    def read_file(self, path: str, start_line: int = 1, end_line: int = 0) -> str:
        """Read a text file from the workspace.

        Args:
            path (str): File path relative to the workspace root.
            start_line (int): 1-indexed first line to read. Defaults to 1.
            end_line (int): Last line to read (0 = end of file). Defaults to 0.

        Returns:
            str: The file contents with line numbers.
        """
        try:
            p = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        if not p.is_file():
            return f"Error: '{path}' is not a file"
        if p.stat().st_size > _MAX_READ_BYTES:
            return f"Error: '{path}' is too large to read ({p.stat().st_size} bytes)"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading '{path}': {e}"
        lines = text.splitlines()
        end = len(lines) if end_line <= 0 else min(end_line, len(lines))
        start = max(1, start_line)
        chunk = lines[start - 1 : end]
        return "\n".join(f"{start + i:>5}| {line}" for i, line in enumerate(chunk))

    def search_code(self, query: str, path: str = ".", max_results: int = 50) -> str:
        """Search the workspace for a string (case-insensitive substring match).

        Args:
            query (str): Text to search for.
            path (str): Directory to search within. Defaults to workspace root.
            max_results (int): Maximum number of matches to return. Defaults to 50.

        Returns:
            str: Matching lines as ``path:line: content``.
        """
        try:
            root = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        q = query.lower()
        results: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS and not d.startswith(".")]
            for fn in filenames:
                fp = Path(dirpath) / fn
                try:
                    if fp.stat().st_size > _MAX_READ_BYTES:
                        continue
                    for i, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        if q in line.lower():
                            results.append(f"{self._rel(fp)}:{i}: {line.strip()[:200]}")
                            if len(results) >= max_results:
                                return "\n".join(results)
                except Exception:
                    continue
        return "\n".join(results) if results else "No matches found."

    def write_file(self, path: str, content: str) -> str:
        """Create or completely overwrite a file with new content.

        Args:
            path (str): File path relative to the workspace root.
            content (str): The full new file content.

        Returns:
            str: Confirmation message.
        """
        try:
            p = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {self._rel(p)}"

    def edit_file(self, path: str, old_string: str, new_string: str) -> str:
        """Replace an exact substring in a file (like a precise find & replace).

        Args:
            path (str): File path relative to the workspace root.
            old_string (str): The exact text to replace (must be unique in the file).
            new_string (str): The replacement text.

        Returns:
            str: Confirmation or an error if the target text was not found/unique.
        """
        try:
            p = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        if not p.is_file():
            return f"Error: '{path}' is not a file"
        text = p.read_text(encoding="utf-8", errors="replace")
        count = text.count(old_string)
        if count == 0:
            return f"Error: old_string not found in '{path}'"
        if count > 1:
            return f"Error: old_string appears {count} times in '{path}'; make it more specific"
        p.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
        return f"Edited {self._rel(p)}"

    def create_file(self, path: str, content: str = "") -> str:
        """Create a new file (errors if it already exists).

        Args:
            path (str): File path relative to the workspace root.
            content (str): Optional initial content.

        Returns:
            str: Confirmation message.
        """
        try:
            p = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        if p.exists():
            return f"Error: '{path}' already exists"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Created {self._rel(p)}"

    def delete_file(self, path: str) -> str:
        """Delete a file from the workspace.

        Args:
            path (str): File path relative to the workspace root.

        Returns:
            str: Confirmation message.
        """
        try:
            p = self._resolve(path)
        except ValueError as e:
            return f"Error: {e}"
        if not p.is_file():
            return f"Error: '{path}' is not a file"
        p.unlink()
        return f"Deleted {self._rel(p)}"

    def run_command(self, command: str, timeout: int = 60) -> str:
        """Run a shell command from the workspace root and return its output.

        Args:
            command (str): The shell command to execute.
            timeout (int): Max seconds to wait. Defaults to 60.

        Returns:
            str: Combined stdout/stderr and the exit code.
        """
        if not self.enable_shell:
            return "Error: shell execution is disabled in settings"
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.base),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {timeout}s"
        except Exception as e:
            return f"Error running command: {e}"
        out = (proc.stdout or "")[-8000:]
        err = (proc.stderr or "")[-4000:]
        return json.dumps({"exit_code": proc.returncode, "stdout": out, "stderr": err})


__all__ = ["WorkspaceTools"]
