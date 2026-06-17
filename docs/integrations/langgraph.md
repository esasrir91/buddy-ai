# LangGraph Integration

`buddy.integrations.langgraph` lets you use Buddy agents and teams as nodes in a
LangGraph `StateGraph`, build linear pipelines in one call, and route between
members with Buddy's Competency Engine.

```bash
pip install "buddy-ai[langgraph]"
```

```python
from buddy.integrations.langgraph import (
    BuddyNode,
    add_buddy_node,
    build_sequential_graph,
    build_default_state,
    make_competency_edge,
)
```

## Buddy agent → LangGraph node

A `BuddyNode` is a plain `state -> state_update` callable (sync and async) —
exactly LangGraph's node contract. It reads a prompt from the graph state, runs
the Buddy agent, and writes the result back.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.integrations.langgraph import BuddyNode

writer = Agent(name="writer", model=OpenAIChat(id="gpt-4o-mini"))
node = BuddyNode(writer, input_key="input", output_key="output")

update = node({"input": "Write one sentence about RAG."})
# {"output": "...", "messages": [AIMessage(...)]}
```

**Input resolution order:** `state[input_key]` → content of the last
`state["messages"]` entry → stringified state.

**State update:** writes `state[output_key]`, and (when `append_messages=True`)
appends an assistant message to `state["messages"]` using LangGraph's
`add_messages` reducer when available.

`BuddyNode` itself requires only Buddy — no LangGraph import — so you can unit
test nodes without a graph.

## Linear pipeline in one call

`build_sequential_graph` assembles and compiles a multi-agent pipeline. Each
step appends to `messages`, and the graph runs them in order.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.integrations.langgraph import build_sequential_graph

writer = Agent(name="writer", model=OpenAIChat(id="gpt-4o-mini"))
editor = Agent(name="editor", model=OpenAIChat(id="gpt-4o-mini"))

graph = build_sequential_graph([writer, editor])
final = graph.invoke({"input": "Draft and then polish a tagline for a coffee app."})
print(final["output"])
```

Steps may be bare agents (named by `.name`) or `(name, agent)` pairs. Pass
`compile=False` to get the uncompiled `StateGraph` for further wiring, or
`checkpointer=...` to enable durable state and resume.

```python
from langgraph.checkpoint.memory import MemorySaver

graph = build_sequential_graph([writer, editor], checkpointer=MemorySaver())
```

## Adding nodes to your own graph

```python
from langgraph.graph import StateGraph, START, END
from buddy.integrations.langgraph import add_buddy_node, build_default_state

graph = StateGraph(build_default_state())
add_buddy_node(graph, "writer", writer)
add_buddy_node(graph, "editor", editor)
graph.add_edge(START, "writer")
graph.add_edge("writer", "editor")
graph.add_edge("editor", END)
app = graph.compile()
```

`build_default_state()` returns a `TypedDict` schema with `input`, `output`, and
a reducer-backed `messages` channel.

## Competency-aware routing

`make_competency_edge` turns a Buddy
[`CompetencyRouter`](../advanced/competency.md) into a LangGraph conditional-edge
function: it classifies the task and returns the name of the most competent
member, which LangGraph uses to pick the next node.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.eval.competency_runtime import (
    CompetencyRouter, CompetencyTracker, KeywordDomainClassifier, MemberProfile,
)
from buddy.integrations.langgraph import BuddyNode, build_default_state, make_competency_edge
from langgraph.graph import StateGraph, START, END

alice = MemberProfile(
    Agent(name="alice", model=OpenAIChat(id="gpt-4o-mini"), instructions="Python expert."),
    CompetencyTracker(base=10, seed={"python": 9.0, "sql": 4.0}),
)
bob = MemberProfile(
    Agent(name="bob", model=OpenAIChat(id="gpt-4o-mini"), instructions="SQL expert."),
    CompetencyTracker(base=10, seed={"python": 5.0, "sql": 8.0}),
)
router = CompetencyRouter([alice, bob], base=10, domains=["python", "sql"],
                          classifier=KeywordDomainClassifier())

graph = StateGraph(build_default_state())
graph.add_node("alice", BuddyNode(alice.agent, name="alice"))
graph.add_node("bob", BuddyNode(bob.agent, name="bob"))
graph.add_conditional_edges(START, make_competency_edge(router), {"alice": "alice", "bob": "bob"})
graph.add_edge("alice", END)
graph.add_edge("bob", END)
app = graph.compile()

# A SQL task routes to bob.
app.invoke({"input": "Write a SQL query for top customers by revenue."})
```

!!! tip "One competency model, online and offline"
    The same router that scores and prioritizes training offline now also drives
    runtime routing inside your graph — no separate logic to maintain.

## API summary

| Symbol | Type | Description |
|--------|------|-------------|
| `BuddyNode(agent, *, name=, input_key=, output_key=, append_messages=)` | class | Buddy agent/team as a LangGraph node |
| `add_buddy_node(graph, name, agent, ...)` | function | Register a Buddy agent on a `StateGraph` |
| `build_sequential_graph(steps, *, state_schema=, compile=, checkpointer=)` | function | Build & compile a linear pipeline |
| `build_default_state()` | function | Default `TypedDict` state schema |
| `make_competency_edge(router, *, input_key=, domain_key=)` | function | Conditional edge that routes by competency |
