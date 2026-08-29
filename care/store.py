"""Local persistence for Buddy Care: conversations, tickets, escalations, CSAT.

JSONL files under ``~/.buddy/aura_care/``. This is a self-contained MVP store;
production deployments would swap this for Postgres + a real CRM/ticketing
integration (Zendesk/Freshdesk) behind the same interface.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DIR = Path(os.getenv("BUDDY_CARE_DATA", Path.home() / ".buddy" / "aura_care"))
_LOCK = threading.Lock()

_FILES = {
    "messages": _DIR / "messages.jsonl",
    "tickets": _DIR / "tickets.jsonl",
    "escalations": _DIR / "escalations.jsonl",
    "csat": _DIR / "csat.jsonl",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(kind: str, record: Dict[str, Any]) -> Dict[str, Any]:
    _DIR.mkdir(parents=True, exist_ok=True)
    record.setdefault("ts", _now())
    with _LOCK:
        with _FILES[kind].open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _read(kind: str, limit: Optional[int] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    path = _FILES[kind]
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if session_id and rec.get("session_id") != session_id:
            continue
        out.append(rec)
    return out[-limit:] if limit else out


# ---------------------------------------------------------------- messages
def log_message(session_id: str, role: str, text: str, channel: str = "web") -> Dict[str, Any]:
    return _append("messages", {"session_id": session_id, "role": role, "text": text, "channel": channel})


def conversation(session_id: str) -> List[Dict[str, Any]]:
    return _read("messages", session_id=session_id)


def list_sessions(limit: int = 100) -> List[Dict[str, Any]]:
    msgs = _read("messages")
    sessions: Dict[str, Dict[str, Any]] = {}
    for m in msgs:
        sid = m.get("session_id", "")
        s = sessions.setdefault(sid, {"session_id": sid, "channel": m.get("channel"), "messages": 0, "last_ts": None, "preview": ""})
        s["messages"] += 1
        s["last_ts"] = m.get("ts")
        if m.get("role") == "user":
            s["preview"] = (m.get("text") or "")[:80]
    return sorted(sessions.values(), key=lambda x: x["last_ts"] or "", reverse=True)[:limit]


# ----------------------------------------------------------------- tickets
def create_ticket(session_id: str, subject: str, details: str, priority: str = "normal") -> Dict[str, Any]:
    return _append("tickets", {
        "id": "TKT-" + uuid.uuid4().hex[:8].upper(),
        "session_id": session_id, "subject": subject, "details": details,
        "priority": priority, "status": "open",
    })


def list_tickets(limit: int = 200) -> List[Dict[str, Any]]:
    return list(reversed(_read("tickets", limit=limit)))


# ------------------------------------------------------------- escalations
def create_escalation(session_id: str, reason: str, sentiment: Optional[str] = None) -> Dict[str, Any]:
    return _append("escalations", {
        "id": "ESC-" + uuid.uuid4().hex[:8].upper(),
        "session_id": session_id, "reason": reason, "sentiment": sentiment, "status": "pending",
    })


def list_escalations(limit: int = 200) -> List[Dict[str, Any]]:
    return list(reversed(_read("escalations", limit=limit)))


# -------------------------------------------------------------------- csat
def record_csat(session_id: str, score: int, comment: str = "") -> Dict[str, Any]:
    return _append("csat", {"session_id": session_id, "score": int(score), "comment": comment})


def list_csat(limit: int = 1000) -> List[Dict[str, Any]]:
    return _read("csat", limit=limit)


def all_records(kind: str) -> List[Dict[str, Any]]:
    return _read(kind)


__all__ = [
    "log_message", "conversation", "list_sessions",
    "create_ticket", "list_tickets",
    "create_escalation", "list_escalations",
    "record_csat", "list_csat", "all_records",
]
