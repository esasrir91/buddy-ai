from enum import Enum
from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvalType(str, Enum):
    ACCURACY = "accuracy"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    COMPETENCY = "competency"


class EvalRunCreate(BaseModel):
    """Data sent to the API to create an evaluation run"""

    model_config = ConfigDict(extra="forbid")
    agent_id: Optional[Identifier] = None
    model_id: Optional[Identifier] = None
    model_provider: Optional[str] = None
    team_id: Optional[Identifier] = None
    name: Optional[str] = None
    evaluated_entity_name: Optional[str] = None

    run_id: Identifier
    eval_type: EvalType
    eval_data: Dict[str, Any]
