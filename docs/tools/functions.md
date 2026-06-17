# Function Calling

Underneath every tool is a `Function` — a Pydantic model
(`buddy.tools.function.Function`) that captures *what* a callable is so the model
can decide *when* to call it. This page covers how a `Function` is built, how its
JSON schema is generated, and how a `FunctionCall` runs it.

```python
from buddy.tools import Function, FunctionCall
```

## The `Function` model

A `Function` stores the metadata sent to the model plus the callable to run and
its execution options. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Function name (a–z, A–Z, 0–9, `_`, `-`; max 64 chars). |
| `description` | `Optional[str]` | What the function does; defaults to the docstring. |
| `parameters` | `Dict[str, Any]` | JSON Schema describing the parameters. |
| `strict` | `Optional[bool]` | Strict schema mode (all properties required). |
| `entrypoint` | `Optional[Callable]` | The callable that is actually executed. |
| `instructions` / `add_instructions` | | Usage instructions and whether to add them to the system message. |
| `show_result` | `bool` | Show the result alongside sending it to the model. |
| `stop_after_tool_call` | `bool` | Stop the agent after this call. |
| `pre_hook` / `post_hook` | `Optional[Callable]` | Run before / after the entrypoint. |
| `tool_hooks` | `Optional[List[Callable]]` | Middleware around the call. |
| `requires_confirmation` / `requires_user_input` / `external_execution` | | Human-in-the-loop and external-execution flags. |
| `cache_results` / `cache_dir` / `cache_ttl` | | Disk-caching configuration. |

The default `parameters` value describes a no-argument function:

```python
{"type": "object", "properties": {}, "required": []}
```

`Function.to_dict()` returns only the model-facing subset — `name`,
`description`, `parameters`, `strict`, `requires_confirmation`, and
`external_execution` — which is what gets sent to the provider.

## Building a `Function` from a callable

`Function.from_callable(callable, name=None, strict=False)` is how plain
functions become tools. It:

1. Reads the signature and resolves type hints with `get_type_hints`.
2. Drops `agent`, `team`, and `self` from the parameters (injected at runtime).
3. Parses the docstring for per-parameter descriptions.
4. Generates the JSON Schema via `buddy.utils.json_schema.get_json_schema`.
5. Marks parameters as `required` based on `strict` or the absence of defaults.

```python
from buddy.tools import Function

def lookup(symbol: str, limit: int = 5) -> str:
    """Look up recent prices for a ticker.

    Args:
        symbol (str): The ticker symbol.
        limit (int): How many rows to return.
    """
    ...

fn = Function.from_callable(lookup)
print(fn.name)         # "lookup"
print(fn.parameters)   # JSON schema with "symbol" required, "limit" optional
```

### Schema generation rules

- **Required vs optional.** With `strict=False`, a parameter is required only if
  it has no default. With `strict=True`, every property is required and
  `additionalProperties` is set to `False`.
- **Descriptions.** When a docstring documents a parameter's type, it is encoded
  as `(type) description`; otherwise just the description is used.
- **Injected parameters.** `agent`, `team`, and `self` are always excluded from
  the schema.

For tools created via `@tool` or a `Toolkit`, the same logic runs through
`Function.process_entrypoint(strict=...)`, which additionally honours
`requires_user_input` / `user_input_fields` by moving those fields into a
`user_input_schema` instead of the model-facing parameters.

!!! note "Argument validation"
    Before execution, the entrypoint is wrapped with Pydantic's `validate_call`
    (with `arbitrary_types_allowed=True`) so arguments are validated against the
    type hints. Async generators — and coroutines on Pydantic < 2.10.0 — are
    left unwrapped.

## Calling a function: `FunctionCall`

A `FunctionCall` pairs a `Function` with the `arguments` the model produced and
performs one invocation.

| Field | Description |
|-------|-------------|
| `function` | The `Function` to call. |
| `arguments` | The argument dict from the model. |
| `result` | The value returned by the entrypoint. |
| `call_id` | Provider-supplied call identifier. |
| `error` | Set if argument parsing or execution failed. |

```python
from buddy.tools import FunctionCall

call = FunctionCall(function=fn, arguments={"symbol": "ACME", "limit": 3})
result = call.execute()           # synchronous
# result = await call.aexecute()  # asynchronous
```

`execute()` (and `aexecute()`) returns a `FunctionExecutionResult`:

```python
class FunctionExecutionResult(BaseModel):
    status: Literal["success", "failure"]
    result: Optional[Any] = None
    error: Optional[str] = None
```

Internally, `execute()`:

1. Runs `pre_hook` (if any).
2. Builds the entrypoint args, injecting `agent` / `team` / `fc` if requested.
3. Checks the disk cache when `cache_results` is enabled (non-generators only).
4. Runs the entrypoint — directly, or wrapped in the `tool_hooks` chain.
5. Caches non-generator results, runs `post_hook`, and returns the result.

`get_call_str()` produces a readable, terminal-width-aware representation such as
`lookup(symbol=ACME, limit=3)` used in `show_tool_calls` output.

!!! tip "`AgentRunException` propagates"
    If a hook or the entrypoint raises `AgentRunException`, it is re-raised
    rather than swallowed — letting the agent loop handle control-flow signals.
    Other exceptions are captured into a `failure` result.

See [Tool Execution](execution.md) for how the agent drives these calls, and
[Custom Tools](custom.md) for building functions and toolkits.
