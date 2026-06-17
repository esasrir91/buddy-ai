"""
Example 12 — Competency Engine

This example demonstrates how to:
1. Score an agent's multi-domain competency (vertical / crosswise / deficit)
2. Get deficit-driven learning recommendations
3. Configure an autonomous competency loop (live signals -> score -> training)
4. Route tasks at runtime to the most competent member, with outcome feedback

Parts 1-3 run fully offline (no API key needed). Part 4 uses real Agents and
requires OPENAI_API_KEY.

Prerequisites:
    pip install buddy-ai
    # Part 4 only:
    export OPENAI_API_KEY=sk-...
"""

import os

from buddy.eval.competency import (
    AutonomousCompetencyLoop,
    CompetencyEval,
    DomainSpec,
)
from buddy.eval.competency_runtime import (
    CompetencyRouter,
    CompetencyTracker,
    KeywordDomainClassifier,
    MemberProfile,
)

# ---------------------------------------------------------------------------
# 1. Score an agent's competency
# ---------------------------------------------------------------------------
print("=" * 60)
print("1. Competency score")
print("=" * 60)

ev = CompetencyEval(
    domains={"reasoning": 7, "memory": 6, "deployment": 4},
    base=9,
    dependency={("reasoning", "deployment"): 0.4},
)
result = ev.run(print_summary=True, print_results=True)

print(f"\nCompetency index: {result.index:.2%}")
print(f"Weakest domain:   {result.weakest_domain()}")


# ---------------------------------------------------------------------------
# 2. Deficit-driven learning recommendations
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("2. What should it learn next?")
print("=" * 60)
for action in ev.recommend_actions(deficit_threshold=1.0):
    print(f"  [{action.priority:5.2f}] {action.domain}: {action.reason}")


# ---------------------------------------------------------------------------
# 3. Autonomous loop (configured here with offline signals; not started)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("3. Autonomous competency loop")
print("=" * 60)

# In production each signal reads a live measurement (eval score, success rate...).
live_scores = {"python": 5.0, "sql": 8.0}

loop = AutonomousCompetencyLoop(
    [
        DomainSpec("python", lambda: live_scores["python"], data_path="data/python"),
        DomainSpec("sql", lambda: live_scores["sql"], data_path="data/sql"),
    ],
    base=9,
    dependency={("python", "sql"): 0.5},
    interval_seconds=3600,
    target_index=0.95,
    auto_train=False,  # set True (with real data_paths) to enqueue training jobs
)

snapshot = loop.evaluate_once()
print(f"  index={snapshot.index:.2%}  weakest={snapshot.weakest_domain()}")
# loop.start()  # uncomment to run continuously in the background
# loop.stop()


# ---------------------------------------------------------------------------
# 4. Runtime routing + outcome feedback (requires OPENAI_API_KEY)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("4. Runtime competency routing")
print("=" * 60)

if not os.getenv("OPENAI_API_KEY"):
    print("  (skipped — set OPENAI_API_KEY to run the live routing demo)")
else:
    from buddy.agent import Agent
    from buddy.models.openai import OpenAIChat

    alice = MemberProfile(
        Agent(name="alice", model=OpenAIChat(id="gpt-4o-mini"), instructions="You are a Python expert."),
        CompetencyTracker(base=10, seed={"python": 9.0, "sql": 4.0}),
    )
    bob = MemberProfile(
        Agent(name="bob", model=OpenAIChat(id="gpt-4o-mini"), instructions="You are a SQL expert."),
        CompetencyTracker(base=10, seed={"python": 5.0, "sql": 8.0}),
    )

    router = CompetencyRouter(
        [alice, bob],
        base=10,
        domains=["python", "sql"],
        classifier=KeywordDomainClassifier(),  # avoids an extra LLM call in the demo
    )

    response, decision = router.run(
        "Write a SQL query to find the top 5 customers by revenue.",
        success_evaluator=lambda task, resp: bool(resp and resp.content),
    )
    print(f"  routed to: {decision.member_name}  (domain={decision.domain}, policy={decision.policy})")
    print(f"  response:  {str(response.content)[:120]}...")
    print(f"  {decision.member_name}/sql competency now: {bob.tracker.get('sql'):.2f}")
