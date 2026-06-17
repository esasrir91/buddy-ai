# FastAPI Apps

`FastAPIApp` (`buddy.app.fastapi`) serves one or more agents, teams, or
workflows behind a small FastAPI application.

## Full example

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(
    agent_id="api_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant.",
)

fastapi_app = FastAPIApp(agents=[agent])
app = fastapi_app.get_app()

if __name__ == "__main__":
    fastapi_app.serve(app, host="0.0.0.0", port=7777)
```

## Constructor

```python
FastAPIApp(
    agents=None,      # Optional[List[Agent]]
    teams=None,       # Optional[List[Team]]
    workflows=None,   # Optional[List[Workflow]]
    settings=None,    # Optional[APIAppSettings]
    api_app=None,     # bring your own FastAPI instance
    router=None,      # bring your own APIRouter
    app_id=None,
    name=None,
    description=None,
    version=None,
    monitoring=True,
)
```

At least one of `agents`, `teams`, or `workflows` is required.

## Building and serving the app

`FastAPIApp` does **not** start a server on construction. Two steps:

1. `get_app()` returns a configured `fastapi.FastAPI` instance (CORS, exception
   handlers, and the router are wired up here).
2. `serve(app, *, host="localhost", port=7777, reload=False, workers=None)` runs
   it with `uvicorn`.

```python
fastapi_app = FastAPIApp(agents=[agent])
app = fastapi_app.get_app()
fastapi_app.serve(app, host="0.0.0.0", port=7777)
```

!!! tip "Reload and workers need an import string"
    `serve()` accepts either a `FastAPI` object or an import string. To use
    `reload=True` or multiple `workers`, expose `app` at module scope and pass
    the string form, e.g. `fastapi_app.serve("my_module:app", reload=True)`.

## Endpoints

The app exposes exactly two routes:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/status` | Health check — returns `{"status": "available"}` |
| `POST` | `/runs` | Run an agent, team, or workflow |

### `POST /runs`

The body is sent as **multipart form data** (not JSON). Key fields:

| Field | Where | Notes |
|-------|-------|-------|
| `agent_id` / `team_id` / `workflow_id` | query | Exactly one; selects the target |
| `message` | form | Required for agents and teams |
| `workflow_input` | form | Required for workflows (JSON string allowed) |
| `stream` | form | `true` for an SSE `text/event-stream` |
| `session_id`, `user_id` | form | Optional; a `session_id` is generated if omitted |
| `files` | form | Optional uploads (images, audio, video, or documents) |

```bash
# Health check
curl http://localhost:7777/status

# Run the agent (note: form fields, and agent_id as a query param)
curl -X POST "http://localhost:7777/runs?agent_id=api_agent" \
  -F "message=What is 2 + 2?"

# Stream the response as server-sent events
curl -N -X POST "http://localhost:7777/runs?agent_id=api_agent" \
  -F "message=Tell me a story" -F "stream=true"
```

!!! warning "`agent_id` must match"
    `/runs` looks up the agent whose `agent_id` equals the query value. Set
    `agent_id` on the `Agent` (as above) so it is predictable; otherwise read
    the auto-generated `agent.agent_id` after construction.

## Running with uvicorn directly

Because `get_app()` returns a standard FastAPI object, you can also run it with
the `uvicorn` CLI:

```bash
uvicorn my_module:app --host 0.0.0.0 --port 7777
```

## See also

- [Deployment Overview](overview.md)
- [Docker](docker.md)
