"""LangGraph interoperability for Buddy AI.

Drop Buddy agents and teams into a LangGraph ``StateGraph`` as nodes, build
linear pipelines in one call, and route between members using Buddy's
Competency Engine.

Public API:

- :class:`BuddyNode` — wrap a Buddy ``Agent``/``Team`` as a LangGraph node
  (a ``state -> state_update`` callable, sync and async).
- :func:`add_buddy_node` — register a Buddy agent on an existing ``StateGraph``.
- :func:`build_sequential_graph` — assemble and compile a linear multi-agent
  pipeline from an ordered list of agents.
- :func:`build_default_state` — the default ``TypedDict`` state schema
  (``input``, ``output``, ``messages``) with ``add_messages`` reducer.
- :func:`make_competency_edge` — a conditional-edge function that routes to the
  most competent member via a ``CompetencyRouter``.

``BuddyNode`` requires only Buddy. The graph builders import ``langgraph``
lazily and raise a clear error if it is not installed.
"""

from __future__ import annotations

from buddy.integrations.langgraph.graph import (
    add_buddy_node,
    build_default_state,
    build_sequential_graph,
)
from buddy.integrations.langgraph.nodes import BuddyNode
from buddy.integrations.langgraph.routing import make_competency_edge

__all__ = [
    "BuddyNode",
    "add_buddy_node",
    "build_sequential_graph",
    "build_default_state",
    "make_competency_edge",
]
