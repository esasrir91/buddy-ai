"""Buddy Care - the customer-care / BPO capability built on Buddy.

A grounded support agent (knowledge base + ticketing + escalation + order
lookup), a supervisor console with analytics (deflection, CSAT, sentiment,
escalation rate), an embeddable chat widget, and a local store for
conversations/tickets/escalations. Voice, WhatsApp, email and CRM connectors
are roadmap-pluggable on top of Buddy's existing channel/voice tools.
"""

import buddy.models  # noqa: F401  (resolve framework circular imports early)

from buddy.care.settings import CareSettings, load_settings, save_settings

__all__ = ["CareSettings", "load_settings", "save_settings"]
