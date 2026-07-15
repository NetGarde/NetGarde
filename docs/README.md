# <img src="assets/trustedge-icon.svg" width="28" height="28" align="absmiddle" alt="" /> TrustEdge documentation

Engineering docs for the [TrustEdge](https://github.com/TrustEdgeOrg/TrustEdge) endpoint security observability platform. The [root README](../README.md) is the product overview; this folder covers implementation detail.

TrustEdge centers on **endpoint telemetry → stream → detection attack → alert**. It is not a DNS/VPN policy product.

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Documentation map

| | Document | Audience | Contents |
|---|----------|----------|----------|
| <img src="assets/icons/flow.svg" width="18" height="18" align="absmiddle" alt="" /> | [DESIGN.md](DESIGN.md) | Engineers | Domain model, topology, frontend/backend patterns |
| <img src="assets/icons/architecture.svg" width="18" height="18" align="absmiddle" alt="" /> | [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Engineers | Architecture, data flows, trust boundaries |
| <img src="assets/icons/collection.svg" width="18" height="18" align="absmiddle" alt="" /> | [GRAPH_ENGINE.md](GRAPH_ENGINE.md) | Engineers | Observability graph model and projections |
| <img src="assets/icons/platforms.svg" width="18" height="18" align="absmiddle" alt="" /> | [DEPLOY.md](DEPLOY.md) | Operators | AWS layout, CI/CD |
| <img src="assets/icons/config.svg" width="18" height="18" align="absmiddle" alt="" /> | [ENV_SETUP.md](ENV_SETUP.md) | Operators | Environment variables and troubleshooting |
| <img src="assets/icons/api.svg" width="18" height="18" align="absmiddle" alt="" /> | [API.md](API.md) | Integrators | REST API reference |
| <img src="assets/icons/privacy.svg" width="18" height="18" align="absmiddle" alt="" /> | [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md) | Operators | Production logging and Insights queries |

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Repository layout

| Path | Role |
|------|------|
| `frontend/` | React 19 dashboard (feature modules) |
| `backend/` | FastAPI API, alerts, twin graph |
| `detection-engine/` | Rules engine on the agent event stream |
| `scripts/` | EC2 / ops helpers |
| `.github/workflows/` | CI test, ECR build, S3/EC2 deploy |

Sibling repos: [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent), [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API).

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Reading paths

**Architecture review**

1. [../README.md](../README.md) — product scope and pipeline  
2. [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — components and flows  
3. [DESIGN.md](DESIGN.md) — principles and code structure  

**Production operations**

1. [DEPLOY.md](DEPLOY.md)  
2. [ENV_SETUP.md](ENV_SETUP.md)  
3. [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)  

---

## <img src="assets/icons/upload.svg" width="22" height="22" align="absmiddle" alt="" /> External references

| Resource | Location |
|----------|----------|
| Backend env catalog | [backend/.env.example](../backend/.env.example) |
| Production backend env | [backend/.env.production.example](../backend/.env.production.example) |
| Frontend env catalog | [frontend/.env.example](../frontend/.env.example) |
| Screenshot assets | [images/README.md](images/README.md) |
| Endpoint agent | [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) |
| Agent API | [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) |
| Organization | [TrustEdgeOrg](https://github.com/TrustEdgeOrg) |
