"""CareTools - a customer-support toolkit the support agent can use during a
conversation: raise tickets, escalate to a human, look up orders, search the
knowledge base, and record CSAT. Bound to a single conversation ``session_id``.
"""

from __future__ import annotations

from typing import List, Optional

from buddy.care import store
from buddy.tools import Toolkit


class CareTools(Toolkit):
    def __init__(self, session_id: str, knowledge_text: str = "", **kwargs):
        self.session_id = session_id
        self.knowledge_text = knowledge_text or ""
        super().__init__(
            name="care_tools",
            tools=[
                self.search_knowledge,
                self.create_ticket,
                self.escalate_to_human,
                self.lookup_order,
                self.record_csat,
            ],
            **kwargs,
        )

    def search_knowledge(self, query: str) -> str:
        """Search the company knowledge base / FAQ for an answer.

        Args:
            query (str): What to look up (a question or keywords).

        Returns:
            str: The most relevant snippets from the knowledge base, or a note if empty.
        """
        if not self.knowledge_text.strip():
            return "No knowledge base configured."
        q = [w for w in query.lower().split() if len(w) > 2]
        paras = [p.strip() for p in self.knowledge_text.split("\n\n") if p.strip()]
        scored = sorted(paras, key=lambda p: sum(p.lower().count(w) for w in q), reverse=True)
        hits = [p for p in scored if sum(p.lower().count(w) for w in q) > 0][:4]
        return "\n\n".join(hits) if hits else "No matching knowledge-base entry found."

    def create_ticket(self, subject: str, details: str, priority: str = "normal") -> str:
        """Raise a support ticket for follow-up by the team.

        Args:
            subject (str): Short summary of the issue.
            details (str): Full details, including any IDs the customer gave.
            priority (str): One of low, normal, high, urgent.

        Returns:
            str: Confirmation with the ticket ID.
        """
        t = store.create_ticket(self.session_id, subject, details, priority)
        return f"Ticket {t['id']} created (priority: {t['priority']}). The team will follow up."

    def escalate_to_human(self, reason: str) -> str:
        """Hand the conversation off to a human support agent.

        Args:
            reason (str): Why escalation is needed (e.g. angry customer, complex refund).

        Returns:
            str: Confirmation that a human has been notified.
        """
        e = store.create_escalation(self.session_id, reason)
        return f"Escalated to a human agent ({e['id']}). A teammate will join shortly."

    def lookup_order(self, order_id: str) -> str:
        """Look up the status of a customer's order (demo connector).

        Args:
            order_id (str): The order/reference number.

        Returns:
            str: The order status. Replace this connector with your real OMS/CRM.
        """
        # Demo/pluggable: real deployments wire this to the order system.
        return (
            f"[demo] Order {order_id}: shipped, expected delivery in 2-3 business days. "
            "(Connect Buddy Care to your order system to return live data.)"
        )

    def record_csat(self, score: int, comment: str = "") -> str:
        """Record a customer satisfaction score at the end of a conversation.

        Args:
            score (int): Satisfaction rating from 1 (bad) to 5 (great).
            comment (str): Optional free-text feedback.

        Returns:
            str: Acknowledgement.
        """
        store.record_csat(self.session_id, score, comment)
        return "Thanks for the feedback!"


__all__ = ["CareTools"]
