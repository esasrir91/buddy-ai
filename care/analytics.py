"""Lightweight, dependency-free analytics + sentiment for Buddy Care.

Computes the metrics a BPO/support lead cares about: volume, deflection rate
(resolved without human), escalation rate, CSAT, and rough sentiment - all from
the local store. Swap for a proper analytics pipeline at scale.
"""

from __future__ import annotations

from typing import Any, Dict, List

from buddy.care import store

_NEG = {
    "angry", "furious", "terrible", "worst", "useless", "horrible", "hate",
    "disappointed", "frustrated", "annoyed", "broken", "refund", "cancel",
    "complaint", "unacceptable", "ridiculous", "never", "scam",
}
_POS = {
    "thanks", "thank", "great", "perfect", "awesome", "love", "excellent",
    "helpful", "amazing", "good", "appreciate", "wonderful", "resolved",
}


def sentiment_of(text: str) -> str:
    t = text.lower()
    pos = sum(t.count(w) for w in _POS)
    neg = sum(t.count(w) for w in _NEG)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def overview() -> Dict[str, Any]:
    sessions = store.list_sessions(limit=100000)
    escalations = store.list_escalations(limit=100000)
    tickets = store.list_tickets(limit=100000)
    csat = store.list_csat(limit=100000)
    messages = store.all_records("messages")

    escalated_sessions = {e.get("session_id") for e in escalations}
    total_sessions = len(sessions)
    deflected = total_sessions - len(escalated_sessions)

    # Sentiment over customer messages.
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}
    for m in messages:
        if m.get("role") == "user":
            sentiments[sentiment_of(m.get("text", ""))] += 1

    scores = [c.get("score", 0) for c in csat if isinstance(c.get("score"), int)]
    avg_csat = round(sum(scores) / len(scores), 2) if scores else None

    by_channel: Dict[str, int] = {}
    for s in sessions:
        by_channel[s.get("channel") or "web"] = by_channel.get(s.get("channel") or "web", 0) + 1

    return {
        "total_conversations": total_sessions,
        "total_messages": len(messages),
        "open_tickets": sum(1 for t in tickets if t.get("status") == "open"),
        "tickets": len(tickets),
        "escalations": len(escalations),
        "escalation_rate": round(len(escalated_sessions) / total_sessions, 3) if total_sessions else 0,
        "deflection_rate": round(deflected / total_sessions, 3) if total_sessions else 0,
        "avg_csat": avg_csat,
        "csat_responses": len(scores),
        "sentiment": sentiments,
        "by_channel": by_channel,
    }


__all__ = ["overview", "sentiment_of"]
