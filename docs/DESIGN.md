# <img src="assets/icons/flow.svg" width="28" height="28" align="absmiddle" alt="" /> TrustEdge Design Guide

This document describes how TrustEdge is designed: product goals, system topology, domain concepts, UI conventions, and backend patterns. Use it when adding features, reviewing PRs, or onboarding.

For setup and deployment, see the [main README](../README.md). For environment variables, see [ENV_SETUP.md](ENV_SETUP.md).

---

## <img src="assets/icons/collection.svg" width="22" height="22" align="absmiddle" alt="" /> Product goals

TrustEdge is a **self-hosted security observability platform** (EDR-lite endpoint telemetry + behavior baselines + rules-based detection) for teams and operators who want unified security visibility without enterprise complexity. The core promise:

1. **Live observability** — TrustEdge Agent streams process, app, and network posture into the network map and detection alerts.
2. **EDR-lite endpoint detection** — TrustEdge Agent events feed a Kafka-backed rules engine (shell→downloader chains, temp-path execution, network drift).
3. **Behavior-aware drift** — Per-device baselines and abnormal scores surface drift; rules-based scoring, not LLM judgment.
4. **AI-assisted explanations** *(optional)* — OpenAI or Ollama can summarize network overview and per-device behavior for operators; falls back to templates when AI is off or unavailable.
5. **Soft quarantine** — Operators can flag devices; agent-side network isolation is a follow-on.

DNS policy packs, dnsmasq sync, live DNS query feeds, and WireGuard VPN enroll are **out of scope** (removed from the product).

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Observability model

| Layer | Source | Dashboard |
|-------|--------|-----------|
| Application | Foreground app reports (TrustEdge Agent) | Network map |
| Endpoint posture | TrustEdge Agent (process, network summary, app focus) | Network map, detection alerts |
| Drift | Behavior baselines vs live scoring | Client profiles |
| Detection | TrustEdge Agent events → detection-engine rules | Security alerts, network map |

---

## Design principles

| Principle | What it means in practice |
|-----------|---------------------------|
| **Endpoint-first** | Device identity is agent `external_id` in PostgreSQL; live posture also lands in Redis twin keys. |
| **Single source of truth** | Device and alert state live in RDS. |
| **Feature modules** | Both frontend and backend are organized by domain feature (`devices`, `twin`, etc.), not by technical layer alone. |
| **Dark-first UI** | The dashboard defaults to dark mode. Light mode is supported; navigation chrome adapts per mode. |
| **Pragmatic layering** | Backend layering (route → controller → service → repository) is encouraged but not uniform. Mature paths (`devices`) use controllers and Protocols; newer paths may call services directly from routes. |

---

## System topology

```
┌──────────────────┐                    ┌─────────────────────────────────────────┐
│ TrustEdge Agent  │── HTTPS events ───►│ Agent API → Kafka → detection-engine   │
└──────────────────┘                    └──────────────────┬──────────────────────┘
                                                           │ alerts ingest
                                        ┌──────────────────▼──────────────────────┐
                                        │ EC2 host                                 │
                                        │  ┌─────────────────────────────────┐    │
                                        │  │ Docker: FastAPI backend :8000   │    │
                                        │  └──────────────┬──────────────────┘    │
                                        └─────────────────┼───────────────────────┘
                                                          │
                    ┌─────────────────────────────────────┼─────────────────────┐
                    ▼                                     ▼                     ▼
             CloudFront + S3                       AWS RDS PostgreSQL      Redis (twin)
             React dashboard                       devices + alerts
```

### Runtime responsibilities

| Component | Runs where | Responsibility |
|-----------|------------|----------------|
| **React dashboard** | S3 + CloudFront | Admin UI, attack alerts, devices, network map |
| **FastAPI backend** | Docker on EC2 | REST API, alerts, devices, security graph |
| **detection-engine** | Docker / service | Rules on agent Kafka topic → alert ingest |
| **TrustEdge Agent API** | Docker on EC2 | Agent event ingest |

---

## Domain concepts

### Observability graph

- **Observability graph engine** — Canonical entity/dependency model for impact analysis, blast radius, and RCA. See [GRAPH_ENGINE.md](GRAPH_ENGINE.md).

### Devices & clients

