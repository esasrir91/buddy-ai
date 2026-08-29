"""Varam AI - Civil pack: civil-engineering copilot (estimation/BOQ, rate analysis,
quantity takeoff, IS-code design checks). Civil-law/litigation support is on the
roadmap as a separate sub-pack; this scaffold covers civil engineering first.
"""

from __future__ import annotations

from buddy.verticals.civil.agent import build_civil_agent
from buddy.verticals.civil.tools import CivilTools

__all__ = ["build_civil_agent", "CivilTools"]
