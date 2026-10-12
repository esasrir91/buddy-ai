from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class WorkflowCreate(BaseModel):
    """Data sent to API to create a Workflow"""

    model_config = ConfigDict(extra="forbid")

    workflow_id: Identifier
    app_id: Optional[Identifier] = None
    name: Optional[str] = None
    config: Dict[str, Any]
