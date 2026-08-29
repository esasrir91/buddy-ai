"""The GraphSpec schema - the single source of truth for the Buddy Builder.

A builder document is *not* just a node graph. Buddy's features fall into five
distinct surfaces, and the spec models all of them so the builder can cover
100%% of the framework:

1. **Canvas nodes** (``nodes`` + ``edges``)   - agents, teams, models, tools,
   logic (loop/parallel/condition/router), and resource nodes (vectordb,
   embedder, reranker, knowledge, storage).
2. **Capabilities** (``capabilities`` on a node) - agent/team level mixins that
   are *flags*, not nodes: reasoning, personality, security, evolution, memory.
3. **Resource nodes** - modelled as regular nodes (surface 1) wired by edges.
4. **Triggers** (``triggers``)                - deployment channels: API,
   playground, Slack, WhatsApp, Discord, AG-UI, webhook.
5. **Ops** (``evals`` / ``training``)         - evaluation suites and fine-tuning.

The compiler reads this document and produces live Buddy objects. The frontend
(React Flow) reads and writes the exact same shape.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

SPEC_VERSION = "1.0"

# Port "kinds" describe what can legally connect to what. The compiler and the
# frontend both use these to validate edges.
PortKind = Literal[
    "model",
    "tool",
    "knowledge",
    "vectordb",
    "embedder",
    "reranker",
    "memory",
    "storage",
    "flow",  # agent/team/workflow-step composition
    "data",  # generic data passthrough (workflow step I/O)
]


class Port(BaseModel):
    """A connection point on a node."""

    id: str
    name: str
    kind: PortKind
    # ``many`` = this port accepts multiple inbound connections (e.g. an agent's
    # ``tools`` port, or a team's ``members`` port).
    many: bool = False


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0


class Node(BaseModel):
    """A single block on the canvas.

    ``type`` is a registry key (e.g. ``"agent"``, ``"team"``,
    ``"model.anthropic.Claude"``, ``"tool.googlesearch.GoogleSearchTools"``,
    ``"logic.condition"``). The registry maps the type to a NodeType that
    declares ports + a JSON Schema for ``data``.
    """

    id: str
    type: str
    label: Optional[str] = None
    # Validated against the NodeType.config_schema at compile time.
    data: Dict[str, Any] = Field(default_factory=dict)
    # Surface 2: agent/team-level capability mixins keyed by name
    # (e.g. {"reasoning": {...}, "security": {...}}).
    capabilities: Dict[str, "Capability"] = Field(default_factory=dict)
    # UI only - ignored by the compiler.
    position: Position = Field(default_factory=Position)


class Edge(BaseModel):
    """A directed connection from one node's output port to another's input."""

    id: str
    source: str
    source_port: str
    target: str
    target_port: str


class Capability(BaseModel):
    """An agent/team level feature toggle (surface 2).

    Examples: reasoning, personality, security, evolution, memory. These are not
    standalone nodes because in Buddy they are constructor flags / mixins.
    """

    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class Trigger(BaseModel):
    """A deployment channel (surface 4).

    ``type`` examples: ``"api"``, ``"playground"``, ``"slack"``, ``"whatsapp"``,
    ``"discord"``, ``"agui"``, ``"webhook"``.
    """

    id: str
    type: str
    # Which root node this trigger serves (defaults to the graph root).
    target: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class EvalSpec(BaseModel):
    """An evaluation suite to run against the graph (surface 5)."""

    id: str
    type: Literal["accuracy", "performance", "reliability", "competency"]
    config: Dict[str, Any] = Field(default_factory=dict)


class TrainingSpec(BaseModel):
    """A fine-tuning / training job definition (surface 5)."""

    enabled: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)


class GraphSpec(BaseModel):
    """The complete builder document."""

    spec_version: str = SPEC_VERSION
    id: str
    name: str
    description: Optional[str] = None
    # What the root of this graph compiles into.
    kind: Literal["agent", "team", "workflow"] = "agent"
    # Optional explicit root node id; otherwise inferred (the node nothing else
    # depends on, matching ``kind``).
    root: Optional[str] = None

    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)

    triggers: List[Trigger] = Field(default_factory=list)
    evals: List[EvalSpec] = Field(default_factory=list)
    training: Optional[TrainingSpec] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ----------------------------------------------------------------- helpers
    def node_by_id(self, node_id: str) -> Optional[Node]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def incoming_edges(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.target == node_id]

    def outgoing_edges(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.source == node_id]


Node.model_rebuild()

__all__ = [
    "SPEC_VERSION",
    "Port",
    "PortKind",
    "Position",
    "Node",
    "Edge",
    "Capability",
    "Trigger",
    "EvalSpec",
    "TrainingSpec",
    "GraphSpec",
]
