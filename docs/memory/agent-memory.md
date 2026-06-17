# Agent Memory

`AgentMemory` (`buddy.memory.agent.AgentMemory`) is the classic memory object an
agent uses to track a conversation and, optionally, build durable user memories.
This page covers the two most common needs: replaying **conversation history**
and enabling **agentic memory**.

```python
from buddy.memory import AgentMemory
```

## What `AgentMemory` holds

An `AgentMemory` instance keeps:

- `runs` — a list of `AgentRun` objects (each a message, the messages sent, and
  the `RunResponse`).
- `messages` — the running list of `Message` objects sent to the model.
- `summary` — an optional `SessionSummary` for the session.
- `memories` — an optional list of `Memory` (durable user facts).
- `db` — an optional `MemoryDb` for persisting user memories.

It also references the helper components it drives: a `MemoryClassifier`,
`MemoryManager`, and `MemorySummarizer`.

## Conversation history

By default the agent does not replay past turns. Set
`add_history_to_messages=True` to inject recent runs into the prompt, and
`num_history_runs` to control how many:

```python
from buddy.agent import Agent
from buddy.memory import AgentMemory

agent = Agent(
    memory=AgentMemory(),
    add_history_to_messages=True,
    num_history_runs=5,
)

agent.print_response("My name is Dana.")
agent.print_response("What's my name?")  # the prior run is in context
```

Under the hood, `AgentMemory.get_messages_from_last_n_runs(last_n=...)` collects
messages from the most recent runs, skipping messages already tagged as history
so they are not duplicated across turns.

!!! note "`num_history_responses` is deprecated"
    Older code used `num_history_responses`; it still works but is superseded by
    `num_history_runs`. If set, the agent copies its value into
    `num_history_runs`.

### Reading history as a tool

Separately from prompt replay, you can give the model a tool to *query* its
history on demand:

```python
agent = Agent(memory=AgentMemory(), read_chat_history=True)
```

This adds a tool the model can call to read the chat history; pair it with
`read_tool_call_history=True` to also expose past tool calls.

## Agentic memory

`enable_agentic_memory=True` lets the agent actively manage the user's memories
as part of its reasoning — deciding what to add, update, or remove — rather than
only extracting memories passively at the end of a run:

```python
from buddy.agent import Agent
from buddy.memory import AgentMemory
from buddy.memory.db.sqlite import SqliteMemoryDb

agent = Agent(
    memory=AgentMemory(db=SqliteMemoryDb(db_file="memory.db")),
    enable_agentic_memory=True,
    user_id="dana@example.com",
)
```

Enabling it also turns on memory references in the response by default (see
[Memory Overview](overview.md)). For passive extraction instead, use
`enable_user_memories=True` — both paths require a `db` to persist anything; see
[User Memories](user-memories.md).

## Inspecting memory programmatically

`AgentMemory` exposes helpers useful for debugging and analytics:

| Method | Returns |
|--------|---------|
| `get_messages()` | All messages as dictionaries. |
| `get_messages_from_last_n_runs(last_n)` | Messages from the last *n* runs. |
| `get_message_pairs()` | `(user, assistant)` tuples per run. |
| `get_tool_calls(num_calls)` | Recent tool calls from the messages. |
| `load_user_memories()` | Reload user memories from the `db`. |
| `clear()` | Reset runs, messages, summary, and memories. |

```python
for user_msg, assistant_msg in agent.memory.get_message_pairs():
    print(user_msg.get_content_string(), "->", assistant_msg.get_content_string())
```

!!! tip "Memory updates need a database"
    `update_memory()` and `update_summary()` only persist when a `MemoryDb` is
    attached. Without one, the agent logs a warning and skips the write.

See [Session Management](sessions.md) for session summaries and state, and
[Memory Storage](storage.md) for configuring the backend.
