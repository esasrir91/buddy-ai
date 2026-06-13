"""
06_planning_agent.py — PlanningAgent with hierarchical task decomposition

Demonstrates the full planning cycle: create plan → validate → execute → monitor.

Install:
    pip install buddy-ai

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy.planning.planner import PlanningAgent, PlanStrategy

agent = PlanningAgent(
    name="planner",
    planning_strategy=PlanStrategy.HIERARCHICAL,
    plan_validation=True,
    adaptive_replanning=True,
    max_planning_depth=4,
)

if __name__ == "__main__":
    # Create a plan
    plan = agent.create_execution_plan(
        goal="Research and summarize the latest AI safety developments",
        context={"depth": "comprehensive", "sources": "academic and news"},
        constraints=["Stay within 500 words", "Use only 2026 sources"],
        resources=["web_search", "document_reader"],
    )

    print(f"Plan created: {plan.plan_id}")
    print(f"Goal: {plan.goal}")
    print(f"Steps ({len(plan.steps)}):")
    for step in plan.steps:
        print(f"  [{step.step_type.value}] {step.name}: {step.description}")

    # Monitor
    monitor = agent.monitor_execution(plan)
    print(f"\nPlan status: {monitor['status']}")
    print(f"Completion: {monitor['completion_percentage']:.1f}%")

    # Validate
    validation = agent.validate_plan(plan)
    print(f"\nPlan valid: {validation['valid']}")
    if not validation["valid"]:
        print(f"Issues: {validation['issues']}")
