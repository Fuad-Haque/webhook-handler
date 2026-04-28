import json
import time
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_models import Endpoint, ReplayLog, WebhookEvent
from app.ws_manager import manager

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class EndpointCreate(BaseModel):
    name: str
    source: str
    secret: str | None = None


class ReplayRequest(BaseModel):
    target_url: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def serialize_event(event: WebhookEvent) -> dict:
    return {
        "id": str(event.id),
        "endpoint_id": str(event.endpoint_id),
        "method": event.method,
        "headers": event.headers,
        "body": event.body,
        "raw_body": event.raw_body,
        "source_ip": event.source_ip,
        "signature_status": event.signature_status,
        "received_at": event.received_at.isoformat(),
    }


def verify_signature(endpoint: Endpoint, headers: dict, body: bytes) -> str:
    if not endpoint.secret:
        return "unverified"
    source = endpoint.source.lower()
    try:
        if source == "stripe":
            sig = headers.get("stripe-signature", "")
            if not sig:
                return "unverified"
            import hmac, hashlib
            parts = dict(p.split("=", 1) for p in sig.split(",") if "=" in p)
            ts = parts.get("t", "")
            signed_payload = f"{ts}.{body.decode()}"
            expected = hmac.new(
                endpoint.secret.encode(), signed_payload.encode(), hashlib.sha256
            ).hexdigest()
            return "valid" if hmac.compare_digest(expected, parts.get("v1", "")) else "invalid"

        elif source == "github":
            sig = headers.get("x-hub-signature-256", "")
            if not sig:
                return "unverified"
            import hmac, hashlib
            expected = "sha256=" + hmac.new(
                endpoint.secret.encode(), body, hashlib.sha256
            ).hexdigest()
            return "valid" if hmac.compare_digest(expected, sig) else "invalid"

        elif source == "shopify":
            sig = headers.get("x-shopify-hmac-sha256", "")
            if not sig:
                return "unverified"
            import hmac, hashlib, base64
            expected = base64.b64encode(
                hmac.new(endpoint.secret.encode(), body, hashlib.sha256).digest()
            ).decode()
            return "valid" if hmac.compare_digest(expected, sig) else "invalid"

    except Exception:
        return "invalid"

    return "unverified"


# ── Endpoint CRUD ─────────────────────────────────────────────────────────────

@router.post("/endpoints")
async def create_endpoint(data: EndpointCreate, db: AsyncSession = Depends(get_db)):
    ep = Endpoint(name=data.name, source=data.source, secret=data.secret)
    db.add(ep)
    await db.commit()
    await db.refresh(ep)
    return {
        "id": str(ep.id),
        "name": ep.name,
        "source": ep.source,
        "created_at": ep.created_at.isoformat(),
    }


@router.get("/endpoints")
async def list_endpoints(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Endpoint).order_by(Endpoint.created_at.desc())
    )
    endpoints = result.scalars().all()
    return [
        {
            "id": str(ep.id),
            "name": ep.name,
            "source": ep.source,
            "created_at": ep.created_at.isoformat(),
        }
        for ep in endpoints
    ]


@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(endpoint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await db.delete(ep)
    await db.commit()
    return {"deleted": str(endpoint_id)}


# ── Catch-all receiver ────────────────────────────────────────────────────────

@router.api_route(
    "/endpoints/{endpoint_id}/receive",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def receive_webhook(
    endpoint_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes)
    except Exception:
        body_json = None

    sig_status = verify_signature(ep, dict(request.headers), body_bytes)

    event = WebhookEvent(
        endpoint_id=endpoint_id,
        method=request.method,
        headers=dict(request.headers),
        body=body_json,
        raw_body=body_bytes.decode("utf-8", errors="replace"),
        source_ip=request.client.host if request.client else "unknown",
        signature_status=sig_status,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    await manager.broadcast(
        json.dumps({"type": "new_event", "event": serialize_event(event)})
    )

    return {"received": str(event.id), "signature": sig_status}


# ── Events list ───────────────────────────────────────────────────────────────

@router.get("/endpoints/{endpoint_id}/events")
async def list_events(endpoint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.endpoint_id == endpoint_id)
        .order_by(WebhookEvent.received_at.desc())
        .limit(100)
    )
    events = result.scalars().all()
    return [serialize_event(e) for e in events]


# ── Replay ────────────────────────────────────────────────────────────────────

@router.post("/events/{event_id}/replay")
async def replay_event(
    event_id: uuid.UUID, data: ReplayRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                data.target_url,
                content=event.raw_body or "",
                headers={"Content-Type": "application/json"},
            )
        elapsed = int((time.time() - start) * 1000)
        log = ReplayLog(
            event_id=event_id,
            target_url=data.target_url,
            status_code=resp.status_code,
            response_time_ms=elapsed,
            success=200 <= resp.status_code < 300,
        )
    except Exception:
        log = ReplayLog(
            event_id=event_id,
            target_url=data.target_url,
            status_code=0,
            response_time_ms=int((time.time() - start) * 1000),
            success=False,
        )

    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {
        "id": str(log.id),
        "event_id": str(log.event_id),
        "target_url": log.target_url,
        "status_code": log.status_code,
        "response_time_ms": log.response_time_ms,
        "success": log.success,
        "replayed_at": log.replayed_at.isoformat(),
    }


@router.get("/events/{event_id}/replays")
async def get_replay_logs(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReplayLog)
        .where(ReplayLog.event_id == event_id)
        .order_by(ReplayLog.replayed_at.desc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "event_id": str(log.event_id),
            "target_url": log.target_url,
            "status_code": log.status_code,
            "response_time_ms": log.response_time_ms,
            "success": log.success,
            "replayed_at": log.replayed_at.isoformat(),
        }
        for log in logs
    ]