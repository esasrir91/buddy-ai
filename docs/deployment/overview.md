# Deployment Overview

Buddy agents, teams, and workflows can be served in several ways. They all wrap
the same agent objects — pick the surface that fits your audience.

| Option | Module / class | Best for |
|--------|----------------|----------|
| **FastAPI REST API** | `buddy.app.fastapi.FastAPIApp` | Programmatic access from any client |
| **Playground UI** | `buddy.app.playground.Playground` / `buddy.playground.serve_playground_app` | Interactive chat & debugging |
| **Slack** | `buddy.app.slack.SlackAPI` | Slack workspaces |
| **WhatsApp** | `buddy.app.whatsapp.WhatsappAPI` | WhatsApp Business |
| **Discord** | `buddy.app.discord.DiscordClient` | Discord servers |
| **AG-UI** | `buddy.app.agui.AGUIApp` | AG-UI compatible front-ends |
| **Docker** | [`Dockerfile`](docker.md) / `docker-compose.yml` | Containerized runs |
| **Kubernetes** | [manifests](kubernetes.md) | Scaled, orchestrated runs |
| **Cloud** | [platforms](cloud.md) | Render, Fly.io, Cloud Run, ECS, … |

## FastAPI REST API

`FastAPIApp` builds a FastAPI app from your agents/teams/workflows. The
constructor takes the objects; `host`/`port` are arguments to `serve()`:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(agent_id="api_agent", model=OpenAIChat(id="gpt-4o-mini"))

fastapi_app = FastAPIApp(agents=[agent])
app = fastapi_app.get_app()

if __name__ == "__main__":
    fastapi_app.serve(app, host="0.0.0.0", port=7777)
```

It exposes two routes — `GET /status` and `POST /runs`. See
[FastAPI Apps](fastapi.md) for the full request/response shape.

## Playground UI

```python
from buddy.app.playground import Playground

playground = Playground(agents=[agent])
app = playground.get_app()
playground.serve(app, host="localhost", port=7777)
```

The console prints a Playground URL pointing at your local endpoint. A
convenience helper is also available:

```python
from buddy.playground import serve_playground_app

# pass an import string so reload/workers work
serve_playground_app("my_module:app", host="localhost", port=7777)
```

## Chat platforms

Slack, WhatsApp, and AG-UI apps extend the same base and take an `agent` or
`team`:

```python
from buddy.app.slack import SlackAPI

slack_app = SlackAPI(agent=agent)
app = slack_app.get_app()
slack_app.serve(app, port=7777)
```

Discord uses a dedicated client:

```python
from buddy.app.discord import DiscordClient

DiscordClient(agent=agent)
```

!!! tip "Set a stable `agent_id`"
    `POST /runs` selects an agent by `agent_id`. If you don't pass one, a random
    UUID is assigned at init. Set `agent_id="..."` explicitly so clients can
    address it reliably.

## See also

- [FastAPI Apps](fastapi.md)
- [Docker](docker.md) · [Kubernetes](kubernetes.md) · [Cloud Platforms](cloud.md)
