# Custom Tools

When the built-in toolkits don't cover your use case, you can expose your own
code as tools in three escalating levels of control: a **plain function**, the
**`@tool` decorator**, or a **`Toolkit` subclass**.

## Plain functions

The simplest tool is a normal Python function. Pass it directly to the agent;
its type hints and docstring are turned into a JSON schema by
`Function.from_callable`.

```python
from buddy.agent import Agent

def convert_currency(amount: float, rate: float) -> str:
    """Convert an amount using an exchange rate.

    Args:
        amount (float): The source amount.
        rate (float): The exchange rate to apply.
    """
    return f"{amount * rate:.2f}"

agent = Agent(tools=[convert_currency])
```

!!! tip "Docstrings are the contract"
    The `Args:` section is parsed (via `docstring_parser`) into parameter
    descriptions the model sees. Parameters without a default value become
    `required` in the schema.

## The `@tool` decorator

Use `@tool` when you need more than a schema — caching, result display, user
confirmation, or hooks. It converts the function into a `Function` instance.

```python
from buddy.tools import tool

@tool(
    name="search_docs",
    description="Search internal documentation.",
    show_result=True,
    cache_results=True,
    cache_ttl=600,
)
def search_docs(query: str) -> str:
    """Search the docs index for a query."""
    ...
    return "results"
```

### Decorator options

`@tool` accepts only the following keyword arguments (passing any other raises a
`ValueError`):

| Argument | Type | Effect |
|----------|------|--------|
| `name` | `str` | Override the tool name. |
| `description` | `str` | Override the description (defaults to the docstring). |
| `strict` | `bool` | Enforce strict JSON-schema parameter checking. |
| `instructions` | `str` | Usage instructions for the tool. |
| `add_instructions` | `bool` | Add `instructions` to the system message (default `True`). |
| `show_result` | `bool` | Show the result in the response after the call. |
| `stop_after_tool_call` | `bool` | Stop the agent run after this tool runs. |
| `requires_confirmation` | `bool` | Require user confirmation before executing. |
| `requires_user_input` | `bool` | Require user-provided input before executing. |
| `user_input_fields` | `List[str]` | Fields supplied by the user rather than the model. |
| `external_execution` | `bool` | Execute outside the agent loop. |
| `pre_hook` | `Callable` | Runs before the function. |
| `post_hook` | `Callable` | Runs after the function. |
| `tool_hooks` | `List[Callable]` | Middleware wrapped around the call. |
| `cache_results` | `bool` | Cache results to disk. |
| `cache_dir` | `str` | Cache directory (defaults to the system temp dir). |
| `cache_ttl` | `int` | Cache lifetime in seconds (default `3600`). |

!!! warning "Mutually exclusive flags"
    Only one of `requires_user_input`, `requires_confirmation`, or
    `external_execution` may be `True` at a time — setting more than one raises
    a `ValueError`.

`@tool` works with and without parentheses, and supports sync, async, and async
generator functions:

```python
@tool
def simple(): ...

@tool(cache_results=True)
def configured(): ...

@tool
async def async_tool(): ...
```

## Subclassing `Toolkit`

Group related operations into a `Toolkit`. Register the methods you want to
expose by passing them to `super().__init__(..., tools=[...])`; with
`auto_register=True` (the default) they are wrapped as `Function` instances.

```python
from typing import List, Callable
from buddy.tools import Toolkit

class InventoryTools(Toolkit):
    def __init__(self, **kwargs):
        tools: List[Callable] = [self.check_stock, self.reserve_item]
        super().__init__(name="inventory", tools=tools, **kwargs)

    def check_stock(self, sku: str) -> str:
        """Return the available quantity for a SKU.

        Args:
            sku (str): The product SKU.
        """
        return "42 in stock"

    def reserve_item(self, sku: str, quantity: int) -> str:
        """Reserve a quantity of a SKU.

        Args:
            sku (str): The product SKU.
            quantity (int): Units to reserve.
        """
        return f"Reserved {quantity} of {sku}"

agent_tools = InventoryTools()
```

### Toolkit constructor options

The `Toolkit` base class exposes shared controls for every toolkit:

| Argument | Purpose |
|----------|---------|
| `name` | A descriptive name for the toolkit. |
| `tools` | The list of callables to register. |
| `instructions` / `add_instructions` | Toolkit-level instructions and whether to inject them. |
| `include_tools` / `exclude_tools` | Allow/deny lists of method names to register. |
| `requires_confirmation_tools` | Method names that require user confirmation. |
| `external_execution_required_tools` | Method names executed outside the agent loop. |
| `stop_after_tool_call_tools` | Method names that stop the run after executing. |
| `show_result_tools` | Method names whose results are shown. |
| `cache_results` / `cache_ttl` / `cache_dir` | Caching configuration for all methods. |
| `auto_register` | Automatically register the methods in `tools` (default `True`). |

!!! note "Validated names"
    `include_tools` and `exclude_tools` are validated against the registered
    method names — referencing an unknown method raises a `ValueError`.

You can also register a function after construction:

```python
tk = InventoryTools()
tk.register(some_callable, name="optional_alias")
```

## Accessing the agent inside a tool

If a tool's signature includes an `agent` (or `team`) parameter, the agent
injects itself at call time and removes it from the model-facing schema:

```python
@tool
def remember(fact: str, agent) -> str:
    """Store a fact about the user."""
    agent.session_state.setdefault("facts", []).append(fact)
    return "stored"
```

See [Function Calling](functions.md) for how schemas are generated and
[Tool Execution](execution.md) for the hook and execution flow.
