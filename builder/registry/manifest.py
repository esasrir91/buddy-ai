"""Node manifest types and JSON-Schema generation.

A :class:`NodeType` is the builder's description of one draggable block: its
category, label, ports, and a JSON Schema for its ``data`` config. The schema is
generated automatically from the target class/callable's signature so the
palette and config forms stay in sync with the framework with zero hand-coding.
"""

from __future__ import annotations

import enum
import inspect
import typing
from dataclasses import MISSING, fields, is_dataclass
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Manifest models
# --------------------------------------------------------------------------- #


class PortDef(BaseModel):
    id: str
    name: str
    kind: str
    many: bool = False
    direction: str = "in"  # "in" | "out"


class NodeType(BaseModel):
    """Describes a single draggable node type."""

    type: str  # registry key, e.g. "model.anthropic.Claude"
    category: str  # "core" | "model" | "tool" | "logic" | "vectordb" | ...
    label: str
    description: Optional[str] = None
    # Dotted import path of the target class (None for structural nodes that the
    # compiler resolves with bespoke logic, e.g. agent/team/logic.*).
    target: Optional[str] = None
    ports: List[PortDef] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    # Free-form tags for search/filtering in the palette.
    tags: List[str] = Field(default_factory=list)


class CapabilityDef(BaseModel):
    """An agent/team-level capability (surface 2)."""

    name: str
    label: str
    description: Optional[str] = None
    config_schema: Dict[str, Any] = Field(default_factory=dict)


class Catalog(BaseModel):
    """The full set of building blocks the builder exposes."""

    node_types: List[NodeType] = Field(default_factory=list)
    capabilities: List[CapabilityDef] = Field(default_factory=list)
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    evals: List[Dict[str, Any]] = Field(default_factory=list)
    # Diagnostics: modules that could not be introspected (missing optional deps)
    skipped: List[Dict[str, str]] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# JSON Schema generation from a callable signature
# --------------------------------------------------------------------------- #

_PRIMITIVES = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    dict: {"type": "object"},
    list: {"type": "array"},
}

# Parameters that are wired by *edges*, not entered as form values. We skip them
# in the config schema; the compiler injects them from connected nodes.
EDGE_PARAMS = {
    "model",
    "tools",
    "team",
    "members",
    "agent",
    "knowledge",
    "vector_db",
    "vectordb",
    "embedder",
    "reranker",
    "memory",
    "storage",
    "db",
    "executor",
    "steps",
    "client",
    "async_client",
}

# Never expose these as configurable fields.
_SKIP_PARAMS = {"self", "args", "kwargs"}


