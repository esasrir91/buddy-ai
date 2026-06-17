# Performance

Practical knobs for making agents faster and cheaper. Every option below maps to
a real parameter in the `buddy` package.

## Pick the right model

Model choice dominates both latency and cost. Use a small, fast model for simple
tasks and reserve large models for hard ones.

```python
from buddy.models.openai import OpenAIChat

fast = OpenAIChat(id="gpt-4o-mini")   # quick, cheap
strong = OpenAIChat(id="gpt-4o")       # slower, more capable
```

For zero-network-latency development, run locally with `Ollama`
(`from buddy.models.ollama import Ollama`).

## Limit conversation history

When history is enabled, only the last `num_history_runs` runs are included
(default `3`). Fewer runs means smaller prompts and lower cost.

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    add_history_to_messages=True,
    num_history_runs=2,   # keep prompts small
)
```

!!! note "History is off by default"
    `add_history_to_messages` defaults to `False`. Only enable it (and keep
    `num_history_runs` low) when the task actually needs prior turns.

## Cap tool calls

Bound how many tools a single run may invoke with `tool_call_limit`. This
prevents runaway loops and keeps latency predictable.

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[...],
    tool_call_limit=3,
)
```

## Stream for perceived latency

Streaming does not make generation faster, but it shows tokens as they arrive,
which dramatically improves perceived responsiveness in UIs.

```python
for event in agent.run("Write a long explanation.", stream=True):
    if event.content:
        print(event.content, end="", flush=True)
```

## Go async for concurrency

Use `arun()` to run many agents concurrently instead of serially — ideal for
batch processing or serving multiple requests.

```python
import asyncio

async def main():
    results = await asyncio.gather(
        agent.arun("Question 1"),
        agent.arun("Question 2"),
        agent.arun("Question 3"),
    )
    for r in results:
        print(r.content)

asyncio.run(main())
```

## Reuse sessions and knowledge

| Knob | Where | Effect |
|------|-------|--------|
| `cache_session` | `Agent(cache_session=True)` (default) | Keeps the session in memory to avoid re-reading from storage each run. |
| `num_documents` | `AgentKnowledge(num_documents=5)` | Fewer retrieved chunks → smaller prompts. Lower it for speed. |
| `knowledge.load(recreate=False)` | knowledge base | Reuse an existing index instead of rebuilding it every run. |

```python
from buddy.knowledge.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

kb = PDFKnowledgeBase(
    path="docs/",
    vector_db=ChromaDb(collection="docs", persistent_client=True),
    num_documents=3,   # retrieve fewer, more-relevant chunks
)
kb.load(recreate=False)  # build once, reuse afterwards
```

!!! tip "Measure before optimizing"
    Read `RunResponse.metrics` to see token usage and timing per run, then tune
    the knobs above where they matter most. See [Debugging](debugging.md).
