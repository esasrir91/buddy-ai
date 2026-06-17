# Tool Execution

This page traces what happens between the model deciding to call a tool and the
result flowing back into the conversation — and how to observe, limit, and wrap
that flow.

## The execution loop

When an agent runs, it prepares its tools (converting every callable, `@tool`,
and `Toolkit` method into a `Function`) and passes the schemas to the model
along with `tool_choice` and `tool_call_limit`. The loop is then:

1. The model returns one or more tool calls with arguments.
2. For each call, the agent constructs a `FunctionCall` and runs it via
   `execute()` (or `aexecute()` for async).
3. The returned value is appended to the message history as a tool result.
4. The model is invoked again with the results, repeating until it produces a
   final answer or the tool-call limit is reached.

Each call returns a `FunctionExecutionResult` with `status`, `result`, and
`error` (see [Function Calling](functions.md)).

## Limiting tool calls

`tool_call_limit` caps how many tool calls a run may make. It is passed through
to the model when generating responses, so once the limit is hit the model stops
requesting further tools.

```python
from buddy.agent import Agent
from buddy.tools.calculator import CalculatorTools

agent = Agent(
    tools=[CalculatorTools(enable_all=True)],
    tool_call_limit=3,
)
```

`tool_choice` controls *whether* and *which* tool is called:

```python
# Force a specific tool
agent = Agent(
    tools=[CalculatorTools()],
    tool_choice={"type": "function", "function": {"name": "add"}},
)
```

## Tool hooks (middleware)

`tool_hooks` is a list of callables wrapped around every tool call, innermost
last. Each hook receives the *next* function in the chain and must call it to
continue — letting you log, time, authorize, or transform calls.

The agent attaches its `tool_hooks` to each `Function` as tools are registered.
Hook arguments are matched **by parameter name**, so declare only what you need.
Available names include `agent`, `team`, `name` / `function_name`,
`function` / `func` / `function_call` (the next callable), and
`args` / `arguments`.

```python
def logging_hook(function_name, function, arguments):
    print(f"→ {function_name}({arguments})")
    result = function(**arguments)   # call the next link in the chain
    print(f"← {function_name} returned {result!r}")
    return result

agent = Agent(
    tools=[CalculatorTools(enable_all=True)],
    tool_hooks=[logging_hook],
)
```

Multiple hooks nest: the first hook in the list is the outermost wrapper, and
the entrypoint sits at the centre. For async tool calls, async hooks are awaited
and sync hooks are run directly; sync calls skip async hooks with a warning.

### `pre_hook` and `post_hook`

A single `Function` can also define `pre_hook` and `post_hook` callables that run
immediately before and after the entrypoint (the post-hook runs only on
success). Like tool hooks, they receive `agent`, `team`, or `fc` (the
`FunctionCall`) by parameter name. These are typically set via the
[`@tool` decorator](custom.md).

## Showing tool calls

With `show_tool_calls=True` (the default), the agent surfaces each call and its
result in the rendered response via `RunResponse.formatted_tool_calls`. Disable
it for quieter output:

```python
agent = Agent(tools=[CalculatorTools()], show_tool_calls=False)
```

Per-tool, `show_result=True` (on a `Function` or `@tool`) additionally shows the
raw result, and `stop_after_tool_call=True` ends the run right after that tool.

## Error handling

`FunctionCall.execute()` is defensive:

- A raised `AgentRunException` is re-raised so the agent loop can act on it
  (used for control-flow signals).
- Any other exception is logged and captured into a
  `FunctionExecutionResult(status="failure", error=...)` rather than crashing the
  run, so the model can see the error text and recover.

```python
def flaky(x: int) -> str:
    """Sometimes fails."""
    if x < 0:
        raise ValueError("x must be non-negative")
    return str(x * 2)
# A negative argument yields a failure result, not an unhandled crash.
```

!!! tip "Caching expensive calls"
    Set `cache_results=True` (with `cache_ttl`) on a tool to memoize results to
    disk. The cache key is derived from the function name and arguments; `agent`
    and `team` are excluded, and generator results are never cached.

## Human-in-the-loop

Three flags pause or externalize execution:

| Flag | Behaviour |
|------|-----------|
| `requires_confirmation` | The call waits for user confirmation before running. |
| `requires_user_input` | Specified fields are collected from the user, not the model. |
| `external_execution` | The call is handed off to run outside the agent loop. |

Only one of these may be enabled per tool. See [Custom Tools](custom.md) for
configuring them.
