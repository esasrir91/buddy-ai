# Designing Multi-Agent Systems

A multi-agent system splits a hard problem across **specialist agents** and lets
a `Team` leader combine their work. This page covers how to design specialists,
choose a coordination mode, and nest teams.

## Specialist agents

Give each member a narrow `role` and an appropriately sized `model`. The role
tells the leader what the member is good at and shapes how tasks are delegated.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

planner = Agent(name="Planner",  role="Break a goal into clear steps",
                model=OpenAIChat(id="gpt-4o"))
coder   = Agent(name="Coder",    role="Write and fix Python code",
                model=OpenAIChat(id="gpt-4o"))
critic  = Agent(name="Critic",   role="Review output for correctness",
                model=OpenAIChat(id="gpt-4o-mini"))
```

!!! tip "Right-size the models"
    Use a stronger model for the leader and for hard specialist roles; a smaller,
    cheaper model is often enough for narrow tasks like reviewing or formatting.

## Choosing a mode

| Use case | Mode | Why |
|----------|------|-----|
| One of several experts should handle the whole task | `route` | The leader picks the single best member — no wasted calls |
| The task needs several members and a combined answer | `coordinate` | The leader delegates subtasks and synthesizes results |
| Members should build on each other's work jointly | `collaborate` | Members work together toward a shared output |

=== "Route"

    ```python
    from buddy import Team
    from buddy.models.openai import OpenAIChat

    support = Team(
        members=[billing_agent, technical_agent, account_agent],
        mode="route",
        model=OpenAIChat(id="gpt-4o-mini"),
    )
    support.print_response("My invoice looks wrong this month.")
    ```

=== "Coordinate"

    ```python
    team = Team(
        members=[planner, coder, critic],
        mode="coordinate",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Plan, implement, then review before answering.",
    )
    team.print_response("Build a function that parses ISO dates.")
    ```

=== "Collaborate"

    ```python
    brainstorm = Team(
        members=[ideator_a, ideator_b],
        mode="collaborate",
        model=OpenAIChat(id="gpt-4o"),
    )
    brainstorm.print_response("Propose names for a new analytics product.")
    ```

## Nested teams

A `Team` member can itself be a `Team`, because `members` accepts
`Union[Agent, "Team"]`. This lets you compose departments of specialists.

```python
research_team = Team(
    name="Research",
    members=[web_researcher, paper_researcher],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o-mini"),
)

org = Team(
    name="Editorial",
    members=[research_team, writer, editor],  # a team as a member
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
)

org.print_response("Produce a fact-checked briefing on solid-state batteries.")
```

The outer leader treats the nested team like any other member: it delegates a
task and receives a synthesized result back.

## Design checklist

- **Distinct roles** — overlapping roles confuse delegation; keep them sharp.
- **Pick the simplest mode** that solves the task — `route` is cheapest.
- **Add `instructions`** to the leader to set the overall procedure.
- **Set `success_criteria`** so the leader knows when to stop.
- **Turn on `show_members_responses`** while developing to see each member's
  contribution.