- **Device** — An endpoint identified by `external_id` (agent device id), optional hostname/MAC.
- **Behavior profile** — Rolling baseline of activity; abnormal scores surface drift.
- **Quarantine** — Soft flag in the API/dashboard; agent-side network isolation is not yet enforced.

### Alerts

- Detection-engine posts to `POST /security/alerts/ingest`.
- Dashboard shows attack alerts; the `dns_alerts` table remains as the store for alert rows via `app.features.alerts`.

---

## Quarantine pipeline

```
Dashboard action (quarantine)
    → Backend writes soft quarantine state in DB
```

Agent-enforced network isolation is a follow-on (no WireGuard host agent).

---

## Security model

| Token | Used by | Protects |
|-------|---------|----------|
| `ADMIN_API_TOKEN` | Dashboard, admin scripts | Device management, quarantine |
| `DNS_INGEST_TOKEN` | Flow watcher, detection-engine ingest | Service-to-service ingest (shared token name) |
| `DEVICE_TOKEN_SECRET` | Device-authenticated APIs | HMAC device tokens (e.g. network attribution) |

- Admin auth is **disabled when `ADMIN_API_TOKEN` is empty** — always set this in production.
- CloudFront terminates HTTPS for the dashboard and proxies API requests to the backend.

---

## Frontend design

### Visual language

| Aspect | Choice |
|--------|--------|
| **Framework** | React 19 + TypeScript |
| **Component library** | Material UI 7 (CSS variables, color schemes) |
| **Charts** | MUI X Charts (dashboard feature overrides) |
| **Font** | Inter |
| **Default mode** | Dark (`InitColorSchemeScript defaultMode="dark"`) |
| **Border radius** | 8px (theme `shape.borderRadius`) |
| **Primary accent** | Blue `hsl(210, 98%, 48%)` (brand palette) |

### Color & chrome

Palette tokens live in `frontend/src/shared/theme/themePrimitives.ts`:

- **brand** — primary actions, selected nav accent
- **gray** — backgrounds, text, dividers
- **green / orange / red** — success, warning, error

Navigation chrome (`shared/theme/navigationChrome.ts`):

- **Dark mode** — neutral sidebar and navbar; primary blue for selected nav indicator
- **Light mode** — Azure-style navbar (`#0078d4`); white icon buttons on top bar
- Selected nav items show a **3px left accent bar** and tinted background

Reusable sx helpers:

- `sidebarNavItemSx` / `sidebarSectionButtonSx` — nav list items
- `navbarIconButtonSx` — top bar icon buttons
- `chromelessIconButtonSx` — inline help icons without bordered chrome

### Layout shell

Every route is wrapped in `shared/components/Layout.tsx`:

```
AppTheme (+ chart customizations)
  ├─ SideMenu          (collapsible: 220px ↔ 64px)
  ├─ AppNavbar         (48px top bar; mobile drawer trigger)
  └─ main
       └─ Header (breadcrumbs) + page content
```

Shell components live under `features/dashboard/components/` (SideMenu, AppNavbar, Header, MenuContent) even though Layout is in `shared/`.

### Navigation structure

Defined in `features/dashboard/components/MenuContent.tsx`:

| Section | Items |
|---------|-------|
| **Home** | Dashboard (`/`) |
| **My network** | Client map, Network map |
| **Analytics** | Client profiles |

Routes are declared in `frontend/src/routes/index.tsx`. Pages in `pages/` are thin entry points; feature UI lives in `features/`.

### Feature folder convention

```
features/<name>/
├── components/     # UI scoped to this domain
├── hooks/          # useXxx data hooks
├── config/         # api.ts — fetch wrappers (xxxApi objects)
├── types/          # TypeScript models
├── utils/          # Pure helpers (optional)
└── theme/          # Feature-specific MUI overrides (optional)
```

**API pattern** — each feature's `config/api.ts` uses `shared/config/apiBaseUrl.ts` and `shared/utils/authHeaders.ts`:

```typescript
// Typical shape
export const devicesApi = {
  list: () => apiFetch<Device[]>('/devices'),
  quarantine: (id: number, hours: number) => apiFetch(...),
};
```

**Cross-feature imports are allowed** — e.g. dashboard hooks compose devices + security alerts.

### Page patterns

| Style | Example | Pattern |
|-------|---------|---------|
| Thin page | `ClientProfilesPage` | `return <ClientProfiles />` |
| Composed page | Dashboard home | Page owns layout; imports feature components + hooks |

