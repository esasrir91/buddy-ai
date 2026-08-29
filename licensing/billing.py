"""Payment webhook verification + event mapping for Razorpay (India) and Stripe
(global). Signature checks use only stdlib hmac/hashlib — no third-party SDKs.

Set secrets via env:
  - BUDDY_RAZORPAY_WEBHOOK_SECRET
  - BUDDY_STRIPE_WEBHOOK_SECRET
  - BUDDY_PRICE_MAP  (optional JSON: {"<stripe_price_id_or_razorpay_plan_id>": "pro"|"team"|...})

Checkout is handled via provider-hosted pages (Stripe Payment Links / Razorpay
Payment Links); this module handles the server-to-server webhooks that tell us
a user paid, upgraded, or cancelled.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional


def _price_map() -> Dict[str, str]:
    raw = os.getenv("BUDDY_PRICE_MAP", "")
    if not raw:
        return {}
    try:
        return {str(k): str(v) for k, v in json.loads(raw).items()}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────── Razorpay (India)
def verify_razorpay(body: bytes, signature: str, secret: Optional[str] = None) -> bool:
    secret = secret or os.getenv("BUDDY_RAZORPAY_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_razorpay(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a Razorpay event to {action, plan, customer_ref, email, seats}."""
    etype = event.get("event", "")
    payload = event.get("payload", {})
    sub = (payload.get("subscription", {}) or {}).get("entity", {}) or {}
    pay = (payload.get("payment", {}) or {}).get("entity", {}) or {}
    notes = sub.get("notes") or pay.get("notes") or {}
    customer_ref = sub.get("customer_id") or pay.get("customer_id") or sub.get("id")
    email = pay.get("email") or notes.get("email")
    plan = notes.get("plan") or _price_map().get(sub.get("plan_id", ""), None)

    if etype in ("subscription.activated", "subscription.charged",
                 "subscription.resumed", "payment.captured"):
        return {"action": "upgrade", "plan": plan or "pro", "customer_ref": customer_ref,
                "email": email, "seats": notes.get("seats")}
    if etype in ("subscription.cancelled", "subscription.halted", "subscription.completed"):
        return {"action": "downgrade", "plan": "free", "customer_ref": customer_ref, "email": email}
    return None


# ──────────────────────────────────────────────────────────────── Stripe (global)
def verify_stripe(body: bytes, signature_header: str, secret: Optional[str] = None) -> bool:
    """Stripe webhook signature header: 'Stripe-Signature: t=<unix>,v1=<hex hmac>'.
    Rejects payloads older than 5 minutes to prevent replay attacks.
    """
    secret = secret or os.getenv("BUDDY_STRIPE_WEBHOOK_SECRET", "")
    if not secret or not signature_header:
        return False
    parts = dict(p.split("=", 1) for p in signature_header.split(",") if "=" in p)
    ts = parts.get("t")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False
    try:
        if abs(int(time.time()) - int(ts)) > 300:
            return False
    except ValueError:
        return False
    signed = f"{ts}.".encode() + body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def parse_stripe(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a Stripe webhook event to {action, plan, customer_ref, email, seats}."""
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object", {}) or {}
    customer_ref = obj.get("customer") or obj.get("id")
    email = obj.get("customer_email") or (obj.get("customer_details") or {}).get("email")
    metadata = obj.get("metadata") or {}

    # Resolve plan from metadata first, then from Stripe Price ID via BUDDY_PRICE_MAP
    plan = metadata.get("plan")
    if not plan:
        items_data = ((obj.get("items") or {}).get("data") or
                      obj.get("lines", {}).get("data") or [])
        if items_data:
            price_id = (items_data[0].get("price") or {}).get("id", "")
            plan = _price_map().get(price_id)

    if etype in ("checkout.session.completed", "customer.subscription.created",
                 "customer.subscription.updated", "invoice.payment_succeeded"):
        # invoice.payment_succeeded fires on every renewal; only upgrade on first payment
        if etype == "invoice.payment_succeeded" and obj.get("billing_reason") == "subscription_cycle":
            return None
        return {"action": "upgrade", "plan": plan or "pro", "customer_ref": customer_ref,
                "email": email, "seats": metadata.get("seats")}
    if etype in ("customer.subscription.deleted", "customer.subscription.paused"):
        return {"action": "downgrade", "plan": "free", "customer_ref": customer_ref, "email": email}
    return None


__all__ = [
    "verify_razorpay", "parse_razorpay",
    "verify_stripe", "parse_stripe",
]
