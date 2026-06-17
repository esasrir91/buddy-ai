# Agent Configuration

This page collects practical recipes for configuring an [`Agent`](agent-class.md).
Every option below is a keyword argument to the constructor.

## Instructions vs. description / goal / role

Buddy builds the system message from several complementary fields. Use the one
that matches your intent:

| Field | Purpose |
|-------|---------|
| `instructions` | Concrete, task-level directions ("Answer in two sentences."). |
| `description` | Persona / who the agent is. |
| `goal` | The objective the agent pursues. |
| `role` | The agent's function within a [team](../team/overview.md). |
| `success_criteria` | A definition of done. |

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="A meticulous financial analyst.",
    goal="Help the user understand quarterly earnings.",
    instructions=[
        "Cite figures from the provided context only.",
        "Flag any assumptions explicitly.",
    ],
    success_criteria="The user can explain the result in one sentence.",
)
```

!!! tip "Lists of instructions"
    `instructions` accepts a `str`, a `list[str]`, or a callable. Lists render as
    separate bullet points, which keeps long guidance readable.

## Conversation history

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    add_history_to_messages=True,
    num_history_runs=5,
)
```

- `add_history_to_messages` includes prior turns in each prompt.
- `num_history_runs` (default `3`) controls how many past runs are included.
- `num_history_responses` is accepted for backwards compatibility and, when set,
  overrides `num_history_runs`.

## Memory & user memories

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    enable_user_memories=True,       # capture durable facts about the user
    enable_session_summaries=True,   # summarize sessions
)
```

When `enable_user_memories` or `enable_agentic_memory` is on, Buddy auto-enables
memory references (`add_memory_references`) unless you set it explicitly. See
[Agent memory](../memory/agent-memory.md) for backends.

## Output formatting & structured output

```python
from pydantic import BaseModel

class Ticket(BaseModel):
    title: str
    priority: int

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,                # human-readable formatting
    response_model=Ticket,       # OR parse into a Pydantic model
    use_json_mode=True,          # request JSON from the model
)
```

!!! note
    `markdown=True` and `response_model` are mutually exclusive in practice:
    setting a `response_model` turns markdown rendering off so the parsed object
    is returned cleanly.

## Retries & resilience

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    retries=3,
    delay_between_retries=2,
    exponential_backoff=True,
)
```

With `exponential_backoff=True`, the delay grows after each failed attempt
starting from `delay_between_retries` seconds.

## Tool behavior

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[...],
    show_tool_calls=True,   # default; print each tool call
    tool_call_limit=5,      # cap calls per run
)
```

See [Tools](../core/tools.md) for building toolkits and functions.

## Prompt caching

Set `cache_prompt=True` to activate provider-native prompt caching. Buddy handles all the
plumbing — no prompt edits required.

```python
from buddy.models.anthropic import Claude
from buddy.models.openai import OpenAIChat

# Anthropic: cache_control injected on system + tools + history
agent = Agent(
    model=Claude(id="claude-opus-4-5"),
    cache_prompt=True,
    add_history_to_messages=True,
)

# OpenAI: server-side automatic caching; cache metrics surfaced in RunResponse
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    cache_prompt=True,
)
```

After a run, inspect cache token counts:

```python
response = agent.run("...")
print(response.metrics.get("cached_tokens"))       # tokens served from cache
print(response.metrics.get("cache_write_tokens"))  # tokens written to cache
```

!!! tip
    See the full [Prompt Caching guide](../advanced/prompt-caching.md) for fine-grained
    control with `PromptCacheConfig`, 1-hour TTL, and per-provider details.

## Debugging & monitoring

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    debug_mode=True,    # verbose logs (debug_level 1 or 2)
    monitoring=True,    # send run data to the Buddy platform
    telemetry=True,     # anonymous usage stats (on by default)
)
```

!!! tip "Environment overrides"
    `debug_mode` also activates when `BUDDY_DEBUG=true`. Monitoring and telemetry
    can be toggled with `BUDDY_MONITOR` and `BUDDY_TELEMETRY` environment
    variables, which take precedence over the constructor values.

## Detecting optional features

Some capabilities are gated behind optional dependencies. Check availability at
runtime:

```python
from buddy import get_available_features, check_feature

print(get_available_features())     # e.g. ['reasoning', 'planning', 'core']
print(check_feature("multimodal"))  # True / False
```
