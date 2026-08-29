"""Varam licensing & entitlements.

A self-contained license server + offline client:
  - issues signed (Ed25519) entitlement tokens carrying plan, features, quotas
    and trial/expiry info;
  - apps verify those tokens offline with the embedded public key, enforce
    quotas locally, and honour an offline grace period;
  - payment webhooks (Razorpay / Paddle) upgrade/downgrade plans.

No external dependency beyond ``cryptography`` (already available). Tokens are a
compact JWT-like structure signed with EdDSA.
"""

from buddy.licensing.entitlements import PLANS, entitlements_for
from buddy.licensing.tokens import issue_token, verify_token

__all__ = ["PLANS", "entitlements_for", "issue_token", "verify_token"]
