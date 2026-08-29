"""Workspace path sandbox – identical logic to WorkspaceTools._resolve."""
from __future__ import annotations
import os
from pathlib import Path


class Sandbox:
    def __init__(self, base_path: str) -> None:
        self.base = Path(base_path).expanduser().resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def resolve(self, path: str) -> Path:
        """Resolve *path* inside the workspace; raise ValueError on traversal."""
        if os.path.isabs(path):
            p = Path(path).resolve()
        else:
            p = (self.base / path).resolve()
        if self.base != p and self.base not in p.parents:
            raise ValueError(f"Path '{path}' escapes the workspace.")
        return p

    def rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.base)).replace("\\", "/")
        except ValueError:
            return str(p)

    def assert_enabled(self, flag: bool, tool_name: str) -> None:
        if not flag:
            raise RuntimeError(f"{tool_name} is disabled in this workspace.")
