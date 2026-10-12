from typing import Annotated, Any, Dict, Literal, Optional

from pydantic import BaseModel, StringConstraints, model_validator


WorkspaceString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
WorkspaceEventType = Literal["setup", "start", "stop", "update"]
WorkspaceEventStatus = Literal["in_progress", "success", "failed"]


class WorkspaceCreate(BaseModel):
    ws_name: WorkspaceString
    git_url: Optional[WorkspaceString] = None
    visibility: Optional[WorkspaceString] = None
    ws_data: Optional[Dict[str, Any]] = None


class WorkspaceUpdate(BaseModel):
    id_workspace: WorkspaceString
    ws_name: Optional[WorkspaceString] = None
    git_url: Optional[WorkspaceString] = None
    visibility: Optional[WorkspaceString] = None
    ws_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkspaceDelete(BaseModel):
    id_workspace: WorkspaceString
    ws_name: Optional[WorkspaceString] = None


class WorkspaceEvent(BaseModel):
    id_workspace: WorkspaceString
    event_type: WorkspaceEventType
    event_status: WorkspaceEventStatus
    event_data: Optional[Dict[str, Any]] = None


class WorkspaceSchema(BaseModel):
    """Workspace data returned by the API."""

    id_workspace: Optional[WorkspaceString] = None
    ws_name: Optional[WorkspaceString] = None
    is_active: Optional[bool] = None
    git_url: Optional[WorkspaceString] = None
    visibility: Optional[WorkspaceString] = None
    ws_data: Optional[Dict[str, Any]] = None


class WorkspaceIdentifier(BaseModel):
    ws_key: Optional[WorkspaceString] = None
    id_workspace: Optional[WorkspaceString] = None

    @model_validator(mode="after")
    def validate_identifier(self) -> "WorkspaceIdentifier":
        if not self.ws_key and not self.id_workspace:
            raise ValueError("At least one of ws_key or id_workspace is required")
        return self
