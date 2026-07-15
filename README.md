# <img src="docs/assets/trustedge-icon.svg" alt="" width="36" height="36" align="absmiddle" /> TrustEdge

**Self-hosted endpoint security observability** — EDR-lite telemetry, rules-based attack detection, and operator alerts.

React dashboard · FastAPI control plane · [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) · [Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) · AWS deploy with CI/CD.

[![Deploy Develop](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml/badge.svg)](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml)

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Endpoint → Collector → Batch → Compress → Secure upload → Agent API → Stream → Detection Attack → Alert" width="1000" />
</p>

---

## Why it exists

Security teams need **endpoint signal and attack detection** without a heavyweight EDR stack. TrustEdge is the self-hosted control plane for that path:

| Piece | Role |
|-------|------|
| **[TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)** | Collects device, network, activity, and process telemetry on the endpoint |
| **[Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)** | Registers devices, accepts compressed batches, publishes to Kafka |
| **TrustEdge** | Detection engine, alerts, observability graph, operator dashboard |

Detection stays **rules-based**. Optional LLMs only explain state for operators — they do not decide blocks.

---

## How it works

1. **Endpoint** — laptop or workstation running TrustEdge Agent  
2. **Collector → Batch → Compress** — on-device pipeline  
3. **Secure upload** — HTTPS to Agent API with a device token  
4. **Agent API → Stream** — validate, persist, publish (`trustedge.agent.events`)  
5. **Detection Attack** — rules engine evaluates process / network patterns  
6. **Alert** — findings land in the TrustEdge UI for operators  

Deep dive: [System architecture](docs/SYSTEM_ARCHITECTURE.md) · [Design](docs/DESIGN.md)

---

## Platform at a glance

| Capability | Implementation |
|------------|----------------|
| Endpoint telemetry | Device details, network summary, app focus, process start/exit |
| Detection | Kafka-backed rules engine on agent events |
| Alerts | Twin / attack alerts in the dashboard |
| Observability graph | Entity and dependency view for endpoint posture |
| AI operations | Optional network / device summaries (OpenAI or Ollama) |
| Production ops | CloudWatch JSON logs, Alembic, ECR deploy |

---

## Screenshots

> More captures: [docs/images/README.md](docs/images/README.md)

### Dashboard & monitoring

![Network overview — AI summary, live stats, and alerts](docs/images/dashboard-home.png)

### Policy & clients

![Behavior baseline, score, and quarantine](docs/images/client-profiles.png)

### Operations

![Geographic client map](docs/images/client-map.png)

---

## Architecture

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Endpoints** | TrustEdge Agent on macOS / Linux / Windows | Collect posture telemetry |
| **Ingest** | TrustEdge-Agent-API | Auth, validate, optional Kafka publish |
| **Stream** | Kafka / Redpanda | `trustedge.agent.events` |
| **Detection** | `detection-engine` | Rules on process and network signals |
| **Control plane** | FastAPI backend | Alerts, twin graph, admin API |
| **UI** | React (S3 / CloudFront) | Operator dashboard |
| **Data** | PostgreSQL (RDS), Redis, ECR | State, live mirrors, images |

---

## Tech stack

| Area | Technologies |
|------|----------------|
| Frontend | React 19, TypeScript, Material UI 7, MUI X Charts |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2 |
| Endpoint agent | Go 1.22 ([TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)) |
| Ingest API | FastAPI ([TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)) |
| Real-time | Redis, Kafka/Redpanda |
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
| <img src="docs/assets/icons/api.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/API.md](docs/API.md) | REST API reference |
| <img src="docs/assets/icons/config.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/ENV_SETUP.md](docs/ENV_SETUP.md) | Environment variables |
| <img src="docs/assets/icons/privacy.svg" width="18" height="18" align="absmiddle" alt="" /> | [docs/CLOUDWATCH_LOGGING.md](docs/CLOUDWATCH_LOGGING.md) | Production logging |

---

## Ecosystem

| Repository | Role |
|------------|------|
| **[TrustEdge](https://github.com/TrustEdgeOrg/TrustEdge)** | This control plane · detection · UI |
| **[TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)** | Endpoint collector |
| **[TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)** | Ingest · validate · Kafka |

---

Part of [TrustEdgeOrg](https://github.com/TrustEdgeOrg) · Portfolio and educational use.
