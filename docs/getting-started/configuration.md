# Configuration

## API Keys

Each model provider reads its credentials from an environment variable. If you
don't pass `api_key=` explicitly, the model looks the key up from the
environment (for example, `OpenAIChat` falls back to `OPENAI_API_KEY`).

```bash
# Common providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...
COHERE_API_KEY=...
DEEPSEEK_API_KEY=...

# AWS Bedrock uses standard AWS credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Buddy Platform (optional monitoring)
BUDDY_API_KEY=your_key_here
```

Store these in a `.env` file (see [`.env.example`](https://github.com/esasrir91/buddy-ai/blob/main/.env.example))
or export them in your shell. You can also pass a key directly:

```python
from buddy.models.openai import OpenAIChat

model = OpenAIChat(id="gpt-4o-mini", api_key="sk-...")
```

## Model Defaults & Generation Settings

Generation parameters such as `temperature` and `max_tokens` are set on the
**model**, not the agent. `OpenAIChat` defaults to `id="gpt-4o"` when no id is
given.

```python
from buddy.models.openai import OpenAIChat

model = OpenAIChat(
    id="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1024,
)
```

## Agent Options

The agent controls behaviour around the model — output formatting, tool-call
visibility, history, and debugging.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="my_agent",
    model=OpenAIChat(id="gpt-4o-mini", temperature=0.7),
    instructions="Be concise.",
    markdown=True,              # render responses as markdown
    show_tool_calls=True,       # print tool calls in the output
    debug_mode=False,           # verbose internal logging when True
    add_history_to_messages=True,
    num_history_runs=3,
)
```

!!! tip "Debugging a run"
    Set `debug_mode=True` to see the assembled system prompt, messages, and tool
    calls for each run — the fastest way to understand what the model received.

## Session Storage

Persist agent sessions between restarts with a `buddy.storage` backend. Each
takes a `table_name`; SQLite stores to a file, PostgreSQL to a database URL.

```python
from buddy.storage.sqlite import SqliteStorage
from buddy.storage.postgres import PostgresStorage

# SQLite (no server required)
storage = SqliteStorage(table_name="sessions", db_file="buddy.db")

# PostgreSQL
storage = PostgresStorage(
    table_name="sessions",
    db_url="postgresql://user:pass@localhost:5432/buddy",
)
```

Pass the backend to the agent via `storage=...`. For long-term user memories,
see [Memory](../core/memory.md).

## Logging

```python
# Standard library logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use the buddy logger helpers
from buddy.utils.log import logger, set_log_level_to_debug
set_log_level_to_debug()
```

## Next Steps

- [Quick Start](quickstart.md) — build and deploy your first agent
- [Agent System](../core/agents.md) — full list of agent parameters
- [Model Providers](../core/models.md) — provider-specific configuration
