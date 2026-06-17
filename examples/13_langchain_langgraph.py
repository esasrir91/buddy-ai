"""
Example 13 — LangChain & LangGraph integration

This example demonstrates how to:
1. Use a Buddy model as a LangChain chat model (BuddyChatModel)
2. Convert tools between Buddy and LangChain in both directions
3. Expose a Buddy Agent as a LangChain tool (BuddyAgentTool)
4. Build a multi-agent LangGraph pipeline from Buddy agents (build_sequential_graph)
5. Route between agents with Buddy's Competency Engine (make_competency_edge)

Prerequisites:
    pip install "buddy-ai[langgraph]"   # installs langchain-core + langgraph
    export OPENAI_API_KEY=sk-...        # required for the live agent runs
"""

import os

from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools import tool

# ---------------------------------------------------------------------------
# Tools used across both ecosystems
# ---------------------------------------------------------------------------


@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text."""
    return len(text.split())


# ---------------------------------------------------------------------------
# 1. Buddy model -> LangChain chat model
# ---------------------------------------------------------------------------
print("=" * 60)
print("1. BuddyChatModel — Buddy's providers inside LangChain")
print("=" * 60)

if not os.getenv("OPENAI_API_KEY"):
    print("Set OPENAI_API_KEY to run the live LangChain/LangGraph demos.\n")
else:
    from buddy.integrations.langchain import BuddyChatModel

    llm = BuddyChatModel(buddy_model=OpenAIChat(id="gpt-4o-mini"))
    result = llm.invoke("Say hello in French in 3 words.")
    print(f"LangChain invoke -> {result.content}\n")

# ---------------------------------------------------------------------------
# 2. Tool conversion (Buddy <-> LangChain)
# ---------------------------------------------------------------------------
print("=" * 60)
print("2. Tool conversion in both directions")
print("=" * 60)

from buddy.integrations.langchain import from_langchain_tool, to_langchain_tool

lc_tool = to_langchain_tool(word_count)
print(f"Buddy -> LangChain tool: name={lc_tool.name!r}")

back_to_buddy = from_langchain_tool(lc_tool)
print(f"LangChain -> Buddy Function: name={back_to_buddy.name!r}\n")

# ---------------------------------------------------------------------------
# 3. Buddy Agent -> LangChain tool
# ---------------------------------------------------------------------------
print("=" * 60)
print("3. BuddyAgentTool — a Buddy agent as a LangChain tool")
print("=" * 60)

from buddy.integrations.langchain import BuddyAgentTool

researcher = Agent(
    name="researcher",
    model=OpenAIChat(id="gpt-4o-mini"),
    description="Researches a topic and returns concise bullet points.",
)
agent_tool = BuddyAgentTool(researcher, name="research", description="Research a topic").as_tool()
print(f"Exposed Buddy agent as LangChain tool: {agent_tool.name!r}\n")

# ---------------------------------------------------------------------------
# 4. LangGraph pipeline from Buddy agents
# ---------------------------------------------------------------------------
print("=" * 60)
print("4. build_sequential_graph — multi-agent LangGraph pipeline")
print("=" * 60)

if os.getenv("OPENAI_API_KEY"):
    from buddy.integrations.langgraph import build_sequential_graph

    writer = Agent(name="writer", model=OpenAIChat(id="gpt-4o-mini"), description="Write a short paragraph.")
    editor = Agent(name="editor", model=OpenAIChat(id="gpt-4o-mini"), description="Tighten and polish text.")

    graph = build_sequential_graph([writer, editor])
    final_state = graph.invoke({"input": "Write one sentence about RAG, then polish it."})
    print(f"Pipeline output -> {final_state.get('output')}\n")
else:
    print("Skipped (needs OPENAI_API_KEY).\n")

# ---------------------------------------------------------------------------
# 5. Competency-aware routing edge in LangGraph
# ---------------------------------------------------------------------------
print("=" * 60)
print("5. make_competency_edge — route to the most competent member")
print("=" * 60)

if os.getenv("OPENAI_API_KEY"):
    from langgraph.graph import END, START, StateGraph

    from buddy.eval.competency_runtime import (
        CompetencyRouter,
        CompetencyTracker,
        KeywordDomainClassifier,
        MemberProfile,
    )
    from buddy.integrations.langgraph import BuddyNode, build_default_state, make_competency_edge

    alice = MemberProfile(
        Agent(name="alice", model=OpenAIChat(id="gpt-4o-mini"), instructions="You are a Python expert."),
        CompetencyTracker(base=10, seed={"python": 9.0, "sql": 4.0}),
    )
    bob = MemberProfile(
        Agent(name="bob", model=OpenAIChat(id="gpt-4o-mini"), instructions="You are a SQL expert."),
        CompetencyTracker(base=10, seed={"python": 5.0, "sql": 8.0}),
    )
    router = CompetencyRouter([alice, bob], base=10, domains=["python", "sql"], classifier=KeywordDomainClassifier())

    graph = StateGraph(build_default_state())
    graph.add_node("alice", BuddyNode(alice.agent, name="alice"))
    graph.add_node("bob", BuddyNode(bob.agent, name="bob"))
    graph.add_conditional_edges(START, make_competency_edge(router), {"alice": "alice", "bob": "bob"})
    graph.add_edge("alice", END)
    graph.add_edge("bob", END)
    app = graph.compile()

    out = app.invoke({"input": "Write a SQL query to find the top 5 customers by revenue."})
    print(f"Routed pipeline output -> {out.get('output')}")
else:
    print("Skipped (needs OPENAI_API_KEY).")
