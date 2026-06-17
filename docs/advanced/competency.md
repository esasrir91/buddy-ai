# Competency Engine

The **Competency Engine** (`buddy.eval.competency` and `buddy.eval.competency_runtime`)
gives an agent or team a balance-aware **competency score** across multiple
domains, and turns that score into action — both **offline** (autonomously
prioritizing what to train next) and **online** (routing each task to the most
competent member and adapting how it runs).

!!! note "What it is — and isn't"
    The competency index is an **interpretable scoring and orchestration layer**.
    It helps you *measure*, *route*, and *prioritize learning* — it does not by
    itself make the underlying model better at a task. The cross-domain
    interaction term only becomes meaningful once you supply a real
    domain-dependency graph.

## The score

For an agent operating across *n* domains with competency `a_i` in `[0, base]`:

| Component | Formula | Meaning |
|-----------|---------|---------|
| **Vertical** | `V = Σ aᵢ²` | per-domain depth |
| **Crosswise** | `C = 2 Σ_{i<j} wᵢⱼ aᵢ aⱼ` | dependency-weighted cross-domain interaction |
| **Integrated** | `U = V + C` | overall integrated competency |
| **Index** | `I = U / U_max` | normalized competency in `[0, 1]` |
| **Deficit** | `δᵢ = base − aᵢ` | per-domain gap to mastery |
| **Priority** | `Pᵢ = δᵢ · (1 + λ·κ̂ᵢ)` | deficit amplified by crosswise centrality |

With `wᵢⱼ = 1`, `V + C = (Σ aᵢ)²`. Supplying a dependency graph makes `C` a
genuine, non-separable interaction signal that rewards balanced, connected
competence.

## Scoring an agent

```python
from buddy.eval.competency import CompetencyEval

ev = CompetencyEval(
    domains={"reasoning": 7, "memory": 6, "deployment": 4},
    base=9,
    dependency={("reasoning", "deployment"): 0.4},  # supply a real graph
)
result = ev.run()

print(f"Competency index: {result.index:.2%}")
print(f"Weakest domain:   {result.weakest_domain()}")

for action in ev.recommend_actions(deficit_threshold=1.0):
    print(action.domain, round(action.priority, 2), action.reason)
```

`CompetencyResult` exposes `vertical`, `crosswise`, `integrated`, `index`,
`deficits`, `centrality`, `priority`, plus `print_summary()` and
`print_results()` for rich console output.

## Autonomous learning loop

The loop reads **live signals** each cycle, scores competency, and automatically
enqueues training jobs for the highest-priority gaps — no hand-set scores.

```python
from buddy.eval.competency import AutonomousCompetencyLoop, DomainSpec

loop = AutonomousCompetencyLoop(
    [
        DomainSpec("python", lambda: measure_python(), data_path="data/python"),
        DomainSpec("sql", lambda: measure_sql(), data_path="data/sql"),
    ],
    base=9,
    dependency={("python", "sql"): 0.5},
    interval_seconds=3600,
    target_index=0.95,
)

loop.start()   # runs in the background, self-improving
# ... later ...
loop.stop()
```

Each `DomainSpec.signal` is re-evaluated every cycle, so the score always
reflects fresh measurements. When the index is below `target_index`, the loop
calls `TrainingJobManager.enqueue_from_competency()` for the weakest domains.

## Runtime routing & outcome feedback

`buddy.eval.competency_runtime` applies the same signal at **task time**: it
infers the task's domain, routes to the most competent member, adapts execution,
and feeds the outcome back into a live tracker.

```python
from buddy.eval.competency_runtime import (
    CompetencyRouter,
    CompetencyTracker,
    MemberProfile,
)

alice = MemberProfile(alice_agent, CompetencyTracker(base=10, seed={"python": 9, "sql": 4}))
bob   = MemberProfile(bob_agent,   CompetencyTracker(base=10, seed={"python": 5, "sql": 8}))

router = CompetencyRouter(
    [alice, bob],
    base=10,
    domains=["python", "sql"],
    strong_model=strong_model,   # used when a domain's deficit is high
)

response, decision = router.run(
    "optimize this slow SQL query",
    success_evaluator=lambda task, resp: "PASS" in str(resp.content),
)

print(decision.member_name, decision.policy, decision.model_tier)
```

The router produces a `RoutingDecision` with the chosen `domain`, `member_name`,
`competency`, `deficit`, a **policy** (`proceed` / `review` / `escalate`) and a
**model tier** (`standard` / `strong`). Recorded outcomes update the member's
`CompetencyTracker` via an exponential moving average, and
`CompetencyTracker.signal(domain)` plugs straight into `DomainSpec` — closing the
loop between runtime performance and offline training.

## The full loop

```
runtime routing → outcome feedback → competency score → autonomous training
        ↑                                                          │
        └──────────────────── better scores ←──────────────────────┘
```

## Caveats

- **Domain awareness is required.** Routing/prioritization need to know each
  task's domain (tag it, or let `LLMDomainClassifier` infer it).
- **Outcome feedback is only as good as your `success_evaluator`.**
- **The "strong" model tier** only helps if you actually pass a stronger
  `strong_model` to the router.
- **Training effect depends on your data** — the loop reliably *targets* the
  right gap; whether scores rise depends on the training data each domain points
  to.
