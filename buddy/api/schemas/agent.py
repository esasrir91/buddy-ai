from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AgentSessionCreate(BaseModel):
    """Data sent to API to create an Agent Session"""

    model_config = ConfigDict(extra="forbid")

    session_id: Identifier
    agent_data: Optional[Dict[str, Any]] = None


class AgentRunCreate(BaseModel):
    """Data sent to API to create an Agent Run"""

    model_config = ConfigDict(extra="forbid")

    session_id: Identifier
    team_session_id: Optional[Identifier] = None
    workflow_session_id: Optional[Identifier] = None
    run_id: Optional[Identifier] = None
    run_data: Optional[Dict[str, Any]] = None
    agent_data: Optional[Dict[str, Any]] = None


class AgentCreate(BaseModel):
    """Data sent to API to create an Agent"""

    model_config = ConfigDict(extra="forbid")

    agent_id: Identifier
    team_id: Optional[Identifier] = None
    app_id: Optional[Identifier] = None
    workflow_id: Optional[Identifier] = None
    name: Optional[str] = None
    config: Dict[str, Any]
