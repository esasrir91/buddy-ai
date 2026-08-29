"""Thin entitlement gate for the Aura backend.

Wraps the offline ``buddy.licensing.client.Entitlements`` with a process-wide
singleton and a ``require``/``enforce_quota`` helper that raise HTTP 402 (Payment
Required) so the UI can prompt an upgrade. Free/trial/pro/team all work offline.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from buddy.licensing.client import Entitlements, QuotaExceeded

_FEATURE_LABEL = {
    "tool_studio": "Tool Studio",
    "observer": "Observer",
    "training": "Model training",
    "pulse": "Pulse AI teammate",
    "care": "Customer-Care",
    "pack_ca": "Varam for CA",
    "pack_valuation": "Varam for Valuation",
    "pack_civil": "Varam for Civil",
    "team_workspaces": "Team workspaces",
}

_ent: Optional[Entitlements] = None


def get() -> Entitlements:
    global _ent
    if _ent is None:
        _ent = Entitlements.load()
    return _ent


def reload() -> Entitlements:
    global _ent
    _ent = Entitlements.load()
    return _ent


def require(feature: str) -> None:
    if not get().has(feature):
        label = _FEATURE_LABEL.get(feature, feature)
        raise HTTPException(status_code=402, detail={
            "error": "upgrade_required",
            "feature": feature,
            "message": f"{label} is a Pro feature. Start your free trial or upgrade to unlock it.",
            "plan": get().plan,
        })


def enforce_quota(name: str, amount: int = 1) -> None:
    try:
        get().consume(name, amount)
    except QuotaExceeded as e:
        raise HTTPException(status_code=402, detail={
            "error": "quota_exceeded", "quota": name, "message": str(e), "plan": get().plan,
        })


__all__ = ["get", "reload", "require", "enforce_quota"]
