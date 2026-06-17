"""Helpers to assemble LangGraph state graphs from Buddy agents."""

from typing import TYPE_CHECKING, Annotated, Any, List, Optional, Sequence, Tuple, TypedDict, Union

from buddy.integrations._utils import require
from buddy.integrations.langgraph.nodes import BuddyNode

if TYPE_CHECKING:  # pragma: no cover - typing only
    from buddy.agent import Agent
    from buddy.team import Team

AgentLike = Union["Agent", "Team", BuddyNode]
NamedStep = Union[AgentLike, Tuple[str, AgentLike]]

# Populated lazily by build_default_state() so get_type_hints() can resolve the
# state schema's annotations from this module's globals.
add_messages = None  # type: ignore[assignment]
_DEFAULT_STATE: Optional[type] = None


def add_buddy_node(
    graph: Any,
    name: str,
    agent: AgentLike,
    *,
    input_key: str = "input",
    output_key: str = "output",
    append_messages: bool = True,
) -> BuddyNode:
    """Add a Buddy agent/team to an existing LangGraph ``StateGraph``.

    Args:
        graph: A ``langgraph.graph.StateGraph`` instance.
        name: Node name within the graph.
        agent: A Buddy ``Agent``/``Team`` or a pre-built :class:`BuddyNode`.
        input_key / output_key / append_messages: Forwarded to :class:`BuddyNode`
            when ``agent`` is not already a node.

    Returns:
        The :class:`BuddyNode` that was registered.
    """
    node = (
        agent
        if isinstance(agent, BuddyNode)
        else BuddyNode(
            agent,
            name=name,
            input_key=input_key,
            output_key=output_key,
            append_messages=append_messages,
        )
    )
    graph.add_node(name, node)
    return node


def build_sequential_graph(
    steps: Sequence[NamedStep],
    *,
    state_schema: Optional[type] = None,
    compile: bool = True,
    checkpointer: Any = None,
) -> Any:
    """Build a linear LangGraph pipeline from an ordered list of Buddy agents.

    Each step's output feeds the next step's ``input`` via a shared ``output``/
    ``input`` hop, and every step also appends to ``state["messages"]``.

    Args:
        steps: Ordered agents/teams or ``(name, agent)`` pairs. Bare agents use
            their ``.name`` (falling back to ``step_{i}``).
        state_schema: Optional LangGraph state schema. Defaults to a built-in
            ``BuddyGraphState`` (``input``, ``output``, ``messages``).
        compile: If True (default), return a compiled graph ready to ``invoke``.
            If False, return the uncompiled ``StateGraph`` for further wiring.
        checkpointer: Optional LangGraph checkpointer passed to ``compile``.

    Returns:
        A compiled graph (``compile=True``) or the ``StateGraph`` instance.
    """
    require("langgraph", "langgraph")
    from langgraph.graph import END, START, StateGraph

    schema = state_schema or build_default_state()
    graph = StateGraph(schema)

    resolved: List[Tuple[str, AgentLike]] = []
    for i, step in enumerate(steps):
        if isinstance(step, tuple):
            name, agent = step
        else:
            agent = step
            name = getattr(agent, "name", None) or f"step_{i}"
        resolved.append((str(name), agent))

    if not resolved:
        raise ValueError("build_sequential_graph requires at least one step.")

    for i, (name, agent) in enumerate(resolved):
        # Chain output -> input between consecutive steps by writing the next
        # step's input key. The first node reads the user-provided "input".
        append_messages = True
        add_buddy_node(graph, name, agent, append_messages=append_messages)

    graph.add_edge(START, resolved[0][0])
    for (name, _), (next_name, _) in zip(resolved, resolved[1:]):
        graph.add_edge(name, next_name)
    graph.add_edge(resolved[-1][0], END)

    if compile:
        return graph.compile(checkpointer=checkpointer) if checkpointer else graph.compile()
    return graph


def build_default_state() -> type:
    """Return the default LangGraph state schema used by Buddy helpers.

    The schema is built once and cached. ``add_messages`` is injected into this
    module's globals so LangGraph's ``get_type_hints`` can resolve the
    ``Annotated`` reducer annotation (TypedDict subclasses resolve forward refs
    against their defining module's globals, not local scope).
    """
    global _DEFAULT_STATE, add_messages
    if _DEFAULT_STATE is not None:
        return _DEFAULT_STATE

    require("langgraph", "langgraph")
    try:
        from langgraph.graph.message import add_messages as _add_messages

        add_messages = _add_messages

        class BuddyGraphState(TypedDict, total=False):
            input: str
            output: str
            messages: Annotated[list, add_messages]

    except ImportError:  # pragma: no cover - older langgraph without reducer

        class BuddyGraphState(TypedDict, total=False):  # type: ignore[no-redef]
            input: str
            output: str
            messages: list

    _DEFAULT_STATE = BuddyGraphState
    return _DEFAULT_STATE
