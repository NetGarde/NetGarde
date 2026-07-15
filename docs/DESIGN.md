# <img src="assets/icons/flow.svg" width="28" height="28" align="absmiddle" alt="" /> TrustEdge Design Guide

How TrustEdge is designed as an **endpoint security observability** platform: product goals, topology, UI conventions, and backend patterns.

Setup: [main README](../README.md) · Env: [ENV_SETUP.md](ENV_SETUP.md) · Architecture: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)

---

## <img src="assets/icons/collection.svg" width="22" height="22" align="absmiddle" alt="" /> Product goals

TrustEdge is a self-hosted control plane for **EDR-lite endpoint telemetry** and **rules-based attack detection**. The core promise:

1. **Endpoint signal** — TrustEdge Agent streams device, network, activity, and process posture (no VPN required for telemetry).  
2. **Reliable ingest** — Agent API authenticates devices, accepts compressed batches, and publishes to a stream.  
3. **Detection Attack** — A Kafka-backed rules engine evaluates process and network patterns.  
4. **Operator alerts** — Findings surface in the dashboard (attack / twin alerts).  
5. **Observability graph** — Entity and dependency views for posture and investigation.  
6. **AI explanations** *(optional)* — OpenAI or Ollama can summarize state; detection remains rules-based.

> TrustEdge is **not** a DNS filtering or dnsmasq policy product. Older VPN/DNS modules may still exist in the monorepo; they are outside the current product scope.

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Observability model

| Layer | Source | Dashboard |
|-------|--------|-----------|
| Endpoint posture | TrustEdge Agent events | Overview, twin graph, device views |
| Detection | `detection-engine` rules on agent stream | Attack / twin alerts |
| Live mirrors | Redis (optional) | Operator status |
| Desired ops state | RDS records for alerts / devices | Admin UI |

---

## Design principles

| Principle | Practice |
|-----------|----------|
| **Endpoint-first** | Product flows start at the agent, not at DNS or VPN |
| **Rules for security** | Detection and scoring are deterministic; LLMs explain only |
| **Feature modules** | Frontend/backend organized by domain (`twin`, `devices`, `dashboard`, …) |
| **Dark-first UI** | Dashboard defaults to dark mode |
| **Pragmatic layering** | Route → (controller) → service → repository when it helps |

---

## System topology

```text
┌─────────────────┐     HTTPS + zstd      ┌──────────────────────────┐
│ TrustEdge Agent │ ───────────────────► │ TrustEdge-Agent-API      │
│ (endpoint)      │                       │ register · events        │
└─────────────────┘                       └────────────┬─────────────┘
                                                       │ Kafka
                                                       ▼
                                              ┌────────────────────┐
                                              │ detection-engine   │
                                              └─────────┬──────────┘
                                                        │ alerts ingest
                                                        ▼
┌──────────────┐   REST / WS   ┌─────────────────────────────────────┐
│ React UI     │◄─────────────►│ FastAPI backend · RDS · Redis       │
│ (CloudFront) │               │ twin graph · attack alerts · admin  │
└──────────────┘               └─────────────────────────────────────┘
```

| Component | Runs where | Responsibility |
|-----------|------------|----------------|
| **TrustEdge Agent** | Endpoint OS | Collect + upload telemetry |
| **Agent API** | Separate service / compose | Ingest + stream publish |
| **detection-engine** | Docker | Consume events, fire rules |
| **FastAPI backend** | Docker on EC2 | Alerts, twin graph, admin API |
| **React dashboard** | S3 + CloudFront | Operator UI |

---

## Domain concepts

| Concept | Meaning |
|---------|---------|
| **Device** | An endpoint enrolled with the Agent API / known to TrustEdge |
| **Event** | Agent telemetry envelope (`client_details`, `network_summary`, `action_summary`, `process_*`) |
| **Detection Attack** | Rules match on the event stream |
| **Alert** | Persisted finding shown to operators |
| **Observability graph** | Canonical entities + edges for investigation ([GRAPH_ENGINE.md](GRAPH_ENGINE.md)) |

---

## Security model

| Token | Used by | Protects |
|-------|---------|----------|
| `ADMIN_API_TOKEN` | Dashboard, admin scripts | Admin REST surfaces |
| Agent enroll / device tokens | Agent ↔ Agent API | Registration and event ingest |

- Admin auth is **disabled when `ADMIN_API_TOKEN` is empty** — always set this in production.  
- CloudFront terminates HTTPS for the dashboard and proxies API requests to the backend.

---

## Frontend design

### Visual language

| Aspect | Choice |
|--------|--------|
| **Framework** | React 19 + TypeScript |
| **Component library** | Material UI 7 |
| **Charts** | MUI X Charts |
| **Default mode** | Dark |
| **Primary accent** | Blue `hsl(210, 98%, 48%)` |

Palette tokens: `frontend/src/shared/theme/themePrimitives.ts`.  
Navigation chrome: `shared/theme/navigationChrome.ts`.

### Layout shell

```text
AppTheme
  ├─ SideMenu
  ├─ AppNavbar
  └─ main → Header + page content
```

Routes: `frontend/src/routes/index.tsx`. Feature UI lives under `features/`.

### Feature folder convention

```text
features/<name>/
├── components/
├── hooks/
├── config/       # api.ts
├── types/
└── utils/        # optional
```

---

## Backend design

### Layout

```text
backend/app/
├── main.py
├── shared/          # DB, config, auth, logging, Redis
└── features/        # twin, devices, dashboard, …
detection-engine/    # Kafka consumer + rules (repo root)
```

### Layered architecture (pragmatic)

```text
Route → Controller (optional) → Service → Repository → Model
```

Prefer domain exceptions + controller mapping for new code. Shared errors: `shared/errors/`.

### Schemas & models

- ORM models under `features/<name>/models/`  
- Pydantic schemas under `features/<name>/schemas/`  

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Flows and trust boundaries |
| [GRAPH_ENGINE.md](GRAPH_ENGINE.md) | Observability graph model |
| [API.md](API.md) | REST reference |
| [DEPLOY.md](DEPLOY.md) | AWS deploy |
| [ENV_SETUP.md](ENV_SETUP.md) | Environment variables |
| [TrustEdge-Agent docs](https://github.com/TrustEdgeOrg/TrustEdge-Agent) | Collector details |
| [TrustEdge-Agent-API docs](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) | Ingest schemas |
