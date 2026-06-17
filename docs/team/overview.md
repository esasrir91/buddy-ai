# Team Overview

A **Team** (`buddy.team.Team`) lets several agents work together on a task under
a coordinating leader. The leader is itself driven by a model; it decides how to
involve the members and how to assemble the final answer.

!!! note "Version"
    Documents buddy-ai **2.2.0**. The `Team` API below is verified against
    `buddy/team/team.py`.

## Anatomy of a team

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat

researcher = Agent(
    name="Researcher",
    role="Find accurate, up-to-date information",
    model=OpenAIChat(id="gpt-4o-mini"),
)
writer = Agent(
    name="Writer",
    role="Turn research into clear prose",
    model=OpenAIChat(id="gpt-4o"),
)

team = Team(
    members=[researcher, writer],   # REQUIRED, first positional argument
    mode="coordinate",              # default
    model=OpenAIChat(id="gpt-4o"),  # the leader's model
    name="content_team",
    instructions="Research the topic, then write a concise article.",
    markdown=True,
)

team.print_response("Write a short article about quantum computing.")
```

!!! warning "It's `members`, not `agents`"
    The constructor's first parameter is **`members`** — a list of `Agent` or
    nested `Team` objects. There is no `agents=` argument, no `team.collaborate()`
    method, and no `TeamController`. Give each member a `role`; give the leader a
    `model`.

## Coordination modes

The `mode` parameter selects how the leader engages members:

| Mode | Behavior |
|------|----------|
| `route` | The leader **delegates to the single best member** for the task and returns its output. |
| `coordinate` *(default)* | The leader **delegates to members and synthesizes** their outputs into one response. |
| `collaborate` | **Members work together** on the task, with the leader facilitating. |

```python
team = Team(members=[researcher, writer], mode="route")
```

## Running a team

| Method | Returns |
|--------|---------|
| `team.run(message, ...)` | A `TeamRunResponse` (or an event iterator when `stream=True`) |
| `team.print_response(message, ...)` | Streams a formatted response to the console |
| `team.arun(message, ...)` | Async version of `run` |

```python
response = team.run("Summarize the latest on fusion energy.")
print(response.content)
```

## Useful constructor options

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `name` | `None` | Human-readable team name |
| `instructions` | `None` | Guidance for the leader |
| `success_criteria` | `None` | What "done" looks like |
| `markdown` | `False` | Ask the leader to format output as Markdown |
| `show_members_responses` | `False` | Surface each member's response |
| `enable_agentic_context` | `False` | Let the leader maintain & share team context |
| `share_member_interactions` | `False` | Pass prior member outputs to members |
| `knowledge` | `None` | Attach an `AgentKnowledge` base to the team |

## Where to go next

- [Multi-agent systems](multi-agent.md) — designing specialists and picking a mode.
- [Orchestration](orchestration.md) — how the leader delegates internally.
- [Communication](communication.md) — how members exchange tasks and results.
