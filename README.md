# Webhook Inspector

<div align="center">

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Sora&weight=700&size=22&duration=2800&pause=1000&color=6C63FF&center=true&vCenter=true&width=700&lines=Real-time+Webhook+Debugging+Dashboard;WebSocket+%C2%B7+HMAC+Verification+%C2%B7+Replay+Engine;Stripe+%C2%B7+GitHub+%C2%B7+Shopify+%C2%B7+Any+Source;Built+for+developers+who+ship+fast.)](https://git.io/typing-svg)

</div>

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js_16-000000?style=for-the-badge&logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)

</div>

---

## Overview

**Webhook Inspector** is a production-grade, real-time webhook debugging and inspection platform — a self-hosted alternative to webhook.site. It provides developers a dedicated URL to receive, inspect, verify, and replay webhook events from any source including Stripe, GitHub, and Shopify, with live event delivery via WebSocket.

**Live Dashboard** → [webhook-inspector-frontend.vercel.app](https://webhook-inspector-frontend.vercel.app)  
**Backend API / Swagger Docs** → [webhook-handler-production-99e2.up.railway.app/docs](https://webhook-handler-production-99e2.up.railway.app/docs)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Stack](#stack)
- [API Reference](#api-reference)
- [Signature Verification](#signature-verification)
- [Environment Variables](#environment-variables)
- [Quick Start](#quick-start)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Error Handling](#error-handling)
- [Author](#author)

---

## Features

| Feature | Detail |
|---------|--------|
| Real-time Event Feed | Events are pushed via WebSocket — no polling or manual refresh required |
| HMAC Signature Verification | Automatically validates Stripe, GitHub, and Shopify webhook signatures |
| Replay Engine | Re-POST any stored event to any target URL with full delivery logging |
| Endpoint Management | Create isolated, named receivers per integration or project |
| Persistent Storage | All events and replay logs are persisted in PostgreSQL (Neon) |
| WebSocket Keepalive | 30-second ping interval maintains stable connections through Railway idle timeouts |
| Health Endpoint | `/health` endpoint for uptime monitoring and deployment readiness checks |
| Swagger / OpenAPI Docs | Full interactive API documentation auto-generated at `/docs` |

---

## Architecture

```
Browser (Next.js · Vercel)
    │
    ├── HTTP (REST) ──────────── FastAPI (Railway)
    │                                │
    │                           PostgreSQL (Neon)
    │
    └── WebSocket ────────────── FastAPI /ws
                                     │
                              Broadcasts on new event arrival
```

### Request Lifecycle

```
Inbound Webhook (POST /endpoints/{id}/receive)
    │
    ├── Parse headers + raw body
    ├── HMAC signature verification (if secret configured)
    ├── Persist event to PostgreSQL
    └── Broadcast event to all connected WebSocket clients
```

### WebSocket Connection Flow

```
Client connects → /ws
    │
    ├── Server registers client in active connections pool
    ├── 30s server-side ping to keep connection alive
    ├── On new event: broadcast JSON payload to all clients
    └── On disconnect: client removed from pool
```

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy (async), asyncpg |
| Database | PostgreSQL — Neon (serverless) |
| Realtime | WebSocket — native FastAPI (`websockets`) |
| Deployment | Vercel (frontend) + Railway (backend) |
| API Documentation | Swagger UI — auto-generated via FastAPI |

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/endpoints` | Create a new webhook receiver endpoint |
| `GET` | `/endpoints` | List all registered receiver endpoints |
| `GET` | `/endpoints/{id}` | Retrieve a specific receiver endpoint |
| `DELETE` | `/endpoints/{id}` | Delete a receiver endpoint and its events |
| `ANY` | `/endpoints/{id}/receive` | Catch-all webhook receiver — accepts any HTTP method |
| `GET` | `/endpoints/{id}/events` | List all events received by an endpoint |
| `GET` | `/events/{id}` | Retrieve a single event with full headers and body |
| `POST` | `/events/{id}/replay` | Replay a stored event to a target URL |
| `GET` | `/events/{id}/replays` | List all replay delivery attempts for an event |
| `WS` | `/ws` | WebSocket connection for real-time event push |
| `GET` | `/health` | Health check — returns service status |

### Request / Response Examples

**Create an endpoint**
```http
POST /endpoints
Content-Type: application/json

{
  "name": "stripe-production",
  "secret": "whsec_xxxxxxxxxxxxxxxx"
}
```

```json
{
  "id": "ep_01HZ...",
  "name": "stripe-production",
  "url": "https://webhook-handler-production-99e2.up.railway.app/endpoints/ep_01HZ.../receive",
  "created_at": "2025-05-01T10:00:00Z"
}
```

**Replay an event**
```http
POST /events/{id}/replay
Content-Type: application/json

{
  "target_url": "https://your-service.com/webhooks/stripe"
}
```

```json
{
  "replay_id": "rpl_02AB...",
  "event_id": "evt_01HZ...",
  "target_url": "https://your-service.com/webhooks/stripe",
  "status_code": 200,
  "delivered_at": "2025-05-01T10:05:00Z"
}
```

---

## Signature Verification

Webhook Inspector automatically verifies cryptographic signatures for the following sources when an endpoint is configured with a signing secret.

| Source | Signature Header | Algorithm |
|--------|-----------------|-----------|
| Stripe | `stripe-signature` | HMAC-SHA256 with timestamp tolerance |
| GitHub | `X-Hub-Signature-256` | HMAC-SHA256 |
| Shopify | `X-Shopify-Hmac-SHA256` | HMAC-SHA256 Base64-encoded |

Events that fail signature verification are logged with a `verification_failed` status and are not broadcast to WebSocket clients.

---

## Environment Variables

### Backend (`.env`)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

# Application
APP_ENV=production
ALLOWED_ORIGINS=https://webhook-inspector-frontend.vercel.app

# Optional: default signing secret fallback
DEFAULT_WEBHOOK_SECRET=
```

### Frontend (`.env.local`)

```env
# Backend API base URL
NEXT_PUBLIC_API_URL=https://webhook-handler-production-99e2.up.railway.app

# WebSocket URL
NEXT_PUBLIC_WS_URL=wss://webhook-handler-production-99e2.up.railway.app/ws
```

A fully documented `.env.example` file is included in both repositories.

---

## Quick Start

### Backend

```bash
git clone https://github.com/Fuad-Haque/webhook-handler
cd webhook-handler
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
git clone https://github.com/Fuad-Haque/webhook-inspector-frontend
cd webhook-inspector-frontend
cp .env.example .env.local
npm install
npm run dev
```

Backend runs at `http://localhost:8000` — Swagger docs at `http://localhost:8000/docs`.  
Frontend runs at `http://localhost:3000`.

---

## Docker

Both services include Docker and Docker Compose support for local development and self-hosted deployment.

```bash
# Clone both repositories into the same parent directory
git clone https://github.com/Fuad-Haque/webhook-handler
git clone https://github.com/Fuad-Haque/webhook-inspector-frontend

# Configure environment files
cp webhook-handler/.env.example webhook-handler/.env
cp webhook-inspector-frontend/.env.example webhook-inspector-frontend/.env.local

# Start all services
docker compose up --build
```

Services started:
- `backend` — FastAPI on port `8000`
- `frontend` — Next.js on port `3000`
- `db` — PostgreSQL on port `5432` (local development only)

---

## Project Structure

### Backend

```
webhook-handler/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── routers/
│   │   ├── endpoints.py     # Endpoint CRUD routes
│   │   ├── events.py        # Event retrieval and replay routes
│   │   └── ws.py            # WebSocket connection manager
│   ├── models/
│   │   ├── endpoint.py      # SQLAlchemy endpoint model
│   │   └── event.py         # SQLAlchemy event model
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/
│   │   ├── verification.py  # HMAC signature verification logic
│   │   └── replay.py        # Event replay and delivery logging
│   └── db.py                # Async database session setup
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Frontend

```
webhook-inspector-frontend/
├── app/
│   ├── page.tsx             # Dashboard — real-time event feed
│   ├── endpoints/           # Endpoint management pages
│   └── events/[id]/         # Event detail and replay UI
├── components/
│   ├── EventFeed.tsx        # WebSocket-driven live event list
│   ├── EventDetail.tsx      # Payload inspector with syntax highlighting
│   └── ReplayPanel.tsx      # Replay form and delivery log
├── lib/
│   ├── api.ts               # Typed API client (REST)
│   └── ws.ts                # WebSocket connection manager
├── .env.example
└── docker-compose.yml
```

---

## Error Handling

| Status Code | Scenario |
|-------------|----------|
| `200 OK` | Request processed successfully |
| `201 Created` | Endpoint or resource created |
| `400 Bad Request` | Invalid request body or missing required fields |
| `404 Not Found` | Endpoint or event ID does not exist |
| `422 Unprocessable Entity` | Request validation error (Pydantic) |
| `498 Invalid Token` | HMAC signature verification failed |
| `500 Internal Server Error` | Unexpected server error |
| `503 Service Unavailable` | Database connectivity issue |

---

## Author

Built by [Fuad Haque](https://fuadhaque.com)

[fuadhaque.dev@gmail.com](mailto:fuadhaque.dev@gmail.com) · [Book a Call](https://cal.com/fuad-haque) · [GitHub](https://github.com/Fuad-Haque)
