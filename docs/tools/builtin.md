# Built-in Tools

Buddy AI ships with around 80 ready-made toolkits under `buddy/tools/`. Each is a
class subclassing `Toolkit`; import it, instantiate it, and pass the instance to
an agent's `tools` list. Most toolkits expose boolean flags in their constructor
to enable or disable individual operations, and read credentials from
environment variables.

```python
from buddy.agent import Agent
from buddy.tools.tavily import TavilyTools

agent = Agent(tools=[TavilyTools()])  # reads TAVILY_API_KEY from the environment
```

!!! note "Optional dependencies"
    Many toolkits wrap third-party SDKs (e.g. `tavily-python`, `PyGithub`,
    `docker`). Install the relevant package before using the toolkit.

## Catalogue

### Web & search

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `TavilyTools` | `buddy.tools.tavily` | Web search via the Tavily API. |
| `GoogleSearchTools` | `buddy.tools.googlesearch` | Google web search. |
| `SerperTools` | `buddy.tools.serper` | Search via Serper.dev. |
| `SerpApiTools` | `buddy.tools.serpapi` | Search via SerpAPI. |
| `ValyuTools` | `buddy.tools.valyu` | Valyu search API. |
| `WikipediaTools` | `buddy.tools.wikipedia` | Query and read Wikipedia. |
| `WebsiteTools` | `buddy.tools.website` | Read and parse web pages. |
| `WebBrowserTools` | `buddy.tools.webbrowser` | Open URLs in a browser. |
| `PlaywrightTools` | `buddy.tools.playwright_tool` | Browser automation with Playwright. |
| `SeleniumTools` | `buddy.tools.selenium_tool` | Browser automation with Selenium. |
| `BrowserbaseTools` | `buddy.tools.browserbase` | Headless browsing via Browserbase. |

### Code & data

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `PythonTools` | `buddy.tools.python` | Write and execute Python code. |
| `CalculatorTools` | `buddy.tools.calculator` | Arithmetic and math operations. |
| `SQLTools` | `buddy.tools.sql` | Run SQL queries. |
| `PostgresTools` | `buddy.tools.postgres` | PostgreSQL operations. |
| `PandasTools` | `buddy.tools.pandas` | Manipulate data with pandas. |
| `VisualizationTools` | `buddy.tools.visualization` | Generate charts. |
| `CsvTools` | `buddy.tools.csv_toolkit` | Read and query CSV files. |
| `ElasticsearchTools` | `buddy.tools.elasticsearch_tool` | Query Elasticsearch. |

### Files & system

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `FileTools` | `buddy.tools.file` | Read, write, search, and manage files. |
| `LocalFileSystemTools` | `buddy.tools.local_file_system` | Local filesystem operations. |
| `ShellTools` | `buddy.tools.shell` | Run shell commands. |
| `DockerTools` | `buddy.tools.docker` | Manage Docker containers and images. |
| `KubernetesTools` | `buddy.tools.kubernetes_tools` | Interact with a Kubernetes cluster. |
| `SleepTools` | `buddy.tools.sleep` | Pause execution. |

### Communication

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `EmailTools` | `buddy.tools.email` | Send email. |
| `GmailTools` | `buddy.tools.gmail` | Gmail integration. |
| `SlackTools` | `buddy.tools.slack` | Post to Slack. |
| `MicrosoftTeamsTools` | `buddy.tools.microsoft_teams` | Post to Microsoft Teams. |
| `TwitterTools` | `buddy.tools.twitter` | Twitter/X integration. |
| `WhatsAppTools` | `buddy.tools.whatsapp` | Send WhatsApp messages. |
| `SMSTools` | `buddy.tools.sms` | Send SMS. |
| `PushNotificationTools` | `buddy.tools.push_notifications` | Send push notifications. |

### Productivity & project management

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `GithubTools` | `buddy.tools.github` | GitHub repositories, issues, PRs. |
| `BitbucketTools` | `buddy.tools.bitbucket` | Bitbucket integration. |
| `JiraTools` | `buddy.tools.jira` | Jira issues. |
| `LinearTools` | `buddy.tools.linear` | Linear issues. |
| `ConfluenceTools` | `buddy.tools.confluence` | Confluence pages. |
| `GoogleCalendarTools` | `buddy.tools.googlecalendar` | Google Calendar events. |
| `GoogleSheetsTools` | `buddy.tools.googlesheets` | Google Sheets. |
| `GoogleMapTools` | `buddy.tools.google_maps` | Google Maps queries. |

