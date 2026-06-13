# Workflow System

Workflows let you define structured, repeatable sequences of agent tasks with branching, loops, and parallel execution.

## Basic Workflow

```python
from buddy.workflow import Workflow
from buddy import Agent
from buddy.models.openai import OpenAIChat

def research_task(topic: str) -> str:
    agent = Agent(model=OpenAIChat(id="gpt-4o-mini"))
    response = agent.run(f"Research: {topic}")
    return response.content

def write_task(research: str) -> str:
    agent = Agent(model=OpenAIChat(id="gpt-4o"))
    response = agent.run(f"Write an article based on:\n{research}")
    return response.content

workflow = Workflow(name="content_pipeline")

@workflow.step
def step1(topic: str):
    return research_task(topic)

@workflow.step
def step2(research: str):
    return write_task(research)

result = workflow.run("quantum computing")
```

## Workflow v2 Features

- **Conditional branching** — `if_step`, `else_step`
- **Parallel execution** — run steps concurrently
- **Loops** — iterate until condition is met
- **Routers** — dynamically pick the next step
- **State management** — shared state across steps

## See Also

- [Workflow Definition](definition.md)
- [Workflow Execution](execution.md)
