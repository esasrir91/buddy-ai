# Planning

`PlanningAgent` (`buddy.planning`) extends [`Agent`](../agents/agent-class.md)
with hierarchical task planning: it decomposes a goal into an `ExecutionPlan` of
steps, executes them with dependency tracking, and can adaptively replan when a
step fails.

Planning is feature-gated:

```python
from buddy import check_feature
assert check_feature("planning")

from buddy import PlanningAgent, ExecutionPlan, PlanStep, PlanStatus
```

## Strategies

`PlanStrategy` selects how a goal is turned into a plan:

| Member | Behavior |
|--------|----------|
| `HIERARCHICAL` | Decompose the goal into tasks and subtasks (default). |
| `REACTIVE` | A single sense–act step, no look-ahead. |
| `DELIBERATIVE` | Full look-ahead: model world → search → select → execute. |
| `HYBRID` | Deliberative backbone with a reactive fallback step. |

## Creating and executing a plan

```python
from buddy import PlanningAgent
from buddy.models.openai import OpenAIChat
from buddy.planning import PlanStrategy

agent = PlanningAgent(
    model=OpenAIChat(id="gpt-4o"),
    planning_strategy=PlanStrategy.HIERARCHICAL,
    adaptive_replanning=True,
)

plan = agent.create_execution_plan(
    goal="Launch a product landing page",
    constraints=["Ship within one week"],
    resources=["design team", "CMS"],
)

results = agent.execute_plan(plan)
print(results["completed_steps"], "/", results["total_steps"])
```

`create_execution_plan(goal, context=None, constraints=None, resources=None)`
returns an `ExecutionPlan` and stores it as `agent.current_plan`. `execute_plan`
returns a results dict with `plan_id`, `goal`, `total_steps`, `completed_steps`,
`failed_steps`, and per-step `step_results`.

!!! note "Step actions are scaffolding"
    `execute_plan` walks the steps, honoring dependencies and retries. Steps with
    an `action` are dispatched through an internal executor that currently returns
    placeholder results, while steps without an action fall back to
    `agent.run(...)`. Wire real tools into the action executor to make plans do
    useful work.

## The ExecutionPlan

`ExecutionPlan` is a Pydantic model:

| Field | Description |
|-------|-------------|
| `plan_id` | Auto-generated UUID. |
| `goal` / `description` | What the plan achieves. |
| `steps` | List of `PlanStep`. |
| `status` | A `PlanStatus` value. |
| `success_criteria` / `constraints` / `resources_required` | Plan metadata. |

Useful properties and helpers: `completion_percentage`, `failed_steps`,
`executable_steps`, `get_step(step_id)`, `add_step(step)`, `remove_step(step_id)`.

## PlanStep

Each `PlanStep` carries:

| Field | Description |
|-------|-------------|
| `step_id` | Auto-generated UUID. |
| `name` / `description` | Human-readable step. |
| `step_type` | A `PlanStepType` (see below). |
| `action` / `parameters` | Action name and its arguments. |
| `dependencies` | IDs of steps that must complete first. |
| `priority` | `1` (high) to `5` (low). |
| `retry_count` / `max_retries` | Retry bookkeeping (`max_retries` default `3`). |
| `status` | A `PlanStatus` value. |
| `subtasks` | Nested `PlanStep`s for decomposed work. |

`PlanStepType` members: `ACTION`, `SUBTASK`, `CONDITION`, `PARALLEL`,
`SEQUENCE`, `LOOP`.

## Plan status

`PlanStatus` tracks lifecycle for both plans and steps:

| Member | Meaning |
|--------|---------|
| `CREATED` | Not yet started. |
| `IN_PROGRESS` | Currently executing. |
| `COMPLETED` | Finished successfully. |
| `FAILED` | Execution failed. |
| `CANCELLED` | Aborted. |
| `REPLANNING` | Being regenerated. |

## Monitoring and replanning

```python
status = agent.monitor_execution(plan)
print(status["completion_percentage"], status["failed_steps"])

# Validate structure (cycles, constraints, resources)
report = agent.validate_plan(plan)
print(report["valid"], report["issues"])
```

When `adaptive_replanning=True`, a step that exhausts its retries triggers
generation of alternative steps in place of the failed one. The
`AdvancedPlanningMixin` also provides `replan()`, `optimize_plan()`, and
`get_plan_complexity()` for managing plans over time.

!!! tip
    Use `validate_plan()` before executing — it checks for circular dependencies
    and (extensible) resource/constraint satisfaction so failures surface early.
