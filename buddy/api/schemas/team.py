from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TeamSessionCreate(BaseModel):
    """Data sent to API to create a Team Session"""

    model_config = ConfigDict(extra="forbid")

    session_id: Identifier
    team_data: Optional[Dict[str, Any]] = None


class TeamRunCreate(BaseModel):
    """Data sent to API to create a Team Run"""

    model_config = ConfigDict(extra="forbid")

    session_id: Identifier
    team_session_id: Optional[Identifier] = None
    workflow_session_id: Optional[Identifier] = None
    run_id: Optional[Identifier] = None
    run_data: Optional[Dict[str, Any]] = None
    team_data: Optional[Dict[str, Any]] = None


class TeamCreate(BaseModel):
    """Data sent to API to create a Team"""

    model_config = ConfigDict(extra="forbid")

    team_id: Identifier
    parent_team_id: Optional[Identifier] = None
    app_id: Optional[Identifier] = None
    workflow_id: Optional[Identifier] = None
    name: Optional[str] = None
    config: Dict[str, Any]
