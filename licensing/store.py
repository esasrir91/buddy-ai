"""SQLite persistence for the license server (stdlib only).

Tables: accounts, devices, events. Plan state lives on the account. Swap for
Postgres in production behind the same functions.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB = Path(os.getenv("BUDDY_LICENSE_DB", Path.home() / ".buddy" / "licensing" / "licenses.db"))
_LOCK = threading.Lock()


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_DB)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _LOCK, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts(
                id TEXT PRIMARY KEY, email TEXT UNIQUE, plan TEXT NOT NULL DEFAULT 'free',
                trial_ends INTEGER, seats INTEGER DEFAULT 1,
                customer_ref TEXT, created INTEGER, updated INTEGER
            );
            CREATE TABLE IF NOT EXISTS devices(
                id TEXT PRIMARY KEY, account_id TEXT, name TEXT, created INTEGER,
                UNIQUE(account_id, id)
            );
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT, kind TEXT,
                data TEXT, ts INTEGER
            );
            """
        )


def _now() -> int:
    return int(time.time())


def get_account_by_email(email: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM accounts WHERE email=?", (email.lower(),)).fetchone()
        return dict(row) if row else None


def get_account(account_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return dict(row) if row else None


def create_account(email: str, plan: str = "free", trial_ends: Optional[int] = None) -> Dict[str, Any]:
    acc = {
        "id": "acc_" + uuid.uuid4().hex[:16], "email": email.lower(), "plan": plan,
        "trial_ends": trial_ends, "seats": 1, "customer_ref": None,
        "created": _now(), "updated": _now(),
    }
    with _LOCK, _conn() as c:
        c.execute(
            "INSERT INTO accounts(id,email,plan,trial_ends,seats,customer_ref,created,updated)"
            " VALUES(:id,:email,:plan,:trial_ends,:seats,:customer_ref,:created,:updated)", acc)
    log_event(acc["id"], "account_created", {"plan": plan})
    return acc


def update_plan(account_id: str, plan: str, *, seats: Optional[int] = None,
                trial_ends: Optional[int] = None, customer_ref: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with _LOCK, _conn() as c:
        sets = ["plan=?", "updated=?"]
        vals: List[Any] = [plan, _now()]
        if seats is not None:
            sets.append("seats=?"); vals.append(seats)
        if trial_ends is not None:
            sets.append("trial_ends=?"); vals.append(trial_ends)
        if customer_ref is not None:
            sets.append("customer_ref=?"); vals.append(customer_ref)
        vals.append(account_id)
        c.execute(f"UPDATE accounts SET {','.join(sets)} WHERE id=?", vals)
    log_event(account_id, "plan_changed", {"plan": plan, "seats": seats})
    return get_account(account_id)


def upsert_account_by_ref(customer_ref: str, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find an account by payment-customer ref, or by email; used by webhooks."""
    with _conn() as c:
        row = c.execute("SELECT * FROM accounts WHERE customer_ref=?", (customer_ref,)).fetchone()
        if row:
            return dict(row)
    if email:
        acc = get_account_by_email(email) or create_account(email)
        update_plan(acc["id"], acc["plan"], customer_ref=customer_ref)
        return get_account(acc["id"])
    return None


# ----------------------------------------------------------------- devices
def register_device(account_id: str, device_id: str, name: str = "") -> Dict[str, Any]:
    dev = {"id": device_id, "account_id": account_id, "name": name, "created": _now()}
    with _LOCK, _conn() as c:
        c.execute("INSERT OR IGNORE INTO devices(id,account_id,name,created) VALUES(:id,:account_id,:name,:created)", dev)
    return dev


def list_devices(account_id: str) -> List[Dict[str, Any]]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM devices WHERE account_id=?", (account_id,)).fetchall()]


def revoke_device(account_id: str, device_id: str) -> bool:
    with _LOCK, _conn() as c:
        cur = c.execute("DELETE FROM devices WHERE account_id=? AND id=?", (account_id, device_id))
        return cur.rowcount > 0


def device_count(account_id: str) -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM devices WHERE account_id=?", (account_id,)).fetchone()["n"]


# ------------------------------------------------------------------ events
def log_event(account_id: str, kind: str, data: Dict[str, Any]) -> None:
    with _LOCK, _conn() as c:
        c.execute("INSERT INTO events(account_id,kind,data,ts) VALUES(?,?,?,?)",
                  (account_id, kind, json.dumps(data), _now()))


__all__ = [
    "init_db", "get_account", "get_account_by_email", "create_account", "update_plan",
    "upsert_account_by_ref", "register_device", "list_devices", "revoke_device",
    "device_count", "log_event",
]
