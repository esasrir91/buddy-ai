# Memory Overview

Memory is what lets an agent stay coherent across turns and personalize itself
to a user over time. Buddy AI separates a few distinct concerns that are often
conflated:

| Concept | What it is | Lifetime |
|---------|-----------|----------|
| **Chat history** | The recent run-by-run conversation replayed into the prompt. | Per session. |
| **Session summaries** | A condensed summary of a session's important points. | Per session, persisted. |
| **User memories** | Durable facts about a *user*, extracted across sessions. | Across sessions, persisted. |

These map onto the relevant `Agent` parameters:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `memory` | `None` | The memory object (`AgentMemory` or the v2 `Memory`). |
| `add_history_to_messages` | `False` | Replay recent runs into the prompt. |
| `num_history_runs` | `3` | How many past runs to replay. |
| `enable_user_memories` | `False` | Create/update durable user memories after each run. |
| `enable_agentic_memory` | `False` | Let the agent manage user memories as a tool. |
| `enable_session_summaries` | `False` | Create/update a session summary after each run. |
| `add_memory_references` | `None` | Add user-memory references to the response. |
| `add_session_summary_references` | `None` | Add summary references to the response. |

!!! note "Reference defaults"
    When left unset, `add_memory_references` defaults to
    `enable_user_memories or enable_agentic_memory`, and
    `add_session_summary_references` defaults to `enable_session_summaries`.

## Two memory implementations

Buddy AI ships two memory layers. The classic `AgentMemory` and a newer v2
`Memory`. The `Agent.memory` parameter accepts either:

```python
from buddy.memory import AgentMemory, Memory, MemoryRow, TeamMemory
# v2:
from buddy.memory.v2.memory import Memory as MemoryV2
```

=== "AgentMemory (v1)"

    `buddy.memory.agent.AgentMemory` holds `runs`, `messages`, an optional
    session `summary`, and a list of user `memories`. It coordinates a
    `MemoryClassifier`, `MemoryManager`, and `MemorySummarizer`, and persists
    user memories to a `MemoryDb`.

    ```python
    from buddy.agent import Agent
    from buddy.memory import AgentMemory
    from buddy.memory.db.sqlite import SqliteMemoryDb

    agent = Agent(
        memory=AgentMemory(db=SqliteMemoryDb(db_file="memory.db")),
        enable_user_memories=True,
        add_history_to_messages=True,
        num_history_runs=5,
    )
    ```

=== "Memory (v2)"

    `buddy.memory.v2.memory.Memory` organizes user memories and session
    summaries per-user and per-session, backed by a pluggable `MemoryDb`
    (SQLite, Postgres, MongoDB, Redis, Firestore).

    ```python
    from buddy.agent import Agent
    from buddy.memory.v2.memory import Memory
    from buddy.memory.v2.db.sqlite import SqliteMemoryDb

    agent = Agent(
        memory=Memory(db=SqliteMemoryDb(db_file="memory.db")),
        enable_user_memories=True,
    )
    ```

## How the pieces fit together

```
        user message
              │
   add_history_to_messages ──► recent runs replayed into the prompt
              │
        agent run (model + tools)
              │
   enable_user_memories ──► MemoryClassifier decides "remember this?"
              │                    └► MemoryManager writes to MemoryDb
   enable_session_summaries ──► MemorySummarizer condenses the session
```

Chat history is in-context and ephemeral; user memories and summaries are
extracted by helper models and persisted so they survive across sessions.

## Where to go next

- [Agent Memory](agent-memory.md) — conversation history and agentic memory.
- [Session Management](sessions.md) — sessions, state, and summaries.
- [User Memories](user-memories.md) — extracting and recalling user facts.
- [Memory Storage](storage.md) — wiring a database backend.
