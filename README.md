# <img src="docs/assets/trustedge-icon.svg" alt="" width="36" height="36" align="absmiddle" /> TrustEdge

**Self-hosted security observability** — endpoint telemetry, rules-based detection, and attack alerts.

React dashboard · FastAPI control plane · [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) · [Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) · AWS deploy with CI/CD.

[![Deploy Develop](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml/badge.svg)](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml)

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Endpoint → Collector → Batch → Compress → Secure upload → Agent API → Stream → Detection Attack → Alert" width="1000" />
</p>

---

## Architecture

TrustEdge separates **collection** (on the endpoint), **ingest + detection** (Agent API → Kafka → rules engine), and **operator views** (FastAPI + React). <p align="center">
  <img width="100%" alt="TrustEdge architecture — endpoint agents, Agent API, Kafka, detection engine, control plane, and dashboard" src="docs/assets/architecture.svg" />
</p>

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Edge** | TrustEdge Agent (macOS / Linux / Windows) | Collect · batch · compress · HTTPS upload |
| **Ingest** | [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) | Auth, validate, persist, publish |
| **Stream** | Kafka / Redpanda (`trustedge.agent.events`) | Durable event bus for detection |
| **Detection** | `detection-engine` | Rules on agent events → attack alerts |
| **Control plane** | FastAPI · Twin · dashboard APIs | Alerts, graph, network map, devices |
| **Dashboard** | React on S3 + CloudFront | Attack alerts, maps, behavior profiles |
| **Data** | PostgreSQL (RDS), Redis | Source of truth + live usage |

**Design notes**

- **Rules for security, LLM for explanation** — scoring stays deterministic  
- **Observability-first enforcement** — quarantine is opt-in  

More detail: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) · [Design](docs/DESIGN.md)

---

## Why it exists

Most security tools are either heavy enterprise stacks or narrow point products. TrustEdge is a **unified, self-hosted** control plane for endpoint signal and detection:

| Path | What it does |
|------|----------------|
| **Endpoint** | [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) → [Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) → stream → detection → alerts |
| **Dashboard** | Network map, client map, behavior drift, attack alerts |
| **Ops** | CloudWatch logs, Alembic, ECR deploy |

Detection and scoring stay **rules-based**; optional LLMs only explain state for operators.

---

## How it works

1. **Endpoint** — device running TrustEdge Agent  
2. **Collector → Batch → Compress** — on-device telemetry pipeline  
3. **Secure upload** — HTTPS to Agent API  
4. **Agent API → Stream** — validate, persist, publish  
5. **Detection Attack → Alert** — rules engine + dashboard alerts  

---

## Platform at a glance

| Capability | Implementation |
|------------|----------------|
| Security observability | Network map, client map, endpoint posture, attack alerts |
| Endpoint telemetry | TrustEdge Agent: process, app focus, network posture |
| Detection | Kafka-backed rules on agent events |
| Behavior intelligence | Per-device baselines, drift scoring |
| AI operations | Optional network / behavior summaries |
| Production ops | CloudWatch JSON logs, Alembic, ECR deploy |

---

## Screenshots

> More captures: [docs/images/README.md](docs/images/README.md)

### Dashboard & monitoring

![Network overview — AI summary, live stats, and alerts](docs/images/dashboard-home.png)

### Clients

![Behavior baseline, score, and quarantine](docs/images/client-profiles.png)

### Operations

![Geographic client map](docs/images/client-map.png)

---

## Tech stack

| Area | Technologies |
|------|----------------|
| Frontend | React 19, TypeScript, Material UI 7, MUI X Charts |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2 |
| Endpoint agent | Go 1.22 ([TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)) |
| Real-time | WebSocket, Redis, Kafka/Redpanda |
| Data | PostgreSQL 16 (RDS) |
| Infrastructure | AWS EC2, RDS, S3, CloudFront, ECR |
| Observability | Structured JSON logging, CloudWatch Logs Insights |
| CI/CD | GitHub Actions |
| Containers | Docker, Docker Compose |

---

## Quick start

```bash
git clone https://github.com/TrustEdgeOrg/TrustEdge.git
cd TrustEdge
```

- Production AWS: [docs/DEPLOY.md](docs/DEPLOY.md)  
- Environment variables: [docs/ENV_SETUP.md](docs/ENV_SETUP.md)  
- Endpoint agent: [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)  
- Agent ingest API: [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)  

---

## Documentation

| | Document | Description |
|---|----------|-------------|
| <img src="docs/assets/icons/layout.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/README.md](docs/README.md) | Documentation index |
| <img src="docs/assets/icons/architecture.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Components and data flows |
| <img src="docs/assets/icons/flow.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/DESIGN.md](docs/DESIGN.md) | Domain model and conventions |
| <img src="docs/assets/icons/platforms.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/DEPLOY.md](docs/DEPLOY.md) | AWS production deploy |
| <img src="docs/assets/icons/api.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/API.md](docs/API.md) | REST and WebSocket reference |
| <img src="docs/assets/icons/config.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/ENV_SETUP.md](docs/ENV_SETUP.md) | Environment variables |
| <img src="docs/assets/icons/agent.svg" width="18" height="18" align="absmiddle" alt="" /> | [host-agent/README.md](host-agent/README.md) | EC2 host agent |

---

## Ecosystem

| Repository | Role |
|------------|------|
| **[TrustEdge](https://github.com/TrustEdgeOrg/TrustEdge)** | This control plane |
| **[TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)** | Endpoint collector |
| **[TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)** | Ingest · validate · Kafka |

---

Part of [TrustEdgeOrg](https://github.com/TrustEdgeOrg) · Portfolio and educational use.
