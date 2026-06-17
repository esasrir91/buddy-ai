# Tools

Tools extend what an agent can do beyond text generation. A tool can be a plain
Python function, a function decorated with `@tool`, or a `Toolkit` that groups
several related functions. The model calls them automatically when useful.

## Built-in Toolkits

Buddy AI ships toolkits under `buddy.tools.<module>`. Each is a `Toolkit`
subclass — instantiate it and pass it in the `tools` list.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.tavily import TavilyTools             # Web search
from buddy.tools.python import PythonTools             # Code execution
from buddy.tools.calculator import CalculatorTools     # Arithmetic
from buddy.tools.file import FileTools                 # Read/write files
from buddy.tools.github import GithubTools             # GitHub API
from buddy.tools.gmail import GmailTools               # Gmail
from buddy.tools.wikipedia import WikipediaTools       # Wikipedia lookups
from buddy.tools.dalle import DalleTools               # Image generation
from buddy.tools.sql import SQLTools                   # Database queries
from buddy.tools.docker import DockerTools             # Docker
from buddy.tools.kubernetes_tools import KubernetesTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[TavilyTools(), CalculatorTools()],
    show_tool_calls=True,
)
agent.print_response("Search for the population of Tokyo, then halve it.")
```

!!! note "Verify before you import"
    Module file names occasionally differ from the class name (for example, the
    Kubernetes toolkit lives in `buddy.tools.kubernetes_tools`). Check the file
    under `buddy/tools/` if an import fails.

## Plain Functions as Tools

Any function with type hints and a docstring can be passed directly. The
docstring and signature are used to build the schema the model sees.

```python
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g. "London").
        units: Temperature units — "celsius" or "fahrenheit".
    """
    return {"city": city, "temp": 22, "units": units, "condition": "sunny"}

agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), tools=[get_weather])
agent.print_response("What's the weather in London?")
```

## The `@tool` Decorator

Use `@tool` (from `buddy.tools`) when you want to override the name/description
or set execution behaviour such as caching or stopping after the call.

```python
from buddy.tools import tool

@tool(name="lookup_order", description="Look up an order by its ID.", show_result=True)
def lookup_order(order_id: str) -> dict:
    return {"order_id": order_id, "status": "shipped"}

agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), tools=[lookup_order])
```

Useful `@tool` options (all optional): `name`, `description`, `instructions`,
`show_result`, `stop_after_tool_call`, `requires_confirmation`,
`cache_results`, `cache_ttl`.

## Custom Toolkits

Group related functions in a `Toolkit` subclass. Pass the methods you want to
expose to `super().__init__(tools=[...])` so they get registered.

```python
from buddy.tools import Toolkit

class WeatherToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="weather", tools=[self.get_current, self.get_forecast])

    def get_current(self, city: str) -> str:
        """Get current weather for a city."""
        return f"Sunny, 22°C in {city}"

    def get_forecast(self, city: str, days: int = 3) -> str:
        """Get a multi-day weather forecast."""
        return f"{days}-day forecast for {city}: mostly sunny"

agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), tools=[WeatherToolkit()])
```

!!! tip "Showing tool calls"
    Set `show_tool_calls=True` on the agent to print each tool invocation and
    its result — handy while developing and debugging tools.

## See Also

- [Agent System](agents.md) — how agents decide to call tools
- [Knowledge](knowledge.md) — retrieval as a built-in capability
