import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.handlers import (
    handle_charge_refunded,
    handle_customer_created,
    handle_inventory_update,
    handle_issues,
    handle_order_cancelled,
    handle_order_created,
    handle_order_paid,
    handle_payment_failed,
    handle_payment_succeeded,
    handle_product_created,
    handle_pull_request,
    handle_push,
    handle_release,
)
from app.models import DashboardResponse, UserCreate, UserResponse, Token
from app.storage import (
    add_event,
    add_user,
    events_log,
    get_event_by_id,
    get_user_by_email,
    get_user_by_username,
    is_processed,
    mark_processed,
    update_event,
)
from app.verification import (
    verify_github_signature,
    verify_shopify_signature,
    verify_stripe_signature,
)
from app.routers import inspector
from app.ws_manager import manager

STRIPE_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "placeholder")
GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "placeholder")
SHOPIFY_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "placeholder")

app = FastAPI(title="Webhook Handler", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fuadhaque.com",
        "https://webhook-inspector-frontend.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inspector.router)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate):
    if get_user_by_username(user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if get_user_by_email(user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = {
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": hash_password(user_in.password),
        "created_at": datetime.now(timezone.utc),
    }
    user = add_user(user_dict)
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"],
    )


@app.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=token, token_type="bearer")


# ── Webhook helpers ───────────────────────────────────────────────────────────

def _make_event(source: str, event_type: str, event_id: str, payload: dict) -> dict:
    return {
        "id": event_id,
        "source": source,
        "event_type": event_type,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "processed_at": None,
        "status": "received",
        "payload": payload,
        "result": None,
        "error": None,
    }


def _set_status(event_id: str, status_val: str):
    update_event(event_id, {"status": status_val})


# ── Stripe webhook ────────────────────────────────────────────────────────────

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if STRIPE_SECRET != "placeholder" and signature:
        if not verify_stripe_signature(payload, signature, STRIPE_SECRET):
            raise HTTPException(status_code=401, detail="Invalid Stripe signature")

    try:
        event = json.loads(payload)
    except Exception as e:
        bad_id = str(uuid4())
        add_event(_make_event("stripe", "parse_error", bad_id, {}))
        update_event(bad_id, {"status": "error", "error": str(e)})
        return {"received": True, "event_id": bad_id}

    event_id = event.get("id", str(uuid4()))
    event_type = event.get("type", "unknown")
    event_data = event.get("data", {})

    entry = _make_event("stripe", event_type, event_id, event)
    add_event(entry)

    if is_processed(event_id):
        return {"received": True, "event_id": event_id, "note": "already processed"}

    mark_processed(event_id)
    _set_status(event_id, "processing")

    stripe_routes = {
        "payment_intent.succeeded": handle_payment_succeeded,
        "payment_intent.payment_failed": handle_payment_failed,
        "customer.created": handle_customer_created,
        "charge.refunded": handle_charge_refunded,
    }

    handler = stripe_routes.get(event_type)
    if handler:
        background_tasks.add_task(handler, event_id, event_data)
    else:
        _set_status(event_id, "ignored")

    return {"received": True, "event_id": event_id}


# ── GitHub webhook ────────────────────────────────────────────────────────────

@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    github_event = request.headers.get("X-GitHub-Event", "unknown")
    signature = request.headers.get("X-Hub-Signature-256", "")

    if GITHUB_SECRET != "placeholder" and signature:
        if not verify_github_signature(payload, signature, GITHUB_SECRET):
            raise HTTPException(status_code=401, detail="Invalid GitHub signature")

    try:
        event = json.loads(payload)
    except Exception as e:
        bad_id = str(uuid4())
        add_event(_make_event("github", "parse_error", bad_id, {}))
        update_event(bad_id, {"status": "error", "error": str(e)})
        return {"received": True, "event_id": bad_id}

    delivery_id = request.headers.get("X-GitHub-Delivery", str(uuid4()))
    event_id = delivery_id

    entry = _make_event("github", github_event, event_id, event)
    add_event(entry)

    if is_processed(event_id):
        return {"received": True, "event_id": event_id, "note": "already processed"}

    mark_processed(event_id)
    _set_status(event_id, "processing")

    github_routes = {
        "push": handle_push,
        "pull_request": handle_pull_request,
        "issues": handle_issues,
        "release": handle_release,
    }

    handler = github_routes.get(github_event)
    if handler:
        background_tasks.add_task(handler, event_id, event)
    else:
        _set_status(event_id, "ignored")

    return {"received": True, "event_id": event_id}


# ── Shopify webhook ───────────────────────────────────────────────────────────

@app.post("/webhooks/shopify")
async def shopify_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    topic = request.headers.get("X-Shopify-Topic", "unknown")
    signature = request.headers.get("X-Shopify-Hmac-SHA256", "")

    if SHOPIFY_SECRET != "placeholder" and signature:
        if not verify_shopify_signature(payload, signature, SHOPIFY_SECRET):
            raise HTTPException(status_code=401, detail="Invalid Shopify signature")

    try:
        event = json.loads(payload)
    except Exception as e:
        bad_id = str(uuid4())
        add_event(_make_event("shopify", "parse_error", bad_id, {}))
        update_event(bad_id, {"status": "error", "error": str(e)})
        return {"received": True, "event_id": bad_id}

    event_id = str(event.get("id", str(uuid4())))
    idempotency_key = f"shopify-{topic}-{event_id}"

    entry = _make_event("shopify", topic, idempotency_key, event)
    add_event(entry)

    if is_processed(idempotency_key):
        return {"received": True, "event_id": idempotency_key, "note": "already processed"}

    mark_processed(idempotency_key)
    _set_status(idempotency_key, "processing")

    shopify_routes = {
        "orders/create": handle_order_created,
        "orders/paid": handle_order_paid,
        "orders/cancelled": handle_order_cancelled,
        "products/create": handle_product_created,
        "inventory_levels/update": handle_inventory_update,
    }

    handler = shopify_routes.get(topic)
    if handler:
        background_tasks.add_task(handler, idempotency_key, event)
    else:
        _set_status(idempotency_key, "ignored")

    return {"received": True, "event_id": idempotency_key}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_model=DashboardResponse)
async def dashboard(current_user: dict = Depends(get_current_user)):
    total = len(events_log)
    by_source: dict = {}
    by_status: dict = {}

    for e in events_log:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1

    error_count = by_status.get("error", 0)
    error_rate = (error_count / total * 100) if total > 0 else 0.0

    recent = sorted(events_log, key=lambda x: x["received_at"], reverse=True)[:10]

    return DashboardResponse(
        total_events=total,
        by_source=by_source,
        by_status=by_status,
        recent_events=recent,
        error_rate=round(error_rate, 2),
    )


# ── Events ────────────────────────────────────────────────────────────────────

@app.get("/events")
async def list_events(
    source: str = None,
    status: str = None,
    event_type: str = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    if limit > 100:
        limit = 100

    filtered = events_log
    if source:
        filtered = [e for e in filtered if e["source"] == source]
    if status:
        filtered = [e for e in filtered if e["status"] == status]
    if event_type:
        filtered = [e for e in filtered if e["event_type"] == event_type]

    total = len(filtered)
    page = filtered[skip: skip + limit]
    return {"total": total, "skip": skip, "limit": limit, "events": page}


@app.get("/events/{event_id}")
async def get_event(event_id: str, current_user: dict = Depends(get_current_user)):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    sources_active = list({e["source"] for e in events_log})
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events_log),
        "sources_active": sources_active,
    }