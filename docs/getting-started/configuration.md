# Configuration

## API Keys

Set provider keys as environment variables or in a `.env` file:

```bash
# Core
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Buddy Platform
BUDDY_API_KEY=your_key_here
```

See [`.env.example`](https://github.com/esasrir91/buddy-ai/blob/main/.env.example) for the full list.

## Agent Defaults

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="my_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="Be concise.",
    markdown=True,
    debug_mode=False,
    show_tool_calls=True,
    temperature=0.7,
    max_tokens=1024,
)
```

## Storage Backends

```python
from buddy.storage.sqlite import SqliteStorage
from buddy.storage.postgres import PostgresStorage

# SQLite (default, no setup required)
storage = SqliteStorage(table_name="sessions", db_file="buddy.db")

# PostgreSQL
storage = PostgresStorage(
    table_name="sessions",
    db_url="postgresql://user:pass@localhost:5432/buddy"
)
```

## Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use the buddy logger
from buddy.utils.log import logger, set_log_level_to_debug
set_log_level_to_debug()
```
