"""Compiler: GraphSpec -> live Buddy objects.

The compiler is a pure, deterministic function. It topologically resolves the
node graph (memoizing shared sub-graphs), instantiates each node, injects
edge-connected inputs into the right constructor arguments, and applies
agent/team capabilities. The root node is returned as a ready-to-run
:class:`~buddy.agent.Agent`, :class:`~buddy.team.Team` or
:class:`~buddy.workflow.Workflow`.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from buddy.builder.compiler.errors import CompileError
from buddy.builder.spec.schema import GraphSpec, Node

# category -> package for reconstructing the dotted import path from a node type
_CATEGORY_PACKAGE = {
    "model": "buddy.models",
    "tool": "buddy.tools",
    "vectordb": "buddy.vectordb",
    "embedder": "buddy.embedder",
    "reranker": "buddy.reranker",
    "knowledge": "buddy.knowledge",
    "storage": "buddy.storage",
}

# Which input ports accept *multiple* connections (collected into a list).
_MANY_PORTS = {
    "agent": {"tools"},
    "team": {"members", "tools"},
    "workflow": {"steps"},
    "logic.steps": {"in"},
    "logic.loop": {"in"},
    "logic.parallel": {"in"},
    "logic.condition": {"in"},
    "logic.router": {"in"},
}

# Map an input port name to the constructor kwarg it feeds.
_PORT_TO_KWARG = {
    "model": "model",
    "tools": "tools",
    "knowledge": "knowledge",
    "storage": "storage",
    "members": "members",
    "embedder": "embedder",
    "vectordb": "vector_db",
    "reranker": "reranker",
}

# Capability name -> kwargs applied to Agent/Team (filtered to the real
# constructor signature so unknown kwargs never raise).
_CAPABILITY_KWARGS = {
    "markdown": lambda cfg: {"markdown": cfg.get("markdown", True)},
    "reasoning": lambda cfg: {
        "reasoning": cfg.get("reasoning", True),
        "reasoning_min_steps": cfg.get("reasoning_min_steps"),
        "reasoning_max_steps": cfg.get("reasoning_max_steps"),
    },
    "memory": lambda cfg: {
        "enable_user_memories": cfg.get("enable_user_memories"),
        "enable_session_summaries": cfg.get("enable_session_summaries"),
        "add_history_to_messages": cfg.get("add_history_to_messages"),
        "num_history_runs": cfg.get("num_history_runs"),
    },
}


@dataclass
class CompiledGraph:
    root: Any
    kind: str
    objects: Dict[str, Any]  # node_id -> built object


def _import_target(dotted: str) -> type:
    module_path, _, name = dotted.rpartition(".")
    mod = importlib.import_module(module_path)
    obj = getattr(mod, name, None)
    if obj is None:
        raise CompileError(f"Could not import '{dotted}'")
    return obj


def _resolve_target(node: Node) -> Optional[type]:
    """Resolve the concrete class to instantiate for a node type."""
    t = node.type
    if t == "agent":
        return _import_target("buddy.agent.Agent")
    if t == "team":
        return _import_target("buddy.team.Team")
    if t == "workflow":
        return _import_target("buddy.workflow.Workflow")
    if t == "tool.custom_function":
        return None  # handled specially
    if t.startswith("logic.") or t.startswith("io."):
        return None  # structural - no direct class

    category = t.split(".", 1)[0]
    package = _CATEGORY_PACKAGE.get(category)
    if not package:
        raise CompileError(f"Unknown node type '{t}'", node.id)
    rest = t.split(".", 1)[1]
    return _import_target(f"{package}.{rest}")


def _accepts_kwarg(cls: type, key: str) -> bool:
    """Whether ``cls.__init__`` accepts ``key`` (or **kwargs)."""
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return True
    params = sig.parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return True
    return key in params


def _filter_kwargs(cls: type, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None and _accepts_kwarg(cls, k)}


def _build_custom_function(node: Node):
    """Compile a user-authored Python function into a Buddy tool."""
    from buddy.tools.function import Function

    name = node.data.get("name") or "custom_function"
    code = node.data.get("code") or "def {n}():\n    return ''".format(n=name)
    description = node.data.get("description")
    namespace: Dict[str, Any] = {}
    try:
        exec(code, namespace)  # noqa: S102 - intentional: user-authored tool body
    except Exception as exc:
        raise CompileError(f"Custom function failed to compile: {exc}", node.id)
    fn = namespace.get(name)
    if not callable(fn):
        raise CompileError(f"Custom function '{name}' not found in provided code", node.id)
    if description:
        fn.__doc__ = description
    return Function.from_callable(fn) if hasattr(Function, "from_callable") else fn


def compile_graph(spec: GraphSpec) -> CompiledGraph:
    """Compile a :class:`GraphSpec` into live Buddy objects."""
    built: Dict[str, Any] = {}
    building: set = set()

    def gather_inputs(node: Node) -> Dict[str, List[Any]]:
        grouped: Dict[str, List[Any]] = {}
        for edge in spec.incoming_edges(node.id):
            src = spec.node_by_id(edge.source)
            if src is None:
                raise CompileError(f"Edge references missing node '{edge.source}'", node.id)
            grouped.setdefault(edge.target_port, []).append(build(src))
        return grouped

    def build(node: Node) -> Any:
        if node.id in built:
            return built[node.id]
        if node.id in building:
            raise CompileError("Cycle detected in graph", node.id)
        building.add(node.id)

        obj = _build_node(node, gather_inputs(node))

        building.discard(node.id)
        built[node.id] = obj
        return obj

    root_node = _find_root(spec)
    root_obj = build(root_node)
    return CompiledGraph(root=root_obj, kind=spec.kind, objects=built)


def _build_node(node: Node, inputs: Dict[str, List[Any]]) -> Any:
    t = node.type

    # ---- structural pass-throughs (io / logic) --------------------------- #
    if t.startswith("io."):
        # IO nodes don't produce a Buddy object; they pass their single input
        # through (or None for the input node).
        passthrough = inputs.get("in", [None])
        return passthrough[0] if passthrough else None

    if t == "tool.custom_function":
        return _build_custom_function(node)

    if t.startswith("logic."):
        return _build_logic(node, inputs)

    cls = _resolve_target(node)
    if cls is None:
        raise CompileError(f"Cannot resolve node type '{t}'", node.id)

    kwargs: Dict[str, Any] = dict(node.data)

    # Inject edge-wired inputs into the right kwargs.
    many = _MANY_PORTS.get(t, set())
    for port, values in inputs.items():
        kwarg = _PORT_TO_KWARG.get(port, port)
        if port in many or kwarg in ("tools", "members"):
            kwargs.setdefault(kwarg, [])
            kwargs[kwarg].extend(values)
        else:
            kwargs[kwarg] = values[0]

    # Apply capabilities (surface 2) for agent/team.
    if t in ("agent", "team"):
        for cap_name, cap in node.capabilities.items():
            if not cap.enabled:
                continue
            mapper = _CAPABILITY_KWARGS.get(cap_name)
            if mapper:
                kwargs.update({k: v for k, v in mapper(cap.config).items() if v is not None})

    try:
        return cls(**_filter_kwargs(cls, kwargs))
    except CompileError:
        raise
    except Exception as exc:
        raise CompileError(f"Failed to instantiate {t}: {exc}", node.id)


def _build_logic(node: Node, inputs: Dict[str, List[Any]]) -> Any:
    """Build a Workflow v2 logic primitive from its connected steps."""
    t = node.type
    members = inputs.get("in", [])
    name = node.data.get("name") or t.split(".")[-1]
    try:
        v2 = importlib.import_module("buddy.workflow.v2")
    except Exception as exc:
        raise CompileError(f"Workflow v2 unavailable: {exc}", node.id)

    if t == "logic.step":
        Step = getattr(v2, "Step")
        target = members[0] if members else None
        return _make_step(Step, name, target, node)
    if t == "logic.steps":
        Steps = getattr(v2, "Steps")
        return Steps(name=name, steps=members)
    if t == "logic.loop":
        Loop = getattr(v2, "Loop")
        return Loop(name=name, steps=members)
    if t == "logic.parallel":
        Parallel = getattr(v2, "Parallel")
        return Parallel(*members, name=name)
    if t == "logic.condition":
        Condition = getattr(v2, "Condition")
        return Condition(name=name, steps=members)
    if t == "logic.router":
        Router = getattr(v2, "Router")
        return Router(name=name, choices=members)
    raise CompileError(f"Unknown logic node '{t}'", node.id)


def _make_step(Step, name, target, node):
    from buddy.agent import Agent
    from buddy.team import Team

    if isinstance(target, Agent):
        return Step(name=name, agent=target)
    if isinstance(target, Team):
        return Step(name=name, team=target)
    if target is not None:
        return Step(name=name, executor=target)
    raise CompileError("Step has no connected agent/team", node.id)


def _find_root(spec: GraphSpec) -> Node:
    if spec.root:
        node = spec.node_by_id(spec.root)
        if node is None:
            raise CompileError(f"Declared root '{spec.root}' not found")
        return node

    # Root = a node of the declared kind that has no outgoing edges (nothing
    # depends on it), preferring agent/team/workflow nodes.
    candidates = [n for n in spec.nodes if not spec.outgoing_edges(n.id)]
    if not candidates:
        candidates = list(spec.nodes)

    preferred_types = {"workflow": "workflow", "team": "team", "agent": "agent"}
    want = preferred_types.get(spec.kind, "agent")
    for node in candidates:
        if node.type == want:
            return node
    for node in candidates:
        if node.type in ("agent", "team", "workflow"):
            return node
    if candidates:
        return candidates[0]
    raise CompileError("Graph has no nodes to compile")


__all__ = ["compile_graph", "CompiledGraph"]
