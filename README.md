# <img src="docs/assets/trustedge-icon.svg" alt="" width="36" height="36" align="absmiddle" /> TrustEdge

**Self-hosted security observability** — endpoint telemetry, rules-based detection, VPN enrollment, and optional quarantine.

React dashboard · FastAPI control plane · [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) · WireGuard enrollment · AWS deploy with CI/CD.

[![Deploy Develop](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml/badge.svg)](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml)

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Endpoint → Collector → Batch → Compress → Secure upload → Agent API → Stream → Detection Attack → Alert" width="1000" />
</p>

---

## Why it exists

Most security tools are either heavy enterprise stacks or narrow point products. TrustEdge is a **unified, self-hosted** control plane:

| Path | What it does |
|------|----------------|
| **Endpoint** | [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) → [Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) → stream → detection → alerts |
| **Access** | WireGuard enroll, IP pool, live usage, optional quarantine |
| **Ops** | CloudWatch logs, Alembic, ECR deploy |

Detection and scoring stay **rules-based**; optional LLMs only explain state for operators.

---

## How it works

1. **Endpoint** — device running TrustEdge Agent  
2. **Collector → Batch → Compress** — on-device telemetry pipeline  
3. **Secure upload** — HTTPS to Agent API  
4. **Agent API → Stream** — validate, persist, publish  
5. **Detection Attack → Alert** — rules engine + dashboard alerts  

VPN clients can also enroll for WireGuard access and report usage / foreground app context used on the network map.

Deep dive: [System architecture](docs/SYSTEM_ARCHITECTURE.md) · [Design](docs/DESIGN.md)

---

## Platform at a glance

| Capability | Implementation |
|------------|----------------|
| Security observability | Network map, client map, endpoint posture, attack alerts |
| Endpoint telemetry | TrustEdge Agent: process, app focus, network posture |
| Detection | Kafka-backed rules on agent events |
| Secure access | WireGuard VPN, enrollment API, IP pool |
| Behavior intelligence | Per-device baselines, drift scoring |
| Enforcement | Host agent quarantine (iptables, opt-in) |
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

## Architecture

Application logic runs in Docker on EC2; WireGuard and iptables stay on the **host**.

<p align="center">
  <img width="90%" alt="TrustEdge system architecture" src="https://github.com/user-attachments/assets/bab37178-52c4-4f6d-b4ac-1500230d0af5" />
</p>

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Endpoint agents** | TrustEdge Agent | Process, app, network posture |
| **EC2 host** | WireGuard, iptables | VPN, quarantine |
| **Host agents** | `trustedge-wg-agent` | Peer apply, block/unblock |
| **Application** | FastAPI, detection-engine, React | Ingest, detection, UI |
| **Data** | PostgreSQL (RDS), Redis, Kafka/Redpanda, ECR | State, live usage, event bus, images |

**Design notes**

- **Rules for security, LLM for explanation** — scoring stays deterministic  
- **Observability-first enforcement** — quarantine is opt-in  

---

## Tech stack

| Area | Technologies |
|------|----------------|
| Frontend | React 19, TypeScript, Material UI 7, MUI X Charts |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2 |
| Endpoint agent | Go 1.22 ([TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)) |
| Real-time | WebSocket, Redis, Kafka/Redpanda |
| Data | PostgreSQL 16 (RDS) |
| Network | WireGuard, iptables |
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
- Enroll VPN client: [TrustEdgeClient](https://github.com/TrustEdgeOrg/TrustEdgeClient)  
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
| **[TrustEdgeClient](https://github.com/TrustEdgeOrg/TrustEdgeClient)** | VPN enroll client |

---

Part of [TrustEdgeOrg](https://github.com/TrustEdgeOrg) · Portfolio and educational use.
