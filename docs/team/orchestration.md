# Orchestration

This page explains **how a `Team` leader coordinates members internally** and the
parameters that shape that behavior. All details are taken from
`buddy/team/team.py`.

## The leader delegates through tools

A team's leader is an LLM driven by the team's `model`. Rather than calling
members directly in Python, the leader is given **member tools**: it invokes a
member by emitting a tool call, the member runs, and its output returns to the
leader as the tool result. The leader then either returns that result (`route`)
or synthesizes a final answer from one or more member results (`coordinate`).

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat

team = Team(
    members=[researcher, writer],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),   # the model that drives delegation
)
```

By default `add_member_tools_to_system_message=True`, so the leader is told which
members and member-tools are available when it plans the run.

## Mode dispatch

At run time the leader branches on `self.mode`:

- **`route`** — choose the single most appropriate member and return its output.
- **`coordinate`** — delegate subtasks to one or more members and merge the
  results into a single response.
- **`collaborate`** — have members work jointly toward a shared result.

## Parameters that shape orchestration

| Parameter | Default | Effect |
|-----------|---------|--------|
| `enable_agentic_context` | `False` | The leader can **maintain a team context** and automatically share it with members across the run. |
| `share_member_interactions` | `False` | Previous member interactions are forwarded to subsequent members, so they see what others produced. |
| `get_member_information_tool` | `False` | Adds a tool the leader can call to look up information about the team's members. |
| `add_member_tools_to_system_message` | `True` | Lists member tools in the leader's system message. |
| `search_knowledge` | `True` | If the team has `knowledge`, the leader gets a knowledge-search tool (Agentic RAG at the team level). |

```python
team = Team(
    members=[planner, coder, critic],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    enable_agentic_context=True,      # leader builds & shares working context
    share_member_interactions=True,   # members see each other's outputs
    get_member_information_tool=True,  # leader can query member capabilities
)
```

## Why these matter

- **`enable_agentic_context`** is the difference between members working in
  isolation and the leader curating a shared, evolving brief. Turn it on when
  later members depend on earlier conclusions.
- **`share_member_interactions`** is lighter weight: it simply relays prior
  member outputs without the leader actively curating them.
- **`get_member_information_tool`** helps the leader route correctly when there
  are many members with similar-sounding roles.

!!! note "Synthesis happens in the leader"
    In `coordinate` mode the final answer is produced by the **leader's** model,
    not concatenated from members. The quality of synthesis therefore depends on
    the leader's `model` and `instructions`.

## Reasoning (optional)

The leader can run a reasoning pass before delegating. Relevant constructor
parameters include `reasoning` (default `False`), `reasoning_model`,
`reasoning_agent`, `reasoning_min_steps` (default `1`) and `reasoning_max_steps`
(default `10`).

See [Communication](communication.md) for how tasks and results actually flow
between the leader and members.
