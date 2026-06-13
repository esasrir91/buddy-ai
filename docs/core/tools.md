# Tools

Tools extend what an agent can do beyond text generation. Any Python function with type hints becomes a callable tool.

## Built-in Tools

```python
from buddy.tools.tavily import TavilyTools       # Web search
from buddy.tools.python import PythonTools        # Code execution
from buddy.tools.github import GithubTools        # GitHub API
from buddy.tools.gmail import GmailTools          # Gmail
from buddy.tools.calculator import CalculatorTools
from buddy.tools.wikipedia import WikipediaTools
from buddy.tools.dalle import DallETools           # Image generation
from buddy.tools.sql import SQLTools               # Database queries
from buddy.tools.docker import DockerTools
from buddy.tools.kubernetes import KubernetesTools

agent = Agent(tools=[TavilyTools(), PythonTools()])
```

## Custom Tool Functions

```python
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g. "London")
        units: Temperature units — celsius or fahrenheit
    """
    return {"city": city, "temp": 22, "units": units, "condition": "sunny"}

agent = Agent(tools=[get_weather])
```

## Toolkits

Group related tools in a `Toolkit` class:

```python
from buddy.tools import Toolkit

class WeatherToolkit(Toolkit):
    name = "weather"

    def get_current(self, city: str) -> str:
        """Get current weather."""
        return f"Sunny, 22°C in {city}"

    def get_forecast(self, city: str, days: int = 3) -> str:
        """Get weather forecast."""
        return f"{days}-day forecast for {city}: mostly sunny"

agent = Agent(tools=[WeatherToolkit()])
```

See [Built-in Tools](../tools/builtin.md) for the complete tool catalogue.
