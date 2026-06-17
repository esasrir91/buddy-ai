# Teaching AI Agents to Know What They Don't Know

**Buddy AI v2.2.0** introduces the **Competency Engine** — a new way to measure, route, and improve your AI agents across multiple skill areas. If you've ever wondered *"Is my agent actually good at SQL, or just lucky?"* or *"Which teammate should handle this task?"*, this release is for you.

!!! note "Install v2.2.0"
    ```bash
    pip install -U buddy-ai
    ```

    - **PyPI:** [buddy-ai 2.2.0](https://pypi.org/project/buddy-ai/2.2.0/)
    - **GitHub:** [esasrir91/buddy-ai](https://github.com/esasrir91/buddy-ai)
    - **Technical reference:** [Competency Engine docs](../advanced/competency.md)

---

## What's new in v2.2.0

The headline feature is the **Competency Engine** — a scoring and orchestration layer that sits on top of your existing models and agents. It does three things:

1. **Scores** how strong an agent (or team) is across multiple domains — like a report card with more than one subject.
2. **Prioritizes** what to learn or retrain next — like a study planner that focuses on the biggest gaps first.
3. **Routes** incoming tasks to the most competent team member at runtime — and updates scores based on real outcomes.

Buddy AI already ships **PULSE**, the autonomous virtual employee that works your task queue, writes files, learns from documents, and remembers context across sessions. PULSE remains the flagship for *doing work*. The Competency Engine is the new layer for *knowing where you're strong, where you're weak, and who should do what*.

!!! tip "Honest framing"
    The Competency Engine is a **scoring, routing, and orchestration layer**. It helps you measure competency, decide who handles a task, and prioritize training — it does **not** make the underlying LLM smarter by itself. Think of it as the coach and dispatcher, not a new brain.

---

## The idea in plain English

Imagine a student with subjects like Python, SQL, and deployment. You could ask:

- *"How are they doing overall?"* → A single **competency index** (0–100%) that rewards balanced strength across subjects, not just one high score.
- *"What should they study next?"* → A ranked list of **gaps**, weighted so fixing a weak area that other subjects depend on gets priority.
- *"Who on the team should answer this question?"* → Route the task to whoever is strongest in that domain, and adjust confidence (proceed / review / escalate) based on how competent they are.

That's the Competency Engine in a nutshell: **report card + study planner + smart dispatcher**.

Under the hood, the score decomposes into:

| Piece | Plain English |
|-------|---------------|
| **Vertical** | How deep your mastery is in each domain on its own |
| **Crosswise** | How well your domains work *together* (when you define dependencies) |
| **Deficit** | How far each domain is from your target "mastery" level |
| **Priority** | Which gap to fix first — bigger deficits in connected domains rank higher |

The full formulas and API details live in the [Competency Engine reference](../advanced/competency.md). The rest of this article shows you how to use it in code.

---

## Part 1: Score your agent with `CompetencyEval`

Start by giving each domain a score on a scale from 0 to your target **base** (e.g. 9 out of 9). These numbers can come from evals, success rates, or manual estimates — whatever reflects current mastery.

```python
from buddy.eval.competency import CompetencyEval

ev = CompetencyEval(
    domains={"reasoning": 7, "memory": 6, "deployment": 4},
    base=9,
    dependency={("reasoning", "deployment"): 0.4},  # deployment leans on reasoning
)
result = ev.run(print_summary=True, print_results=True)

print(f"Competency index: {result.index:.2%}")
print(f"Weakest domain:   {result.weakest_domain()}")
```

You'll see a breakdown per domain — competency, deficit, centrality, and priority — plus an overall **competency index**.

Ask *"what should it learn next?"* with deficit-driven recommendations:

```python
for action in ev.recommend_actions(deficit_threshold=1.0):
    print(f"  [{action.priority:5.2f}] {action.domain}: {action.reason}")
```

In this example, **deployment** likely tops the list: it's far below the target, and it's connected to reasoning via the dependency graph.

!!! note "No API key needed"
    Part 1 runs fully offline. You only need `pip install buddy-ai`.

---

## Part 2: Autonomous loop with `AutonomousCompetencyLoop` and `DomainSpec`

Scoring once is useful; keeping scores fresh is better. The **autonomous loop** re-reads live signals every cycle, recomputes the index, and (optionally) enqueues training for the weakest gaps.

Each domain is a `DomainSpec`: a name, a **signal** callable that returns the current score, and an optional path to training data.

```python
from buddy.eval.competency import AutonomousCompetencyLoop, DomainSpec

# In production, each signal reads a live measurement (eval score, success rate, etc.)
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

# loop.start()  # run continuously in the background
# loop.stop()
```

Signals are re-evaluated every cycle, so the loop always reflects **current** performance — not a number you typed once and forgot.

When `auto_train=True` and you provide real `data_path` values, the loop can enqueue training jobs for the highest-priority deficits via Buddy's training job manager. Set `auto_train=False` while you're experimenting, as shown above.

---

## Part 3: Runtime routing with `CompetencyRouter` and `CompetencyTracker`

Offline scoring tells you the big picture. **Runtime routing** applies the same signal when a task arrives:

1. Classify the task into a competency domain.
2. Pick the team member with the **lowest deficit** in that domain.
3. Choose a policy: **proceed**, **review**, or **escalate** — and optionally upgrade to a stronger model tier.
4. Record the outcome back into a live `CompetencyTracker`, so future routing gets smarter.

```python
import os

from buddy.eval.competency_runtime import (
    CompetencyRouter,
    CompetencyTracker,
    KeywordDomainClassifier,
    MemberProfile,
)

if not os.getenv("OPENAI_API_KEY"):
    print("Set OPENAI_API_KEY to run the live routing demo.")
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
        classifier=KeywordDomainClassifier(),  # keyword match for demos; use LLM classifier in production
    )

    response, decision = router.run(
        "Write a SQL query to find the top 5 customers by revenue.",
        success_evaluator=lambda task, resp: bool(resp and resp.content),
    )
    print(f"Routed to: {decision.member_name}  (domain={decision.domain}, policy={decision.policy})")
    print(f"Response:  {str(response.content)[:120]}...")
    print(f"{decision.member_name}/sql competency now: {bob.tracker.get('sql'):.2f}")
```

A SQL task routes to **bob** (higher SQL competency). After a successful run, bob's SQL score nudges upward via an exponential moving average — the tracker learns from real outcomes, not guesses.

The tracker's `signal()` method plugs directly into `DomainSpec`, so runtime results feed the same scores used by the autonomous loop. One competency model, offline and online.

!!! tip "Classifier choice"
    `KeywordDomainClassifier` is great for demos and tests. In production, omit the `classifier` argument (defaults to `LLMDomainClassifier`) or pass your own.

---

## Putting it together

| Layer | Module | When to use |
|-------|--------|-------------|
| **Scoring** | `CompetencyEval` | Snapshot an agent's strengths and gaps |
| **Learning loop** | `AutonomousCompetencyLoop` | Continuously measure and prioritize training |
| **Runtime routing** | `CompetencyRouter` + `CompetencyTracker` | Send each task to the right agent and learn from outcomes |

Together with **PULSE** (autonomous work execution) and Buddy's existing eval, training, and team tools, v2.2.0 gives you a full loop: **measure → route → execute → learn → repeat**.

---

## Next steps

- [Competency Engine reference](../advanced/competency.md) — formulas, thresholds, and full API
- [Example script](https://github.com/esasrir91/buddy-ai/blob/main/examples/12_competency_engine.py) — runnable walkthrough (`examples/12_competency_engine.py`)
- [PULSE — Virtual Employee](../advanced/pulse.md) — autonomous teammate that ships real work
- [Getting Started](../getting-started/installation.md) — install and configure Buddy AI

```bash
pip install -U buddy-ai
```

Happy building — and may your agents always know what they don't know.
