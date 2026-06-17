"""Competency-aware conditional edges for LangGraph.

Bridges Buddy's :class:`~buddy.eval.competency_runtime.CompetencyRouter` to
LangGraph's conditional-edge API, so a graph can dynamically route to the most
competent member node for each task.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from buddy.eval.competency_runtime import CompetencyRouter


def make_competency_edge(
    router: "CompetencyRouter",
    *,
    input_key: str = "input",
    domain_key: Optional[str] = None,
    record_decision_key: str = "routing_decision",
) -> Callable[[Dict[str, Any]], str]:
    """Build a LangGraph conditional-edge function from a ``CompetencyRouter``.

    The returned function reads the task text from the graph state, asks the
    router which member should handle it, and returns that member's name — which
    LangGraph uses to select the next node. Wire each member node's name to match
    the member names registered on the router.

    Args:
        router: A configured ``CompetencyRouter``.
        input_key: State key holding the task text. Defaults to ``"input"``.
        domain_key: Optional state key holding a pre-classified domain; if set
            and present, classification is skipped.
        record_decision_key: Unused by the edge itself, reserved for callers that
            also store the decision in state.

    Returns:
        A callable ``state -> member_name`` suitable for
        ``graph.add_conditional_edges(source, make_competency_edge(router), mapping)``.

    Example:
        >>> edge = make_competency_edge(router)
        >>> graph.add_conditional_edges(
        ...     "classify",
        ...     edge,
        ...     {"alice": "alice", "bob": "bob"},
        ... )
    """

    def _route(state: Dict[str, Any]) -> str:
        task = state.get(input_key)
        if not task:
            messages = state.get("messages")
            if messages:
                last = messages[-1]
                task = getattr(last, "content", None) or (
                    last[1] if isinstance(last, (tuple, list)) and len(last) == 2 else str(last)
                )
        task = task if isinstance(task, str) else str(task or "")

        domain = state.get(domain_key) if domain_key else None
        decision = router.decide(task, domain=domain)
        return decision.member_name

    return _route
