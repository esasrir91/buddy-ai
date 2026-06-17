# Integrations

How to deploy Buddy agents and connect them to model providers, vector stores,
and chat platforms.

## Deploy as a REST API (FastAPI)

`FastAPIApp` wraps agents, teams, and workflows in a FastAPI application. Build
the app with `get_app()`, then `serve()` it.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(
    name="api_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant.",
    markdown=True,
)

app = FastAPIApp(agents=[agent])
fastapi_app = app.get_app()  # returns a FastAPI instance

if __name__ == "__main__":
    app.serve(fastapi_app, host="0.0.0.0", port=7777)
```

`FastAPIApp(agents=..., teams=..., workflows=...)` accepts any combination (at
least one is required). `serve()` is a method on the app and **requires** the
FastAPI app object as its first argument.

| `serve()` parameter | Default | Description |
|---------------------|---------|-------------|
| `app` | — (required) | The FastAPI app (from `get_app()`) or an import string. |
| `host` | `"localhost"` | Bind address. |
| `port` | `7777` | Port. |
| `reload` | `False` | Auto-reload (dev). |
| `workers` | `None` | Number of worker processes. |

The generated API exposes `GET /status` and `POST /runs`. Select the target with
the `agent_id` (or `team_id` / `workflow_id`) query parameter:

```bash
curl -X POST "http://localhost:7777/runs?agent_id=<AGENT_ID>" \
  -F "message=What is 2 + 2?"
```

!!! warning "Common deployment pitfalls"
    `FastAPIApp` has no `port` argument in its constructor — set the port on
    `serve()`. And `serve()` is not a zero-argument call: pass the app from
    `get_app()`.

## Chat platforms

Buddy ships adapters for several messaging platforms under `buddy.app.*`:

| Platform | Import | Class |
|----------|--------|-------|
| Slack | `from buddy.app.slack import SlackAPI` | `SlackAPI` |
| WhatsApp | `from buddy.app.whatsapp import WhatsappAPI` | `WhatsappAPI` |
| Discord | `from buddy.app.discord import DiscordClient` | `DiscordClient` |

Each wraps an agent or team behind that platform's webhook/client. Configure the
platform's credentials (tokens, signing secrets) via environment variables as
required by the provider's SDK.

## Model providers

Providers live under `buddy.models.*`. Install the matching extra and set the
provider's API key.

| Provider | Import | Extra |
|----------|--------|-------|
| OpenAI | `from buddy.models.openai import OpenAIChat` | `buddy-ai[openai]` |
| Anthropic | `from buddy.models.anthropic import Claude` | `buddy-ai[anthropic]` |
| Google | `from buddy.models.google import Gemini` | `buddy-ai[google]` |
| AWS Bedrock | `from buddy.models.aws import AwsBedrock` | `buddy-ai[aws]` |
| Groq | `from buddy.models.groq import Groq` | — |
| Ollama (local) | `from buddy.models.ollama import Ollama` | — |

Buddy includes 30+ provider packages under `buddy.models.*` — see
[Model Providers](../models/overview.md) for the full list.

```python
from buddy import Agent
from buddy.models.ollama import Ollama

# Run fully locally with Ollama — no API key required
agent = Agent(model=Ollama(id="llama3"))
agent.print_response("Hello from a local model!")
```

## Vector databases

Knowledge bases can be backed by any vector store under `buddy.vectordb.*`, for
example `ChromaDb`:

```python
from buddy.knowledge.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

kb = PDFKnowledgeBase(
    path="docs/",
    vector_db=ChromaDb(collection="docs", persistent_client=True, path="tmp/chromadb"),
)
kb.load()
```

See the [Knowledge API](../api/knowledge-api.md) for the full knowledge-base and
vector-DB reference.

## PULSE — virtual employee

For the higher-level "virtual employee" integration (onboarding, knowledge
transfer, professional memory), see [PULSE — Virtual Employee](../advanced/pulse.md).
Availability can be checked at runtime with `check_feature("pulse")`.
