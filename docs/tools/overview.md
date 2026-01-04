# Tools & Functions Overview

The Buddy AI tool system allows agents to interact with external services, APIs, and perform actions beyond text generation. With 200+ built-in tools and a simple framework for creating custom tools, agents can accomplish complex tasks.

## Core Concepts

### What are Tools?
Tools are functions that agents can call to:
- **Retrieve information** (web search, database queries)
- **Perform actions** (send emails, create files)
- **Process data** (calculations, transformations)
- **Integrate with services** (APIs, cloud platforms)

### Tool Types

```mermaid
graph TD
    A[Tools] --> B[Built-in Tools]
    A --> C[Custom Tools]
    A --> D[Function Tools]
    
    B --> E[Web Tools]
    B --> F[File Tools]
    B --> G[API Tools]
    B --> H[Data Tools]
    
    C --> I[Python Functions]
    C --> J[API Integrations]
    C --> K[Custom Classes]
    
    D --> L[Decorated Functions]
    D --> M[Lambda Functions]
```

## Quick Start

### Basic Tool Usage
```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.web import DuckDuckGoSearch
from buddy.tools.calculator import Calculator

agent = Agent(
    model=OpenAIChat(),
    tools=[DuckDuckGoSearch(), Calculator()],
    instructions="Use tools when needed to help users."
)

response = agent.run("What's 15% of 1000?")
# Agent will use Calculator tool

response = agent.run("What's the latest news about AI?")
# Agent will use DuckDuckGoSearch tool
```

### Creating Custom Tools
```python
from buddy.tools import Toolkit

class WeatherTool(Toolkit):
    def get_weather(self, city: str) -> str:
        \"\"\"Get current weather for a city.
        
        Args:
            city: Name of the city
            
        Returns:
            Weather information
        \"\"\"
        # Your weather API integration here
        return f"Weather in {city}: Sunny, 72°F"

# Use the custom tool
agent = Agent(
    model=OpenAIChat(),
    tools=[WeatherTool()],
    instructions="Help users with weather information."
)

response = agent.run("What's the weather like in New York?")
```

## Built-in Tools

### Web & Search Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `DuckDuckGoSearch` | Web search | General web queries |
| `WebScraper` | Extract web content | Scrape specific URLs |
| `URLReader` | Read URL content | Get page text |
| `YouTubeSearch` | Search YouTube | Find videos |
| `WikipediaSearch` | Search Wikipedia | Get encyclopedia info |

```python
from buddy.tools.web import DuckDuckGoSearch, WebScraper, URLReader

tools = [
    DuckDuckGoSearch(),
    WebScraper(),
    URLReader()
]

agent = Agent(model=OpenAIChat(), tools=tools)
```

### File & Data Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `FileReader` | Read files | Local file access |
| `FileWriter` | Write files | Save content |
| `CSVReader` | Read CSV files | Data analysis |
| `JSONProcessor` | Handle JSON | API responses |
| `PDFReader` | Extract PDF text | Document processing |

```python
from buddy.tools.file import FileReader, FileWriter, CSVReader

tools = [
    FileReader(),
    FileWriter(),
    CSVReader()
]
```

### Calculation & Data Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `Calculator` | Math calculations | Arithmetic operations |
| `DataAnalyzer` | Analyze datasets | Statistical analysis |
| `ChartGenerator` | Create visualizations | Data visualization |
| `DateTimeTools` | Date/time operations | Time calculations |

```python
from buddy.tools.calculator import Calculator
from buddy.tools.data import DataAnalyzer, ChartGenerator

tools = [Calculator(), DataAnalyzer(), ChartGenerator()]
```

### Communication Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `EmailSender` | Send emails | Email notifications |
| `SlackMessenger` | Slack integration | Team communication |
| `SMSender` | Send SMS | Text notifications |
| `DiscordBot` | Discord integration | Chat bots |

```python
from buddy.tools.email import EmailSender
from buddy.tools.slack import SlackMessenger

tools = [
    EmailSender(smtp_server="smtp.gmail.com", username="user", password="pass"),
    SlackMessenger(token="slack-token")
]
```

### API & Integration Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `HTTPClient` | HTTP requests | API calls |
| `DatabaseQuery` | Database access | SQL queries |
| `CloudStorage` | Cloud file storage | AWS S3, GCS |
| `PaymentProcessor` | Payment handling | Stripe, PayPal |

