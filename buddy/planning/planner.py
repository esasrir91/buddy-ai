"""
Advanced Planning Agent Implementation

Provides hierarchical task planning with adaptive replanning capabilities.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from buddy import Agent
from buddy.models import Model


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
        if not self.steps:
            return 0.0
        completed_steps = sum(1 for step in self.steps if step.is_completed)
        return (completed_steps / len(self.steps)) * 100

    @property
    def failed_steps(self) -> List[PlanStep]:
        """Get all failed steps"""
        return [step for step in self.steps if step.is_failed]

    @property
    def executable_steps(self) -> List[PlanStep]:
        """Get steps that can be executed now"""
        return [step for step in self.steps if step.can_execute]

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get step by ID"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def add_step(self, step: PlanStep) -> None:
        """Add step to plan"""
        self.steps.append(step)

    def remove_step(self, step_id: str) -> bool:
        """Remove step from plan"""
        for i, step in enumerate(self.steps):
            if step.step_id == step_id:
                self.steps.pop(i)
                return True
        return False


class PlanningStrategy(BaseModel):
    """Base class for planning strategies"""

    strategy_name: str

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
        """Decompose high-level goal into main tasks"""
        # This would use AI model to decompose goal
        # For now, return example decomposition
        return [
            {
                "name": "analyze_requirements",
                "description": f"Analyze requirements for: {goal}",
                "action": "analyze",
                "parameters": {"goal": goal, "context": context},
            },
            {
                "name": "plan_execution",
                "description": "Create detailed execution plan",
                "action": "plan",
                "parameters": {"requirements": "analyzed_requirements"},
            },
            {
                "name": "execute_plan",
                "description": "Execute the planned actions",
                "action": "execute",
                "parameters": {"plan": "detailed_plan"},
            },
            {
                "name": "validate_results",
                "description": "Validate execution results",
                "action": "validate",
                "parameters": {"results": "execution_results"},
            },
        ]

    def _decompose_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompose complex task into subtasks"""
        # AI-driven task decomposition
        return [
            {
                "name": f"{task['name']}_step_1",
                "description": f"First step of {task['name']}",
                "action": "step1",
                "parameters": {},
            },
            {
                "name": f"{task['name']}_step_2",
                "description": f"Second step of {task['name']}",
                "action": "step2",
                "parameters": {},
            },
        ]

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
        for old_step in current_plan.steps:
            if old_step.is_completed:
                # Find matching step in new plan and mark as completed
                for new_step in updated_plan.steps:
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
        seen_actions = set()

        for step in plan.steps:
            if step.action not in seen_actions or step.step_type != PlanStepType.ACTION:
                optimized_steps.append(step)
                if step.action:
                    seen_actions.add(step.action)

        plan.steps = optimized_steps
        return plan

    def get_plan_complexity(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Calculate plan complexity metrics"""
        return {
            "total_steps": len(plan.steps),
            "max_depth": max((len(step.subtasks) for step in plan.steps), default=0),
            "total_dependencies": sum(len(step.dependencies) for step in plan.steps),
            "estimated_duration": plan.total_estimated_duration,
            "complexity_score": len(plan.steps) + sum(len(step.subtasks) for step in plan.steps),
        }


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

        context = context or {}
        constraints = constraints or []
        resources = resources or []

        # Select planning strategy
        strategy = self._planning_strategies[self.planning_strategy]
        if not strategy:
            raise ValueError(f"Planning strategy '{self.planning_strategy}' not implemented")

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
            "total_steps": len(plan.steps),
            "completed_steps": 0,
            "failed_steps": 0,
            "step_results": [],
        }

        try:
            for step in plan.steps:
                if not self._can_execute_step(step, plan):
                    continue

                step_result = self._execute_step(step)
                execution_results["step_results"].append(step_result)

                if step.is_completed:
                    execution_results["completed_steps"] += 1
                elif step.is_failed:
                    execution_results["failed_steps"] += 1

                    if self.adaptive_replanning:
                        replan_result = self._adaptive_replan(plan, step)
                        if replan_result["replanned"]:
                            execution_results["replanning_events"] = execution_results.get("replanning_events", 0) + 1

                # Monitor execution if enabled
                if monitor:
                    self._monitor_execution(plan, step)

            # Complete plan
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

        return monitoring_data

    def validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Public method to validate plan structure and feasibility"""
        return self._validate_plan(plan)

    def _validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate plan structure and feasibility"""
        issues = []

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

    def _execute_step(self, step: PlanStep) -> Dict[str, Any]:
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
                # Execute subtasks
                subtask_results = []
                for subtask in step.subtasks:
                    subtask_result = self._execute_step(subtask)
                    subtask_results.append(subtask_result)

                step.result = subtask_results
                step.status = PlanStatus.COMPLETED

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
        # Implementation would integrate with tool system
        # For now, return mock result
        return f"Executed {action} with parameters: {parameters}"

    def _adaptive_replan(self, plan: ExecutionPlan, failed_step: PlanStep) -> Dict[str, Any]:
        """Adaptive replanning when step fails"""

        if failed_step.retry_count >= failed_step.max_retries:
            # Generate alternative approach
            alternative_steps = self._generate_alternative_steps(failed_step)

            # Replace failed step with alternatives
            step_index = plan.steps.index(failed_step)
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
        # Implementation would break dependency cycles
        pass

    @property
    def current_plan(self) -> Optional[ExecutionPlan]:
        """Get current execution plan"""
        return self._current_plan

    @property
    def execution_history(self) -> List[ExecutionPlan]:
        """Get execution history"""
        return self._execution_history.copy()
