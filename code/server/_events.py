"""Per-session event bus for CursorTools → SSE stream communication."""
from __future__ import annotations

import queue
import threading
from typing import Any, Dict, Optional

# {session_id: Queue[dict | None]}
_queues: Dict[str, "queue.Queue[Optional[Dict[str, Any]]]"] = {}
# {session_id: (threading.Event, dict | None)}
_answer_holders: Dict[str, threading.Event] = {}
_answers: Dict[str, Any] = {}
_lock = threading.Lock()


def register(session_id: str) -> "queue.Queue[Optional[Dict[str, Any]]]":
    q: queue.Queue = queue.Queue()
    with _lock:
        _queues[session_id] = q
    return q


def get_queue(session_id: str) -> "queue.Queue[Optional[Dict[str, Any]]]":
    with _lock:
        q = _queues.get(session_id)
    if q is None:
        q = register(session_id)
    return q


def emit(session_id: str, event: Dict[str, Any]) -> None:
    with _lock:
        q = _queues.get(session_id)
    if q is not None:
        q.put(event)


def close(session_id: str) -> None:
    """Signal the SSE stream that the agent run is done."""
    with _lock:
        q = _queues.get(session_id)
    if q is not None:
        q.put(None)  # sentinel


def unregister(session_id: str) -> None:
    with _lock:
        _queues.pop(session_id, None)
        _answer_holders.pop(session_id, None)
        _answers.pop(session_id, None)


def wait_answer(session_id: str, timeout: float = 300.0) -> Optional[Any]:
    """Block until the UI posts an answer for this session."""
    ev = threading.Event()
    with _lock:
        _answer_holders[session_id] = ev
    answered = ev.wait(timeout=timeout)
    with _lock:
        _answer_holders.pop(session_id, None)
        return _answers.pop(session_id, None) if answered else None


def post_answer(session_id: str, answers: Any) -> bool:
    with _lock:
        _answers[session_id] = answers
        ev = _answer_holders.get(session_id)
    if ev:
        ev.set()
        return True
    return False
