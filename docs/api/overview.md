# API Overview

This section is the reference for the **Buddy AI Python library** — the classes
and functions you import from the `buddy` package to build agents, teams,
knowledge bases, and workflows. It is *not* a REST API reference (though Buddy
can also serve agents over HTTP — see [Serving over HTTP](#serving-over-http)
below and [Integrations](../examples/integrations.md)).

!!! note "How to read these pages"
    Each page documents the constructor parameters and the runtime methods of one
    core class, grounded in the source under `buddy/`. Parameters are grouped into
    tables; defaults match the code. Optional features (planning, multimodal,
    reasoning, security, PULSE) import lazily, so they only appear if their extra
    dependencies are installed — check with `get_available_features()`.

## The public surface

Everything you need for the common cases is importable directly from the
top-level package:

```python
from buddy import (
    Agent,            # a single LLM-powered agent
    Team,             # a group of agents that collaborate
    Model,            # base class for model providers
    Function,         # a tool wrapping a callable
    Toolkit,          # a collection of related tools
    AgentMemory,      # conversation/session memory
    AgentKnowledge,   # retrieval / knowledge base base class
    get_version_info,
    get_available_features,
    check_feature,
)
```

## Core classes

| Class | Import | Reference |
|-------|--------|-----------|
| `Agent` | `from buddy import Agent` | [Agent API](agent-api.md) |
| `Team` | `from buddy import Team` | [Team API](team-api.md) |
| `AgentKnowledge` | `from buddy import AgentKnowledge` | [Knowledge API](knowledge-api.md) |
| `AgentMemory` | `from buddy import AgentMemory` | [Memory](../core/memory.md) |
| `Workflow` | `from buddy.workflow import Workflow` | [Workflow API](workflow-api.md) |
| `Model` | `from buddy.models.base import Model` | [Models](../models/overview.md) |
| `Toolkit` / `Function` / `@tool` | `from buddy.tools import Toolkit, Function, tool` | [Tools](../tools/overview.md) |

Provider classes live under `buddy.models.*` (e.g. `from buddy.models.openai
import OpenAIChat`), tools under `buddy.tools.*`, knowledge bases under
`buddy.knowledge.*`, and vector stores under `buddy.vectordb.*`.

## Feature detection

The package degrades gracefully when optional extras are missing. Use the helper
functions to introspect what is available at runtime:

```python
from buddy import get_version_info, get_available_features, check_feature

get_version_info()        # {"version": ..., "features": {...}, ...}
get_available_features()  # e.g. ["planning", "reasoning", "pulse", "core"]
check_feature("pulse")    # True / False
```

The feature keys are `planning`, `multimodal`, `evolution`, `reasoning`,
`personality`, `security`, `pulse`, and `core` (always `True`).

## Serving over HTTP

Agents, teams, and workflows can be exposed as a FastAPI application via
`FastAPIApp` (`from buddy.app.fastapi import FastAPIApp`). The generated app
exposes a small REST surface:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/status` | Health check — returns `{"status": "available"}` |
| `POST` | `/runs` | Run an agent, team, or workflow |

`POST /runs` accepts form fields (`message`, `stream`, `monitor`, `session_id`,
`user_id`, `workflow_input`, `files`) and selects the target via the
`agent_id`, `team_id`, or `workflow_id` query parameter. See
[Integrations](../examples/integrations.md) for a deployment walkthrough.

!!! tip "Prefer the Python API for embedding"
    If you are embedding Buddy inside your own service, call `Agent.run()` /
    `Team.run()` directly rather than going through HTTP — you get typed
    `RunResponse` objects instead of JSON.
