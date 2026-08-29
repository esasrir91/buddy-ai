"""Compact, signed entitlement tokens (JWT-like, EdDSA / Ed25519).

Format:  base64url(header) . base64url(payload) . base64url(signature)
The signature covers "header.payload". Verification is fully offline given the
public key, so apps work without contacting the server (within the grace window).
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from buddy.licensing.keys import ensure_keys, load_public_key

_HEADER = {"alg": "EdDSA", "typ": "VRM"}


class TokenError(Exception):
    pass


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(payload: Dict[str, Any], private_key: Optional[Ed25519PrivateKey] = None) -> str:
    if private_key is None:
        private_key, _ = ensure_keys()
    header_b = _b64e(json.dumps(_HEADER, separators=(",", ":")).encode())
    payload_b = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{header_b}.{payload_b}".encode("ascii")
    sig = private_key.sign(signing_input)
    return f"{header_b}.{payload_b}.{_b64e(sig)}"


def _verify_signature(token: str, public_key: Ed25519PublicKey) -> Dict[str, Any]:
    try:
        header_b, payload_b, sig_b = token.split(".")
    except ValueError:
        raise TokenError("malformed token")
    signing_input = f"{header_b}.{payload_b}".encode("ascii")
    try:
        public_key.verify(_b64d(sig_b), signing_input)
    except InvalidSignature:
        raise TokenError("bad signature")
    return json.loads(_b64d(payload_b))


def verify_token(
    token: str,
    public_key_pem: Optional[str] = None,
    *,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    """Verify signature and expiry. Returns the payload.

    Raises ``TokenError`` on bad signature. Adds derived flags:
      - ``expired``: past ``exp``
      - ``in_grace``: expired but within ``grace_until`` (apps keep working)
      - ``trial_expired``: plan == 'trial' and now > trial_ends
    """
    pub = load_public_key(public_key_pem) if public_key_pem else ensure_keys()[1]
    payload = _verify_signature(token, pub)

    now = int(time.time()) if now is None else now
    exp = int(payload.get("exp", 0))
    grace_until = int(payload.get("grace_until", exp))
    payload["expired"] = bool(exp and now > exp)
    payload["in_grace"] = bool(payload["expired"] and now <= grace_until)
    payload["hard_expired"] = bool(exp and now > grace_until)

    trial_ends = payload.get("trial_ends")
    payload["trial_expired"] = bool(
        payload.get("plan") == "trial" and trial_ends and now > int(trial_ends)
    )
    return payload


__all__ = ["issue_token", "verify_token", "TokenError"]
