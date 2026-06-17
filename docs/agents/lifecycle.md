# Agent Run Lifecycle

This page traces what happens between calling `agent.run(...)` and receiving a
[`RunResponse`](#the-runresponse-object). Understanding the sequence helps when
debugging tools, memory, or streaming.

## Construction

Creating an `Agent` only stores configuration — no network calls happen. Fields
such as `run_id`, `run_response`, and `session_metrics` start as `None` and are
populated per run.

## `initialize_agent()`

The first thing `run()` does (after resolving the session) is call
`initialize_agent()`, which applies defaults and prepares the agent:

```text
initialize_agent()
  ├─ set_defaults()        # derive memory/summary reference flags, history runs
  ├─ set_default_model()   # fall back to OpenAIChat(id="gpt-4o") if no model
  ├─ set_storage_mode()    # mark storage as "agent" mode
  ├─ set_debug()           # honor debug_mode / BUDDY_DEBUG
  └─ set_agent_id()        # assign a UUID if agent_id is unset
```

!!! note
    `initialize_agent()` is idempotent and safe to run on every call — it simply
    re-applies defaults.

## The run sequence

A synchronous, non-streaming run proceeds roughly as follows:

1. **Session resolution** — `session_id` and `user_id` are established and any
   existing session is read from `storage`.
2. **Knowledge filter setup** — if `knowledge_filters` or
   `enable_agentic_knowledge_filters` are set, valid filters are initialized.
3. **Context resolution** — if `context` is provided, it is resolved into the run.
4. **Message building** — the system message (from `instructions`,
   `description`, `goal`, history, references, etc.) and the user message are
   assembled into `RunMessages`.
5. **Model call** — the model is invoked with the assembled messages and any
   tool schemas.
6. **Tool calls** — if the model requests tools, Buddy executes them (subject to
   `tool_call_limit` and `tool_hooks`) and feeds results back to the model, which
   may loop until it produces a final answer.
7. **Response assembly** — the final content is collected into a `RunResponse`,
   `metrics` are aggregated from the messages, and `session_metrics` are updated.
8. **Persistence** — the session (including metrics) is written back to storage.

```python
response = agent.run("Find the capital of France and explain why it matters.")
print(response.content)
print(response.metrics)        # aggregated per-message metrics
print(agent.session_metrics)   # cumulative SessionMetrics for the session
```

## Async and streaming

- `arun(...)` performs the same sequence asynchronously and returns a
  `RunResponse`.
- `run(..., stream=True)` returns an `Iterator[RunResponseEvent]`; each event
  carries incremental `content`. Intermediate steps (tool calls, reasoning) can
  be surfaced with `stream_intermediate_steps=True`.

```python
for event in agent.run("Summarize the news", stream=True,
                       stream_intermediate_steps=True):
    if event.content:
        print(event.content, end="", flush=True)
```

## The RunResponse object

`run()` and `arun()` return a `RunResponse` (`buddy.run.response.RunResponse`).
Key attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `content` | `Any` | Final answer — a string, or a `response_model` instance. |
| `content_type` | `str` | Type tag for `content` (e.g. `"str"`). |
| `thinking` / `reasoning_content` | `str` | Reasoning traces, when present. |
| `messages` | `list[Message]` | Full message list for the run. |
| `metrics` | `dict` | Aggregated token/time metrics (see [Metrics](metrics.md)). |
| `model` / `model_provider` | `str` | Which model produced the response. |
| `tools` | `list[ToolExecution]` | Tools executed during the run. |
| `run_id` / `agent_id` / `session_id` | `str` | Identifiers for this run. |
| `citations` | `Citations` | Source citations, when available. |
| `status` | `RunStatus` | Run status (e.g. running, paused, cancelled). |
| `created_at` | `int` | Unix timestamp of creation. |

Helper members include `to_dict()` and the properties `is_paused`,
`is_cancelled`, `tools_requiring_confirmation`,
`tools_requiring_user_input`, and `tools_awaiting_external_execution`.

```python
response = agent.run("What changed in the latest release?")
if response.tools_requiring_confirmation:
    ...  # pause for human approval before continuing
```

!!! tip
    The agent also caches the latest run on `agent.run_response`, so you can
    inspect it after `print_response()` even though that method returns `None`.
