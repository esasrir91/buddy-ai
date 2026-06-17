# Memory

Buddy AI agents support two complementary kinds of memory:

- **Chat history** — recent turns of the current conversation, replayed into the
  prompt so the agent has short-term context.
- **User memories** — durable facts about a user, stored in a database and
  recalled across sessions.

## Chat History (Short-Term)

The simplest form of memory needs no database. Set `add_history_to_messages`
and control how many prior runs are included with `num_history_runs`.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="chat_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    add_history_to_messages=True,
    num_history_runs=3,   # replay the last 3 exchanges
)

agent.print_response("My name is Alice.")
agent.print_response("What is my name?")   # remembers within the session
```

!!! note "Reading chat history as a tool"
    Set `read_chat_history=True` to also give the agent a tool it can call to
    look back through the full conversation history on demand.

## User Memories (Long-Term)

Long-term memories persist to a `MemoryDb` and are keyed by `user_id`, so they
survive across sessions. Attach a `Memory` object and enable
`enable_user_memories` on the agent.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory.v2.memory import Memory
from buddy.memory.v2.db.sqlite import SqliteMemoryDb

agent = Agent(
    name="memory_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    memory=Memory(db=SqliteMemoryDb(table_name="memories", db_file="memory.db")),
    enable_user_memories=True,
)

agent.print_response("My name is Alice and I love hiking.", user_id="alice", session_id="s1")
agent.print_response("What do you know about me?",          user_id="alice", session_id="s2")
```

When `enable_user_memories=True`, the agent extracts salient facts after each
run and stores them; on later runs they are retrieved and added to the context.
Use `enable_agentic_memory=True` to instead let the agent decide when to create,
update, or delete memories itself.

### MemoryDb Backends

`Memory` stores user memories through a `MemoryDb` from `buddy.memory.v2.db`:

| Backend | Class | Import |
|---------|-------|--------|
| SQLite | `SqliteMemoryDb` | `buddy.memory.v2.db.sqlite` |
| PostgreSQL | `PostgresMemoryDb` | `buddy.memory.v2.db.postgres` |
| MongoDB | `MongoMemoryDb` | `buddy.memory.v2.db.mongodb` |
| Redis | `RedisMemoryDb` | `buddy.memory.v2.db.redis` |
| Firestore | `FirestoreMemoryDb` | `buddy.memory.v2.db.firestore` |

## Classic `AgentMemory`

The original `AgentMemory` (`buddy.memory.agent`) is still available and is also
re-exported from the top level (`from buddy import AgentMemory`). It exposes
flags such as `create_user_memories`, `update_user_memories_after_run`, and
`create_session_summary`, and accepts a `MemoryDb` via its `db` field.

```python
from buddy import Agent, AgentMemory
from buddy.models.openai import OpenAIChat
from buddy.memory.v2.db.sqlite import SqliteMemoryDb

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    memory=AgentMemory(
        db=SqliteMemoryDb(table_name="memories", db_file="memory.db"),
        create_user_memories=True,
        create_session_summary=True,
    ),
)
```

## Session Storage

Chat history and run state can be persisted between process restarts by giving
the agent `storage` (a `buddy.storage` backend such as `SqliteStorage` or
`PostgresStorage`). See [Configuration](../getting-started/configuration.md) for
storage setup.

## See Also

- [Agent System](agents.md) — agent parameters in context
- [Knowledge](knowledge.md) — retrieval-augmented context
