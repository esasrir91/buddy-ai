# Team Overview

Teams enable multiple agents to collaborate on complex tasks under a shared coordinator.

## Basic Team

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat

researcher = Agent(name="researcher", role="Find accurate information", model=OpenAIChat(id="gpt-4o-mini"))
writer = Agent(name="writer", role="Write compelling content", model=OpenAIChat(id="gpt-4o"))

team = Team(
    name="content_team",
    agents=[researcher, writer],
    model=OpenAIChat(id="gpt-4o"),
)

team.print_response("Write a blog post about quantum computing.")
```

## Coordination Modes

| Mode | Description |
|------|-------------|
| `route` | Coordinator picks the best agent for each message |
| `coordinate` | Coordinator orchestrates all agents in sequence |
| `collaborate` | Agents discuss and reach consensus |

```python
team = Team(agents=[...], mode="coordinate")
```

## Shared Resources

Teams can share memory and knowledge across all member agents:

```python
team = Team(
    agents=[a1, a2, a3],
    shared_memory=Memory(...),
    shared_knowledge=PDFKnowledgeBase(...),
)
```

## Nested Teams

Teams can contain other teams:

```python
sub_team = Team(name="research_team", agents=[researcher1, researcher2])
main_team = Team(name="main", agents=[sub_team, writer])
```

See [Multi-Agent Systems](multi-agent.md) for advanced patterns.
