"""Provider-neutral response schema normalization helpers."""

from typing import Any

from pydantic import BaseModel

from buddy.utils.json_schema import inline_pydantic_schema


def get_response_schema_for_provider(response_model: type[BaseModel], provider: str) -> dict[str, Any]:
    """Return an inlined JSON schema suitable for a provider response format."""
    del provider
    return inline_pydantic_schema(response_model.model_json_schema())
