"""
Unit tests for the planning module — strategies, plan data models, and PlanningAgent.
"""

import pytest
from buddy.planning.planner import (
    PlanStrategy,
    PlanStatus,
    PlanStepType,
    PlanStep,
    ExecutionPlan,
    HierarchicalPlanning,
    ReactiveThinkPlanning,
    DeliberativePlanning,
    HybridPlanning,
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
    step = PlanStep(name="s1", step_type=PlanStepType.ACTION, description="d",
                    status=PlanStatus.FAILED)
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
