# Team API

`Team` orchestrates multiple agents (and even nested teams) toward a shared
goal. It is defined in `buddy.team.team` and re-exported as `from buddy import
Team`.

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat

researcher = Agent(name="researcher", role="Find facts", model=OpenAIChat(id="gpt-4o-mini"))
writer = Agent(name="writer", role="Write the final piece", model=OpenAIChat(id="gpt-4o"))

team = Team(
    name="content_team",
    members=[researcher, writer],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
)
team.print_response("Write a short article about quantum computing.")
```

!!! warning "Use `members=`, not `agents=`"
    The first parameter is `members` (a list of `Agent` or `Team`). It is
    **required** — a team must have at least one member.

## Core parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `members` | `list[Agent \| Team]` | — (required) | The team members. |
| `mode` | `"route" \| "coordinate" \| "collaborate"` | `"coordinate"` | How the team operates (see below). |
| `model` | `Model` | `None` | Model used by the team leader. |
| `name` | `str` | `None` | Team name. |
| `role` | `str` | `None` | Role when this team is nested in another team. |
| `instructions` | `str \| list[str] \| Callable` | `None` | Instructions for the team leader. |
| `description` | `str` | `None` | High-level description. |
| `success_criteria` | `str` | `None` | Definition of a successful outcome. |
| `markdown` | `bool` | `False` | Format responses as Markdown. |

### Modes

| Mode | Behavior |
|------|----------|
| `coordinate` | The leader plans and delegates subtasks to members, then synthesizes a final answer. |
| `route` | The leader routes each request to the single most appropriate member. |
| `collaborate` | Members work together on the task, sharing context. |

## Memory, knowledge & tools

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory` | `TeamMemory \| Memory` | `None` | Shared memory backend. |
| `enable_user_memories` | `bool` | `False` | Maintain user memories. |
| `knowledge` | `AgentKnowledge` | `None` | Team-level knowledge base. |
| `search_knowledge` | `bool` | `True` | Give the team a knowledge-search tool. |
| `tools` | `list[Toolkit \| Callable \| Function \| dict]` | `None` | Team-leader tools. |
| `enable_agentic_context` | `bool` | `False` | Let the leader maintain shared context across members. |
| `share_member_interactions` | `bool` | `False` | Share member outputs with other members. |
| `add_history_to_messages` | `bool` | `False` | Include prior turns. |
| `num_history_runs` | `int` | `3` | Past runs to include when history is on. |
| `show_members_responses` | `bool` | `False` | Include member responses in the output. |
| `response_model` | `Type[BaseModel]` | `None` | Parse the final answer into a Pydantic model. |

## Methods

```python
def run(message, *, stream=None, stream_intermediate_steps=None,
        session_id=None, session_state=None, user_id=None, retries=None,
        audio=None, images=None, videos=None, files=None,
        knowledge_filters=None, **kwargs)
        -> TeamRunResponse | Iterator[RunResponseEvent | TeamRunResponseEvent]
```

| Method | Returns | Description |
|--------|---------|-------------|
| `run(message, ...)` | `TeamRunResponse` | Run the team. With `stream=True`, returns an event iterator. |
| `arun(message, ...)` | `TeamRunResponse` (awaitable) | Async version of `run`. |
| `print_response(message, ...)` | `None` | Run and pretty-print to the console. |
| `aprint_response(message, ...)` | `None` (awaitable) | Async version of `print_response`. |

## TeamRunResponse

`run()` returns a `TeamRunResponse` (`buddy.run.team.TeamRunResponse`). It mirrors
`RunResponse` and adds member results:

| Field | Type | Description |
|-------|------|-------------|
| `content` | `Any` | The team's final answer. |
| `member_responses` | `list[TeamRunResponse \| RunResponse]` | Each member's individual response. |
| `messages` | `list[Message]` | Full message list for the run. |
| `metrics` | `dict` | Aggregated token/timing metrics. |
| `tools` | `list[ToolExecution]` | Tool calls made by the team leader. |
| `team_id` / `team_name` / `session_id` | `str` | Identifiers. |
| `status` | `RunStatus` | Run status. |

!!! tip "Inspecting delegation"
    Iterate `response.member_responses` to see exactly what each agent
    contributed — useful when debugging routing or coordination decisions.
