# Agent System

The `Agent` class is the core building block of Buddy AI. An agent combines an LLM, tools, memory, and knowledge into a single runnable entity.

## Basic Agent

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="assistant",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant.",
)
agent.print_response("Hello!")
```

## Key Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique agent identifier |
| `model` | `Model` | LLM provider and model ID |
| `instructions` | `str \| list[str]` | System prompt(s) |
| `tools` | `list` | Tools the agent can call |
| `subagents` | `list[Agent]` | Agents available for task delegation |
| `knowledge` | `AgentKnowledge` | RAG knowledge base |
| `memory` | `Memory` | Persistent session memory |
| `parallel_tool_calls` | `bool` | Execute eligible synchronous tool calls concurrently |
| `cache_prompt` | `bool` | Enable provider-native caching for the agent and its auxiliary/subagent models |
| `advisor` | `bool` | Ask for guidance before the agent generates its response |
| `advisor_config` | `dict` | Configure advisor `instructions` and optional `model` |
| `judge` | `bool` | Evaluate the completed response against criteria |
| `judge_config` | `dict` | Configure judge `criteria` and optional `model` |
| `markdown` | `bool` | Render responses as markdown |
| `show_tool_calls` | `bool` | Print tool calls in output |
| `debug_mode` | `bool` | Verbose debug logging |

## Running an Agent

```python
# Print to console
agent.print_response("What is AI?")

# Get response object
response = agent.run("What is AI?")
print(response.content)

# Async
response = await agent.arun("What is AI?")

# Stream tokens — pass stream=True to run()
for chunk in agent.run("Explain AI...", stream=True):
    print(chunk.content, end="", flush=True)

# print_response can also stream directly to the console
agent.print_response("Explain AI...", stream=True)
```

## Subagents and Parallel Tools

Subagents use the existing team transfer tools. Set `parallel_tool_calls=True` to execute eligible synchronous tool calls concurrently; calls requiring confirmation, external execution, or user input remain paused and are not run in parallel.

```python
researcher = Agent(name="researcher", model=...)
writer = Agent(name="writer", model=...)

agent = Agent(
    model=...,
    subagents=[researcher, writer],
    parallel_tool_calls=True,
    cache_prompt=True,
)
```

`cache_prompt=True` is propagated to the agent's reasoning, parser, output, advisor, judge, and subagent models. Each provider activates only the caching mechanism it supports.

## Advisor and Judge

The advisor and judge use Buddy's model interface, so they work with any configured model provider. If their config omits `model`, they use the agent's model. Advisor guidance is included in the prompt; judge feedback is returned on `RunResponse.judge_result`.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),  # Replace with any Buddy model provider
    advisor=True,
    advisor_config={"instructions": "Point out important constraints."},
    judge=True,
    judge_config={"criteria": "The response must answer every part of the request."},
)

response = agent.run("Review the deployment plan")
print(response.advisor_feedback)
print(response.judge_result)
```

## Structured Output

```python
from pydantic import BaseModel
from buddy import Agent

class Summary(BaseModel):
    title: str
    points: list[str]
    word_count: int

agent = Agent(model=..., response_model=Summary)
response = agent.run("Summarize quantum computing.")
summary: Summary = response.content  # parsed into the Pydantic model
print(summary.title)
```

## See Also

- [Agent Configuration](../agents/configuration.md)
- [Agent Lifecycle](../agents/lifecycle.md)
- [Memory System](../memory/overview.md)
