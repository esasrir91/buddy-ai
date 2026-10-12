from httpx import Response

import buddy.api.evals as evals_module
from buddy.api.schemas.evals import EvalRunCreate, EvalType


class _Client:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def post(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self.response


class _AsyncClient(_Client):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def post(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self.response


def _eval_run():
    return EvalRunCreate(
        run_id="run-1",
        eval_type=EvalType.ACCURACY,
        eval_data={"score": 0.9},
        model_id="model-1",
    )


def test_create_eval_run_skips_when_api_disabled(monkeypatch):
    client = _Client(Response(201))
    monkeypatch.setattr(evals_module.api, "AuthenticatedClient", lambda: client)
    monkeypatch.setattr(evals_module.BUDDY_cli_settings, "api_enabled", False)

    evals_module.create_eval_run(_eval_run())

    assert client.calls == []


def test_create_eval_run_posts_payload(monkeypatch):
    client = _Client(Response(201))
    monkeypatch.setattr(evals_module.api, "AuthenticatedClient", lambda: client)
    monkeypatch.setattr(evals_module.BUDDY_cli_settings, "api_enabled", True)

    evals_module.create_eval_run(_eval_run())

    assert client.calls == [
        (
            "/v2/eval-runs",
            {
                "json": {
                    "eval_run": {
                        "run_id": "run-1",
                        "eval_type": "accuracy",
                        "eval_data": {"score": 0.9},
                        "model_id": "model-1",
                    }
                }
            },
        )
    ]


def test_create_eval_run_logs_http_errors(monkeypatch):
    client = _Client(Response(500))
    messages = []
    monkeypatch.setattr(evals_module.api, "AuthenticatedClient", lambda: client)
    monkeypatch.setattr(evals_module.BUDDY_cli_settings, "api_enabled", True)
    monkeypatch.setattr(evals_module, "log_debug", messages.append)

    evals_module.create_eval_run(_eval_run())

    assert messages[-1].startswith("Could not create evaluation run:")


async def test_async_create_eval_run_skips_when_api_disabled(monkeypatch):
    client = _AsyncClient(Response(201))
    monkeypatch.setattr(evals_module.api, "AuthenticatedAsyncClient", lambda: client)
    monkeypatch.setattr(evals_module.BUDDY_cli_settings, "api_enabled", False)

    await evals_module.async_create_eval_run(_eval_run())

    assert client.calls == []


async def test_async_create_eval_run_posts_payload(monkeypatch):
    client = _AsyncClient(Response(201))
    monkeypatch.setattr(evals_module.api, "AuthenticatedAsyncClient", lambda: client)
    monkeypatch.setattr(evals_module.BUDDY_cli_settings, "api_enabled", True)

    await evals_module.async_create_eval_run(_eval_run())

    assert client.calls[0][0] == "/v2/eval-runs"
    assert client.calls[0][1]["json"]["eval_run"]["eval_type"] == "accuracy"


async def test_async_create_eval_run_logs_http_errors(monkeypatch):
    client = _AsyncClient(Response(500))
    messages = []
    monkeypatch.setattr(evals_module.api, "AuthenticatedAsyncClient", lambda: client)
    monkeypatch.setattr(evals_module.BUDDY_cli_settings, "api_enabled", True)
    monkeypatch.setattr(evals_module, "log_debug", messages.append)

    await evals_module.async_create_eval_run(_eval_run())

    assert messages[-1].startswith("Could not create evaluation run:")