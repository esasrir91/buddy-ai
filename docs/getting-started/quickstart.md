# Quick Start

Get a Buddy AI agent running in under 2 minutes.

## 1. Install

```bash
pip install buddy-ai
export OPENAI_API_KEY=sk-...
```

## 2. Create your first agent

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="assistant",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant.",
    markdown=True,
)

agent.print_response("What is the capital of Japan?")
```

## 3. Add tools

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.tavily import TavilyTools

agent = Agent(
    name="researcher",
    model=OpenAIChat(id="gpt-4o"),
    tools=[TavilyTools()],
    show_tool_calls=True,
)

agent.print_response("What are the latest AI releases in 2026?")
```

## 4. Use multiple providers

```python
from buddy.models.anthropic import Claude

agent = Agent(
    name="claude_agent",
    model=Claude(id="claude-opus-4-5"),
    instructions="You are an analytical assistant.",
)
```

## 5. Deploy as an API

`FastAPIApp` wraps one or more agents in a FastAPI application. Build the app
with `get_app()`, then pass it to `serve()` (the `app` argument is required).

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(name="api_agent", model=OpenAIChat(id="gpt-4o-mini"))

fastapi_app = FastAPIApp(agents=[agent])
app = fastapi_app.get_app()

if __name__ == "__main__":
    fastapi_app.serve(app, host="localhost", port=7777)  # http://localhost:7777
```

!!! tip "Auto-reload during development"
    `serve()` calls `uvicorn.run()` under the hood. To enable `reload=True` (or
    `workers=N`), save the code to a module and pass an import string instead of
    the app instance, e.g. `fastapi_app.serve("main:app", reload=True)`.

## Next Steps

- [Configuration](configuration.md) — API keys, defaults, storage
- [Examples](examples.md) — More runnable scripts
- [Agent System](../core/agents.md) — Deep dive into agents
- [Model Providers](../models/overview.md) — All 30+ supported models
