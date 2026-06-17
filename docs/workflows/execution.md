# Executing Workflows

Once defined, a workflow runs by calling `run()` (or `arun()` for async). This
page covers the two return styles, streaming, the async variants, and
persistence — all grounded in `buddy/workflow/workflow.py` and
`buddy/run/workflow.py`.

## Return a single response

The simplest workflows compute an answer and **return** a `RunResponse`. The
framework stamps it with the current `run_id`, `session_id` and `workflow_id`,
records it in memory, and persists the session.

```python
result = workflow.run(topic="quantum computing")
print(result.content)
```

## Stream events by yielding

If your `run()` is a **generator** (it `yield`s), `run()` returns an iterator and
the framework streams items as they are produced. Yielded items should be
`RunResponse` objects or workflow run events; the framework accumulates their
string `content` into the workflow's `run_response`.

```python
from buddy.workflow import Workflow, RunResponse
from buddy.run.workflow import WorkflowCompletedEvent
from buddy import Agent
from buddy.models.openai import OpenAIChat


class StreamingWorkflow(Workflow):
    writer = Agent(model=OpenAIChat(id="gpt-4o"))

    def run(self, topic: str):
        draft = self.writer.run(f"Write about {topic}").content
        yield RunResponse(content=draft)
        yield WorkflowCompletedEvent(run_id=self.run_id, content=draft)


for event in StreamingWorkflow().run(topic="fusion energy"):
    print(event.content)
```

The available workflow events (`buddy.run.workflow`) are
`WorkflowRunResponseStartedEvent` and `WorkflowCompletedEvent`, with the
`RunEvent` enum values `WorkflowStarted` and `WorkflowCompleted`.

!!! note "Yield events, not arbitrary objects"
    The framework warns if a yielded item is not a recognized run/team/workflow
    event or a `RunResponse`. Stick to those types when streaming.

## Async execution

Override `arun()` to run asynchronously. The framework detects whether `arun` is
a coroutine or an async generator and wires the appropriate path:

```python
class AsyncWorkflow(Workflow):
    writer = Agent(model=OpenAIChat(id="gpt-4o"))

    async def arun(self, topic: str) -> RunResponse:
        resp = await self.writer.arun(f"Write about {topic}")
        return RunResponse(content=resp.content)


import asyncio
result = asyncio.run(AsyncWorkflow().arun(topic="batteries"))
```

An async generator `arun()` streams via an async iterator, mirroring the sync
streaming behavior above.

## Persistence & resuming

When a `storage` backend is set, each run:

1. Reads the existing `WorkflowSession` for `session_id` at the start.
2. Merges the stored `session_state` into the current workflow.
3. Runs your logic.
4. Adds the run to memory and writes the session back.

To resume a prior session, construct the workflow with the same `session_id` and
`storage`; the stored state and history load automatically.

```python
wf = MyWorkflow(session_id="user-42", storage=my_storage)
wf.run(...)        # picks up where session "user-42" left off
```

Use `new_session()` to start a fresh session id, and `delete_session(session_id)`
to remove one.

## What you get back

| Style | `run()` returns |
|-------|-----------------|
| Plain | A single `RunResponse` |
| Generator | An iterator of events / `RunResponse` |
| Async coroutine | A `RunResponse` (awaited) |
| Async generator | An async iterator of events |

In every case the workflow keeps a `run_response` whose `content` reflects the
accumulated output of the run.
