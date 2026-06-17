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
| `knowledge` | `AgentKnowledge` | RAG knowledge base |
| `memory` | `Memory` | Persistent session memory |
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
