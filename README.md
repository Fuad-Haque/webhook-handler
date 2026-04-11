# Webhook Handler — FastAPI

A production-ready webhook handler for Stripe, GitHub, and Shopify with JWT auth, idempotency, background processing, and a live dashboard.

**Live URL:** https://webhook-handler-production-99e2.up.railway.app
**Docs:** https://webhook-handler-production-99e2.up.railway.app/docs

## Structure

```
app/
├── models.py       — Pydantic schemas
├── auth.py         — JWT auth (hash, verify, token, dependency)
├── storage.py      — In-memory store (users, events, idempotency set)
├── verification.py — HMAC signature verification (Stripe / GitHub / Shopify)
├── handlers.py     — Async event handlers (simulate real processing)
└── main.py         — FastAPI app, all routes
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in real secrets
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for the interactive API docs.

## Webhook Endpoints (no auth — called by providers)

| Method | Path | Source |
|--------|------|--------|
| POST | `/webhooks/stripe` | Stripe |
| POST | `/webhooks/github` | GitHub |
| POST | `/webhooks/shopify` | Shopify |

### Signature Verification
- Secrets default to `"placeholder"` → verification is skipped (great for local testing)
- Set real secrets in `.env` to enable HMAC verification
- A bad signature returns **401**; everything else always returns **200**

## Authenticated Endpoints (Bearer JWT required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/token` | Get JWT token |
| GET | `/dashboard` | Stats + last 10 events |
| GET | `/events` | Paginated event log (filter by source/status/event_type) |
| GET | `/events/{event_id}` | Full event detail including payload & result |
| GET | `/health` | Service health |

## Supported Event Types

**Stripe:** `payment_intent.succeeded`, `payment_intent.payment_failed`, `customer.created`, `charge.refunded`

**GitHub:** `push`, `pull_request`, `issues`, `release`

**Shopify:** `orders/create`, `orders/paid`, `orders/cancelled`, `products/create`, `inventory_levels/update`

Unrecognized events are logged with status `ignored` and return 200.

## Idempotency

Each event ID is tracked in `processed_event_ids`. Duplicate deliveries return `{"received": true, "note": "already processed"}` immediately without re-running handlers.

## Quick Test (curl)

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"fuad","email":"fuad@example.com","password":"secret123"}'

# Login
curl -X POST http://localhost:8000/auth/token \
  -d "username=fuad&password=secret123"

# Send a test Stripe webhook
curl -X POST http://localhost:8000/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"id":"evt_test_001","type":"payment_intent.succeeded","data":{"object":{"customer":"cus_123","amount":4999}}}'

# Dashboard (use token from login)
curl http://localhost:8000/dashboard \
  -H "Authorization: Bearer <your_token>"
```

## Deployment (Railway)

```bash
railway init
railway up
# Set env vars in Railway dashboard
```
