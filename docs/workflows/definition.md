# Defining a Workflow

A workflow is a subclass of `Workflow` (`buddy.workflow.workflow`) with a custom
`run()` method. This page covers the `run()` signature, agents as class
attributes, `session_state`, storage, and how caching can be implemented.

## The `run()` signature

Override `run(self, ...)` with whatever parameters your workflow needs. The
arguments you pass to `workflow.run(**kwargs)` are forwarded to your method.

```python
from buddy.workflow import Workflow, RunResponse
from buddy import Agent
from buddy.models.openai import OpenAIChat


class SummaryWorkflow(Workflow):
    description = "Summarize a document at a given length."

    summarizer = Agent(model=OpenAIChat(id="gpt-4o-mini"))

    def run(self, text: str, max_words: int = 100) -> RunResponse:
        resp = self.summarizer.run(f"Summarize in <= {max_words} words:\n{text}")
        return RunResponse(content=resp.content)


wf = SummaryWorkflow()
wf.run(text="...", max_words=60)
```

!!! note "Return a `RunResponse`"
    A non-streaming `run()` should **return a `RunResponse`**. The framework logs
    a warning and returns `None` if it gets anything else. A streaming `run()`
    yields events instead — see [Execution](execution.md).

## Agents and teams as attributes

Declare the agents/teams a workflow uses as **class attributes** (as above). The
framework propagates the workflow's `session_id` to any `Agent` attributes during
a run, keeping their sessions aligned with the workflow.

## `session_state`

`session_state` is a `dict` that lives for the session and is persisted to
storage when one is configured. Use it to carry values between runs of the same
session.

```python
class CounterWorkflow(Workflow):
    def run(self) -> RunResponse:
        count = self.session_state.get("count", 0) + 1
        self.session_state["count"] = count
        return RunResponse(content=f"Run #{count}")


wf = CounterWorkflow(session_state={"count": 0})
```

When a session is loaded from storage, the stored `session_state` is merged into
the current one, so prior values survive across process restarts.

## Storage & sessions

Pass a `storage` backend to persist runs. After each run the framework writes a
`WorkflowSession` (session id, workflow id, memory, `session_data`, `extra_data`)
via `storage.upsert(...)`, and reads it back at the start of the next run.

```python
from buddy.storage.sqlite import SqliteStorage  # example backend

wf = CounterWorkflow(
    session_id="user-42",
    session_state={"count": 0},
    storage=SqliteStorage(table_name="workflows", db_file="tmp/wf.db"),
)
```

Helper methods include `load_session()`, `new_session()`, `rename_session()` and
`delete_session(session_id)`.

## Caching results

The framework has no dedicated cache primitive, but `session_state` makes
caching a few lines of code: check it before doing expensive work, and store the
result for next time.

```python
class CachedResearch(Workflow):
    researcher = Agent(model=OpenAIChat(id="gpt-4o-mini"))

    def run(self, topic: str) -> RunResponse:
        cache = self.session_state.setdefault("research", {})
        if topic in cache:
            return RunResponse(content=cache[topic])  # cache hit
        result = self.researcher.run(f"Research: {topic}").content
        cache[topic] = result
        return RunResponse(content=result)
```

With a `storage` backend configured, the cache persists across runs because
`session_state` is saved with the session.

## Other settings

`__init__` also accepts `name`, `workflow_id`, `description`, `session_name`,
`memory`, `extra_data`, and `debug_mode`. `name` defaults to the class name and
`description` to the class-level `description` attribute.
