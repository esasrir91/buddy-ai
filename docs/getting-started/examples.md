# Examples

The [`examples/`](https://github.com/esasrir91/buddy-ai/tree/main/examples)
directory contains twelve runnable scripts that build up from a one-line agent
to autonomous, self-improving systems. Each file is self-contained and
documents its own install and API-key requirements in the docstring at the top.

## Running an Example

```bash
pip install buddy-ai
export OPENAI_API_KEY=sk-...
python examples/01_basic_agent.py
```

Some examples need extra dependencies or keys (noted below and in each file) —
for instance web search needs `tavily-python` and a `TAVILY_API_KEY`.

## The Scripts

### Fundamentals

| # | Script | What it shows |
|---|--------|---------------|
| 01 | [`01_basic_agent.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/01_basic_agent.py) | The minimal agent — a model plus a prompt. See [Agents](../core/agents.md). |
| 02 | [`02_agent_with_tools.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/02_agent_with_tools.py) | Attaching built-in tools (web search + Python execution). See [Tools](../core/tools.md). |
| 03 | [`03_agent_with_memory.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/03_agent_with_memory.py) | Persistent memory so the agent recalls earlier turns. See [Memory](../core/memory.md). |
| 10 | [`10_custom_tool.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/10_custom_tool.py) | Turning a plain Python function into an agent tool. See [Tools](../core/tools.md). |

### Models & Output

| # | Script | What it shows |
|---|--------|---------------|
| 08 | [`08_multi_model_comparison.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/08_multi_model_comparison.py) | Running one prompt across OpenAI, Anthropic, and Google to compare results. See [Models](../core/models.md). |
| 09 | [`09_streaming_agent.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/09_streaming_agent.py) | Real-time token streaming with `run(..., stream=True)` — ideal for chat UIs. |

### Knowledge & Reasoning

| # | Script | What it shows |
|---|--------|---------------|
| 05 | [`05_rag_with_irag.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/05_rag_with_irag.py) | Retrieval-Augmented Generation with the built-in iRAG engine (no vector DB). See [Knowledge](../core/knowledge.md). |
| 06 | [`06_planning_agent.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/06_planning_agent.py) | `PlanningAgent` decomposing a goal into steps, then executing and monitoring them. |

### Multi-Agent & Deployment

| # | Script | What it shows |
|---|--------|---------------|
| 04 | [`04_multi_agent_team.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/04_multi_agent_team.py) | A `Team` where a coordinator delegates to specialist agents. See [Models & Teams](../core/overview.md). |
| 07 | [`07_fastapi_deployment.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/07_fastapi_deployment.py) | Serving an agent as a FastAPI REST API. See [Quick Start](quickstart.md#5-deploy-as-an-api). |

### Autonomous Systems

| # | Script | What it shows |
|---|--------|---------------|
| 11 | [`11_pulse_employee.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/11_pulse_employee.py) | The PULSE virtual employee: KT sessions, meetings, tasks, and status updates. See [PULSE](../advanced/pulse.md). |
| 12 | [`12_competency_engine.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/12_competency_engine.py) | Scoring competency, deficit-driven learning, and runtime routing. See [Competency Engine](../advanced/competency.md). |

!!! tip "Start small"
    If you're new, run `01` → `02` → `03` in order. They introduce the model,
    tools, and memory concepts that every later example builds on.
