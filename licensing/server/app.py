"""Varam License & Entitlement API (FastAPI).

Public:
  GET  /api/license/plans              plan catalog for the pricing page
  GET  /api/license/public-key         Ed25519 public key (PEM) for offline verify
Auth (MVP: email-based; replace with magic-link/OAuth for production):
  POST /api/auth/start                 {email, device_id, device_name} -> token (+ starts 14d trial)
  POST /api/license/refresh            {account_id, device_id} -> fresh token
  GET  /api/license/me?account_id=     account + entitlements (no token minting)
Devices:
  GET  /api/devices?account_id=        list
  POST /api/devices/revoke             {account_id, device_id}
Billing webhooks (server-to-server):
  POST /api/billing/razorpay/webhook   Razorpay (India — INR / UPI)
  POST /api/billing/stripe/webhook     Stripe (global — USD and other currencies)
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import Body, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel

from buddy.licensing import billing, entitlements, service, store
from buddy.licensing.keys import public_key_pem


class StartRequest(BaseModel):
    email: str
    device_id: str
    device_name: str = ""


class RefreshRequest(BaseModel):
    account_id: str
    device_id: str


class RevokeRequest(BaseModel):
    account_id: str
    device_id: str


def _apply(mapped: Optional[dict]) -> dict:
    if not mapped:
        return {"ok": True, "ignored": True}
    acc = store.upsert_account_by_ref(mapped.get("customer_ref", ""), mapped.get("email"))
    if not acc:
        return {"ok": True, "ignored": True, "reason": "no matching account"}
    seats = mapped.get("seats")
    service.apply_plan_change(acc["id"], mapped["plan"], seats=int(seats) if seats else None,
                              customer_ref=mapped.get("customer_ref"))
    return {"ok": True, "account_id": acc["id"], "plan": mapped["plan"]}


def create_app() -> FastAPI:
    store.init_db()
    app = FastAPI(title="Varam AI License API", version="1.0", docs_url="/api/docs")

    @app.get("/api/license/plans")
    def plans():
        return {"plans": entitlements.PUBLIC_PLAN_CATALOG}

    @app.get("/api/license/public-key")
    def pubkey():
        return {"alg": "EdDSA", "public_key": public_key_pem()}

    @app.post("/api/auth/start")
    def start(req: StartRequest):
        return service.signup_or_login(str(req.email), req.device_id, req.device_name)

    @app.post("/api/license/refresh")
    def refresh(req: RefreshRequest):
        res = service.refresh(req.account_id, req.device_id)
        if not res:
            raise HTTPException(404, "account not found")
        return res

    @app.get("/api/license/me")
    def me(account_id: str = Query(...)):
        acc = store.get_account(account_id)
        if not acc:
            raise HTTPException(404, "account not found")
        return {"account": acc, "entitlements": entitlements.entitlements_for(acc["plan"])}

    @app.get("/api/devices")
    def devices(account_id: str = Query(...)):
        return {"devices": store.list_devices(account_id)}

    @app.post("/api/devices/revoke")
    def revoke(req: RevokeRequest):
        return {"ok": store.revoke_device(req.account_id, req.device_id)}

    @app.post("/api/billing/razorpay/webhook")
    async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header("")):
        body = await request.body()
        if not billing.verify_razorpay(body, x_razorpay_signature):
            raise HTTPException(400, "invalid signature")
        return _apply(billing.parse_razorpay(json.loads(body or b"{}")))

    @app.post("/api/billing/stripe/webhook")
    async def stripe_webhook(request: Request, stripe_signature: str = Header("", alias="stripe-signature")):
        body = await request.body()
        if not billing.verify_stripe(body, stripe_signature):
            raise HTTPException(400, "invalid signature")
        return _apply(billing.parse_stripe(json.loads(body or b"{}")))

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


def serve(host: str = "127.0.0.1", port: int = 8800, reload: bool = False) -> None:
    import uvicorn

    if reload:
        uvicorn.run("buddy.licensing.server.app:create_app", host=host, port=port, reload=True, factory=True)
    else:
        uvicorn.run(create_app(), host=host, port=port)


__all__ = ["create_app", "serve"]
