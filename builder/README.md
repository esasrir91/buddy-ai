<div align="center">

<img src="../../assets/aura-logo.png" alt="Buddy Builder" width="110" />

# Buddy Builder

</div>

A **no-code, drag-and-drop platform** for building Buddy agents, teams, workflows
and full agent apps. The builder is a thin visual layer over the Buddy framework:
everything you drag onto the canvas is serialized to a versioned `GraphSpec` JSON
document, which the compiler turns into live Buddy objects.

## Why it covers 100% of Buddy

Buddy's features map onto five "surfaces", and the builder models all of them:

| Surface | What | Where in the builder |
| --- | --- | --- |
| 1. Canvas nodes | Agents, teams, models, tools, logic, resources | Draggable blocks + edges |
| 2. Capabilities | Reasoning, memory, personality, security, evolution | Toggles on the agent/team config panel |
| 3. Resource nodes | Knowledge, vector DBs, embedders, rerankers, storage | Draggable blocks wired by edges |
| 4. Triggers | API, Playground, Slack, WhatsApp, Discord, AG-UI, webhook | Deployment channels |
| 5. Ops | Evaluations, training | Project tabs |

The catalog of blocks is **auto-introspected** from the framework — adding a new
tool to `buddy/tools/` makes it appear in the palette with zero builder code. The
test `tests/builder/test_coverage.py` fails if any framework feature becomes
unreachable.

## Architecture

```
GraphSpec JSON  ──>  compiler  ──>  Agent / Team / Workflow  ──>  runner (stream)
     ^                                                              │
     │  React Flow canvas (frontend/)                               ▼
 catalog (auto-introspection)                                  FastAPI server
```

- `spec/`     — the `GraphSpec` schema (single source of truth)
- `registry/` — auto-introspection into a `Catalog` of `NodeType`s
- `compiler/` — `GraphSpec` → live Buddy objects
- `runner/`   — execute + stream normalized events
- `server/`   — FastAPI: catalog, project CRUD, compile, run (SSE)
- `examples/` — a hand-written spec proving the pipeline end-to-end

## Running

```bash
# 1. Pre-warm the block catalog (introspects the framework, caches to disk)
python -m buddy.builder --build-catalog

# 2. Start the backend (serves the built frontend at / if present)
python -m buddy.builder            # http://127.0.0.1:8500

# 3. (dev) run the frontend with hot reload, proxying /api to the backend
cd frontend && npm install && npm run dev   # http://127.0.0.1:5173

# 3. (prod) build the frontend into the server's static dir
cd frontend && npm run build       # then just `python -m buddy.builder`
```

Set your model API keys in the environment or a `.env` file (the server loads
`./.env` and `sri/workspace/secrets/.env` automatically).

## Programmatic use

```python
import json
from buddy.builder.spec import GraphSpec
from buddy.builder.compiler import compile_graph
from buddy.builder.runner import run_graph_sync

spec = GraphSpec.model_validate(json.load(open("buddy/builder/examples/single_agent.json")))
agent = compile_graph(spec).root          # a real buddy.agent.Agent
print(run_graph_sync(spec, "Hello!"))     # run it
```
