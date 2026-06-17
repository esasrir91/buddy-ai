# Inter-Agent Communication

This page describes **how tasks and results move between a `Team` leader and its
members**, and how shared state lets members build on one another. Details are
grounded in `buddy/team/team.py`.

## The basic loop

1. You call `team.run(message)` (or `print_response`).
2. The leader receives the message and decides which member(s) to involve.
3. The leader **delegates a subtask** by calling a member tool; the member runs
   as an agent and returns a `RunResponse`.
4. The member's output comes back to the leader as the tool result.
5. The leader either returns it (`route`) or **synthesizes** a final
   `TeamRunResponse` (`coordinate`).

Members do not talk to each other directly — the leader mediates every exchange.

## Seeing member responses

By default members work quietly behind the leader. Set
`show_members_responses=True` to surface each member's contribution, which is
invaluable while developing.

```python
from buddy import Team
from buddy.models.openai import OpenAIChat

team = Team(
    members=[researcher, writer],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    show_members_responses=True,
)
team.print_response("Draft a release note for v2.2.0.")
```

## Sharing context between members

Two parameters control how much one member sees of the others' work:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `share_member_interactions` | `False` | Forwards previous member interactions to later members |
| `enable_agentic_context` | `False` | Lets the leader maintain a team context and share it with members |

```python
team = Team(
    members=[planner, coder, critic],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    share_member_interactions=True,  # critic sees planner & coder output
    enable_agentic_context=True,     # leader curates shared context
)
```

Use these when later members depend on earlier results — for example a critic
that must review what the coder produced.

## Shared state

A team carries dictionaries that persist information across a run and across
turns:

| Field | Scope |
|-------|-------|
| `session_state` | Per-session state, persisted to storage when configured |
| `team_session_state` | State **shared between the leader and members** |
| `workflow_session_state` | State shared when the team runs inside a workflow |

`add_state_in_messages` (default `False`) injects state variables into the user
and system messages so the model can read them.

```python
team = Team(
    members=[agent_a, agent_b],
    model=OpenAIChat(id="gpt-4o"),
    team_session_state={"customer_tier": "gold"},
    add_state_in_messages=True,
)
```

## History

To let the leader remember earlier turns of a conversation, enable history:

- `add_history_to_messages` (default `False`) — include prior runs in the
  messages sent to the model.
- `num_history_runs` (default `3`) — how many past runs to include.

```python
team = Team(
    members=[agent_a, agent_b],
    model=OpenAIChat(id="gpt-4o"),
    add_history_to_messages=True,
    num_history_runs=5,
)
```

!!! note "`enable_team_history` is deprecated"
    The older `enable_team_history` flag is deprecated in favor of
    `add_history_to_messages`. Prefer the latter in new code.

## Results

`team.run()` returns a `TeamRunResponse` whose `.content` holds the leader's
final synthesized answer. When `stream=True`, `run()` instead yields an iterator
of run/team events you can consume incrementally.
