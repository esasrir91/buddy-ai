"""Auto-introspection catalog.

Walks every Buddy subsystem, discovers public building blocks (models, tools,
vectordbs, embedders, rerankers, knowledge sources, storage), and turns each
into a :class:`NodeType`. Structural nodes (agent / team / workflow / logic.*)
are declared explicitly because their edge-wiring semantics are bespoke.

Coverage is *automatic*: adding a new tool to ``buddy/tools`` makes it appear in
the palette with no builder code changes. The coverage test in
``tests/builder`` asserts this stays true.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from buddy.builder.registry.manifest import (
    CAPABILITY_DEFS,
    EVAL_DEFS,
    TRIGGER_DEFS,
    Catalog,
    NodeType,
    PortDef,
    schema_from_callable,
)

# (subsystem package, base class dotted path, category, output port kind)
_DISCOVERY: List[Tuple[str, str, str, str]] = [
    ("buddy.models", "buddy.models.base.Model", "model", "model"),
    ("buddy.tools", "buddy.tools.toolkit.Toolkit", "tool", "tool"),
    ("buddy.vectordb", "buddy.vectordb.base.VectorDb", "vectordb", "vectordb"),
    ("buddy.embedder", "buddy.embedder.base.Embedder", "embedder", "embedder"),
    ("buddy.reranker", "buddy.reranker.base.Reranker", "reranker", "reranker"),
    ("buddy.knowledge", "buddy.knowledge.agent.AgentKnowledge", "knowledge", "knowledge"),
    ("buddy.storage", "buddy.storage.base.Storage", "storage", "storage"),
]

_catalog: Optional[Catalog] = None

# Discovering the whole framework imports many modules and is slow (~tens of
# seconds), so the result is cached to disk and reused across restarts.
_CACHE_PATH = Path(os.getenv("BUDDY_BUILDER_CACHE", Path.home() / ".buddy" / "builder_catalog.json"))


def _import_base(path: str) -> Optional[type]:
    module_path, _, cls_name = path.rpartition(".")
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, cls_name, None)
    except Exception:
        return None


def _iter_submodules(package_name: str, skipped: List[Dict[str, str]]):
    """Yield imported submodules of ``package_name``, skipping ones that fail."""
    try:
        package = importlib.import_module(package_name)
    except Exception as exc:  # pragma: no cover - whole subsystem unavailable
        skipped.append({"module": package_name, "error": str(exc)})
        return
    yield package
    if not hasattr(package, "__path__"):
        return
    for info in pkgutil.walk_packages(package.__path__, prefix=package_name + "."):
        name = info.name
        # Skip private and obviously non-component modules.
        leaf = name.rsplit(".", 1)[-1]
        if leaf.startswith("_") or leaf in {"base", "message", "response", "schema", "defaults"}:
            continue
        try:
            yield importlib.import_module(name)
        except Exception as exc:
            # Missing optional dependency -> skip gracefully (the long tail is
            # still reachable via the generic custom-tool / dotted-path node).
            skipped.append({"module": name, "error": type(exc).__name__ + ": " + str(exc)[:140]})


def _public_subclasses(module, base: type) -> List[Type]:
    found = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if name.startswith("_"):
            continue
        if obj is base:
            continue
        if not issubclass(obj, base):
            continue
        # Only classes actually defined in (or re-exported from) buddy.
        if not getattr(obj, "__module__", "").startswith("buddy."):
            continue
        if inspect.isabstract(obj):
            continue
        found.append(obj)
    return found


def _dotted(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def _discover_category(package: str, base_path: str, category: str, port_kind: str, skipped) -> List[NodeType]:
    base = _import_base(base_path)
    if base is None:
        skipped.append({"module": base_path, "error": "base class unavailable"})
        return []

    seen: Dict[str, NodeType] = {}
    for module in _iter_submodules(package, skipped):
        for cls in _public_subclasses(module, base):
            target = _dotted(cls)
            if target in seen:
                continue
            # Short, friendly type key, e.g. "model.anthropic.Claude".
            short = target[len("buddy.") :] if target.startswith("buddy.") else target
            type_key = f"{category}." + short.split(".", 1)[1] if "." in short else f"{category}.{cls.__name__}"
            try:
                config_schema = schema_from_callable(cls)
            except Exception:
                config_schema = {"type": "object", "properties": {}}

            ports: List[PortDef] = [PortDef(id="out", name=category.title(), kind=port_kind, direction="out")]
            # Knowledge sources usually accept a vector_db + embedder.
            if category == "knowledge":
                ports.append(PortDef(id="vectordb", name="Vector DB", kind="vectordb", direction="in"))
                ports.append(PortDef(id="embedder", name="Embedder", kind="embedder", direction="in"))
            if category == "vectordb":
                ports.append(PortDef(id="embedder", name="Embedder", kind="embedder", direction="in"))

            seen[target] = NodeType(
                type=type_key,
                category=category,
                label=_humanize(cls.__name__),
                description=(inspect.getdoc(cls) or "").strip().split("\n")[0] or None,
                target=target,
                ports=ports,
                config_schema=config_schema,
                tags=[category, cls.__module__.split(".")[-1]],
            )
    return list(seen.values())


def _humanize(name: str) -> str:
    # "GoogleSearchTools" -> "Google Search Tools"
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i and (name[i - 1].islower() or (i + 1 < len(name) and name[i + 1].islower())):
            out.append(" ")
        out.append(ch)
    return "".join(out)


# --------------------------------------------------------------------------- #
# Structural nodes (bespoke wiring)
# --------------------------------------------------------------------------- #


def _structural_nodes() -> List[NodeType]:
    from buddy.agent import Agent
    from buddy.team import Team
    from buddy.workflow import Workflow

    agent = NodeType(
        type="agent",
        category="core",
        label="Agent",
        description="An LLM agent: model + instructions + tools + knowledge + memory.",
        target="buddy.agent.Agent",
        ports=[
            PortDef(id="model", name="Model", kind="model", direction="in"),
            PortDef(id="tools", name="Tools", kind="tool", many=True, direction="in"),
            PortDef(id="knowledge", name="Knowledge", kind="knowledge", direction="in"),
            PortDef(id="storage", name="Storage", kind="storage", direction="in"),
            PortDef(id="out", name="Agent", kind="flow", direction="out"),
        ],
        config_schema=schema_from_callable(Agent.__init__),
        tags=["core", "agent"],
    )
    team = NodeType(
        type="team",
        category="core",
        label="Team",
        description="A team of agents/teams (route, coordinate, or collaborate).",
        target="buddy.team.Team",
        ports=[
            PortDef(id="members", name="Members", kind="flow", many=True, direction="in"),
            PortDef(id="model", name="Model", kind="model", direction="in"),
            PortDef(id="tools", name="Tools", kind="tool", many=True, direction="in"),
            PortDef(id="knowledge", name="Knowledge", kind="knowledge", direction="in"),
            PortDef(id="out", name="Team", kind="flow", direction="out"),
        ],
        config_schema=schema_from_callable(Team.__init__),
        tags=["core", "team"],
    )
    workflow = NodeType(
        type="workflow",
        category="core",
        label="Workflow",
        description="A multi-step pipeline of agents/teams/logic.",
        target="buddy.workflow.Workflow",
        ports=[
            PortDef(id="steps", name="Steps", kind="flow", many=True, direction="in"),
            PortDef(id="out", name="Workflow", kind="flow", direction="out"),
        ],
        config_schema=schema_from_callable(Workflow.__init__),
        tags=["core", "workflow"],
    )

    def logic(type_key: str, label: str, desc: str, many_in: bool = True) -> NodeType:
        return NodeType(
            type=type_key,
            category="logic",
            label=label,
            description=desc,
            target=None,
            ports=[
                PortDef(id="in", name="In", kind="flow", many=many_in, direction="in"),
                PortDef(id="out", name="Out", kind="flow", direction="out"),
            ],
            config_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            tags=["logic"],
        )

    logic_nodes = [
        logic("logic.step", "Step", "A single workflow step wrapping an agent/team.", many_in=False),
        logic("logic.steps", "Steps", "A sequential group of steps."),
        logic("logic.loop", "Loop", "Repeat steps until a condition is met."),
        logic("logic.parallel", "Parallel", "Run steps concurrently."),
        logic("logic.condition", "Condition", "Branch based on a condition."),
        logic("logic.router", "Router", "Route input to one of several branches."),
    ]

    # Input / output nodes (workflow data + chat I/O).
    io_nodes = [
        NodeType(
            type="io.input",
            category="io",
            label="Input",
            description="Entry point: the user message / workflow input.",
            target=None,
            ports=[PortDef(id="out", name="Input", kind="data", direction="out")],
            config_schema={"type": "object", "properties": {"name": {"type": "string", "default": "input"}}},
            tags=["io"],
        ),
        NodeType(
            type="io.output",
            category="io",
            label="Output",
            description="Exit point: the final response.",
            target=None,
            ports=[PortDef(id="in", name="Output", kind="data", direction="in")],
            config_schema={"type": "object", "properties": {"name": {"type": "string", "default": "output"}}},
            tags=["io"],
        ),
    ]

    # Custom function tool + MCP - the escape hatch guaranteeing the long tail
    # is always reachable.
    escape_nodes = [
        NodeType(
            type="tool.custom_function",
            category="tool",
            label="Custom Function",
            description="A user-defined Python function exposed as a tool (@tool).",
            target="buddy.tools.function.Function",
            ports=[PortDef(id="out", name="Tool", kind="tool", direction="out")],
            config_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "code": {"type": "string", "description": "Python source for the function body."},
                },
                "required": ["name"],
            },
            tags=["tool", "custom"],
        ),
    ]

    return [agent, team, workflow, *logic_nodes, *io_nodes, *escape_nodes]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def build_catalog(force: bool = False, use_disk_cache: bool = True) -> Catalog:
    """Build (and cache) the full catalog of building blocks.

    Order of resolution: in-memory cache -> disk cache -> full introspection.
    """
    global _catalog
    if _catalog is not None and not force:
        return _catalog

    if use_disk_cache and not force and _CACHE_PATH.exists():
        try:
            _catalog = Catalog.model_validate_json(_CACHE_PATH.read_text(encoding="utf-8"))
            return _catalog
        except Exception:
            pass  # corrupt/old cache -> rebuild

    import buddy  # noqa: F401  ensure top-level package initialised first

    skipped: List[Dict[str, str]] = []
    node_types: List[NodeType] = list(_structural_nodes())

    for package, base_path, category, port_kind in _DISCOVERY:
        node_types.extend(_discover_category(package, base_path, category, port_kind, skipped))

    _catalog = Catalog(
        node_types=node_types,
        capabilities=CAPABILITY_DEFS,
        triggers=TRIGGER_DEFS,
        evals=EVAL_DEFS,
        skipped=skipped,
    )

    if use_disk_cache:
        try:
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(_catalog.model_dump_json(), encoding="utf-8")
        except Exception:
            pass

    return _catalog


def get_catalog() -> Catalog:
    return build_catalog(force=False)


def get_node_type(type_key: str) -> Optional[NodeType]:
    for nt in get_catalog().node_types:
        if nt.type == type_key:
            return nt
    return None


__all__ = ["build_catalog", "get_catalog", "get_node_type"]