---

## Backend design

### Layout

```
backend/app/
├── main.py                 # App factory, middleware, router registration
├── shared/                 # DB, config, auth, errors, logging, Redis, WebSocket
└── features/               # Vertical domain modules
    ├── alerts/             # Alert model (dns_alerts table) + repository
    ├── devices/
    ├── twin/
    ├── vpn/
    ├── dashboard/
    ├── network_attribution/
    ├── network_flows/
    └── client_behavior/    # Used by devices routes
```

Legacy `policy/` code may still exist in the tree but is **not mounted** in `main.py`.

### Layered architecture (pragmatic)

```
Route (FastAPI endpoint, Depends auth + DB)
  └── Controller (optional — HTTP mapping, WebSocket side effects)
       └── Service (business logic, cross-feature orchestration)
            └── Repository (SQLAlchemy CRUD)
                 └── Model (ORM)
```

| Pattern | Features | Notes |
|---------|----------|-------|
| Full stack | `devices` (CRUD) | Controller + `Protocol` interface |
| Thin routes | `vpn`, `dashboard`, `twin` | Route calls service directly |
| Mixed | `devices` (extended routes) | Behavior/quarantine endpoints inline |

**Reference implementation:** `devices` — route → controller/service → repository.

### Dependency injection

- **Shared:** `get_db()` generator in `shared/dependencies.py`
- **Feature factories:** `features/<name>/dependencies.py` for stateless services
- **Inline factories:** DB-scoped services created in route modules
- **Auth:** composable `Depends(verify_admin_api_token)`, `verify_dns_ingest_service`, `verify_enroll_bootstrap`

### Schemas & models

- **ORM models** in `features/<name>/models/` — inherit `Base` from `shared/database.py`
- **API schemas** in `features/<name>/schemas/` — Pydantic v2 with `model_validate` / `from_attributes`
- Services map ORM → response DTOs at the boundary

### Error handling

Three styles coexist (prefer domain exceptions + controller mapping for new code):

1. **Domain exceptions** — `DeviceNotFoundError` raised in service, mapped to 404 in controller
2. **HTTPException in service** — used in some device/policy paths
3. **Route try/except** — used sparingly at the route layer

Shared base: `shared/errors/` (`DomainError`, `NotFoundError`, `ConflictError`, `ValidationError`).

### Cross-feature orchestration

No global event bus. Services import peer services explicitly:

- Alert ingest feeds dashboard attack views
- `device_route.py` aggregates devices, behavior, and policy endpoints
- Network attribution builds maps from endpoint context (+ optional flows)

---

## Data persistence

| Data | Store | Notes |
|------|-------|-------|
| Devices | PostgreSQL (RDS) | Identity via `external_id` |
| Alerts | PostgreSQL (`dns_alerts` table via `alerts` module) | Detection + behavior alerts |
| Agent live state | Redis | Twin / connected agents |
| Agent events | Kafka / Redis (Agent API) | Upstream of detection-engine |

---

## Infrastructure & deployment

| Environment | Trigger | Target |
|-------------|---------|--------|
| `develop` / `main` push | GitHub Actions | EC2 backend (ECR), S3/CloudFront frontend |

---

## Adding a new feature

### Frontend

1. Create `frontend/src/features/<name>/` with `components/`, `hooks/`, `config/api.ts`, `types/`.
2. Add a page in `pages/<Name>Page.tsx` (thin wrapper).
3. Register the route in `routes/index.tsx` wrapped in `<Layout>`.
4. Add a nav item in `MenuContent.tsx` under the appropriate section.
5. Reuse theme tokens and `navigationChrome` sx helpers — avoid one-off colors.

### Backend

1. Create `backend/app/features/<name>/` with `routes/`, `services/`, `repositories/`, `models/`, `schemas/`.
2. Register the router in `main.py`.
3. Add Alembic migration for new tables.
4. Prefer: service raises domain errors, controller maps to HTTP status.
5. Add tests under `backend/tests/unit/<name>/` and `backend/tests/integration/<name>/`.

---

## Related docs

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — component topology
- [API.md](API.md) — REST reference
- [ENV_SETUP.md](ENV_SETUP.md) — configuration
- [DEPLOY.md](DEPLOY.md) — production AWS
- [GRAPH_ENGINE.md](GRAPH_ENGINE.md) — observability graph
