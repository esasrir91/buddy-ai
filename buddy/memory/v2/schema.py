from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class UserMemory:
    """Model for User Memories"""

    memory: str
    topics: Optional[List[str]] = None
    input: Optional[str] = None
    last_updated: Optional[datetime] = None
    memory_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        _dict = {
            "memory_id": self.memory_id,
            "memory": self.memory,
            "topics": self.topics,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "input": self.input,
        }
        return {k: v for k, v in _dict.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserMemory":
        values = data.copy()
        last_updated = values.get("last_updated")
        if isinstance(last_updated, str):
            values["last_updated"] = datetime.fromisoformat(last_updated)
        return cls(**values)


@dataclass
class SessionSummary:
    """Model for Session Summary."""

    summary: str
    topics: Optional[List[str]] = None
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        _dict = {
            "summary": self.summary,
            "topics": self.topics,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
        return {k: v for k, v in _dict.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        values = data.copy()
        last_updated = values.get("last_updated")
        if isinstance(last_updated, str):
            values["last_updated"] = datetime.fromisoformat(last_updated)
        return cls(**values)
