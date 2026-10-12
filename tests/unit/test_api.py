from httpx import Response

import buddy.api.api as api_module


def test_authenticated_headers_refresh_credentials(monkeypatch):
    tokens = iter(["old-token", "new-token"])
    monkeypatch.setattr(api_module, "read_auth_token", lambda: next(tokens))
    client_api = api_module.Api()

    first_headers = client_api.authenticated_headers
    second_headers = client_api.authenticated_headers

    assert first_headers["X-BUDDY-AUTH-TOKEN"] == "old-token"
    assert second_headers["X-BUDDY-AUTH-TOKEN"] == "new-token"
    assert first_headers is not second_headers


def test_invalid_response_requires_success_status():
    assert not api_module.invalid_response(Response(200))
    assert not api_module.invalid_response(Response(204))
    assert api_module.invalid_response(Response(199))
    assert api_module.invalid_response(Response(302))
    assert api_module.invalid_response(Response(400))