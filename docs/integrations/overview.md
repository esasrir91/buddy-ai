# Integrations

Buddy AI plays well with the wider agent ecosystem. The
`buddy.integrations` package provides optional, dependency-light adapters so
Buddy components interoperate with **LangChain** and **LangGraph** — use Buddy's
unified models, agents, and tools where you already are, and bring LangChain
tools into Buddy.

!!! note "Version"
    Documents buddy-ai **2.2.0**. Adapters are verified against
    `langchain-core >= 0.3` and `langgraph >= 0.2`.

## Why integrate instead of replace?

Buddy and LangGraph solve problems at different layers:

| Layer | Strength |
|-------|----------|
| **Buddy** | Agent platform — 30+ models, tools, memory, RAG, teams, PULSE, Competency Engine |
| **LangChain** | Huge tool/connector ecosystem, chains, retrievers |
| **LangGraph** | Graph orchestration — cycles, checkpoints, human-in-the-loop |

Rather than reimplement an orchestration engine, Buddy lets you **use the best of
each**: Buddy agents as the capable unit of work, LangGraph as the orchestration
engine, and LangChain for its connectors.

## Installation

```bash
# LangChain interop only
pip install "buddy-ai[langchain]"

# LangGraph orchestration (also pulls in langchain-core)
pip install "buddy-ai[langgraph]"
```

The adapters import their third-party dependency **lazily**. Importing
`buddy.integrations.langchain` or `buddy.integrations.langgraph` works even when
the package is not installed; a clear, actionable error is raised only when you
actually call an adapter that needs it.

## Detecting availability

```python
import buddy

print(buddy.LANGCHAIN_AVAILABLE)   # True if langchain-core is installed
print(buddy.LANGGRAPH_AVAILABLE)   # True if langgraph is installed
print(buddy.get_available_features())
```

## What's included

### LangChain ([details](langchain.md))

| Adapter | Purpose |
|---------|---------|
| `BuddyChatModel` | Use any Buddy model as a LangChain `BaseChatModel` |
| `BuddyAgentTool` | Expose a Buddy `Agent`/`Team` as a LangChain tool |
| `to_langchain_tool` / `from_langchain_tool` | Convert tools in either direction |
| `to_buddy_messages` / `from_buddy_message` | Convert message objects |

### LangGraph ([details](langgraph.md))

| Adapter | Purpose |
|---------|---------|
| `BuddyNode` | Wrap a Buddy `Agent`/`Team` as a LangGraph node |
| `add_buddy_node` | Register a Buddy agent on an existing `StateGraph` |
| `build_sequential_graph` | Build & compile a linear multi-agent pipeline |
| `build_default_state` | Default state schema (`input`, `output`, `messages`) |
| `make_competency_edge` | Route to the most competent member via the Competency Engine |

## Runnable example

A complete, runnable walkthrough lives at
[`examples/13_langchain_langgraph.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/13_langchain_langgraph.py).
