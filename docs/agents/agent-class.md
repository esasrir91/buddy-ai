# The Agent Class

`Agent` is the core runnable in Buddy AI. It binds a [model](../core/models.md),
instructions, [tools](../core/tools.md), [memory](../memory/overview.md), and
[knowledge](../knowledge/overview.md) into a single object you call with `run()`
or `print_response()`.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="assistant",
    model=OpenAIChat(id="gpt-4o"),
    instructions="You are a concise, helpful assistant.",
    markdown=True,
)
agent.print_response("What is retrieval-augmented generation?")
```

!!! note "Keyword-only constructor"
    Every `Agent` parameter is keyword-only — there are no positional arguments.
    If no `model` is supplied, Buddy defaults to `OpenAIChat(id="gpt-4o")` and
    requires the `openai` package.

## Parameters by area

### Model & identity

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `Model` | `None` | The LLM backing the agent. Falls back to `OpenAIChat(id="gpt-4o")`. |
| `name` | `str` | `None` | Human-readable agent name. |
| `agent_id` | `str` | `None` | Stable ID; auto-generated (UUID) if unset. |
| `user_id` | `str` | `None` | Identifier for the end user of the session. |
| `introduction` | `str` | `None` | Optional introduction added to the chat. |

### Instructions & system message

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instructions` | `str \| list[str] \| Callable` | `None` | Task instructions injected into the system message. |
| `description` | `str` | `None` | High-level persona/description of the agent. |
| `goal` | `str` | `None` | The objective the agent is working toward. |
| `role` | `str` | `None` | Role used when the agent is a team member. |
| `success_criteria` | `str` | `None` | What "done" looks like. |
| `expected_output` | `str` | `None` | Description of the desired output shape. |
| `additional_context` | `str` | `None` | Extra context appended to the system message. |
| `system_message` | `str \| Callable \| Message` | `None` | Override the generated system message entirely. |
| `markdown` | `bool` | `False` | Ask the model to format output as markdown. |
| `add_datetime_to_instructions` | `bool` | `False` | Append the current datetime. |
| `add_name_to_instructions` | `bool` | `False` | Include the agent name in instructions. |

### Tools & tool control

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `list[Toolkit \| Callable \| Function \| dict]` | `None` | Tools the agent may call. |
| `show_tool_calls` | `bool` | `True` | Print tool calls in console output. |
| `tool_call_limit` | `int` | `None` | Maximum number of tool calls per run. |
| `tool_choice` | `str \| dict` | `None` | Force or restrict tool selection. |
| `tool_hooks` | `list[Callable]` | `None` | Hooks wrapped around tool execution. |

### Memory, knowledge & history

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory` | `AgentMemory \| Memory` | `None` | Persistent memory backend. |
| `enable_agentic_memory` | `bool` | `False` | Let the agent manage its own memories. |
| `enable_user_memories` | `bool` | `False` | Capture user memories across runs. |
| `add_history_to_messages` | `bool` | `False` | Include prior turns in the prompt. |
| `num_history_runs` | `int` | `3` | How many past runs to include. |
| `knowledge` | `AgentKnowledge` | `None` | RAG knowledge base. |
| `search_knowledge` | `bool` | `True` | Allow the agent to search knowledge. |
| `add_references` | `bool` | `False` | Inject retrieved references into the prompt. |
| `knowledge_filters` | `dict` | `None` | Metadata filters for retrieval. |

### Reasoning

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reasoning` | `bool` | `False` | Enable step-by-step reasoning. |
| `reasoning_model` | `Model` | `None` | Separate model used for reasoning. |
| `reasoning_min_steps` | `int` | `1` | Minimum reasoning steps. |
| `reasoning_max_steps` | `int` | `10` | Maximum reasoning steps. |

See [Reasoning](../advanced/reasoning.md) for the standalone reasoning engine.

### Output & run control

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `response_model` | `Type[BaseModel]` | `None` | Parse the response into a Pydantic model. |
| `parse_response` | `bool` | `True` | Whether to parse into `response_model`. |
| `use_json_mode` | `bool` | `False` | Request JSON output from the model. |
| `retries` | `int` | `0` | Retries on failure. |
| `delay_between_retries` | `int` | `1` | Seconds between retries. |
| `exponential_backoff` | `bool` | `False` | Grow the retry delay exponentially. |
| `stream` | `bool` | `None` | Default streaming behavior. |
| `debug_mode` | `bool` | `False` | Verbose debug logging. |
| `monitoring` | `bool` | `False` | Send run data to the Buddy platform. |
| `telemetry` | `bool` | `True` | Anonymous usage telemetry. |

## Run methods

| Method | Returns | Use |
|--------|---------|-----|
| `run(message, ...)` | `RunResponse` | Synchronous run. |
| `run(message, stream=True, ...)` | `Iterator[RunResponseEvent]` | Streaming run. |
| `arun(message, ...)` | awaitable `RunResponse` | Async run. |
| `print_response(message, ...)` | `None` | Run and pretty-print to console. |
| `aprint_response(message, ...)` | `None` | Async print. |

!!! warning "Streaming"
    Streaming is enabled by passing `stream=True` to `run()` — there is no
    separate `run_stream()` method.

```python
for event in agent.run("Explain transformers", stream=True):
    print(event.content or "", end="", flush=True)
```

## Structured output

Pass a Pydantic model as `response_model` and read the parsed object from
`RunResponse.content`:

```python
from pydantic import BaseModel
from buddy import Agent
from buddy.models.openai import OpenAIChat

class Summary(BaseModel):
    title: str
    points: list[str]

agent = Agent(model=OpenAIChat(id="gpt-4o"), response_model=Summary)
result = agent.run("Summarize the theory of relativity.")
print(result.content.title)     # -> str
print(result.content.points)    # -> list[str]
```

!!! tip
    When `response_model` is set, `print_response` disables markdown rendering so
    the structured object is shown verbatim.

See [Agent lifecycle](lifecycle.md) for what happens during a run and
[Configuration](configuration.md) for practical recipes.
