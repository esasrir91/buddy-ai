"""
Advanced Planning Agent Implementation

Provides hierarchical task planning with adaptive replanning capabilities.
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from buddy.agent.agent import Agent
from buddy.models.base import Model
from buddy.models.message import Message


class PlanStrategy(str, Enum):
    """Planning strategy types"""

    HIERARCHICAL = "hierarchical"
    REACTIVE = "reactive"
    DELIBERATIVE = "deliberative"
    HYBRID = "hybrid"


class PlanStatus(str, Enum):
    """Plan execution status"""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REPLANNING = "replanning"


class PlanStepType(str, Enum):
    """Types of plan steps"""

    ACTION = "action"  # Execute an action/tool
    SUBTASK = "subtask"  # Decomposed subtask
    CONDITION = "condition"  # Conditional branching
    PARALLEL = "parallel"  # Parallel execution
    SEQUENCE = "sequence"  # Sequential execution
    LOOP = "loop"  # Iterative execution


class PlanStep(BaseModel):
    """Individual step in an execution plan"""

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    step_type: PlanStepType
    description: str
    action: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    estimated_duration: Optional[timedelta] = None
    priority: int = 1  # 1=high, 5=low
    retry_count: int = 0
    max_retries: int = 3
    status: PlanStatus = PlanStatus.CREATED
    result: Optional[Any] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    subtasks: List["PlanStep"] = Field(default_factory=list)

    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_completed(self) -> bool:
        return self.status == PlanStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == PlanStatus.FAILED

    @property
    def can_execute(self) -> bool:
        """Check if step can be executed (all dependencies completed)"""
        return self.status == PlanStatus.CREATED


class ExecutionPlan(BaseModel):
    """Complete execution plan with hierarchical structure"""

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    description: str
    steps: List[PlanStep] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_estimated_duration: Optional[timedelta] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    resources_required: List[str] = Field(default_factory=list)

    @property
    def completion_percentage(self) -> float:
        """Calculate plan completion percentage"""
        steps = self.iter_steps()
        if not steps:
            return 0.0
        completed_steps = sum(1 for step in steps if step.is_completed)
        return (completed_steps / len(steps)) * 100

    @property
    def failed_steps(self) -> List[PlanStep]:
        """Get all failed steps"""
        return [step for step in self.iter_steps() if step.is_failed]

    @property
    def executable_steps(self) -> List[PlanStep]:
        """Get steps that can be executed now"""
        return [
            step
            for step in self.iter_steps()
            if step.can_execute
            and all(
                (dependency := self.get_step(dependency_id)) is not None and dependency.is_completed
                for dependency_id in step.dependencies
            )
        ]

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get step by ID"""
        for step in self.iter_steps():
            if step.step_id == step_id:
                return step
        return None

    def iter_steps(self) -> List[PlanStep]:
        """Return all top-level and nested steps in plan order."""
        result = []
        pending = list(reversed(self.steps))
        while pending:
            step = pending.pop()
            result.append(step)
            pending.extend(reversed(step.subtasks))
        return result

    def add_step(self, step: PlanStep) -> None:
        """Add step to plan"""
        if self.get_step(step.step_id) is not None:
            raise ValueError(f"Duplicate step ID: {step.step_id}")
        self.steps.append(step)

    def remove_step(self, step_id: str) -> bool:
        """Remove step from plan"""
        removed = False

        def remove_from(steps: List[PlanStep]) -> None:
            nonlocal removed
            for step in list(steps):
                if step.step_id == step_id:
                    steps.remove(step)
                    removed = True
                else:
                    remove_from(step.subtasks)
                step.dependencies = [dependency for dependency in step.dependencies if dependency != step_id]

        remove_from(self.steps)
        return removed


class PlanningStrategy(BaseModel):
    """Base class for planning strategies"""

    strategy_name: str
    decomposition_model: Optional[Model] = None

    def create_plan(self, goal: str, context: Dict[str, Any]) -> ExecutionPlan:
        """Create execution plan for given goal"""
        raise NotImplementedError


