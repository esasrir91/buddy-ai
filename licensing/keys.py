"""Ed25519 signing keys for the license server.

The server holds the PRIVATE key (signs tokens). Clients only need the PUBLIC
key (verify tokens) — they can never forge entitlements. Keys live under
``~/.buddy/licensing/`` by default, or wherever ``BUDDY_LICENSE_KEYDIR`` points.

For production, inject the private key via ``BUDDY_LICENSE_PRIVKEY`` (PEM string)
from your secret manager instead of a file on disk.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_KEYDIR = Path(os.getenv("BUDDY_LICENSE_KEYDIR", Path.home() / ".buddy" / "licensing"))
_PRIV = _KEYDIR / "private.pem"
_PUB = _KEYDIR / "public.pem"


def _load_priv_from_env() -> Optional[Ed25519PrivateKey]:
    pem = os.getenv("BUDDY_LICENSE_PRIVKEY")
    if not pem:
        return None
    key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    assert isinstance(key, Ed25519PrivateKey)
    return key


def ensure_keys() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Return (private, public), generating + persisting a keypair on first use."""
    env_priv = _load_priv_from_env()
    if env_priv is not None:
        return env_priv, env_priv.public_key()

    if _PRIV.exists():
        priv = serialization.load_pem_private_key(_PRIV.read_bytes(), password=None)
        assert isinstance(priv, Ed25519PrivateKey)
        return priv, priv.public_key()

    priv = Ed25519PrivateKey.generate()
    _KEYDIR.mkdir(parents=True, exist_ok=True)
    _PRIV.write_bytes(priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    _PUB.write_bytes(priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    try:
        os.chmod(_PRIV, 0o600)
    except Exception:
        pass
    return priv, priv.public_key()


def public_key_pem() -> str:
    _, pub = ensure_keys()
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def load_public_key(pem: str) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem.encode("utf-8"))
    assert isinstance(key, Ed25519PublicKey)
    return key


__all__ = ["ensure_keys", "public_key_pem", "load_public_key"]
