"""Runner: compile a GraphSpec and execute it, yielding transport-agnostic
events that the server adapts to SSE for the live preview panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional, Union

from buddy.builder.compiler import CompiledGraph, compile_graph
from buddy.builder.compiler.errors import CompileError
from buddy.builder.spec.schema import GraphSpec


@dataclass
class RunEvent:
    """A normalized streaming event."""

    type: str  # "started" | "content" | "tool" | "completed" | "error"
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "content": self.content, "data": self.data}


def _extract_content(event: Any) -> Optional[str]:
    """Best-effort pull of streamed text from a Buddy run event/response."""
    for attr in ("content", "delta", "text"):
        val = getattr(event, attr, None)
        if isinstance(val, str) and val:
            return val
    if isinstance(event, str):
        return event
    return None


def _event_kind(event: Any) -> str:
    name = type(event).__name__.lower()
    if "tool" in name:
        return "tool"
    if "error" in name:
        return "error"
    if "complete" in name or "completed" in name:
        return "completed"
    return "content"


def run_graph(
    spec: Union[GraphSpec, Dict[str, Any]],
    message: str,
    *,
    compiled: Optional[CompiledGraph] = None,
) -> Iterator[RunEvent]:
    """Compile (if needed) and run the graph, streaming normalized events."""
    if isinstance(spec, dict):
        spec = GraphSpec.model_validate(spec)

    yield RunEvent(type="started", data={"graph": spec.name})

    try:
        compiled = compiled or compile_graph(spec)
    except CompileError as exc:
        yield RunEvent(type="error", content=str(exc), data={"node_id": exc.node_id})
        return
    except Exception as exc:  # pragma: no cover - defensive
        yield RunEvent(type="error", content=f"Compile failed: {exc}")
        return

    root = compiled.root
    runner = getattr(root, "run", None)
    if not callable(runner):
        yield RunEvent(type="error", content="Compiled object is not runnable")
        return

    streamed_any = False
    try:
        result = runner(message, stream=True)
        for event in result:
            kind = _event_kind(event)
            text = _extract_content(event)
            if text:
                streamed_any = True
                yield RunEvent(type="content", content=text)
            elif kind in ("tool", "error", "completed"):
                yield RunEvent(type=kind, data={"event": type(event).__name__})
    except TypeError:
        # Some objects don't accept stream=; fall back to a single response.
        try:
            result = runner(message)
            text = _extract_content(result) or (str(result) if result is not None else "")
            if text:
                streamed_any = True
                yield RunEvent(type="content", content=text)
        except Exception as exc:
            yield RunEvent(type="error", content=f"Run failed: {exc}")
            return
    except Exception as exc:
        yield RunEvent(type="error", content=f"Run failed: {exc}")
        return

    yield RunEvent(type="completed", data={"streamed": streamed_any})


def run_graph_sync(spec: Union[GraphSpec, Dict[str, Any]], message: str) -> str:
    """Run and collect the full text response (used by tests / non-streaming)."""
    chunks = []
    for event in run_graph(spec, message):
        if event.type == "content":
            chunks.append(event.content)
        elif event.type == "error":
            raise RuntimeError(event.content)
    return "".join(chunks)


__all__ = ["run_graph", "run_graph_sync", "RunEvent"]