class HierarchicalPlanning(PlanningStrategy):
    """Hierarchical task decomposition planning"""

    strategy_name: str = "hierarchical"
    max_depth: int = 5
    min_subtask_complexity: int = 1

    def create_plan(self, goal: str, context: Dict[str, Any]) -> ExecutionPlan:
        """Create hierarchical execution plan"""
        plan = ExecutionPlan(goal=goal, description=f"Hierarchical plan for: {goal}")

        # Decompose goal into main tasks
        main_tasks = self._decompose_goal(goal, context)

        for task in main_tasks:
            # Further decompose complex tasks
            if self._is_complex_task(task):
                subtasks = self._decompose_task(task, context)
                main_step = PlanStep(
                    name=task["name"],
                    step_type=PlanStepType.SUBTASK,
                    description=task["description"],
                    subtasks=[
                        PlanStep(
                            name=subtask["name"],
                            step_type=PlanStepType.ACTION,
                            description=subtask["description"],
                            action=subtask.get("action"),
                            parameters=subtask.get("parameters", {}),
                        )
                        for subtask in subtasks
                    ],
                )
            else:
                main_step = PlanStep(
                    name=task["name"],
                    step_type=PlanStepType.ACTION,
                    description=task["description"],
                    action=task.get("action"),
                    parameters=task.get("parameters", {}),
                )

            plan.add_step(main_step)

        # Set dependencies
        self._set_dependencies(plan)

        return plan

    def _decompose_goal(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompose a goal with the configured model, or keep it as one task."""
        fallback = [{"name": "complete_goal", "description": goal, "action": None, "parameters": {"context": context}}]
        return self._request_tasks(
            f"Decompose this goal into an ordered list of actionable tasks. Return only JSON with a 'tasks' array. "
            f"Each task must have a name and description; action and parameters are optional.\nGoal: {goal}\n"
            f"Context: {json.dumps(context, default=str)}",
            fallback,
        )

    def _decompose_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Further decompose a task when a model is available."""
        return self._request_tasks(
            f"Break this task into small ordered subtasks. Return only JSON with a 'tasks' array.\n"
            f"Task: {json.dumps(task, default=str)}\nContext: {json.dumps(context, default=str)}",
            [task],
        )

    def _request_tasks(self, prompt: str, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Call any Buddy model implementation and normalize its task response."""
        if self.decomposition_model is None:
            return fallback

        try:
            response = self.decomposition_model.response(messages=[Message(role="user", content=prompt)])
            payload = response.parsed if response.parsed is not None else response.content
            if isinstance(payload, str):
                payload = payload.strip()
                if payload.startswith("```"):
                    payload = payload.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                payload = json.loads(payload)
            if isinstance(payload, dict):
                payload = payload.get("tasks", payload.get("steps"))
            if not isinstance(payload, list):
                return fallback

            tasks = []
            for item in payload:
                if not isinstance(item, dict) or not item.get("name") or not item.get("description"):
                    continue
                parameters = item.get("parameters", {})
                tasks.append(
                    {
                        "name": str(item["name"]),
                        "description": str(item["description"]),
                        "action": item.get("action"),
                        "parameters": parameters if isinstance(parameters, dict) else {},
                    }
                )
            return tasks or fallback
        except Exception:
            return fallback

    def _is_complex_task(self, task: Dict[str, Any]) -> bool:
        """Determine if task needs further decomposition"""
        # Simple heuristic - in practice would use AI model
        return len(task.get("description", "")) > 50

    def _set_dependencies(self, plan: ExecutionPlan) -> None:
        """Set dependencies between plan steps"""
        for i, step in enumerate(plan.steps[1:], 1):
            # Simple sequential dependency
            step.dependencies = [plan.steps[i - 1].step_id]


class ReactiveThinkPlanning(PlanningStrategy):
    """Reactive planning: sense–act loop, no look-ahead."""

    strategy_name: str = "reactive"

    def create_plan(self, goal: str, context: Dict[str, Any]) -> ExecutionPlan:
        plan = ExecutionPlan(goal=goal, description=f"Reactive plan for: {goal}")
        plan.add_step(
            PlanStep(
                name="observe_and_act",
                step_type=PlanStepType.ACTION,
                description=f"Observe current state and act toward: {goal}",
                action="react",
                parameters={"goal": goal, "context": context},
            )
        )
        return plan


class DeliberativePlanning(PlanningStrategy):
    """Deliberative planning: full world-model look-ahead before acting."""

    strategy_name: str = "deliberative"

    def create_plan(self, goal: str, context: Dict[str, Any]) -> ExecutionPlan:
        plan = ExecutionPlan(goal=goal, description=f"Deliberative plan for: {goal}")
        steps = [
            ("model_world", PlanStepType.ACTION, "Build world model from context", "model"),
            ("search_space", PlanStepType.ACTION, "Search solution space for optimal path", "search"),
            ("select_action", PlanStepType.ACTION, "Select best action sequence", "select"),
            ("execute", PlanStepType.ACTION, "Execute selected action sequence", "execute"),
        ]
        for name, stype, desc, action in steps:
            plan.add_step(
                PlanStep(name=name, step_type=stype, description=desc, action=action, parameters={"goal": goal})
            )
        for i, step in enumerate(plan.steps[1:], 1):
            step.dependencies = [plan.steps[i - 1].step_id]
        return plan


class HybridPlanning(PlanningStrategy):
    """Hybrid planning: deliberative backbone with reactive override for failures."""

    strategy_name: str = "hybrid"

    def create_plan(self, goal: str, context: Dict[str, Any]) -> ExecutionPlan:
        deliberative = DeliberativePlanning()
        plan = deliberative.create_plan(goal, context)
        plan.description = f"Hybrid plan for: {goal}"
        plan.metadata["reactive_fallback"] = True
        plan.add_step(
            PlanStep(
                name="reactive_fallback",
                step_type=PlanStepType.ACTION,
                description="Reactive fallback: handle unexpected events",
                action="react_fallback",
                parameters={"goal": goal},
            )
        )
        return plan


class AdvancedPlanningMixin:
    """Mixin providing advanced planning capabilities"""

    def create_adaptive_plan(self, goal: str, context: Dict[str, Any] = None) -> ExecutionPlan:
        """Create adaptive plan that can be modified during execution"""
        if not hasattr(self, "create_execution_plan"):
            raise AttributeError("AdvancedPlanningMixin requires create_execution_plan method")

        plan = self.create_execution_plan(goal, context or {})
        plan.metadata["adaptive"] = True
        plan.metadata["modification_count"] = 0
        return plan

    def replan(self, current_plan: ExecutionPlan, new_context: Dict[str, Any] = None) -> ExecutionPlan:
        """Replan based on current state and new context"""
        new_context = new_context or {}

        # Create new plan with updated context
        updated_plan = self.create_execution_plan(current_plan.goal, {**current_plan.metadata, **new_context})

        # Transfer completed steps
        for old_step in current_plan.iter_steps():
            if old_step.is_completed:
                # Find matching step in new plan and mark as completed
                for new_step in updated_plan.iter_steps():
                    if new_step.name == old_step.name:
                        new_step.status = PlanStatus.COMPLETED
                        new_step.result = old_step.result
                        break

        updated_plan.metadata["modification_count"] = current_plan.metadata.get("modification_count", 0) + 1
        return updated_plan

    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan for better execution"""
        # Remove redundant steps
        optimized_steps = []
        action_steps = {}
        removed_step_ids = {}

        for step in plan.steps:
            if step.action and step.step_type == PlanStepType.ACTION and step.action in action_steps:
                removed_step_ids[step.step_id] = action_steps[step.action].step_id
                continue
            optimized_steps.append(step)
            if step.action and step.step_type == PlanStepType.ACTION:
                action_steps[step.action] = step

        plan.steps = optimized_steps
        for step in plan.iter_steps():
            step.dependencies = list(dict.fromkeys(removed_step_ids.get(dep, dep) for dep in step.dependencies))
        return plan

    def get_plan_complexity(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Calculate plan complexity metrics"""
        steps = plan.iter_steps()
        return {
            "total_steps": len(steps),
            "max_depth": self._plan_depth(plan.steps),
            "total_dependencies": sum(len(step.dependencies) for step in steps),
            "estimated_duration": plan.total_estimated_duration,
            "complexity_score": len(steps) + sum(len(step.dependencies) for step in steps),
        }

    @staticmethod
    def _plan_depth(steps: List[PlanStep], depth: int = 1) -> int:
        return max((AdvancedPlanningMixin._plan_depth(step.subtasks, depth + 1) for step in steps), default=depth - 1)


class PlanningAgent(Agent, AdvancedPlanningMixin):
    """Advanced planning agent with hierarchical task decomposition"""

    planning_strategy: PlanStrategy = PlanStrategy.HIERARCHICAL
    decomposition_model: Optional[Model] = None
    plan_validation: bool = True
    adaptive_replanning: bool = True
    max_planning_iterations: int = 3
    execution_monitoring: bool = True
    max_planning_depth: int = 5

    def __init__(self, **kwargs):
        # Extract planning-specific parameters
        self.planning_strategy = kwargs.pop("planning_strategy", PlanStrategy.HIERARCHICAL)
        self.decomposition_model = kwargs.pop("decomposition_model", None)
        self.plan_validation = kwargs.pop("plan_validation", True)
        self.adaptive_replanning = kwargs.pop("adaptive_replanning", True)
        self.max_planning_iterations = kwargs.pop("max_planning_iterations", 3)
        self.execution_monitoring = kwargs.pop("execution_monitoring", True)
        self.max_planning_depth = kwargs.pop("max_planning_depth", 5)

        # Initialize parent Agent
        super().__init__(**kwargs)

        # Initialize planning-specific attributes
        self._current_plan: Optional[ExecutionPlan] = None
        self._execution_history: List[ExecutionPlan] = []
        self._planning_strategies = {
            PlanStrategy.HIERARCHICAL: HierarchicalPlanning(),
            PlanStrategy.REACTIVE: ReactiveThinkPlanning(),
            PlanStrategy.DELIBERATIVE: DeliberativePlanning(),
            PlanStrategy.HYBRID: HybridPlanning(),
        }

    def create_execution_plan(
        self, goal: str, context: Dict[str, Any] = None, constraints: List[str] = None, resources: List[str] = None
    ) -> ExecutionPlan:
        """Generate hierarchical execution plan with dependency tracking"""

        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")
        context = context or {}
        constraints = constraints or []
        resources = resources or []

        # Select planning strategy
        strategy = self._planning_strategies[self.planning_strategy]
        if not strategy:
            raise ValueError(f"Planning strategy '{self.planning_strategy}' not implemented")
        if isinstance(strategy, HierarchicalPlanning):
            strategy.decomposition_model = self.decomposition_model or self.model

        # Create initial plan
        plan = strategy.create_plan(goal, context)

        # Add constraints and resources
        plan.constraints = constraints
        plan.resources_required = resources

        # Validate plan if enabled
        if self.plan_validation:
            validation_result = self._validate_plan(plan)
            if not validation_result["valid"]:
                # Attempt to fix plan
                plan = self._fix_plan(plan, validation_result["issues"])

        # Set as current plan
        self._current_plan = plan

        return plan

    def execute_plan(self, plan: Optional[ExecutionPlan] = None, monitor: bool = None) -> Dict[str, Any]:
        """Execute the plan with monitoring and adaptive replanning"""

        plan = plan or self._current_plan
        if not plan:
            raise ValueError("No plan to execute")

        monitor = monitor if monitor is not None else self.execution_monitoring

        plan.status = PlanStatus.IN_PROGRESS
        plan.started_at = datetime.now()

        execution_results = {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "total_steps": len(plan.iter_steps()),
            "completed_steps": 0,
            "failed_steps": 0,
            "step_results": [],
        }

        try:
            while True:
                pending_steps = [step for step in plan.steps if step.status == PlanStatus.CREATED]
                if not pending_steps:
                    break
                ready_steps = [step for step in pending_steps if self._can_execute_step(step, plan)]
                if not ready_steps:
                    for step in pending_steps:
                        step.status = PlanStatus.FAILED
                        step.error_message = "Dependencies cannot be satisfied"
                    break

                for step in ready_steps:
                    step_result = self._execute_step(step, plan)
                    execution_results["step_results"].append(step_result)
                    while step.is_failed and step.retry_count < step.max_retries:
                        step.status = PlanStatus.CREATED
                        step_result = self._execute_step(step, plan)
                        execution_results["step_results"].append(step_result)
                    if step.is_failed and self.adaptive_replanning:
                        replan_events = execution_results.get("replanning_events", 0)
                        if replan_events < self.max_planning_iterations:
                            replan_result = self._adaptive_replan(plan, step)
                            if replan_result["replanned"]:
                                execution_results["replanning_events"] = replan_events + 1
                    if monitor:
                        self._monitor_execution(plan, step)

            execution_results["completed_steps"] = sum(1 for step in plan.iter_steps() if step.is_completed)
            execution_results["failed_steps"] = sum(1 for step in plan.iter_steps() if step.is_failed)
            plan.status = PlanStatus.COMPLETED if execution_results["failed_steps"] == 0 else PlanStatus.FAILED
            plan.completed_at = datetime.now()

        except Exception as e:
            plan.status = PlanStatus.FAILED
            execution_results["error"] = str(e)

        # Add to execution history
        self._execution_history.append(plan)

        return execution_results

    def monitor_execution(self, plan: Optional[ExecutionPlan] = None) -> Dict[str, Any]:
        """Real-time plan monitoring with adaptive replanning"""

        plan = plan or self._current_plan
        if not plan:
            return {"status": "no_active_plan"}

        monitoring_data = {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "status": plan.status,
            "completion_percentage": plan.completion_percentage,
            "failed_steps": len(plan.failed_steps),
            "executable_steps": len(plan.executable_steps),
            "total_duration": None,
            "estimated_remaining": None,
        }

        if plan.started_at:
            monitoring_data["total_duration"] = datetime.now() - plan.started_at
        remaining = [step.estimated_duration for step in plan.iter_steps() if step.status == PlanStatus.CREATED]
        if remaining and all(duration is not None for duration in remaining):
            monitoring_data["estimated_remaining"] = sum(remaining, timedelta())

        return monitoring_data

    def validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Public method to validate plan structure and feasibility"""
        return self._validate_plan(plan)

    def _validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate plan structure and feasibility"""
        issues = []

        all_steps = plan.iter_steps()
        step_ids = [step.step_id for step in all_steps]
        if len(step_ids) != len(set(step_ids)):
            issues.append("Duplicate step IDs detected")
        known_ids = set(step_ids)
        missing_dependencies = sorted(
            {dependency for step in all_steps for dependency in step.dependencies if dependency not in known_ids}
        )
        if missing_dependencies:
            issues.append(f"Unknown dependencies: {', '.join(missing_dependencies)}")

        # Check for circular dependencies
        if self._has_circular_dependencies(plan):
            issues.append("Circular dependencies detected")

        # Check resource availability
        if not self._check_resource_availability(plan):
            issues.append("Required resources not available")

        # Check constraint satisfaction
        if not self._check_constraints(plan):
            issues.append("Plan violates constraints")

        return {"valid": len(issues) == 0, "issues": issues}

    def _fix_plan(self, plan: ExecutionPlan, issues: List[str]) -> ExecutionPlan:
        """Attempt to fix plan issues"""
        # Simple implementation - in practice would use AI reasoning
        if "Circular dependencies detected" in issues:
            self._remove_circular_dependencies(plan)
        known_ids = {step.step_id for step in plan.iter_steps()}
        for step in plan.iter_steps():
            step.dependencies = [dependency for dependency in step.dependencies if dependency in known_ids]

        return plan

    def _can_execute_step(self, step: PlanStep, plan: ExecutionPlan) -> bool:
        """Check if step can be executed now"""
        if not step.can_execute:
            return False

        # Check dependencies
        for dep_id in step.dependencies:
            dep_step = plan.get_step(dep_id)
            if not dep_step or not dep_step.is_completed:
                return False

        return True

    def _execute_step(self, step: PlanStep, plan: Optional[ExecutionPlan] = None) -> Dict[str, Any]:
        """Execute individual plan step"""
        step.status = PlanStatus.IN_PROGRESS
        step.start_time = datetime.now()

        try:
            if step.step_type == PlanStepType.ACTION:
                # Execute action/tool
                if step.action:
                    result = self._execute_action(step.action, step.parameters)
                    step.result = result
                    step.status = PlanStatus.COMPLETED
                else:
                    # Use agent reasoning
                    result = self.run(step.description, context=step.parameters)
                    step.result = result
                    step.status = PlanStatus.COMPLETED

            elif step.step_type == PlanStepType.SUBTASK:
                subtask_results = []
                pending = [subtask for subtask in step.subtasks if subtask.status == PlanStatus.CREATED]
                while pending:
                    ready = [
                        subtask
                        for subtask in pending
                        if not subtask.dependencies
                        or (
                            plan is not None
                            and all(
                                (dependency := plan.get_step(dependency_id)) is not None and dependency.is_completed
                                for dependency_id in subtask.dependencies
                            )
                        )
                    ]
                    if not ready:
                        raise ValueError(f"Subtask dependencies cannot be satisfied for {step.name}")
                    for subtask in ready:
                        subtask_results.append(self._execute_step(subtask, plan))
                        pending.remove(subtask)
                step.result = subtask_results
                step.status = (
                    PlanStatus.FAILED
                    if any(result["status"] == PlanStatus.FAILED for result in subtask_results)
                    else PlanStatus.COMPLETED
                )

            else:
                # Other step types
                step.result = f"Executed {step.step_type.value}: {step.name}"
                step.status = PlanStatus.COMPLETED

        except Exception as e:
            step.status = PlanStatus.FAILED
            step.error_message = str(e)
            step.retry_count += 1

        step.end_time = datetime.now()

        return {
            "step_id": step.step_id,
            "name": step.name,
            "status": step.status,
            "result": step.result,
            "error": step.error_message,
            "duration": step.duration,
        }

    def _execute_action(self, action: str, parameters: Dict[str, Any]) -> Any:
        """Execute specific action with parameters"""
        for function in (self._functions_for_model or {}).values():
            if function.name == action and function.entrypoint is not None:
                return function.entrypoint(**parameters)
        for tool in self.tools or []:
            if getattr(tool, "name", None) == action and getattr(tool, "entrypoint", None) is not None:
                return tool.entrypoint(**parameters)
            function = getattr(tool, "functions", {}).get(action)
            if function is not None and function.entrypoint is not None:
                return function.entrypoint(**parameters)
            if callable(tool) and getattr(tool, "__name__", None) == action:
                return tool(**parameters)
        response = self.run(f"Execute the planned action '{action}' with parameters: {parameters}", context=parameters)
        return getattr(response, "content", response)

    def _adaptive_replan(self, plan: ExecutionPlan, failed_step: PlanStep) -> Dict[str, Any]:
        """Adaptive replanning when step fails"""

        if failed_step.retry_count >= failed_step.max_retries:
            # Generate alternative approach
            alternative_steps = self._generate_alternative_steps(failed_step)

            # Replace failed step with alternatives
            step_index = plan.steps.index(failed_step)
            for index, alternative in enumerate(alternative_steps):
                if index == 0:
                    alternative.dependencies = list(failed_step.dependencies)
                else:
                    alternative.dependencies = [alternative_steps[index - 1].step_id]
            if alternative_steps:
                alternative_steps[-1].step_id = failed_step.step_id
            plan.steps[step_index : step_index + 1] = alternative_steps

            return {"replanned": True, "new_steps": len(alternative_steps)}

        return {"replanned": False}

    def _generate_alternative_steps(self, failed_step: PlanStep) -> List[PlanStep]:
        """Generate alternative steps for failed step"""
        # AI-driven alternative generation
        return [
            PlanStep(
                name=f"alternative_{failed_step.name}",
                step_type=PlanStepType.ACTION,
                description=f"Alternative approach for {failed_step.description}",
                action="alternative_action",
                parameters=failed_step.parameters,
            )
        ]

    def _monitor_execution(self, plan: ExecutionPlan, step: PlanStep) -> None:
        """Monitor individual step execution"""
        # Implementation would include real-time monitoring
        pass

    def _has_circular_dependencies(self, plan: ExecutionPlan) -> bool:
        """Check for circular dependencies in plan"""
        # Simple cycle detection implementation
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str) -> bool:
            if step_id in rec_stack:
                return True
            if step_id in visited:
                return False

            visited.add(step_id)
            rec_stack.add(step_id)

            step = plan.get_step(step_id)
            if step:
                for dep_id in step.dependencies:
                    if has_cycle(dep_id):
                        return True

            rec_stack.remove(step_id)
            return False

        for step in plan.steps:
            if has_cycle(step.step_id):
                return True

        return False

    def _check_resource_availability(self, plan: ExecutionPlan) -> bool:
        """Check if required resources are available"""
        # Implementation would check actual resource availability
        return True

    def _check_constraints(self, plan: ExecutionPlan) -> bool:
        """Check if plan satisfies constraints"""
        # Implementation would validate constraints
        return True

    def _remove_circular_dependencies(self, plan: ExecutionPlan) -> None:
        """Remove circular dependencies from plan"""
        visiting = set()
        visited = set()

        def remove_cycles(step: PlanStep) -> None:
            if step.step_id in visited:
                return

            visiting.add(step.step_id)
            retained_dependencies = []
            for dependency_id in step.dependencies:
                if dependency_id in visiting:
                    continue

                dependency = plan.get_step(dependency_id)
                if dependency is not None:
                    remove_cycles(dependency)
                retained_dependencies.append(dependency_id)

            step.dependencies = retained_dependencies
            visiting.remove(step.step_id)
            visited.add(step.step_id)

        for step in plan.steps:
            remove_cycles(step)

    @property
    def current_plan(self) -> Optional[ExecutionPlan]:
        """Get current execution plan"""
        return self._current_plan

    @property
    def execution_history(self) -> List[ExecutionPlan]:
        """Get execution history"""
        return self._execution_history.copy()
