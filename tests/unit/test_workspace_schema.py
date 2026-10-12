import pytest
from pydantic import ValidationError

from buddy.api.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceEvent,
    WorkspaceIdentifier,
    WorkspaceSchema,
)


def test_workspace_schema_preserves_visibility():
    workspace = WorkspaceSchema.model_validate({"id_workspace": "ws-1", "visibility": "private"})

    assert workspace.visibility == "private"


def test_workspace_identifier_requires_key_or_id():
    with pytest.raises(ValidationError):
        WorkspaceIdentifier()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: WorkspaceCreate(ws_name="   "),
        lambda: WorkspaceIdentifier(ws_key="   "),
        lambda: WorkspaceEvent(id_workspace="ws-1", event_type="unknown", event_status="success"),
        lambda: WorkspaceEvent(id_workspace="ws-1", event_type="setup", event_status="unknown"),
    ],
)
def test_workspace_schema_rejects_invalid_values(factory):
    with pytest.raises(ValidationError):
        factory()


def test_workspace_strings_are_trimmed():
    workspace = WorkspaceCreate(ws_name="  demo  ", git_url="  git@example.com:org/repo.git  ")

    assert workspace.ws_name == "demo"
    assert workspace.git_url == "git@example.com:org/repo.git"
