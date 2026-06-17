# Evaluation

The `buddy.eval` package provides three focused evaluators for measuring agent
and team quality:

| Evaluator | Module | Measures |
|-----------|--------|----------|
| `AccuracyEval` | `buddy.eval.accuracy` | How close output is to an expected answer (LLM-judged). |
| `PerformanceEval` | `buddy.eval.performance` | Run-time and peak memory usage of a function. |
| `ReliabilityEval` | `buddy.eval.reliability` | Whether the expected tools were called. |

!!! note "Import from the submodules"
    Import each evaluator from its module (the `buddy.eval` package root does not
    re-export them):

    ```python
    from buddy.eval.accuracy import AccuracyEval
    from buddy.eval.performance import PerformanceEval
    from buddy.eval.reliability import ReliabilityEval
    ```

## Accuracy

`AccuracyEval` runs your agent (or team) on an input, then uses an **evaluator
agent** to score the output against `expected_output` on a 1–10 scale.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.eval.accuracy import AccuracyEval

agent = Agent(model=OpenAIChat(id="gpt-4o"))

evaluation = AccuracyEval(
    agent=agent,
    input="What is the capital of France?",
    expected_output="Paris",
    num_iterations=3,
)
result = evaluation.run(print_summary=True)
print(result.avg_score, result.max_score, result.std_dev_score)
```

Key fields: `input` and `expected_output` (str or callable), one of `agent` /
`team`, `num_iterations`, an optional `model` or fully custom `evaluator_agent`,
and `additional_guidelines`. The evaluator defaults to `OpenAIChat(id="o4-mini")`
when no model is provided.

`run()` returns an `AccuracyResult` with `results` (per-iteration
`AccuracyEvaluation`s) and stats `avg_score`, `min_score`, `max_score`,
`std_dev_score`, plus `print_summary()` / `print_results()`. To score an answer
you already have, use `run_with_output(output=...)`. Async variants `arun()` and
`arun_with_output()` are available.

## Performance

`PerformanceEval` benchmarks a callable, separating warm-up runs from measured
iterations and reporting both timing and memory:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.eval.performance import PerformanceEval

agent = Agent(model=OpenAIChat(id="gpt-4o"))

def task():
    agent.run("Say hello.")

perf = PerformanceEval(
    func=task,
    warmup_runs=3,
    num_iterations=10,
)
result = perf.run(print_summary=True)
print(result.avg_run_time, result.p95_run_time)
print(result.avg_memory_usage)   # MiB
```

`PerformanceResult` reports average, min, max, std dev, median, and 95th
percentile for both `run_times` (seconds) and `memory_usages` (MiB). Toggle
`measure_runtime` / `measure_memory`, and enable `memory_growth_tracking` for
allocation diffing in debug mode. Async functions are supported via `arun()`.

## Reliability

`ReliabilityEval` inspects a completed `RunResponse` and checks that the agent
called the tools you expected:

```python
from buddy.eval.reliability import ReliabilityEval

response = agent.run("What's the weather in Paris?")

evaluation = ReliabilityEval(
    agent_response=response,
    expected_tool_calls=["get_weather"],
)
result = evaluation.run(print_results=True)
result.assert_passed()   # raises AssertionError if eval_status != "PASSED"
```

`ReliabilityResult` exposes `eval_status` (`"PASSED"` / `"FAILED"`),
`failed_tool_calls`, and `passed_tool_calls`. Pass a `team_response` instead of
`agent_response` to evaluate a team (member tool calls are included).

!!! tip "Monitoring"
    All three evaluators log results to the Buddy platform by default
    (`monitoring=True`, controlled by the `BUDDY_MONITOR` environment variable).
    Set `monitoring=False` to keep runs local, and `debug_mode=True` (or
    `BUDDY_DEBUG=true`) for verbose logs.

## See also

For a balance-aware, multi-domain **competency score** that turns evaluation
signals into routing and training decisions, see the
[Competency Engine](competency.md).
