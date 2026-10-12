"""
Unit tests for the planning module — strategies, plan data models, and PlanningAgent.
"""

from buddy.planning.planner import (
    DeliberativePlanning,
    ExecutionPlan,
    HierarchicalPlanning,
    HybridPlanning,
    PlanStatus,
    PlanStep,
    PlanStepType,
    ReactiveThinkPlanning,
)

# ── PlanStep ──────────────────────────────────────────────────────────────────


def test_plan_step_defaults():
    step = PlanStep(name="test", step_type=PlanStepType.ACTION, description="a step")
    assert step.status == PlanStatus.CREATED
    assert step.retry_count == 0
    assert step.is_completed is False
    assert step.is_failed is False
    assert step.can_execute is True


def test_plan_step_duration_none_before_execution():
    step = PlanStep(name="s", step_type=PlanStepType.ACTION, description="d")
    assert step.duration is None


# ── ExecutionPlan ─────────────────────────────────────────────────────────────


def test_execution_plan_empty_completion():
    plan = ExecutionPlan(goal="test goal", description="desc")
    assert plan.completion_percentage == 0.0


def test_execution_plan_add_remove_step():
    plan = ExecutionPlan(goal="g", description="d")
    step = PlanStep(name="s1", step_type=PlanStepType.ACTION, description="d")
    plan.add_step(step)
    assert len(plan.steps) == 1
    removed = plan.remove_step(step.step_id)
    assert removed is True
    assert len(plan.steps) == 0


def test_execution_plan_get_step():
    plan = ExecutionPlan(goal="g", description="d")
    step = PlanStep(name="s1", step_type=PlanStepType.ACTION, description="d")
    plan.add_step(step)
    found = plan.get_step(step.step_id)
    assert found is not None
    assert found.step_id == step.step_id


def test_execution_plan_failed_steps():
    plan = ExecutionPlan(goal="g", description="d")
    step = PlanStep(name="s1", step_type=PlanStepType.ACTION, description="d", status=PlanStatus.FAILED)
    plan.add_step(step)
    assert len(plan.failed_steps) == 1


# ── Hierarchical Planning ─────────────────────────────────────────────────────


def test_hierarchical_planning_creates_plan():
    strategy = HierarchicalPlanning()
    plan = strategy.create_plan("write a report", {})
    assert plan.goal == "write a report"
    assert len(plan.steps) > 0
    assert plan.status == PlanStatus.CREATED


def test_hierarchical_planning_sets_dependencies():
    strategy = HierarchicalPlanning()
    plan = strategy.create_plan("test goal", {})
    for step in plan.steps[1:]:
        assert len(step.dependencies) > 0


# ── Reactive Planning ─────────────────────────────────────────────────────────


def test_reactive_planning_creates_plan():
    strategy = ReactiveThinkPlanning()
    plan = strategy.create_plan("respond to event", {"state": "active"})
    assert plan.goal == "respond to event"
    assert len(plan.steps) >= 1
    assert plan.steps[0].action == "react"


# ── Deliberative Planning ─────────────────────────────────────────────────────


def test_deliberative_planning_creates_plan():
    strategy = DeliberativePlanning()
    plan = strategy.create_plan("solve problem", {})
    assert plan.goal == "solve problem"
    assert len(plan.steps) == 4
    step_names = [s.name for s in plan.steps]
    assert "model_world" in step_names
    assert "execute" in step_names


def test_deliberative_planning_sequential_dependencies():
    strategy = DeliberativePlanning()
    plan = strategy.create_plan("test", {})
    for i, step in enumerate(plan.steps[1:], 1):
        assert plan.steps[i - 1].step_id in step.dependencies


# ── Hybrid Planning ───────────────────────────────────────────────────────────


def test_hybrid_planning_creates_plan():
    strategy = HybridPlanning()
    plan = strategy.create_plan("complex task", {})
    assert plan.goal == "complex task"
    assert plan.metadata.get("reactive_fallback") is True
    step_names = [s.name for s in plan.steps]
    assert "reactive_fallback" in step_names


# ── Circular dependency detection ─────────────────────────────────────────────


