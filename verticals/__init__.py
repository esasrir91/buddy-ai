"""Varam AI domain packs - vertical professional copilots.

Each pack (CA, Valuation, Civil) is a thin layer over the Buddy framework: a
tuned agent, a deterministic domain toolkit, a knowledge seed, and document
templates. Packs are co-pilots for *qualified professionals* - a Chartered
Accountant, an IBBI Registered Valuer, or a licensed engineer must review and
sign every deliverable. See ``buddy.verticals.base`` for the shared plumbing.
"""

from __future__ import annotations

# Import early to resolve the framework's internal circular imports (same trick
# used by buddy.code and buddy.builder).
import buddy.models  # noqa: F401

__all__ = ["base", "ca", "valuation", "civil"]
