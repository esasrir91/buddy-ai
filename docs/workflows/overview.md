# Workflow Overview

A **Workflow** (`buddy.workflow.Workflow`) is deterministic, plain-Python
orchestration of agents and teams. Where a `Team` lets an LLM decide who does
what, a `Workflow` puts **you** in control: you subclass `Workflow`, implement a
`run()` method, and call agents/teams in whatever order, branches, and loops your
logic requires.

!!! note "Version"
    Documents buddy-ai **2.2.0**. The base class and execution model below are
    verified against `buddy/workflow/workflow.py`.

## Imports

```python
from buddy.workflow import Workflow, RunResponse, WorkflowSession
```

`Workflow` is the base class, `RunResponse` is the standard result object
(re-exported from `buddy.run.response`), and `WorkflowSession` is the persisted
session record.

## Defining a workflow

Subclass `Workflow` and override `run()`. Inside `run()`, call agents or teams
like normal Python objects and return a `RunResponse`.

```python
from buddy.workflow import Workflow, RunResponse
from buddy import Agent
from buddy.models.openai import OpenAIChat


class ArticleWorkflow(Workflow):
    description = "Research a topic, then write an article."

    researcher = Agent(model=OpenAIChat(id="gpt-4o-mini"))
    writer = Agent(model=OpenAIChat(id="gpt-4o"))

    def run(self, topic: str) -> RunResponse:
        research = self.researcher.run(f"Research: {topic}")
        article = self.writer.run(f"Write an article based on:\n{research.content}")
        return RunResponse(content=article.content)


workflow = ArticleWorkflow()
result = workflow.run(topic="quantum computing")
print(result.content)
```

!!! warning "No step decorators"
    There is no `@workflow.step`, `if_step`, or `else_step` API. Control flow is
    ordinary Python — `if`, `for`, `while`, function calls — written inside
    `run()`. Branching and loops are *patterns you implement*, not framework
    primitives (see [Templates](templates.md)).

## How `run()` is invoked

When you subclass `Workflow` and define `run()`, the framework swaps your method
for an internal `run_workflow()` wrapper. So calling `workflow.run(...)`:

1. Sets up the workflow/session IDs and initializes memory.
2. Creates a fresh `run_id` and a `RunResponse`.
3. Reads any existing session from `storage`.
4. Executes **your** `run()` body.
5. Records the run in memory and writes the session back to `storage`.

Your `run()` may either **return** a single `RunResponse` or **yield** a stream
of events / `RunResponse` objects (see [Execution](execution.md)).

## Configuration

`Workflow.__init__` accepts keyword arguments including `name`, `workflow_id`,
`description`, `session_id`, `session_name`, `session_state`, `memory`,
`storage`, `extra_data`, and `debug_mode`. All are optional — `name` defaults to
the class name and `description` to the class-level `description` attribute.

```python
from buddy.storage.sqlite import SqliteStorage  # example storage backend

workflow = ArticleWorkflow(
    name="article_pipeline",
    session_state={"tone": "concise"},
    storage=SqliteStorage(table_name="workflows", db_file="tmp/wf.db"),
)
```

## Where to go next

- [Defining workflows](definition.md) — the `run()` signature, `session_state`,
  storage and caching.
- [Executing workflows](execution.md) — return vs. yield, streaming, persistence.
- [Templates](templates.md) — sequential, branching, loop and fan-out patterns.