### Cloud

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `AWSTools` | `buddy.tools.aws_tools` | AWS service operations. |
| `AWSLambdaTools` | `buddy.tools.aws_lambda` | Invoke AWS Lambda functions. |

### Media & generative

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `DalleTools` | `buddy.tools.dalle` | Image generation with DALL·E. |
| `OpenAITools` | `buddy.tools.openai` | OpenAI utilities (transcription, etc.). |
| `ElevenLabsTools` | `buddy.tools.eleven_labs` | Text-to-speech with ElevenLabs. |
| `CartesiaTools` | `buddy.tools.cartesia` | Cartesia voice synthesis. |
| `LumaLabTools` | `buddy.tools.lumalab` | Video generation with Luma. |
| `ModelsLabTools` | `buddy.tools.models_labs` | ModelsLab media generation. |
| `GiphyTools` | `buddy.tools.giphy` | Search GIFs via Giphy. |
| `MoviePyVideoTools` | `buddy.tools.moviepy_video` | Edit video with MoviePy. |
| `YouTubeTools` | `buddy.tools.youtube` | Fetch YouTube data and transcripts. |
| `QRCodeTools` | `buddy.tools.qr_code_generator` | Generate QR codes. |

### Reasoning & agent control

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `ReasoningTools` | `buddy.tools.reasoning` | Structured step-by-step reasoning. |
| `ThinkingTools` | `buddy.tools.thinking` | Scratchpad "think" tool. |
| `PlanningTools` | `buddy.tools.planning` | Task planning. |
| `KnowledgeTools` | `buddy.tools.knowledge` | Search the agent's knowledge base. |
| `UserControlFlowTools` | `buddy.tools.user_control_flow` | Request user input mid-run. |
| `Mem0Tools` | `buddy.tools.mem0` | Mem0 memory integration. |

### Other integrations

| Toolkit class | Module | Purpose |
|---------------|--------|---------|
| `OpenWeatherTools` | `buddy.tools.openweather` | Weather data. |
| `IPGeolocationTools` | `buddy.tools.ip_geolocation` | IP geolocation lookups. |
| `TimezoneTools` | `buddy.tools.timezone` | Timezone conversions. |
| `TranslationTools` | `buddy.tools.translation` | Text translation. |
| `CustomApiTools` | `buddy.tools.api` | Call arbitrary HTTP APIs. |
| `MCPTools` / `MultiMCPTools` | `buddy.tools.mcp` | Connect to Model Context Protocol servers. |

!!! tip "Discover the full set"
    This catalogue is representative, not exhaustive. List every toolkit module
    with `glob buddy/tools/*.py`, and read a file to see its constructor flags
    and method docstrings.

## Usage examples

### Selectively enabling operations

Most toolkits accept boolean flags to expose only the operations you need.
`CalculatorTools`, for example, enables the four basic operations by default and
lets you turn on the rest:

```python
from buddy.agent import Agent
from buddy.tools.calculator import CalculatorTools

agent = Agent(
    tools=[CalculatorTools(square_root=True, factorial=True, is_prime=True)],
)
agent.print_response("What is the square root of 1024?")
```

### Combining multiple toolkits

```python
from buddy.agent import Agent
from buddy.tools.python import PythonTools
from buddy.tools.file import FileTools

agent = Agent(
    tools=[
        PythonTools(run_code=True),
        FileTools(base_dir="./workspace"),
    ],
    show_tool_calls=True,
)
```

### Filtering tools on any toolkit

Because every toolkit subclasses `Toolkit`, you can include or exclude
individual methods by name via the base-class arguments:

```python
from buddy.tools.file import FileTools

# Only expose read_file and list_files
tools = FileTools(include_tools=["read_file", "list_files"])
```

See [Custom Tools](custom.md) to build your own toolkit, and
[Tool System](overview.md) for how toolkits are registered with an agent.
