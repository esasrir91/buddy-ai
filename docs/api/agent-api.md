# Agent API

`Agent` is the core class of Buddy AI — an LLM bound to instructions, tools,
memory, and knowledge. It is defined in `buddy.agent.agent` and re-exported as
`from buddy import Agent`.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="assistant",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant.",
    markdown=True,
)
response = agent.run("What is the capital of France?")
print(response.content)
```

!!! note "Keyword-only constructor"
    Every `Agent(...)` argument is keyword-only. There are no positional
    parameters. The tables below cover the most-used parameters; the constructor
    accepts more (history, reasoning, parser/output models, retries, etc.).

## Core parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `Model` | `None` | The LLM provider instance (e.g. `OpenAIChat`). |
| `name` | `str` | `None` | Human-readable agent name. |
| `instructions` | `str \| list[str] \| Callable` | `None` | Behavioral instructions added to the system prompt. |
| `description` | `str` | `None` | High-level description of the agent's role. |
| `goal` | `str` | `None` | The agent's objective. |
| `role` | `str` | `None` | Role used when the agent is a member of a `Team`. |
| `markdown` | `bool` | `False` | Ask the model to format responses as Markdown. |
| `debug_mode` | `bool` | `False` | Enable verbose debug logging. |

## Tools & knowledge

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `list[Toolkit \| Callable \| Function \| dict]` | `None` | Tools the model may call. |
| `show_tool_calls` | `bool` | `True` | Include tool calls in the response output. |
| `tool_call_limit` | `int` | `None` | Maximum number of tool calls per run. |
| `tool_choice` | `str \| dict` | `None` | Force/disable tool use (`"auto"`, `"none"`, or a function spec). |
| `knowledge` | `AgentKnowledge` | `None` | Knowledge base for retrieval. |
| `search_knowledge` | `bool` | `True` | Give the agent a tool to search its knowledge. |
| `add_references` | `bool` | `False` | Inject retrieved references into the prompt (RAG). |

## Memory & history

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory` | `AgentMemory \| Memory` | `None` | Memory backend. |
| `enable_user_memories` | `bool` | `False` | Create/update user memories at the end of runs. |
| `enable_session_summaries` | `bool` | `False` | Maintain session summaries. |
| `add_history_to_messages` | `bool` | `False` | Include prior turns in the prompt. |
| `num_history_runs` | `int` | `3` | Number of past runs to include when history is on. |
| `storage` | `Storage` | `None` | Session persistence backend. |

## Structured output

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `response_model` | `Type[BaseModel]` | `None` | Pydantic model to parse the response into. |
| `parse_response` | `bool` | `True` | Parse the model output into `response_model`. |
| `use_json_mode` | `bool` | `False` | Request JSON-mode output from the provider. |

When `response_model` is set, `RunResponse.content` is an instance of that model:

```python
from pydantic import BaseModel
from buddy import Agent
from buddy.models.openai import OpenAIChat

class City(BaseModel):
    name: str
    country: str
    population: int

agent = Agent(model=OpenAIChat(id="gpt-4o"), response_model=City)
result = agent.run("Tell me about Tokyo.")
print(result.content.country)  # -> a City instance
```

## Methods

```python
def run(message=None, *, stream=None, stream_intermediate_steps=None,
        user_id=None, session_id=None, session_state=None,
        audio=None, images=None, videos=None, files=None,
        messages=None, retries=None, knowledge_filters=None,
        **kwargs) -> RunResponse | Iterator[RunResponseEvent]
```

| Method | Returns | Description |
|--------|---------|-------------|
| `run(message, ...)` | `RunResponse` | Run synchronously. With `stream=True`, returns an iterator of `RunResponseEvent`. |
| `arun(message, ...)` | `RunResponse` (awaitable) | Async version of `run`. With `stream=True`, returns an async iterator. |
| `print_response(message, ...)` | `None` | Run and pretty-print the response to the console (Rich). |
| `aprint_response(message, ...)` | `None` (awaitable) | Async version of `print_response`. |

!!! warning "There is no `run_stream()`"
    To stream, call `run(message, stream=True)` and iterate the result. A
    standalone `run_stream` method does **not** exist.

## RunResponse

`run()` returns a `RunResponse` (`buddy.run.response.RunResponse`). Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `content` | `Any` | The response text, or a `response_model` instance. |
| `content_type` | `str` | `"str"` by default; the model name for structured output. |
| `thinking` / `reasoning_content` | `str` | Model thinking / reasoning trace, when available. |
| `messages` | `list[Message]` | Full message list for the run. |
| `metrics` | `dict` | Token and timing metrics. |
| `tools` | `list[ToolExecution]` | Tool calls made during the run. |
| `citations` | `Citations` | Source citations, when provided. |
| `model` / `model_provider` | `str` | Resolved model id and provider. |
| `run_id` / `session_id` / `agent_id` | `str` | Identifiers for the run. |
| `status` | `RunStatus` | Run status (e.g. `running`, `paused`, `cancelled`). |

Helpers: `to_dict()`, `to_json()`, `from_dict(data)`, and
`get_content_as_string()` (serializes structured content to a string).
