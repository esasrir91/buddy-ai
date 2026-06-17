# User Memories

User memories are durable facts about a *user* — their name, preferences, goals,
constraints — extracted from conversations and persisted so they carry across
sessions. They are keyed by `user_id`, not by session.

## Enabling user memories

Set `enable_user_memories=True` and give the agent a `user_id` and a memory
database:

```python
from buddy.agent import Agent
from buddy.memory import AgentMemory
from buddy.memory.db.sqlite import SqliteMemoryDb

agent = Agent(
    memory=AgentMemory(db=SqliteMemoryDb(db_file="memory.db")),
    enable_user_memories=True,
    user_id="dana@example.com",
)

agent.print_response("I'm vegetarian and I live in Berlin.")
# later, even in a new session with the same user_id:
agent.print_response("Suggest a restaurant for dinner.")
```

When enabled, `add_memory_references` defaults to `True`, so recalled memories
are referenced in the agent's responses.

!!! warning "A database is required"
    Memories are only stored when a `MemoryDb` is attached. Without one, the
    update step logs a warning and returns
    `"Please provide a db to store memories"`. See [Memory Storage](storage.md).

## How memories are created

After a run, Buddy AI decides whether the user's message is worth remembering
using a two-stage pipeline.

### 1. Classification

`MemoryClassifier` (`buddy.memory.classifier`) asks a model a yes/no question:
does this message contain information worth remembering — personal facts, life
events, preferences, goals? It is given the existing memories so it can avoid
duplicates and respond `"no"` when nothing new is present.

```python
should_store = agent.memory.should_update_memory("I'm vegetarian")  # -> True/False
```

### 2. Management

If the classifier says yes, `MemoryManager` (`buddy.memory.manager`) is invoked.
It exposes memory operations to the model as tools — `add_memory`,
`update_memory`, `delete_memory`, and `clear_memory` — and writes the result to
the `MemoryDb` for the given `user_id`.

```python
# Force-create a memory, bypassing the classifier:
agent.memory.update_memory("Prefers vegetarian food", force=True)
```

Each stored item is a `Memory` (`buddy.memory.memory.Memory`):

```python
class Memory(BaseModel):
    memory: str
    id: Optional[str] = None
    topic: Optional[str] = None
    input: Optional[str] = None
```

## How memories are recalled

`AgentMemory.load_user_memories()` reads memories back from the database for the
configured `user_id`. The retrieval strategy is controlled by the `retrieval`
field, a `MemoryRetrieval` enum:

| Strategy | Behaviour |
|----------|-----------|
| `last_n` | Most recent memories (default). |
| `first_n` | Oldest memories first. |
| `semantic` | Reserved — raises `NotImplementedError` (not yet supported). |

`num_memories` caps how many are loaded.

```python
from buddy.memory import AgentMemory
from buddy.memory.memory import MemoryRetrieval
from buddy.memory.db.sqlite import SqliteMemoryDb

memory = AgentMemory(
    db=SqliteMemoryDb(db_file="memory.db"),
    user_id="dana@example.com",
    retrieval=MemoryRetrieval.last_n,
    num_memories=20,
)
```

## Agentic vs passive memory

- `enable_user_memories=True` — passive: memories are extracted after runs via
  the classifier/manager.
- `enable_agentic_memory=True` — agentic: the agent manages memories as part of
  its own reasoning (see [Agent Memory](agent-memory.md)).

!!! tip "Custom models for memory"
    Both `MemoryClassifier` and `MemoryManager` accept a `model`. If none is
    given they default to `OpenAIChat(id="gpt-4o")`; pass your own to control
    cost and provider.

See [Memory Storage](storage.md) to choose a backend, and
[Memory Overview](overview.md) for how this fits the broader picture.
