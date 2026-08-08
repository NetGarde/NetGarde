# Architecture

Component topology, data flows, trust boundaries, and contributor patterns for TrustEdge.

Product overview and screenshots: [root README](../README.md). Deploy: [DEPLOY.md](DEPLOY.md). Env: [ENV_SETUP.md](ENV_SETUP.md).

---

## Stages

<p align="center">
  <img width="100%" alt="TrustEdge architecture — Edge, Ingest, Stream, Detect, Operate" src="assets/architecture.svg" />
</p>

**Primary path:** Agent → HTTPS upload → Agent API → Kafka → detection-engine → alert ingest → FastAPI → React dashboard.

<p align="center">
  <img width="100%" alt="TrustEdge AWS production architecture" src="assets/aws-architecture.svg" />
</p>

AWS host layout and CI/CD: [DEPLOY.md](DEPLOY.md).

---

## Components

| Layer | Components | Role |
|-------|------------|------|
| **Endpoint** | TrustEdge Agent (Go) | Process, activity, network, security lifecycle, AI tools inventory |
| **Ingest** | TrustEdge-Agent-API | Device auth, validate, Kafka publish, live twin |
| **Stream** | Kafka / Redpanda | `trustedge.agent.events` |
| **Detection** | `detection-engine` | YAML rules, behavior baselines, AI activity → alerts |
| **Control plane** | FastAPI + React | Alerts, agents, AI inventory, behavior, sessions |
| **Data** | RDS PostgreSQL, Redis | Durable state · live twin |
| **Hosting** | EC2 Compose, S3, CloudFront, ECR | Runtime, dashboard, images |

---

## Data flows

### Endpoint telemetry

```
TrustEdge Agent → POST /v1/events → Agent API → Kafka (trustedge.agent.events)
                 → detection-engine → POST /security/alerts/ingest → Backend
                 → Agent-API upsert → Postgres agents registry → dashboard Agents
```

### Optional L4 flows

```
Host conntrack watcher → POST /network-flows/bulk → Backend Redis window → GET /network-flows/live
```

---

## Product model

| Layer | Source | Dashboard |
|-------|--------|-----------|
| Endpoint posture | Agent (process, network, activity, AI inventory) | Agents · AI tools inventory |
| Detection | Kafka → rules · behavior · AI activity | Alerts |
| L4 flows | Host conntrack (optional) | Flow ingest / live API |

### Agents

- Durable registry in Postgres (`agents`, keyed by `agent_id`)
- Live presence / twin state in Redis
- AI tools inventory from `known_ai_app` events on agent detail

### Detection engines

- **YAML attack/chain rules** — process, network, security lifecycle
- **Behavioral engine** — per-device baselines, novel-process alerts
- **AI activity engine** — agentic sessions and AI-tool findings

Optional LLMs (Ollama / OpenAI / templates) explain alerts — they do not judge.

---

## Trust boundaries

| Boundary | Role |
|----------|------|
| CloudFront ↔ Backend | HTTPS for dashboard; API proxied to EC2 `:8000` |
| `ADMIN_API_TOKEN` | Dashboard / admin APIs (disabled when empty — always set in production) |
| `TRUSTEDGE_INGEST_TOKEN` | Agent-API, detection-engine, flow ingest |
| Device tokens | Agent ↔ Agent API |

---

## Design principles

| Principle | Practice |
|-----------|----------|
| **Endpoint-first** | Stable agent identity in Postgres; live posture in Redis twin |
| **Single source of truth** | Alerts and agents in RDS |
| **Feature modules** | Frontend and backend organized by domain (`agents`, `twin`, …) |
| **Pragmatic layering** | Route → service → repository; controllers optional |

---

## Frontend conventions

| Aspect | Choice |
|--------|--------|
| Stack | React 19, TypeScript, Material UI 7 |
| Charts | MUI X Charts |
| Theme | Light and dark; brand blue accent |
| Layout | `Layout` + SideMenu + AppNavbar + Header |

**Nav:** Home · Agents · Alerts · Learn · Settings (`MenuContent.tsx`)

**Feature folders:** `features/<name>/{components,hooks,config,types}`

Pages in `pages/` are thin wrappers; routes in `routes/index.tsx`.

---

## Backend conventions

```
backend/app/
├── main.py
├── shared/          # DB, config, auth, logging, Redis
└── features/        # agents, twin, dashboard, network_flows, behaviors, …
```

Prefer: service raises domain errors; route/controller maps to HTTP. Shared errors in `shared/errors/`.

No global event bus — services call peers explicitly (e.g. alert ingest → dashboard views; Agent-API upsert → agents registry).

---

## Adding a feature

### Frontend

1. Create `frontend/src/features/<name>/`
2. Thin page in `pages/`; route in `routes/index.tsx` inside `<Layout>`
3. Nav item in `MenuContent.tsx`
4. Reuse theme tokens — avoid one-off colors

### Backend

1. Create `backend/app/features/<name>/` (routes, services, repositories, models, schemas)
2. Register router in `main.py`
3. Alembic migration for new tables
4. Tests under `backend/tests/unit/` and `backend/tests/integration/`

---

## Related

- [DEPLOY.md](DEPLOY.md) — AWS, CI/CD, CloudWatch
- [ENV_SETUP.md](ENV_SETUP.md) — configuration
- [API.md](API.md) — REST map (live OpenAPI at `/docs`)
- [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) · [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)
