# Deployment Overview

Buddy AI agents can be deployed in multiple ways.

## FastAPI REST API

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(name="api_agent", model=OpenAIChat(id="gpt-4o-mini"))
app = FastAPIApp(agents=[agent], port=7777)
app.serve()
```

Key endpoints:
- `GET /status` — health check
- `POST /runs` — run agent with a message
- `GET /runs/{run_id}` — get run result

## Playground UI

```python
from buddy.app.playground import Playground

playground = Playground(agents=[agent])
playground.serve()
# Open https://app.buddy-ai.com/playground?endpoint=localhost:7777
```

## Docker

See [Docker Deployment](docker.md) for the full guide.

Quick start:

```bash
docker-compose up -d
```

This starts the agent API on port 7777, PostgreSQL on 5432, Redis on 6379, and Qdrant on 6333.

## Slack Bot

```python
from buddy.app.slack import SlackApp

slack = SlackApp(agent=agent, bot_token="xoxb-...")
slack.serve()
```

## Discord Bot

```python
from buddy.app.discord import DiscordApp

discord = DiscordApp(agent=agent, token="...")
discord.serve()
```

## See Also

- [Docker](docker.md)
- [FastAPI Apps](fastapi.md)
- [Cloud Platforms](cloud.md)
