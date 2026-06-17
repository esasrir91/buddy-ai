# Reasoning

Buddy ships two complementary ways to make an agent reason more deliberately:

1. The built-in `reasoning=True` flag on any [`Agent`](../agents/agent-class.md).
2. The standalone reasoning engine in `buddy.reasoning`, which exposes explicit
   strategies (Chain-of-Thought Plus, Tree of Thoughts, and more).

This is the canonical reasoning page.

## Built-in reasoning flag

The simplest path is to turn on reasoning when constructing an agent:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning=True,
    reasoning_min_steps=2,
    reasoning_max_steps=8,
)
agent.print_response("A bat and ball cost $1.10. The bat costs $1 more "
                     "than the ball. How much is the ball?")
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `reasoning` | `False` | Enable step-by-step reasoning. |
| `reasoning_model` | `None` | Use a separate model for the reasoning phase. |
| `reasoning_min_steps` | `1` | Minimum reasoning steps. |
| `reasoning_max_steps` | `10` | Maximum reasoning steps. |

!!! tip
    Pass a dedicated `reasoning_model` (often a stronger or "thinking" model) to
    separate deliberation from final answer generation.

## The reasoning engine

For explicit control over *how* an agent reasons, use `buddy.reasoning`. It is
feature-gated:

```python
from buddy import check_feature
assert check_feature("reasoning")

from buddy import AdvancedReasoning, ReasoningStrategy, ReasoningResult
```

### Strategies

`ReasoningStrategy` enumerates the available approaches:

| Member | Best for |
|--------|----------|
| `CHAIN_OF_THOUGHT` | Plain step-by-step reasoning. |
| `CHAIN_OF_THOUGHT_PLUS` | Step-by-step **with verification** and alternatives. |
| `TREE_OF_THOUGHTS` | Exploring multiple paths and picking the best. |
| `ANALOGICAL_REASONING` | Transferring structure from a familiar domain. |
| `CAUSAL_INFERENCE` | Cause-and-effect analysis and prediction. |
| `LOGICAL_DEDUCTION` | Formal deduction from premises. |
| `HYBRID_REASONING` | Combining several strategies. |

### Running a strategy

```python
from buddy import AdvancedReasoning, ReasoningStrategy

reasoner = AdvancedReasoning()

# Explicit strategy
result = reasoner.reason(
    "How can a city reduce traffic congestion?",
    strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
)

# Auto-select a strategy from the query
auto = reasoner.reason("Why did sales drop last quarter?")

# Combine multiple strategies
hybrid = reasoner.hybrid_reason("Design a fair tournament schedule.")
```

When `strategy` is omitted, `StrategySelector` picks one heuristically — e.g.
causal questions ("why", "because") route to `CAUSAL_INFERENCE`, comparison
questions to `ANALOGICAL_REASONING`, and logic keywords to `LOGICAL_DEDUCTION`.

### ReasoningResult

`reason()` and `hybrid_reason()` return a `ReasoningResult`:

| Field | Description |
|-------|-------------|
| `query` | The original question. |
| `strategy_used` | The `ReasoningStrategy` that produced the result. |
| `reasoning_steps` | List of `ReasoningStep` objects (type, content, confidence). |
| `final_conclusion` | The synthesized answer. |
| `overall_confidence` | Aggregate confidence in `[0, 1]`. |
| `alternative_conclusions` | Other candidate conclusions. |
| `contradictions_found` | Detected contradictions. |
| `verification_passed` | Whether step verification succeeded. |
| `reasoning_time` | Wall-clock time in seconds. |

```python
print(result.final_conclusion)
print(result.overall_confidence)
for step in result.reasoning_steps:
    print(step.step_type, step.confidence, step.content)
```

## Adding reasoning to an agent class

`AdvancedReasoningMixin` adds `reason_advanced()`,
`reason_with_verification()`, and `hybrid_reasoning()` to an agent class:

```python
from buddy import Agent
from buddy.reasoning import AdvancedReasoningMixin, ReasoningStrategy

class ReasoningAgent(AdvancedReasoningMixin, Agent):
    def solve(self, problem: str):
        return self.reason_advanced(
            problem, strategy=ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS
        )
```

## Building blocks

Each strategy is also usable on its own: `ChainOfThoughtPlus`, `TreeOfThoughts`,
`AnalogicalReasoning`, `CausalInference`, and `LogicalDeduction` all expose a
`reason(query, context)` method returning a `ReasoningResult`. `StepVerifier`
(with `VerificationResult`) checks individual steps for consistency,
contradiction, and evidence.

!!! warning "Heuristic core"
    Chain-of-Thought Plus, Tree of Thoughts, and the verifier orchestrate
    reasoning structure and confidence bookkeeping with built-in heuristics. For
    model-quality reasoning on real tasks, pair the engine with a capable model
    (or the agent's `reasoning=True` flag) rather than relying on the heuristics
    alone.
