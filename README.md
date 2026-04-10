# Webhook Handler Service

Production-grade webhook processor for Stripe, GitHub, and Shopify.
Handles signature verification, idempotency, and background event processing.

**Live URL:** https://webhook-handler-fuad.railway.app
**Docs:** https://webhook-handler-fuad.railway.app/docs
**Tech:** Python · FastAPI · JWT · HMAC · Railway

## Features

- Receives events from Stripe, GitHub, and Shopify
- HMAC signature verification (rejects fake requests)
- Idempotency — duplicate events handled safely
- Background processing — always responds in <100ms
- Full event log with status tracking
- JWT-protected dashboard and event history
- Handles unknown events gracefully (logged, not errored)

## Webhook Endpoints

| Service | Endpoint | Verification Header |
|---------|----------|---------------------|
| Stripe | POST /webhooks/stripe | stripe-signature |
| GitHub | POST /webhooks/github | X-Hub-Signature-256 |
| Shopify | POST /webhooks/shopify | X-Shopify-Hmac-SHA256 |

## Event Types Handled

**Stripe:** payment_intent.succeeded, payment_intent.payment_failed,
customer.created, charge.refunded

**GitHub:** push, pull_request, issues, release

**Shopify:** orders/create, orders/paid, orders/cancelled,
products/create, inventory_levels/update

## Management Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /dashboard | Yes | Event summary and stats |
| GET | /events | Yes | Paginated event list |
| GET | /events/{id} | Yes | Single event detail |
| GET | /health | No | Health check |

## Run Locally

```bash
git clone https://github.com/Fuad-Haque/webhook-handler
cd webhook-handler
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add your webhook secrets
uvicorn app.main:app --reload
