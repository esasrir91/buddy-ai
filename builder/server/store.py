"""A minimal JSON-file project store for builder graphs.

Each project is one GraphSpec persisted as ``<store>/<id>.json``. This keeps the
builder dependency-free for local use; swap for a DB-backed store in production.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from buddy.builder.spec.schema import GraphSpec


class ProjectStore:
    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root or os.getenv("BUDDY_BUILDER_HOME", Path.cwd() / ".buddy_builder")) / "projects"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        safe = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
        if not safe:
            raise ValueError("Invalid project id")
        return self.root / f"{safe}.json"

    def list(self) -> List[Dict]:
        out: List[Dict] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                out.append(
                    {
                        "id": doc.get("id", path.stem),
                        "name": doc.get("name", path.stem),
                        "kind": doc.get("kind", "agent"),
                        "description": doc.get("description"),
                        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    }
                )
            except Exception:
                continue
        return out

    def get(self, project_id: str) -> GraphSpec:
        path = self._path(project_id)
        if not path.exists():
            raise FileNotFoundError(project_id)
        return GraphSpec.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, spec: GraphSpec) -> GraphSpec:
        path = self._path(spec.id)
        path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        return spec

    def delete(self, project_id: str) -> None:
        path = self._path(project_id)
        if path.exists():
            path.unlink()


__all__ = ["ProjectStore"]