def _annotation_to_schema(annotation: Any) -> Dict[str, Any]:
    """Best-effort map a type annotation to a JSON Schema fragment."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    # Optional[X] / Union[...]
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]  # noqa: E721
        if len(non_none) == 1:
            return _annotation_to_schema(non_none[0])
        return {}  # heterogeneous union -> free-form

    if origin in (list, List):
        item = _annotation_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item or {}}

    if origin in (dict, Dict):
        return {"type": "object"}

    # Literal[...] -> enum
    if origin is typing.Literal:
        return {"enum": list(args)}

    if inspect.isclass(annotation):
        if issubclass(annotation, enum.Enum):
            return {"enum": [e.value for e in annotation]}
        if annotation in _PRIMITIVES:
            return dict(_PRIMITIVES[annotation])

    return {}


def _iter_init_params(target: Callable) -> List[inspect.Parameter]:
    """Yield constructor parameters for a class or callable, handling dataclasses."""
    if is_dataclass(target):
        # Dataclasses defined with init=False still expose fields() usefully.
        try:
            return list(inspect.signature(target.__init__).parameters.values())
        except (TypeError, ValueError):
            pass
        params: List[inspect.Parameter] = []
        for f in fields(target):
            if not f.init:
                continue
            default = f.default if f.default is not MISSING else inspect.Parameter.empty
            params.append(
                inspect.Parameter(
                    f.name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=f.type,
                )
            )
        return params
    try:
        return list(inspect.signature(target).parameters.values())
    except (TypeError, ValueError):
        return []


def schema_from_callable(target: Callable, extra_skip: Optional[set] = None) -> Dict[str, Any]:
    """Generate a JSON Schema (draft-07 style) for a class constructor.

    Edge-wired params and private params are skipped so only true form fields
    appear. Defaults are preserved so the UI can pre-fill values.
    """
    skip = _SKIP_PARAMS | EDGE_PARAMS | (extra_skip or set())
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param in _iter_init_params(target):
        name = param.name
        if name in skip or name.startswith("_"):
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        schema = _annotation_to_schema(param.annotation)
        if param.default is not inspect.Parameter.empty and param.default is not None:
            # Only attach JSON-serialisable defaults.
            if isinstance(param.default, (str, int, float, bool, list, dict)):
                schema = {**schema, "default": param.default}
        else:
            if param.default is inspect.Parameter.empty:
                required.append(name)

        if not schema:
            schema = {}  # free-form
        properties[name] = schema

    out: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        out["required"] = required
    return out


# --------------------------------------------------------------------------- #
# Static manifests for non-node surfaces (capabilities / triggers / evals)
# --------------------------------------------------------------------------- #

CAPABILITY_DEFS: List[CapabilityDef] = [
    CapabilityDef(
        name="reasoning",
        label="Reasoning",
        description="Step-by-step reasoning (AdvancedReasoning + provider reasoning models).",
        config_schema={
            "type": "object",
            "properties": {
                "reasoning": {"type": "boolean", "default": True},
                "reasoning_min_steps": {"type": "integer", "default": 1},
                "reasoning_max_steps": {"type": "integer", "default": 10},
            },
        },
    ),
    CapabilityDef(
        name="memory",
        label="Memory",
        description="Persistent user memory and session summaries (Memory v2).",
        config_schema={
            "type": "object",
            "properties": {
                "enable_user_memories": {"type": "boolean", "default": True},
                "enable_session_summaries": {"type": "boolean", "default": False},
                "add_history_to_messages": {"type": "boolean", "default": True},
                "num_history_runs": {"type": "integer", "default": 3},
            },
        },
    ),
    CapabilityDef(
        name="personality",
        label="Personality",
        description="Communication style and emotional state (PersonalityEngine).",
        config_schema={
            "type": "object",
            "properties": {
                "communication_style": {
                    "enum": ["professional", "friendly", "concise", "empathetic", "playful"],
                    "default": "professional",
                },
                "tone": {"type": "string"},
            },
        },
    ),
    CapabilityDef(
        name="security",
        label="Security",
        description="Adversarial / prompt-injection protection (AdversarialProtectionSystem).",
        config_schema={
            "type": "object",
            "properties": {
                "threat_level": {"enum": ["low", "medium", "high", "critical"], "default": "medium"},
                "action": {"enum": ["allow", "warn", "sanitize", "block"], "default": "sanitize"},
            },
        },
    ),
    CapabilityDef(
        name="evolution",
        label="Evolution",
        description="Self-improving agent genome + fitness evaluation (EvolutionaryMixin).",
        config_schema={
            "type": "object",
            "properties": {
                "strategy": {"enum": ["mutation", "crossover", "tournament"], "default": "mutation"},
                "population_size": {"type": "integer", "default": 10},
            },
        },
    ),
    CapabilityDef(
        name="markdown",
        label="Markdown output",
        description="Format responses as markdown.",
        config_schema={"type": "object", "properties": {"markdown": {"type": "boolean", "default": True}}},
    ),
]

TRIGGER_DEFS: List[Dict[str, Any]] = [
    {"type": "playground", "label": "Playground", "description": "Interactive local playground UI."},
    {"type": "api", "label": "REST API (FastAPI)", "description": "Serve as a FastAPI endpoint."},
    {"type": "agui", "label": "AG-UI Chat", "description": "Embeddable AG-UI chat widget."},
    {"type": "slack", "label": "Slack", "description": "Slack bot channel."},
    {"type": "whatsapp", "label": "WhatsApp", "description": "WhatsApp channel."},
    {"type": "discord", "label": "Discord", "description": "Discord bot channel."},
    {"type": "webhook", "label": "Webhook", "description": "Generic HTTP webhook trigger."},
]

EVAL_DEFS: List[Dict[str, Any]] = [
    {"type": "accuracy", "label": "Accuracy", "description": "Score correctness against expected answers."},
    {"type": "performance", "label": "Performance", "description": "Latency / throughput measurement."},
    {"type": "reliability", "label": "Reliability", "description": "Tool-call and consistency checks."},
    {"type": "competency", "label": "Competency", "description": "Capability/competency runtime checks."},
]


__all__ = [
    "PortDef",
    "NodeType",
    "CapabilityDef",
    "Catalog",
    "schema_from_callable",
    "EDGE_PARAMS",
    "CAPABILITY_DEFS",
    "TRIGGER_DEFS",
    "EVAL_DEFS",
]
