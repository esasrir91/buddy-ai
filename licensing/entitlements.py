"""The single source of truth for what each plan unlocks.

Features are coarse capability flags the apps check; quotas are numeric limits
(``-1`` = unlimited). The "core coding loop" is intentionally unlimited on every
plan (the user pays their own inference) — we gate convenience/scale/premium
modules, per the commercialization plan.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Premium capability flags used across the suite.
FEATURES = [
    "core_coding",     # Aura IDE + BYO-key/offline — always on
    "builder",         # no-code builder
    "tool_studio",     # LLM tool generation
    "observer",        # screen-monitor assistant
    "training",        # LLM/SLM fine-tuning
    "pulse",           # AI teammate
    "care",            # customer-care suite
    "pack_ca",         # CA / accounting-tax-audit vertical
    "pack_valuation",  # business & asset valuation vertical
    "pack_civil",      # civil-engineering vertical
    "team_workspaces", # shared projects/admin
    "sso",             # enterprise SSO
    "priority_support",
]

# Vertical domain packs (sold as add-ons; bundled into Enterprise).
VERTICAL_PACKS = ["pack_ca", "pack_valuation", "pack_civil"]

# plan -> {features:[...], quotas:{...}}
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "features": ["core_coding", "builder"],
        "quotas": {"tool_studio": 0, "custom_tools": 3, "care_agents": 0, "train_runs": 0, "seats": 1},
    },
    "trial": {  # full Pro + all verticals for 14 days (taste everything)
        "features": ["core_coding", "builder", "tool_studio", "observer", "training", "pulse", "care", "pack_ca", "pack_valuation", "pack_civil", "priority_support"],
        "quotas": {"tool_studio": -1, "custom_tools": -1, "care_agents": 3, "train_runs": 1, "seats": 1},
    },
    "pro": {
        "features": ["core_coding", "builder", "tool_studio", "observer", "training", "pulse", "care", "priority_support"],
        "quotas": {"tool_studio": -1, "custom_tools": -1, "care_agents": 5, "train_runs": -1, "seats": 1},
    },
    "team": {
        "features": ["core_coding", "builder", "tool_studio", "observer", "training", "pulse", "care", "team_workspaces", "priority_support"],
        "quotas": {"tool_studio": -1, "custom_tools": -1, "care_agents": -1, "train_runs": -1, "seats": 5},
    },
    "enterprise": {
        "features": list(FEATURES),
        "quotas": {"tool_studio": -1, "custom_tools": -1, "care_agents": -1, "train_runs": -1, "seats": -1},
    },
}

PUBLIC_PLAN_CATALOG = [
    {"id": "free", "name": "Free", "usd": 0, "inr": 0},
    {"id": "pro", "name": "Pro", "usd": 6, "inr": 399},
    {"id": "team", "name": "Team", "usd": 10, "inr": 849, "per": "user"},
    {"id": "enterprise", "name": "Enterprise", "usd": None, "inr": None},
]

# Domain packs are add-ons on top of any paid plan (bundled free in Enterprise).
PUBLIC_PACK_CATALOG = [
    {"id": "pack_ca", "name": "Varam for CA", "usd": 4, "inr": 299, "desc": "Accounting, GST/TDS, audit & financial-statement copilot (India-first)."},
    {"id": "pack_valuation", "name": "Varam for Valuation", "usd": 4, "inr": 299, "desc": "DCF, comps, sensitivity & Registered-Valuer report drafting."},
    {"id": "pack_civil", "name": "Varam for Civil", "usd": 4, "inr": 299, "desc": "BOQ, rate analysis, quantity take-off & IS-code design checks."},
]


def entitlements_for(plan: str) -> Dict[str, Any]:
    return PLANS.get(plan, PLANS["free"])


def has_feature(plan: str, feature: str) -> bool:
    return feature in entitlements_for(plan)["features"]


def quota(plan: str, name: str) -> int:
    return int(entitlements_for(plan)["quotas"].get(name, 0))


__all__ = [
    "FEATURES", "VERTICAL_PACKS", "PLANS", "PUBLIC_PLAN_CATALOG", "PUBLIC_PACK_CATALOG",
    "entitlements_for", "has_feature", "quota",
]
