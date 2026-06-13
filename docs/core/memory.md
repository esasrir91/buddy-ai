# Memory

Buddy AI agents can remember conversations across sessions using the Memory system.

## Enable Memory

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory.v2.memory import Memory
from buddy.storage.sqlite import SqliteStorage

agent = Agent(
    name="memory_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    memory=Memory(db=SqliteStorage(table_name="sessions", db_file="memory.db")),
    enable_user_memories=True,
)

agent.print_response("My name is Alice.", user_id="alice", session_id="s1")
agent.print_response("What is my name?",  user_id="alice", session_id="s1")
```

## Storage Backends

| Backend | Class | Extra |
|---------|-------|-------|
| SQLite | `SqliteStorage` | core |
| PostgreSQL | `PostgresStorage` | core |
| Redis | `RedisStorage` | core |
| MongoDB | `MongoDbStorage` | core |
| Firestore | `FirestoreStorage` | `[aws]` |

## Memory v2 Features

- Per-user and per-session isolation
- Automatic summarisation of long contexts
- Memory classification (fact, preference, event)
- Cross-session user memory retrieval

See [Agent Memory](../memory/agent-memory.md) for full API reference.