```python
from buddy.tools.http import HTTPClient
from buddy.tools.database import DatabaseQuery

tools = [
    HTTPClient(),
    DatabaseQuery(connection_string="postgresql://...")
]
```

## Custom Tool Development

### Method 1: Function Decorator
```python
from buddy.tools import tool

@tool
def get_current_time() -> str:
    \"\"\"Get the current time.
    
    Returns:
        Current time as string
    \"\"\"
    from datetime import datetime
    return datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")

@tool
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    \"\"\"Calculate tax amount.
    
    Args:
        amount: Base amount
        rate: Tax rate (default 0.1 for 10%)
        
    Returns:
        Tax amount
    \"\"\"
    return amount * rate

# Use with agent
agent = Agent(
    model=OpenAIChat(),
    tools=[get_current_time, calculate_tax]
)
```

### Method 2: Toolkit Class
```python
from buddy.tools import Toolkit

class DatabaseTool(Toolkit):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    def query_users(self, limit: int = 10) -> list:
        \"\"\"Query users from database.
        
        Args:
            limit: Number of users to return
            
        Returns:
            List of user records
        \"\"\"
        # Database query logic here
        return [{\"id\": 1, \"name\": \"John\"}]
    
    def create_user(self, name: str, email: str) -> dict:
        \"\"\"Create a new user.
        
        Args:
            name: User's name
            email: User's email
            
        Returns:
            Created user record
        \"\"\"
        # User creation logic here
        return {\"id\": 123, \"name\": name, \"email\": email}

# Use the toolkit
db_tool = DatabaseTool(\"postgresql://user:pass@localhost/db\")
agent = Agent(model=OpenAIChat(), tools=[db_tool])
```

### Method 3: Async Tools
```python
import asyncio
from buddy.tools import async_tool

@async_tool
async def fetch_api_data(url: str) -> dict:
    \"\"\"Fetch data from an API asynchronously.
    
    Args:
        url: API endpoint URL
        
    Returns:
        API response data
    \"\"\"
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Use with async agent
async def main():
    agent = Agent(model=OpenAIChat(), tools=[fetch_api_data])
    response = await agent.async_run(\"Get data from https://api.example.com/users\")
    print(response.content)

asyncio.run(main())
```

## Tool Configuration

### Tool Parameters
```python
from buddy.tools.web import DuckDuckGoSearch

# Configure tool behavior
search_tool = DuckDuckGoSearch(
    max_results=5,
    region=\"us-en\",
    safesearch=\"moderate\",
    timeout=10
)

agent = Agent(
    model=OpenAIChat(),
    tools=[search_tool],
    tool_call_limit=3,  # Limit tool calls per interaction
    show_tool_calls=True  # Show tool usage to user
)
```

### Tool Access Control
```python
from buddy.tools.file import FileReader

# Restrict file access
file_tool = FileReader(
    allowed_extensions=[\".txt\", \".md\", \".json\"],
    allowed_directories=[\"/safe/path\"],
    max_file_size=1024*1024  # 1MB limit
)
```

### Tool Error Handling
```python
from buddy.tools import Toolkit
from buddy.exceptions import ToolExecutionError

class SafeTool(Toolkit):
    def risky_operation(self, input_data: str) -> str:
        \"\"\"A potentially risky operation.\"\"\"
        try:
            # Risky operation here
            result = process_data(input_data)
            return result
        except Exception as e:
            raise ToolExecutionError(f\"Operation failed: {e}\")

# Agent will handle tool errors gracefully
agent = Agent(model=OpenAIChat(), tools=[SafeTool()])
```

## Advanced Tool Patterns

### Tool Composition
```python
from buddy.tools import Toolkit

class CompositeTool(Toolkit):
    def __init__(self):
        self.search = DuckDuckGoSearch()
        self.file_writer = FileWriter()
    
    def research_and_save(self, topic: str, filename: str) -> str:
        \"\"\"Research a topic and save results to file.
        
        Args:
            topic: Research topic
            filename: Output file name
            
        Returns:
            Success message
        \"\"\"
        # Use multiple tools in sequence
        search_results = self.search.search(topic, max_results=5)
        
        content = \"\\n\".join([r.title + \": \" + r.snippet for r in search_results])
        
        self.file_writer.write_file(filename, content)
        
        return f\"Research on '{topic}' saved to {filename}\"
```

