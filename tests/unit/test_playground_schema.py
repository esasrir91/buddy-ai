import pytest
from pydantic import ValidationError

from buddy.api.schemas.playground import PlaygroundEndpointCreate


def test_playground_endpoint_create_accepts_http_url_and_preserves_string_payload():
    model = PlaygroundEndpointCreate(endpoint=" http://localhost:7777 ")

    assert model.endpoint == "http://localhost:7777"
    assert isinstance(model.model_dump()["endpoint"], str)


@pytest.mark.parametrize("endpoint", ["", "   ", "not-a-url", "javascript:alert(1)"])
def test_playground_endpoint_create_rejects_invalid_endpoint(endpoint):
    with pytest.raises(ValidationError):
        PlaygroundEndpointCreate(endpoint=endpoint)


def test_playground_endpoint_create_rejects_extra_fields():
    with pytest.raises(ValidationError):
        PlaygroundEndpointCreate(endpoint="http://localhost:7777", unexpected=True)