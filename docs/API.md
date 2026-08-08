# <img src="assets/icons/api.svg" width="28" height="28" align="absmiddle" alt="" /> API reference

TrustEdge exposes a FastAPI backend. Interactive docs: `http://127.0.0.1:8000/docs` locally, or your production API host `/docs`.

Admin endpoints require `Authorization: Bearer <ADMIN_API_TOKEN>` when the token is configured. Service ingest uses `TRUSTEDGE_INGEST_TOKEN` (Agent-API upsert, detection-engine, flow ingest). See [ENV_SETUP.md](ENV_SETUP.md).

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| **Agents** | | |
| `GET` | `/agents` | List registered agents (Postgres registry) |
| `POST` | `/internal/agents/upsert` | Upsert agent from Agent-API (`TRUSTEDGE_INGEST_TOKEN`) |
| **Security observability** | | |
| `GET` | `/security/alerts` | Recent detection alerts (proxies detection-engine `GET /alerts` when `DETECTION_ENGINE_URL` is set; otherwise Postgres) |
| `POST` | `/security/alerts/explain` | Explain an alert with the local Ollama model (admin token) |
| `POST` | `/security/alerts/ingest` | Legacy ingest from detection-engine (no-op when `DETECTION_ENGINE_URL` is set) |
| `GET` | `/security/agents` | Live agent presence from Redis (optional) |
| **Network flows** | | |
| `POST` | `/network-flows/bulk` | Ingest conntrack flow samples (`TRUSTEDGE_INGEST_TOKEN`) |
| `POST` | `/network-flows/dns-resolutions/bulk` | Ingest name → IP mappings for flow correlation |
| `GET` | `/network-flows/live` | Recent L4 flows (admin token) |
| **Dashboard** | | |
| `GET` | `/dashboard/network-overview` | Network overview and review summary |

DNS query, WireGuard VPN enroll/usage, policy dnsmasq sync, network map / attribution / graph APIs have been removed.
