# API reference

FastAPI backend. Interactive OpenAPI: local `http://127.0.0.1:8000/docs`, or production API host `/docs`.

- Admin endpoints: `Authorization: Bearer <ADMIN_API_TOKEN>` when configured
- Service ingest: `TRUSTEDGE_INGEST_TOKEN` (Agent-API upsert, detection-engine, flow ingest)

See [ENV_SETUP.md](ENV_SETUP.md).

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| **Agents** | | |
| `GET` | `/agents` | List registered agents (Postgres) |
| `POST` | `/internal/agents/upsert` | Upsert from Agent-API (`TRUSTEDGE_INGEST_TOKEN`) |
| **Security** | | |
| `GET` | `/security/alerts` | Detection alerts |
| `POST` | `/security/alerts/explain` | Explain alert via Ollama (admin) |
| `POST` | `/security/alerts/ingest` | Alert ingest from detection-engine |
| `GET` | `/security/agents` | Live agent presence from Redis (optional) |
| **Network flows** | | |
| `POST` | `/network-flows/bulk` | Conntrack flow samples (`TRUSTEDGE_INGEST_TOKEN`) |
| `POST` | `/network-flows/dns-resolutions/bulk` | Name → IP mappings |
| `GET` | `/network-flows/live` | Recent L4 flows (admin) |
| **Dashboard** | | |
| `GET` | `/dashboard/network-overview` | Network overview / review summary |

This table is a curated map. Prefer live OpenAPI for request/response schemas.