### Conditional Tool Usage
```python
from buddy.tools import Toolkit

class SmartTool(Toolkit):
    def smart_search(self, query: str) -> str:
        \"\"\"Intelligently choose search method based on query.\"\"\"
        if \"weather\" in query.lower():
            return self.get_weather(query)
        elif \"news\" in query.lower():
            return self.search_news(query)
        else:
            return self.web_search(query)
    
    def get_weather(self, query: str) -> str:
        # Weather-specific search
        pass
    
    def search_news(self, query: str) -> str:
        # News-specific search
        pass
    
    def web_search(self, query: str) -> str:
        # General web search
        pass
```

### Tool State Management
```python
from buddy.tools import Toolkit

class StatefulTool(Toolkit):
    def __init__(self):
        self.session_data = {}
        self.user_preferences = {}
    
    def set_preference(self, user_id: str, key: str, value: str) -> str:
        \"\"\"Set user preference.\"\"\"
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id][key] = value
        return f\"Preference {key} set to {value}\"
    
    def get_preference(self, user_id: str, key: str) -> str:
        \"\"\"Get user preference.\"\"\"
        return self.user_preferences.get(user_id, {}).get(key, \"Not set\")
```

## Tool Security

### Input Validation
```python
from buddy.tools import Toolkit
from typing import Literal

class SecureTool(Toolkit):
    def safe_operation(
        self, 
        operation: Literal[\"read\", \"write\", \"delete\"],
        path: str
    ) -> str:
        \"\"\"Perform file operation with validation.
        
        Args:
            operation: Type of operation (read/write/delete only)
            path: File path (validated)
        \"\"\"
        # Validate path
        if \"..\" in path or path.startswith(\"/\"):
            raise ValueError(\"Invalid path\")
        
        # Perform operation
        if operation == \"read\":
            return self._read_file(path)
        elif operation == \"write\":
            return self._write_file(path)
        elif operation == \"delete\":
            return self._delete_file(path)
```

### Environment Isolation
```python
import subprocess
from buddy.tools import Toolkit

class IsolatedTool(Toolkit):
    def run_code(self, code: str, language: str = \"python\") -> str:
        \"\"\"Run code in isolated environment.
        
        Args:
            code: Code to execute
            language: Programming language
        \"\"\"
        if language == \"python\":
            # Run in Docker container for isolation
            result = subprocess.run(
                [\"docker\", \"run\", \"--rm\", \"python:3.10\", \"python\", \"-c\", code],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
```

## Best Practices

### Tool Design
1. **Single Responsibility**: Each tool should have a clear, focused purpose
2. **Clear Documentation**: Provide detailed docstrings with examples
3. **Type Hints**: Use type hints for all parameters and return values
4. **Error Handling**: Handle errors gracefully and provide meaningful messages
5. **Validation**: Validate inputs to prevent security issues

### Performance
1. **Async Tools**: Use async for I/O bound operations
2. **Caching**: Cache expensive operations when appropriate
3. **Timeouts**: Set reasonable timeouts for external calls
4. **Resource Management**: Clean up resources properly

### Security
1. **Input Validation**: Always validate user inputs
2. **Access Control**: Implement proper authorization
3. **Environment Isolation**: Run untrusted code in sandboxes
4. **Audit Logging**: Log tool usage for security monitoring

## Debugging Tools

### Tool Execution Monitoring
```python
# Enable tool call visibility
agent = Agent(
    model=OpenAIChat(),
    tools=[DuckDuckGoSearch()],
    show_tool_calls=True,  # Show tool execution
    debug_mode=True        # Detailed logging
)

response = agent.run(\"Search for latest AI news\")

# Check tool calls
for tool_call in response.tool_calls:
    print(f\"Tool: {tool_call.function_name}\")
    print(f\"Args: {tool_call.arguments}\")
    print(f\"Result: {tool_call.result}\")
```

### Tool Testing
```python
# Test tools independently
from buddy.tools.calculator import Calculator

calc = Calculator()
result = calc.calculate(\"2 + 2\")
assert result == \"4\"

# Test with agent
agent = Agent(model=OpenAIChat(), tools=[calc])
response = agent.run(\"What's 2 + 2?\")
assert \"4\" in response.content
```

## Next Steps

- [Built-in Tools Reference](builtin.md)
- [Custom Tool Development](custom.md)
- [Function Calling Guide](functions.md)
- [Tool Execution & Debugging](execution.md)