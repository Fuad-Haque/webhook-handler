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

## 🪝 What Is This?

A **webhook.site clone** — a real-time inspection dashboard every developer needs when integrating Stripe, GitHub, or Shopify webhooks.

Point your webhook URL here → watch events arrive live → inspect payloads → replay to any target.

**Live Dashboard** → [webhook-inspector-frontend.vercel.app](https://webhook-inspector-frontend.vercel.app)  
**Backend API** → [webhook-handler-production-99e2.up.railway.app/docs](https://webhook-handler-production-99e2.up.railway.app/docs)

---

## ⚡ Features

| Feature | Detail |
|---------|--------|
| 🔴 **Real-time feed** | Events push via WebSocket — no refresh needed |
| 🔐 **HMAC verification** | Validates Stripe / GitHub / Shopify signatures automatically |
| 🔁 **Replay engine** | Re-POST any stored event to any URL with delivery logging |
| 📦 **Endpoint management** | Create isolated receivers per integration |
| 🗄️ **Persistent storage** | All events stored in PostgreSQL (Neon) |
| ⚡ **30s ping keepalive** | WebSocket stays alive through Railway idle timeouts |

---

## 🏗️ Architecture

```
Browser (Next.js · Vercel)
    │
    ├── HTTP (REST) ──────────── FastAPI (Railway)
    │                                │
    │                           PostgreSQL (Neon)
    │
    └── WebSocket ────────────── FastAPI /ws
                                     │
                              broadcasts on new event
```

---

## 🛠️ Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy (async), asyncpg |
| Database | PostgreSQL — Neon |
| Realtime | WebSocket — native FastAPI |
| Deploy | Vercel + Railway |

---

## 🚀 Quick Start

```bash
# Backend
git clone https://github.com/Fuad-Haque/webhook-handler
cd webhook-handler
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
git clone https://github.com/Fuad-Haque/webhook-inspector-frontend
cd webhook-inspector-frontend
cp .env.example .env.local
npm install && npm run dev
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/endpoints` | Create a webhook receiver |
| `ANY` | `/endpoints/{id}/receive` | Catch-all webhook receiver |
| `GET` | `/endpoints/{id}/events` | List received events |
| `POST` | `/events/{id}/replay` | Replay event to target URL |
| `GET` | `/events/{id}/replays` | Replay delivery logs |
| `WS` | `/ws` | Real-time event push |
| `GET` | `/health` | Health check |

---

## 🔐 Signature Verification

| Source | Header | Algorithm |
|--------|--------|-----------|
| Stripe | `stripe-signature` | HMAC-SHA256 |
| GitHub | `X-Hub-Signature-256` | HMAC-SHA256 |
| Shopify | `X-Shopify-Hmac-SHA256` | HMAC-SHA256 Base64 |

---

<div align="center">

Built by [Fuad Haque](https://fuadhaque.com) · [fuadhaque.dev@gmail.com](mailto:fuadhaque.dev@gmail.com) · [Book a Call](https://cal.com/fuad-haque)

</div>
