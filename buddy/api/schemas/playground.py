from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, TypeAdapter, field_validator


_http_url_adapter = TypeAdapter(AnyHttpUrl)


class PlaygroundEndpointCreate(BaseModel):
    """Data sent to API to create a playground endpoint"""

    model_config = ConfigDict(extra="forbid")

    endpoint: str
    playground_data: Optional[Dict[str, Any]] = None

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        value = value.strip()
        _http_url_adapter.validate_python(value)
        return value


class PlaygroundEndpointSchema(BaseModel):
    """Schema for a playground endpoint returned by API"""
    id_workspace: Optional[UUID] = None
    id_playground_endpoint: Optional[UUID] = None
    endpoint: str
    playground_data: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)
