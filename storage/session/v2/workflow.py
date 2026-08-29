from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from buddy.utils.log import logger


@dataclass
class WorkflowSession:
    """Workflow Session v2 — stores full run history for Workflows v2."""

    # Session UUID
    session_id: str
    # ID of the user interacting with this workflow
    user_id: Optional[str] = None
    # ID of the workflow that this session is associated with
    workflow_id: Optional[str] = None
    # Display name of the workflow
    workflow_name: Optional[str] = None
    # List of workflow run records (each a full pipeline execution)
    runs: Optional[List[Any]] = field(default_factory=list)
    # Workflow configuration / step metadata
    workflow_data: Optional[Dict[str, Any]] = None
    # Session Data: session_name, session_state, images, videos, audio
    session_data: Optional[Dict[str, Any]] = None
    # Extra Data stored with this workflow session
    extra_data: Optional[Dict[str, Any]] = None
    # The unix timestamp when this session was created
    created_at: Optional[int] = None
    # The unix timestamp when this session was last updated
    updated_at: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def telemetry_data(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Optional[WorkflowSession]:
        if data is None or data.get("session_id") is None:
            logger.warning("WorkflowSession (v2) is missing session_id")
            return None

        runs = data.get("runs")
        if runs is None:
            runs = []

        return cls(
            session_id=data.get("session_id"),  # type: ignore
            user_id=data.get("user_id"),
            workflow_id=data.get("workflow_id"),
            workflow_name=data.get("workflow_name"),
            runs=runs,
            workflow_data=data.get("workflow_data"),
            session_data=data.get("session_data"),
            extra_data=data.get("extra_data"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