def test_no_circular_dependency_in_hierarchical_plan():
    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent(name="test_agent")
    plan = agent.create_execution_plan("test goal")
    result = agent._validate_plan(plan)
    assert "Circular dependencies detected" not in result.get("issues", [])


def test_hierarchical_planning_uses_model_tasks_from_json():
    from buddy.models.response import ModelResponse
    from buddy.planning.planner import HierarchicalPlanning

    class ModelStub:
        def response(self, **kwargs):
            return ModelResponse(content='```json\n{"tasks":[{"name":"research","description":"Find sources"}]}\n```')

    strategy = HierarchicalPlanning.model_construct(decomposition_model=ModelStub())
    tasks = strategy._request_tasks("prompt", [])
    assert tasks == [{"name": "research", "description": "Find sources", "action": None, "parameters": {}}]


def test_plan_validation_reports_missing_dependencies():
    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent(name="validator")
    plan = ExecutionPlan(goal="g", description="d")
    plan.add_step(PlanStep(name="blocked", step_type=PlanStepType.ACTION, description="d", dependencies=["missing"]))
    result = agent.validate_plan(plan)
    assert result["valid"] is False
    assert any("Unknown dependencies" in issue for issue in result["issues"])


def test_execute_plan_resolves_dependencies_out_of_order():
    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent(adaptive_replanning=False)
    executed = []
    agent._execute_action = lambda action, parameters: executed.append(action) or action
    prerequisite = PlanStep(name="first", step_type=PlanStepType.ACTION, description="d", action="first")
    dependent = PlanStep(
        name="second",
        step_type=PlanStepType.ACTION,
        description="d",
        action="second",
        dependencies=[prerequisite.step_id],
    )
    plan = ExecutionPlan(goal="g", description="d", steps=[dependent, prerequisite])

    result = agent.execute_plan(plan)
    assert executed == ["first", "second"]
    assert result["completed_steps"] == 2
    assert result["failed_steps"] == 0


def test_planner_executes_matching_registered_tool():
    from types import SimpleNamespace

    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent()
    tool_function = SimpleNamespace(name="lookup", entrypoint=lambda query: f"found: {query}")
    agent.tools = [SimpleNamespace(functions={"lookup": tool_function})]
    assert agent._execute_action("lookup", {"query": "item"}) == "found: item"


def test_optimization_remaps_dependencies_from_duplicate_actions():
    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent()
    first = PlanStep(name="first", step_type=PlanStepType.ACTION, description="d", action="lookup")
    duplicate = PlanStep(name="duplicate", step_type=PlanStepType.ACTION, description="d", action="lookup")
    dependent = PlanStep(
        name="dependent",
        step_type=PlanStepType.ACTION,
        description="d",
        action="summarize",
        dependencies=[duplicate.step_id],
    )
    plan = ExecutionPlan(goal="g", description="d", steps=[first, duplicate, dependent])

    agent.optimize_plan(plan)
    assert plan.steps == [first, dependent]
    assert dependent.dependencies == [first.step_id]


def test_replan_preserves_replaced_step_id_for_downstream_dependencies():
    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent()
    failed = PlanStep(
        name="failed", step_type=PlanStepType.ACTION, description="d", status=PlanStatus.FAILED, retry_count=3
    )
    dependent = PlanStep(
        name="dependent", step_type=PlanStepType.ACTION, description="d", dependencies=[failed.step_id]
    )
    plan = ExecutionPlan(goal="g", description="d", steps=[failed, dependent])

    result = agent._adaptive_replan(plan, failed)
    assert result["replanned"] is True
    assert plan.steps[0].step_id == failed.step_id
    assert dependent.dependencies == [plan.steps[0].step_id]


def test_execute_plan_retries_transient_action_failures():
    from buddy.planning.planner import PlanningAgent

    agent = PlanningAgent(adaptive_replanning=False)
    attempts = 0

    def transient_action(action, parameters):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary failure")
        return "done"

    agent._execute_action = transient_action
    plan = ExecutionPlan(
        goal="g",
        description="d",
        steps=[PlanStep(name="retry", step_type=PlanStepType.ACTION, description="d", action="run", max_retries=2)],
    )

    result = agent.execute_plan(plan)
    assert attempts == 2
    assert result["completed_steps"] == 1
    assert result["failed_steps"] == 0
