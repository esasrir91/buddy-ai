from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AppCreate(BaseModel):
    """Data sent to API to create an App"""
    model_config = ConfigDict(extra="forbid")
    app_id: Optional[Identifier] = None
    name: Optional[NonEmptyText] = None
    description: Optional[NonEmptyText] = None
    config: Dict[str, Any]
