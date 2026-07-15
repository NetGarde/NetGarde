# <img src="assets/icons/api.svg" width="28" height="28" align="absmiddle" alt="" /> API reference

TrustEdge exposes a FastAPI backend for **endpoint observability**, twin graph, and attack alerts.

Interactive docs: `http://127.0.0.1:8000/docs` locally, or your production API host `/docs`.

Admin endpoints require `Authorization: Bearer <ADMIN_API_TOKEN>` when configured. See [ENV_SETUP.md](ENV_SETUP.md).

Agent ingest HTTP APIs live in [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API/blob/main/docs/api.md) (`/v1/register`, `/v1/events`).

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| **Security observability** | | |
| `GET` | `/twin/graph/snapshot` | Entity / dependency graph |
| `POST` | `/twin/graph/traverse` | Walk dependencies (impact, blast radius, RCA) |
| `GET` | `/twin/graph/neighbors` | One-hop neighbors |
| **Alerts** | | |
| `GET` | `/twin/alerts` | List TrustEdge Agent detection alerts |
| `POST` | `/twin/alerts/ingest` | Detection-engine → backend alert write path |
| **Devices** | | |
| `GET` | `/devices` | List devices |
| `GET` | `/devices/{id}/behavior-profile` | Optional behavior profile |
| **Dashboard** | | |
| `GET` | `/dashboard/network-overview` | Overview / review summary |

Exact alert paths may grow with the UI — prefer OpenAPI `/docs` as source of truth.

---

## Auth

| Token | Header | Used for |
|-------|--------|----------|
| `ADMIN_API_TOKEN` | `Authorization: Bearer …` | Operator / admin REST |

Device registration and event upload use the **Agent API**, not these TrustEdge admin routes.

---

## Related

- [DESIGN.md](DESIGN.md)  
- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)  
- [Agent API reference](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API/blob/main/docs/api.md)  
