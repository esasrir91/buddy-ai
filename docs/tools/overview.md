# Tool System

Tools let an agent move beyond text generation and *act* — search the web, run
code, query a database, call an API. A tool is just a callable whose signature
and docstring are exposed to the model as a JSON schema; the model decides when
to call it, the agent runs it, and the result is fed back into the conversation.

Everything in this section is built on three primitives exported from
`buddy.tools`:

```python
from buddy.tools import Toolkit, Function, FunctionCall, tool, TokenManager
```

| Primitive | Role |
|-----------|------|
| `Function` | Wraps a callable and stores its name, description, and parameter JSON schema. |
| `FunctionCall` | A single invocation of a `Function` with arguments; runs hooks and the entrypoint. |
| `Toolkit` | Groups related callables (e.g. all calculator operations) into one registerable unit. |
| `tool` | Decorator that turns a function into a `Function` with extra options. |
| `TokenManager` | Helper for managing tool-related credentials. |

## Three ways to give an agent tools

=== "Plain function"

    Pass any Python function. Its type hints and docstring become the schema.

    ```python
    from buddy.agent import Agent

    def get_weather(city: str) -> str:
        """Return the current weather for a city.

        Args:
            city (str): Name of the city.
        """
        return f"It is sunny in {city}."

    agent = Agent(tools=[get_weather])
    ```

=== "@tool decorator"

    Use the decorator when you need more control (caching, confirmation,
    instructions, hooks). See [Custom Tools](custom.md).

    ```python
    from buddy.tools import tool

    @tool(cache_results=True, show_result=True)
    def get_weather(city: str) -> str:
        """Return the current weather for a city."""
        return f"It is sunny in {city}."
    ```

=== "Toolkit"

    Pass a built-in or custom `Toolkit` instance. Every registered method
    becomes a tool.

    ```python
    from buddy.agent import Agent
    from buddy.tools.calculator import CalculatorTools

    agent = Agent(tools=[CalculatorTools(enable_all=True)])
    ```

All three can be mixed in the same `tools` list, which is typed as
`List[Union[Toolkit, Callable, Function, Dict]]`.

## How schemas are generated

When the agent prepares its tools, each callable is turned into a `Function`
(via `Function.from_callable` for plain functions, or directly for `@tool` and
`Toolkit` methods). `Function.process_entrypoint()` then:

1. Reads the signature with `inspect.signature` and `get_type_hints`.
2. Parses the docstring (`docstring_parser`) for parameter descriptions.
3. Builds a JSON Schema via `buddy.utils.json_schema.get_json_schema`.
4. Marks parameters without a default as `required`.

The `agent`, `team`, and `self` parameters are always stripped from the schema —
they are injected at call time, not requested from the model. See
[Function Calling](functions.md) for the internals.

!!! tip "Write good docstrings"
    The model only sees the name, description, and parameter docs you provide.
    A clear docstring with an `Args:` section directly improves tool-calling
    accuracy.

## Controlling tool calls

These `Agent` parameters govern tool behaviour:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `tools` | `None` | The list of tools available to the model. |
| `show_tool_calls` | `True` | Print each tool call and its result in the response. |
| `tool_call_limit` | `None` | Maximum number of tool calls allowed in a run. |
| `tool_choice` | `None` | `"auto"`, `"none"`, or a `{"type": "function", ...}` dict to force a tool. |
| `tool_hooks` | `None` | Middleware callables wrapped around every tool call. |

```python
agent = Agent(
    tools=[CalculatorTools(enable_all=True)],
    show_tool_calls=True,
    tool_call_limit=5,
    tool_choice="auto",
)
```

!!! note "`tool_choice` defaults"
    When no tools are present the effective default is `"none"`; when tools are
    present it is `"auto"` (the model decides). Pass a function dict to force a
    specific tool.

## Where to go next

- [Built-in Tools](builtin.md) — catalogue of ready-made toolkits.
- [Custom Tools](custom.md) — build your own functions and toolkits.
- [Function Calling](functions.md) — how schemas and calls work under the hood.
- [Tool Execution](execution.md) — the call loop, hooks, and error handling.
