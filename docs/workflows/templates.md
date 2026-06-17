# Workflow Templates

Because a `Workflow.run()` is plain Python, common orchestration patterns are
just code. The templates below are complete `Workflow` subclasses that call real
agents — adapt them to your task.

!!! note "Patterns, not primitives"
    buddy-ai does not provide `if_step`/`loop`/`parallel` operators. Each pattern
    here is implemented with ordinary `if`, `while`, `for` and (for fan-out)
    threads. See [Definition](definition.md) and [Execution](execution.md).

## Sequential pipeline

Each stage feeds the next.

```python
from buddy.workflow import Workflow, RunResponse
from buddy import Agent
from buddy.models.openai import OpenAIChat


class Pipeline(Workflow):
    researcher = Agent(model=OpenAIChat(id="gpt-4o-mini"))
    writer = Agent(model=OpenAIChat(id="gpt-4o"))
    editor = Agent(model=OpenAIChat(id="gpt-4o-mini"))

    def run(self, topic: str) -> RunResponse:
        research = self.researcher.run(f"Research: {topic}").content
        draft = self.writer.run(f"Write an article:\n{research}").content
        final = self.editor.run(f"Polish this:\n{draft}").content
        return RunResponse(content=final)
```

## Conditional branching

Pick a path based on a classification step.

```python
class SupportWorkflow(Workflow):
    classifier = Agent(model=OpenAIChat(id="gpt-4o-mini"))
    billing = Agent(model=OpenAIChat(id="gpt-4o"))
    technical = Agent(model=OpenAIChat(id="gpt-4o"))

    def run(self, question: str) -> RunResponse:
        kind = self.classifier.run(
            f"Reply with one word, 'billing' or 'technical':\n{question}"
        ).content.strip().lower()

        if "billing" in kind:
            answer = self.billing.run(question).content
        else:
            answer = self.technical.run(question).content
        return RunResponse(content=answer)
```

## Loop / iterative refinement

Repeat until a critic is satisfied or a budget is exhausted.

```python
class RefineWorkflow(Workflow):
    writer = Agent(model=OpenAIChat(id="gpt-4o"))
    critic = Agent(model=OpenAIChat(id="gpt-4o-mini"))

    def run(self, brief: str, max_iters: int = 3) -> RunResponse:
        draft = self.writer.run(f"Draft:\n{brief}").content
        for _ in range(max_iters):
            review = self.critic.run(
                f"Reply 'APPROVED' or give specific fixes:\n{draft}"
            ).content
            if "APPROVED" in review.upper():
                break
            draft = self.writer.run(f"Revise using feedback:\n{review}\n\n{draft}").content
        return RunResponse(content=draft)
```

## Fan-out / fan-in (parallel)

Run independent agents concurrently with a thread pool, then combine.

```python
from concurrent.futures import ThreadPoolExecutor


class FanOutWorkflow(Workflow):
    analyst = Agent(model=OpenAIChat(id="gpt-4o-mini"))
    synthesizer = Agent(model=OpenAIChat(id="gpt-4o"))

    def run(self, topics: list[str]) -> RunResponse:
        # Fan-out: analyze each topic in parallel
        with ThreadPoolExecutor(max_workers=len(topics)) as pool:
            parts = list(pool.map(
                lambda t: self.analyst.run(f"Analyze: {t}").content, topics
            ))

        # Fan-in: synthesize the parts into one answer
        joined = "\n\n".join(parts)
        summary = self.synthesizer.run(f"Synthesize these analyses:\n{joined}").content
        return RunResponse(content=summary)
```

## Delegating to a team

A workflow stage can be a whole `Team`, combining deterministic control flow with
LLM-driven coordination.

```python
from buddy import Team


class HybridWorkflow(Workflow):
    research_team = Team(
        members=[web_agent, paper_agent],
        mode="coordinate",
        model=OpenAIChat(id="gpt-4o-mini"),
    )
    writer = Agent(model=OpenAIChat(id="gpt-4o"))

    def run(self, topic: str) -> RunResponse:
        research = self.research_team.run(f"Research: {topic}").content
        article = self.writer.run(f"Write an article:\n{research}").content
        return RunResponse(content=article)
```

!!! tip "Combine patterns"
    Real workflows mix these freely — e.g. a sequential pipeline whose middle
    stage branches, with a refinement loop at the end. Keep `run()` readable by
    extracting helper methods for each stage.
