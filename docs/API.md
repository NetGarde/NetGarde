# <img src="assets/icons/api.svg" width="28" height="28" align="absmiddle" alt="" /> API reference

TrustEdge exposes a FastAPI backend. Interactive docs: `http://127.0.0.1:8000/docs` locally, or your production API host `/docs`.

Admin endpoints require `Authorization: Bearer <ADMIN_API_TOKEN>` when the token is configured. Service ingest uses `TRUSTEDGE_INGEST_TOKEN` (Agent-API upsert, detection-engine, flow ingest). See [ENV_SETUP.md](ENV_SETUP.md).

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| **Security observability** | | |
| `GET` | `/security/alerts` | Detection / attack alerts |
| `POST` | `/security/alerts/ingest` | Ingest alerts from detection-engine |
| `GET` | `/security/graph/snapshot` | Canonical entity/dependency graph (`minutes`, `include_flows`) |
| `POST` | `/security/graph/traverse` | Walk dependencies from seed nodes (impact, blast radius, RCA) |
| `GET` | `/security/graph/neighbors` | One-hop neighbors of a node (`node_id`, `direction`, optional `relations`, `layers`) |
| `POST` | `/security/simulate/command` | Parse natural-language what-if commands (rules + Ollama fallback) |
| **Devices** | | |
| `GET` | `/devices` | List devices |
| `GET` | `/devices/blocked-clients` | Devices with active quarantine |
| `GET` | `/devices/{id}/behavior-profile` | Client behavior profile |
| `GET` | `/devices/{id}/client-blocks` | Active per-device domain blocks (legacy) |
| `POST` | `/devices/{id}/quarantine` | Soft quarantine flag (agent isolation TBD) |
| `DELETE` | `/devices/{id}/quarantine` | Release client from quarantine early |
| `GET` | `/devices/{id}/network-attribution` | Hourly per-app usage rollups (`hours`, optional `app_slug`) |
| `GET` | `/devices/{id}/network-attribution/summary` | Top apps with avg minutes/hour and total hours |
| `GET` | `/network-attribution/map` | Device → app graph (`minutes`; `include_flows=true` adds L4 session nodes) |
| **Network flows** | | |
| `POST` | `/network-flows/bulk` | Ingest conntrack flow samples (`TRUSTEDGE_INGEST_TOKEN`) |
| `POST` | `/network-flows/dns-resolutions/bulk` | Ingest name → IP mappings for flow correlation |
| `GET` | `/network-flows/live` | Recent L4 flows (admin token) |
| **Endpoint agent** | | |
| `POST` | `/v1/network-attribution` | Report foreground app intervals (device token) |
| **Dashboard** | | |
| `GET` | `/dashboard/network-overview` | Network overview and review summary |

DNS query, WireGuard VPN enroll/usage, and policy dnsmasq sync APIs have been removed.
