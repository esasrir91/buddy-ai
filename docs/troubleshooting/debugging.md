# Debugging

Tools for understanding what an agent actually did — from verbose logs to
inspecting the structured response.

## Enable debug mode

Set `debug_mode=True` to switch logging to the debug level. This prints the
resolved prompt, model calls, tool invocations, and timing.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    debug_mode=True,
    debug_level=2,   # 1 (default) or 2 for more detail
)
agent.print_response("What is 2 + 2?")
```

You can also enable debug logging without touching code via an environment
variable:

```bash
export BUDDY_DEBUG=true
```

!!! note "Debug levels"
    `debug_level` accepts `1` (default) or `2`. Level `2` adds more granular
    internal logging.

## Show tool calls

When tools are attached, `show_tool_calls=True` (the default) surfaces each tool
invocation in the output so you can see what the model called and with which
arguments.

```python
from buddy.tools.python import PythonTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[PythonTools()],
    show_tool_calls=True,
)
```

## Inspect the RunResponse

`run()` returns a `RunResponse` you can examine programmatically. The richest
view is `to_dict()` / `to_json()`:

```python
response = agent.run("Summarize the news.")

print(response.content)        # the answer
print(response.metrics)        # token + timing metrics
print(response.model, response.model_provider)
for tool in response.tools or []:
    print(tool)                # each ToolExecution
for msg in response.messages or []:
    print(msg.role, msg.content)

print(response.to_json())      # full serialized view
```

| Field | Use when debugging |
|-------|--------------------|
| `content` | The final answer (or structured object). |
| `messages` | The exact prompt/response message sequence. |
| `tools` | Which tools ran, with inputs and outputs. |
| `metrics` | Token usage and latency. |
| `thinking` / `reasoning_content` | The reasoning trace (if enabled). |
| `status` | Run status (`running`, `paused`, `cancelled`, ...). |

## Check installed features

Optional capabilities import lazily. If something behaves as if it is missing,
confirm it is actually available:

```python
from buddy import get_version_info, get_available_features, check_feature

print(get_version_info())         # version + feature map
print(get_available_features())   # list of enabled features
print(check_feature("reasoning")) # True / False
```

The feature keys are `planning`, `multimodal`, `evolution`, `reasoning`,
`personality`, `security`, `pulse`, and `core`.

## Debugging streamed runs

When streaming, iterate the events and print each delta — this makes it obvious
where output stops if a run stalls:

```python
for event in agent.run("Explain TCP.", stream=True, stream_intermediate_steps=True):
    print(type(event).__name__, getattr(event, "content", None))
```

`stream_intermediate_steps=True` also emits tool-call and reasoning events, not
just content deltas.

!!! tip "Reproduce minimally"
    When filing a bug, capture `get_version_info()` and a `response.to_json()`
    from a minimal script — it pinpoints the version, enabled features, and the
    exact model interaction.
