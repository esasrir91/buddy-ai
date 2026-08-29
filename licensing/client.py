"""Offline entitlement client for the apps (Aura, Builder, etc.).

Holds the issued token + the server's public key, verifies the token locally
(works offline within the grace window), and answers feature/quota questions.
Persists local quota counters on device.

Usage:
    ent = Entitlements.load()              # reads ~/.buddy/entitlement.json
    if ent.has("tool_studio"): ...
    ent.consume("custom_tools")            # raises QuotaExceeded when over limit
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from buddy.licensing import entitlements as ent_catalog
from buddy.licensing.tokens import TokenError, verify_token

_STATE = Path(os.getenv("BUDDY_ENTITLEMENT_FILE", Path.home() / ".buddy" / "entitlement.json"))


class QuotaExceeded(Exception):
    pass


class Entitlements:
    def __init__(self, token: str = "", public_key_pem: str = "", counters: Optional[Dict[str, int]] = None):
        self.token = token
        self.public_key_pem = public_key_pem
        self.counters: Dict[str, int] = counters or {}
        self._payload: Dict[str, Any] = {}
        self._refresh_payload()

    # ----------------------------------------------------------- lifecycle
    @classmethod
    def load(cls) -> "Entitlements":
        if _STATE.exists():
            try:
                d = json.loads(_STATE.read_text(encoding="utf-8"))
                return cls(d.get("token", ""), d.get("public_key", ""), d.get("counters", {}))
            except Exception:
                pass
        return cls()  # defaults to Free

    def save(self) -> None:
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(
            {"token": self.token, "public_key": self.public_key_pem, "counters": self.counters},
            indent=2), encoding="utf-8")

    def set_token(self, token: str, public_key_pem: str = "") -> None:
        self.token = token
        if public_key_pem:
            self.public_key_pem = public_key_pem
        self._refresh_payload()
        self.save()

    def _refresh_payload(self) -> None:
        if not self.token:
            self._payload = {}
            return
        try:
            self._payload = verify_token(self.token, self.public_key_pem or None)
        except TokenError:
            self._payload = {}  # invalid/forged -> treat as Free

    # ------------------------------------------------------------- queries
    @property
    def plan(self) -> str:
        p = self._payload
        if not p or p.get("hard_expired") or p.get("trial_expired"):
            return "free"
        return p.get("plan", "free")

    @property
    def in_grace(self) -> bool:
        return bool(self._payload.get("in_grace"))

    def has(self, feature: str) -> bool:
        # Effective plan already accounts for expiry/trial end.
        return ent_catalog.has_feature(self.plan, feature)

    def quota(self, name: str) -> int:
        return ent_catalog.quota(self.plan, name)

    def remaining(self, name: str) -> int:
        q = self.quota(name)
        if q < 0:
            return -1  # unlimited
        return max(0, q - self.counters.get(name, 0))

    def consume(self, name: str, amount: int = 1) -> None:
        q = self.quota(name)
        if q < 0:
            return  # unlimited
        used = self.counters.get(name, 0)
        if used + amount > q:
            raise QuotaExceeded(f"Quota '{name}' exceeded on the {self.plan} plan ({q}).")
        self.counters[name] = used + amount
        self.save()

    def status(self) -> Dict[str, Any]:
        p = self._payload
        return {
            "plan": self.plan,
            "email": p.get("email"),
            "in_grace": self.in_grace,
            "trial_ends": p.get("trial_ends"),
            "trial_expired": bool(p.get("trial_expired")),
            "expired": bool(p.get("expired")),
            "features": ent_catalog.entitlements_for(self.plan)["features"],
            "quotas": ent_catalog.entitlements_for(self.plan)["quotas"],
            "counters": self.counters,
        }


__all__ = ["Entitlements", "QuotaExceeded"]
