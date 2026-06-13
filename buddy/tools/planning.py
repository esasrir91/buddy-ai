from textwrap import dedent
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from buddy.agent import Agent
from buddy.planning import PlanningAgent, ExecutionPlan, PlanStatus, PlanStrategy
from buddy.team.team import Team
from buddy.tools import Toolkit
from buddy.utils.log import log_debug, log_error, logger


class PlanningTools(Toolkit):
    def __init__(
        self,
        create_plan: bool = True,
        validate_plan: bool = True,
        monitor_plan: bool = True,
        replan: bool = True,
        optimize_plan: bool = True,
        todo: bool = True,
        create_todo: bool = True,
        manage_todos: bool = True,
        instructions: Optional[str] = None,
        add_instructions: bool = False,
        **kwargs,
    ):
        """A toolkit that provides advanced planning capabilities for complex task decomposition."""

        # Add instructions for using this toolkit
        if instructions is None:
            self.instructions = dedent("""\
            ## Using Planning Tools
            These tools provide advanced planning capabilities for breaking down complex goals into manageable, executable steps.

            ### Available Planning Tools:
            - **create_plan**: Generate hierarchical execution plans with step-by-step decomposition
            - **validate_plan**: Check plan feasibility, dependencies, and constraints
            - **monitor_plan**: Track plan execution progress and status
            - **replan**: Adapt existing plans based on new context or failures  
            - **optimize_plan**: Improve plan efficiency and remove redundant steps
            - **create_todo**: Create actionable todos from plans or individual tasks
            - **manage_todos**: Track, update, and complete todos with status management

            ### Todo Integration:
            - Automatically convert plan steps into actionable todos
            - Track todo completion and link back to plans
            - Manage todo priorities and deadlines
            - Support todo dependencies and prerequisites

            ### Planning Guidelines:
            - Use create_plan for complex goals that need structured breakdown
            - Validate plans before execution to catch potential issues
            - Monitor plans during execution to track progress
            - Use replan when context changes or steps fail
            - Optimize plans to improve efficiency and resource usage

            ### Best Practices:
            - Start with high-level goals and let the planner decompose them
            - Include relevant context about resources, constraints, and requirements
            - Validate plans especially for critical or resource-intensive tasks
            - Monitor execution to enable adaptive replanning when needed
            - Use todos to break down plans into immediate actionable items
            - Track todo completion to monitor overall plan progress
            - Link todos to plan steps for comprehensive progress tracking
            """)
        else:
            self.instructions = instructions

        tools: List[Any] = []
        if create_plan:
            tools.append(self.create_plan)
        if validate_plan:
            tools.append(self.validate_plan)
        if monitor_plan:
            tools.append(self.monitor_plan)
        if replan:
            tools.append(self.replan)
        if optimize_plan:
            tools.append(self.optimize_plan)
        if create_todo:
            tools.append(self.create_todo)
        if manage_todos:
            tools.append(self.manage_todos)

        super().__init__(
            name="planning_tools",
            instructions=self.instructions,
            add_instructions=add_instructions,
            tools=tools,
            **kwargs,
        )

    def create_plan(
        self, 
        agent: Union[Agent, Team], 
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: str = "hierarchical",
        constraints: Optional[List[str]] = None,
        resources: Optional[List[str]] = None
    ) -> str:
        """Create a comprehensive execution plan for a complex goal using hierarchical decomposition.
        
        This tool breaks down high-level goals into structured, executable steps with dependencies.

        Args:
            goal: The high-level goal to plan for (e.g., "Launch a new product feature")
            context: Additional context like team size, timeline, budget constraints
            strategy: Planning strategy - "hierarchical", "reactive", "deliberative", or "hybrid"
            constraints: List of constraints or limitations (e.g., ["Budget: $10K", "Timeline: 2 weeks"])
            resources: List of available resources (e.g., ["Development team", "QA team", "AWS infrastructure"])

        Returns:
            A detailed execution plan with steps, dependencies, and timeline
        """
        try:
            log_debug(f"Creating execution plan for goal: {goal}")

            # Create a planning agent if the current agent doesn't have planning capabilities
            if not hasattr(agent, 'create_execution_plan'):
                planner = PlanningAgent(
                    name=f"{agent.name}_planner",
                    planning_strategy=PlanStrategy(strategy),
                    plan_validation=True,
                    adaptive_replanning=True
                )
            else:
                planner = agent

            # Create the execution plan
            plan = planner.create_execution_plan(
                goal=goal,
                context=context or {},
                constraints=constraints or [],
                resources=resources or []
            )

            # Store the plan in agent's session state
            if agent.session_state is None:
                agent.session_state = {}
            if "execution_plans" not in agent.session_state:
                agent.session_state["execution_plans"] = {}
            agent.session_state["execution_plans"][plan.plan_id] = plan.model_dump_json()

            # Auto-create todos for plan steps
            todos_created = self._auto_create_todos_from_plan(agent, plan)
            
            # Format the plan for display
            plan_summary = self._format_plan_summary(plan)
            
            # Add todos summary if any were created
            if todos_created > 0:
                plan_summary += f"\n\n🎯 Auto-created {todos_created} todos from plan steps"
                plan_summary += "\n💡 Use manage_todos(action='list') to see all todos"
            
            logger.info(f"Created execution plan {plan.plan_id} with {len(plan.steps)} steps and {todos_created} todos")
            return plan_summary

        except Exception as e:
            log_error(f"Error creating execution plan: {e}")
            return f"Failed to create execution plan: {str(e)}"

    def validate_plan(self, agent: Union[Agent, Team], plan_id: str) -> str:
        """Validate an execution plan for feasibility, dependencies, and constraint satisfaction.

        Args:
            plan_id: ID of the plan to validate

        Returns:
            Validation results with any issues found
        """
        try:
            # Retrieve plan from session state
            plan = self._get_plan_from_session(agent, plan_id)
            if not plan:
                return f"Plan {plan_id} not found"

            # Create planner for validation
            planner = PlanningAgent(name="validator")
            validation_result = planner.validate_plan(plan)

            # Format validation results
            if validation_result['valid']:
                return f"✅ Plan {plan_id} is valid and ready for execution"
            else:
                issues = "\n".join([f"- {issue}" for issue in validation_result['issues']])
                return f"❌ Plan {plan_id} has issues:\n{issues}"

        except Exception as e:
            log_error(f"Error validating plan: {e}")
            return f"Failed to validate plan: {str(e)}"

    def monitor_plan(self, agent: Union[Agent, Team], plan_id: str) -> str:
        """Monitor execution progress and status of a plan.

        Args:
            plan_id: ID of the plan to monitor

        Returns:
            Current plan status, progress, and execution metrics
        """
        try:
            # Retrieve plan from session state
            plan = self._get_plan_from_session(agent, plan_id)
            if not plan:
                return f"Plan {plan_id} not found"

            # Create planner for monitoring
            planner = PlanningAgent(name="monitor")
            monitoring_data = planner.monitor_execution(plan)

            # Format monitoring data
            status_report = dedent(f"""\
            📊 Plan Monitoring Report
            Plan ID: {plan.plan_id}
            Goal: {plan.goal}
            Status: {plan.status.value}
            Progress: {plan.completion_percentage:.1f}% complete
            
            Steps Summary:
            - Total Steps: {len(plan.steps)}
            - Completed: {len([s for s in plan.steps if s.status == PlanStatus.COMPLETED])}
            - In Progress: {len([s for s in plan.steps if s.status == PlanStatus.IN_PROGRESS])}
            - Failed: {len([s for s in plan.steps if s.status == PlanStatus.FAILED])}
            - Pending: {len([s for s in plan.steps if s.status == PlanStatus.CREATED])}
            """)

            return status_report

        except Exception as e:
            log_error(f"Error monitoring plan: {e}")
            return f"Failed to monitor plan: {str(e)}"

    def replan(
        self, 
        agent: Union[Agent, Team], 
        plan_id: str, 
        new_context: Optional[Dict[str, Any]] = None,
        reason: str = "Context changed"
    ) -> str:
        """Adapt an existing plan based on new context, failures, or changed requirements.

        Args:
            plan_id: ID of the plan to replan
            new_context: Updated context or new requirements
            reason: Reason for replanning (e.g., "Step failed", "Requirements changed")

        Returns:
            Updated plan with modifications
        """
        try:
            # Retrieve plan from session state
            current_plan = self._get_plan_from_session(agent, plan_id)
            if not current_plan:
                return f"Plan {plan_id} not found"

            # Create planner for replanning
            planner = PlanningAgent(name="replanner", adaptive_replanning=True)
            
            # Perform replanning
            updated_plan = planner.replan(current_plan, new_context or {})

            # Update session state
            agent.session_state["execution_plans"][updated_plan.plan_id] = updated_plan.model_dump_json()

            # Format replan results
            modification_count = updated_plan.metadata.get("modification_count", 0)
            plan_summary = self._format_plan_summary(updated_plan)

            result = dedent(f"""\
            🔄 Plan Replanned Successfully
            Reason: {reason}
            Modification #: {modification_count}
            Original Plan: {plan_id}
            Updated Plan: {updated_plan.plan_id}
            
            {plan_summary}
            """)

            return result

        except Exception as e:
            log_error(f"Error replanning: {e}")
            return f"Failed to replan: {str(e)}"

    def optimize_plan(self, agent: Union[Agent, Team], plan_id: str) -> str:
        """Optimize an execution plan for better efficiency and resource usage.

        Args:
            plan_id: ID of the plan to optimize

        Returns:
            Optimized plan with improvements summary
        """
        try:
            # Retrieve plan from session state
            plan = self._get_plan_from_session(agent, plan_id)
            if not plan:
                return f"Plan {plan_id} not found"

            # Get original complexity
            planner = PlanningAgent(name="optimizer")
            original_complexity = planner.get_plan_complexity(plan)

            # Optimize the plan
            optimized_plan = planner.optimize_plan(plan)

            # Get new complexity
            new_complexity = planner.get_plan_complexity(optimized_plan)

            # Update session state
            agent.session_state["execution_plans"][plan_id] = optimized_plan.model_dump_json()

            # Format optimization results
            improvements = []
            if new_complexity['total_steps'] < original_complexity['total_steps']:
                improvements.append(f"Reduced steps from {original_complexity['total_steps']} to {new_complexity['total_steps']}")
            if new_complexity['complexity_score'] < original_complexity['complexity_score']:
                improvements.append(f"Reduced complexity score from {original_complexity['complexity_score']} to {new_complexity['complexity_score']}")

            if improvements:
                improvement_text = "\n".join([f"- {imp}" for imp in improvements])
                return f"⚡ Plan Optimized Successfully:\n{improvement_text}"
            else:
                return f"ℹ️ Plan {plan_id} is already well-optimized"

        except Exception as e:
            log_error(f"Error optimizing plan: {e}")
            return f"Failed to optimize plan: {str(e)}"

    def _auto_create_todos_from_plan(self, agent: Union[Agent, Team], plan: ExecutionPlan) -> int:
        """Automatically create todos from plan steps"""
        try:
            # Initialize todos if needed
            if agent.session_state is None:
                agent.session_state = {}
            if "todos" not in agent.session_state:
                agent.session_state["todos"] = {}
            
            todos_created = 0
            
            # Create todos for each plan step
            for step in plan.steps:
                # Determine priority based on step characteristics
                priority = "high" if step.priority <= 2 else "medium" if step.priority <= 3 else "low"
                
                # Create todo
                import uuid
                todo_id = str(uuid.uuid4())[:8]
                
                todo = {
                    "id": todo_id,
                    "title": f"Plan Step: {step.name}",
                    "description": step.description,
                    "priority": priority,
                    "deadline": None,  # Could be derived from step timing
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                    "completed_at": None,
                    "plan_id": plan.plan_id,
                    "step_id": step.step_id,
                    "dependencies": step.dependencies,
                    "tags": ["auto-generated", "plan-step"]
                }
                
                # Store todo
                agent.session_state["todos"][todo_id] = todo
                todos_created += 1
                
                # Create todos for subtasks if they exist
                for subtask in step.subtasks:
                    subtask_todo_id = str(uuid.uuid4())[:8]
                    subtask_todo = {
                        "id": subtask_todo_id,
                        "title": f"Subtask: {subtask.name}",
                        "description": subtask.description,
                        "priority": "medium",
                        "deadline": None,
                        "status": "pending", 
                        "created_at": datetime.now().isoformat(),
                        "completed_at": None,
                        "plan_id": plan.plan_id,
                        "step_id": subtask.step_id,
                        "dependencies": [todo_id],  # Depend on parent step
                        "tags": ["auto-generated", "subtask"]
                    }
                    
                    agent.session_state["todos"][subtask_todo_id] = subtask_todo
                    todos_created += 1
            
            return todos_created
            
        except Exception as e:
            log_error(f"Error auto-creating todos: {e}")
            return 0

    def _get_plan_from_session(self, agent: Union[Agent, Team], plan_id: str) -> Optional[ExecutionPlan]:
        """Retrieve plan from agent's session state"""
        if (agent.session_state and 
            "execution_plans" in agent.session_state and 
            plan_id in agent.session_state["execution_plans"]):
            plan_json = agent.session_state["execution_plans"][plan_id]
            return ExecutionPlan.model_validate_json(plan_json)
        return None

    def _format_plan_summary(self, plan: ExecutionPlan) -> str:
        """Format plan for display"""
        steps_summary = []
        for i, step in enumerate(plan.steps, 1):
            dependencies = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
            steps_summary.append(f"  {i}. {step.name} [{step.step_type.value}]{dependencies}")

        return dedent(f"""\
        📋 Execution Plan: {plan.goal}
        Plan ID: {plan.plan_id}
        Status: {plan.status.value}
        Strategy: {plan.metadata.get('strategy', 'hierarchical')}
        
        Steps ({len(plan.steps)} total):
        {chr(10).join(steps_summary)}
        
        Constraints: {len(plan.constraints)} items
        Resources Required: {len(plan.resources_required)} items
        """)

    def create_todo(
        self, 
        agent: Union[Agent, Team], 
        title: str,
        description: str,
        priority: str = "medium",
        deadline: Optional[str] = None,
        plan_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> str:
        """Create an actionable todo item from a task or plan step.
        
        Args:
            title: Brief title for the todo item
            description: Detailed description of what needs to be done
            priority: Priority level - "high", "medium", "low"
            deadline: Optional deadline in natural language (e.g., "tomorrow", "next week")
            plan_id: Link todo to a specific plan
            step_id: Link todo to a specific plan step
            
        Returns:
            Confirmation of todo creation with ID
        """
        try:
            log_debug(f"Creating todo: {title}")
            
            # Initialize todos in session state if needed
            if agent.session_state is None:
                agent.session_state = {}
            if "todos" not in agent.session_state:
                agent.session_state["todos"] = {}
            
            # Generate todo ID
            import uuid
            todo_id = str(uuid.uuid4())[:8]
            
            # Create todo structure
            todo = {
                "id": todo_id,
                "title": title,
                "description": description,
                "priority": priority,
                "deadline": deadline,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "completed_at": None,
                "plan_id": plan_id,
                "step_id": step_id,
                "dependencies": [],
                "tags": []
            }
            
            # Store todo
            agent.session_state["todos"][todo_id] = todo
            
            # Link to plan step if specified
            link_info = ""
            if plan_id and step_id:
                link_info = f"\n📎 Linked to plan {plan_id}, step {step_id}"
            elif plan_id:
                link_info = f"\n📎 Linked to plan {plan_id}"
            
            priority_emoji = {"high": "🔥", "medium": "📝", "low": "💭"}
            deadline_text = f"\n⏰ Deadline: {deadline}" if deadline else ""
            
            result = dedent(f"""\
            ✅ Todo Created Successfully
            
            {priority_emoji.get(priority, '📝')} **{title}**
            ID: {todo_id}
            Priority: {priority.title()}
            Status: Pending{deadline_text}
            
            Description: {description}{link_info}
            """)
            
            logger.info(f"Created todo {todo_id}: {title}")
            return result
            
        except Exception as e:
            log_error(f"Error creating todo: {e}")
            return f"Failed to create todo: {str(e)}"

    def manage_todos(
        self, 
        agent: Union[Agent, Team], 
        action: str = "list",
        todo_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> str:
        """Manage todos with various operations like list, complete, update, delete.
        
        Args:
            action: Action to perform - "list", "complete", "update", "delete", "filter"
            todo_id: ID of specific todo for update/complete/delete operations
            status: Filter by status or new status for update ("pending", "in_progress", "completed")
            priority: Filter by priority or new priority for update ("high", "medium", "low")
            
        Returns:
            Results of the todo management operation
        """
        try:
            # Initialize todos if needed
            if agent.session_state is None:
                agent.session_state = {}
            if "todos" not in agent.session_state:
                agent.session_state["todos"] = {}
                
            todos = agent.session_state["todos"]
            
            if action == "list":
                return self._list_todos(todos, status, priority)
            
            elif action == "complete" and todo_id:
                return self._complete_todo(todos, todo_id)
            
            elif action == "update" and todo_id:
                return self._update_todo(todos, todo_id, status, priority)
            
            elif action == "delete" and todo_id:
                return self._delete_todo(todos, todo_id)
            
            elif action == "filter":
                return self._list_todos(todos, status, priority)
            
            else:
                return "Invalid action. Use: list, complete, update, delete, or filter"
                
        except Exception as e:
            log_error(f"Error managing todos: {e}")
            return f"Failed to manage todos: {str(e)}"

    def _list_todos(self, todos: Dict[str, Any], status_filter: Optional[str] = None, priority_filter: Optional[str] = None) -> str:
        """List todos with optional filtering"""
        if not todos:
            return "📝 No todos found. Create some todos to get started!"
        
        # Filter todos
        filtered_todos = []
        for todo in todos.values():
            if status_filter and todo["status"] != status_filter:
                continue
            if priority_filter and todo["priority"] != priority_filter:
                continue
            filtered_todos.append(todo)
        
        if not filtered_todos:
            filter_text = f" (filtered by status: {status_filter}, priority: {priority_filter})"
            return f"📝 No todos found{filter_text}"
        
        # Sort by priority and creation date
        priority_order = {"high": 1, "medium": 2, "low": 3}
        filtered_todos.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["created_at"]))
        
        # Format todo list
        status_emojis = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}
        priority_emojis = {"high": "🔥", "medium": "📝", "low": "💭"}
        
        todo_lines = []
        for todo in filtered_todos:
            status_emoji = status_emojis.get(todo["status"], "⏳")
            priority_emoji = priority_emojis.get(todo["priority"], "📝")
            deadline_text = f" | ⏰ {todo['deadline']}" if todo["deadline"] else ""
            
            todo_lines.append(
                f"{status_emoji} {priority_emoji} **{todo['title']}** (ID: {todo['id']}) - {todo['status'].title()}{deadline_text}"
            )
        
        filter_info = ""
        if status_filter or priority_filter:
            filters = []
            if status_filter:
                filters.append(f"status: {status_filter}")
            if priority_filter:
                filters.append(f"priority: {priority_filter}")
            filter_info = f"\nFilters: {', '.join(filters)}"
        
        return dedent(f"""\
        📋 Todo List ({len(filtered_todos)} items){filter_info}
        
        {chr(10).join(todo_lines)}
        
        💡 Use manage_todos(action="complete", todo_id="xxx") to mark items complete
        """)

    def _complete_todo(self, todos: Dict[str, Any], todo_id: str) -> str:
        """Mark a todo as completed"""
        if todo_id not in todos:
            return f"❌ Todo {todo_id} not found"
        
        todo = todos[todo_id]
        todo["status"] = "completed"
        todo["completed_at"] = datetime.now().isoformat()
        
        return f"✅ Todo completed: **{todo['title']}** (ID: {todo_id})"

    def _update_todo(self, todos: Dict[str, Any], todo_id: str, new_status: Optional[str], new_priority: Optional[str]) -> str:
        """Update todo status or priority"""
        if todo_id not in todos:
            return f"❌ Todo {todo_id} not found"
        
        todo = todos[todo_id]
        updates = []
        
        if new_status and new_status in ["pending", "in_progress", "completed"]:
            old_status = todo["status"]
            todo["status"] = new_status
            updates.append(f"status: {old_status} → {new_status}")
            
            if new_status == "completed" and not todo["completed_at"]:
                todo["completed_at"] = datetime.now().isoformat()
        
        if new_priority and new_priority in ["high", "medium", "low"]:
            old_priority = todo["priority"]
            todo["priority"] = new_priority
            updates.append(f"priority: {old_priority} → {new_priority}")
        
        if updates:
            return f"✅ Todo updated: **{todo['title']}** (ID: {todo_id})\nChanges: {', '.join(updates)}"
        else:
            return f"ℹ️ No valid updates provided for todo {todo_id}"

    def _delete_todo(self, todos: Dict[str, Any], todo_id: str) -> str:
        """Delete a todo"""
        if todo_id not in todos:
            return f"❌ Todo {todo_id} not found"
        
        todo = todos.pop(todo_id)
        return f"🗑️ Todo deleted: **{todo['title']}** (ID: {todo_id})"