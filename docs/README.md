# TrustEdge documentation

Engineering and operations docs for [TrustEdge](https://github.com/TrustEdgeOrg/TrustEdge). Product overview and screenshots: [root README](../README.md).

---

## Docs map

| Document | Audience | Contents |
|----------|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Engineers | Topology, flows, trust boundaries, contributor patterns |
| [DEPLOY.md](DEPLOY.md) | Operators | AWS layout, CI/CD, CloudWatch |
| [ENV_SETUP.md](ENV_SETUP.md) | Operators | Environment variables and troubleshooting |
| [API.md](API.md) | Integrators | Curated REST map (live OpenAPI at `/docs`) |

---

## Reading paths

**Architecture review**

1. [../README.md](../README.md) — product scope  
2. [ARCHITECTURE.md](ARCHITECTURE.md) — components and patterns  

**Production operations**

1. [DEPLOY.md](DEPLOY.md)  
2. [ENV_SETUP.md](ENV_SETUP.md)  

---

## Repository layout

| Path | Role |
|------|------|
| `frontend/` | React dashboard |
| `backend/` | FastAPI control plane |
| `detection-engine/` | Rules, behavior, AI activity on Kafka |
| `aws/` | Optional AWS bootstrap scripts |
| `scripts/` | EC2 helpers (including CloudWatch) |
| `.github/workflows/` | CI test and deploy |

---

## External

| Resource | Location |
|----------|----------|
| Backend env catalog | [backend/.env.example](../backend/.env.example) |
| Production backend env | [backend/.env.production.example](../backend/.env.production.example) |
| Frontend env catalog | [frontend/.env.example](../frontend/.env.example) |
| Agent | [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) |
| Agent API | [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) |
| Organization | [TrustEdgeOrg](https://github.com/TrustEdgeOrg) |
