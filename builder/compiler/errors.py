"""Compiler error types - all carry the offending node id where possible so the
frontend can highlight the exact block."""

from __future__ import annotations

from typing import Optional


class CompileError(Exception):
    def __init__(self, message: str, node_id: Optional[str] = None):
        self.node_id = node_id
        super().__init__(f"[node={node_id}] {message}" if node_id else message)


__all__ = ["CompileError"]
