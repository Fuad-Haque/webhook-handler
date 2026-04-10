import asyncio
from datetime import datetime, timezone

from app.storage import update_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _complete(event_id: str, result: dict):
    update_event(event_id, {
        "status": "complete",
        "processed_at": _now(),
        "result": result,
    })


# ── Stripe handlers ──────────────────────────────────────────────────────────

async def handle_payment_succeeded(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    customer = data.get("object", {}).get("customer", "unknown")
    amount = data.get("object", {}).get("amount", 0)
    print(f"[Stripe] payment_intent.succeeded — unlocking account for {customer}, sending receipt (${amount/100:.2f})")
    _complete(event_id, {"action": "account_unlocked", "receipt_sent": True, "customer": customer})


async def handle_payment_failed(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    customer = data.get("object", {}).get("customer", "unknown")
    print(f"[Stripe] payment_intent.payment_failed — sending failure notification to {customer}, scheduling retry")
    _complete(event_id, {"action": "failure_notification_sent", "retry_scheduled": True, "customer": customer})


async def handle_customer_created(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    email = data.get("object", {}).get("email", "unknown")
    print(f"[Stripe] customer.created — creating internal user record for {email}")
    _complete(event_id, {"action": "internal_user_created", "email": email})


async def handle_charge_refunded(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    charge_id = data.get("object", {}).get("id", "unknown")
    amount = data.get("object", {}).get("amount_refunded", 0)
    print(f"[Stripe] charge.refunded — processing refund ${amount/100:.2f} for charge {charge_id}, notifying user")
    _complete(event_id, {"action": "refund_processed", "charge_id": charge_id, "user_notified": True})


# ── GitHub handlers ──────────────────────────────────────────────────────────

async def handle_push(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    repo = data.get("repository", {}).get("full_name", "unknown")
    branch = data.get("ref", "unknown").replace("refs/heads/", "")
    pusher = data.get("pusher", {}).get("name", "unknown")
    print(f"[GitHub] push — triggering CI pipeline for {repo}@{branch} by {pusher}, notifying team")
    _complete(event_id, {"action": "ci_triggered", "repo": repo, "branch": branch, "team_notified": True})


async def handle_pull_request(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    pr_number = data.get("pull_request", {}).get("number", "?")
    repo = data.get("repository", {}).get("full_name", "unknown")
    action = data.get("action", "unknown")
    print(f"[GitHub] pull_request #{pr_number} ({action}) on {repo} — running automated checks, notifying reviewers")
    _complete(event_id, {"action": "checks_triggered", "pr": pr_number, "reviewers_notified": True})


async def handle_issues(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    issue_number = data.get("issue", {}).get("number", "?")
    title = data.get("issue", {}).get("title", "untitled")
    action = data.get("action", "unknown")
    print(f"[GitHub] issues #{issue_number} ({action}): '{title}' — creating ticket in internal system")
    _complete(event_id, {"action": "internal_ticket_created", "issue_number": issue_number, "title": title})


async def handle_release(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    tag = data.get("release", {}).get("tag_name", "unknown")
    repo = data.get("repository", {}).get("full_name", "unknown")
    print(f"[GitHub] release {tag} on {repo} — triggering deployment, updating changelog")
    _complete(event_id, {"action": "deployment_triggered", "tag": tag, "changelog_updated": True})


# ── Shopify handlers ─────────────────────────────────────────────────────────

async def handle_order_created(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    order_id = data.get("id", "unknown")
    customer = data.get("customer", {}).get("email", "unknown")
    print(f"[Shopify] orders/create — order #{order_id} for {customer}: creating fulfillment task, notifying warehouse")
    _complete(event_id, {"action": "fulfillment_task_created", "order_id": order_id, "warehouse_notified": True})


async def handle_order_paid(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    order_id = data.get("id", "unknown")
    total = data.get("total_price", "0.00")
    print(f"[Shopify] orders/paid — order #{order_id} (${total}): sending receipt, updating inventory")
    _complete(event_id, {"action": "receipt_sent", "order_id": order_id, "inventory_updated": True})


async def handle_order_cancelled(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    order_id = data.get("id", "unknown")
    print(f"[Shopify] orders/cancelled — order #{order_id}: processing refund, restoring inventory")
    _complete(event_id, {"action": "refund_processed", "order_id": order_id, "inventory_restored": True})


async def handle_product_created(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    product_id = data.get("id", "unknown")
    title = data.get("title", "untitled")
    print(f"[Shopify] products/create — product '{title}' (#{product_id}): syncing to internal catalog")
    _complete(event_id, {"action": "catalog_synced", "product_id": product_id, "title": title})


async def handle_inventory_update(event_id: str, data: dict):
    await asyncio.sleep(0.1)
    inventory_item_id = data.get("inventory_item_id", "unknown")
    available = data.get("available", 0)
    location_id = data.get("location_id", "unknown")
    print(f"[Shopify] inventory_levels/update — item #{inventory_item_id} at location {location_id}: available={available}")
    _complete(event_id, {"action": "stock_updated", "inventory_item_id": inventory_item_id, "available": available})