"""High-level licensing operations used by the server: start trials, issue/refresh
entitlement tokens, and apply plan changes from billing.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from buddy.licensing import entitlements, store
from buddy.licensing.tokens import issue_token

TRIAL_DAYS = 14
TOKEN_TTL_DAYS = 7          # short-lived; apps refresh
GRACE_DAYS = 14             # offline grace beyond exp before downgrading to free
DAY = 86400


def _effective_plan(acc: Dict[str, Any], now: int) -> str:
    """A trial that has ended behaves as free until billing upgrades it."""
    plan = acc.get("plan", "free")
    if plan == "trial" and acc.get("trial_ends") and now > int(acc["trial_ends"]):
        return "free"
    return plan


def build_token(acc: Dict[str, Any], device_id: str, now: Optional[int] = None) -> str:
    now = int(time.time()) if now is None else now
    plan = _effective_plan(acc, now)
    ent = entitlements.entitlements_for(plan)
    payload: Dict[str, Any] = {
        "sub": acc["id"],
        "email": acc.get("email"),
        "plan": plan,
        "features": ent["features"],
        "quotas": ent["quotas"],
        "seats": acc.get("seats", 1),
        "device_id": device_id,
        "iat": now,
        "exp": now + TOKEN_TTL_DAYS * DAY,
        "grace_until": now + (TOKEN_TTL_DAYS + GRACE_DAYS) * DAY,
        "jti": uuid.uuid4().hex,
        "ver": 1,
    }
    if acc.get("plan") == "trial" and acc.get("trial_ends"):
        payload["trial_ends"] = int(acc["trial_ends"])
    return issue_token(payload)


def signup_or_login(email: str, device_id: str, device_name: str = "") -> Dict[str, Any]:
    """Create the account (with a 14-day trial) on first sight, else log in.
    Returns {account, token}."""
    now = int(time.time())
    acc = store.get_account_by_email(email)
    if acc is None:
        acc = store.create_account(email, plan="trial", trial_ends=now + TRIAL_DAYS * DAY)
    store.register_device(acc["id"], device_id, device_name)
    return {"account": acc, "token": build_token(acc, device_id, now)}


def refresh(account_id: str, device_id: str) -> Optional[Dict[str, Any]]:
    acc = store.get_account(account_id)
    if not acc:
        return None
    store.register_device(acc["id"], device_id)
    return {"account": acc, "token": build_token(acc, device_id)}


def apply_plan_change(account_id: str, plan: str, *, seats: Optional[int] = None,
                      customer_ref: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return store.update_plan(account_id, plan, seats=seats, customer_ref=customer_ref)


__all__ = ["signup_or_login", "refresh", "apply_plan_change", "build_token",
           "TRIAL_DAYS", "TOKEN_TTL_DAYS", "GRACE_DAYS"]
