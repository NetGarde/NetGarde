# <img src="docs/assets/trustedge-icon.svg" alt="" width="36" height="36" align="absmiddle" /> TrustEdge

**Self-hosted security observability** — VPN/DNS visibility, EDR-lite endpoint telemetry, rules-based detection, and optional enforcement.

React dashboard · FastAPI control plane · [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) · WireGuard enrollment · AWS deploy with CI/CD.

[![Deploy Develop](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml/badge.svg)](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml)

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Endpoint → Collector → Batch → Compress → Secure upload → Agent API → Stream → Detection Attack → Alert" width="1000" />
</p>

---

## Why it exists

Most security tools are either heavy enterprises stacks or narrow point products. TrustEdge is a **unified, self-hosted** control plane:

| Path | What it does |
|------|----------------|
| **VPN / DNS** | WireGuard enroll, dnsmasq policy, live WebSocket queries, behavior baselines |
| **Endpoint** | [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) → [Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) → stream → detection |
| **Ops** | What-if policy preview, optional enforcement, CloudWatch logs, ECR deploy |

Enforcement (quarantine, DNS blocks) is **opt-in**. Detection and scoring stay **rules-based**; optional LLMs only explain state for operators.

---

## How it works

**Endpoint path**

1. **Endpoint** — device running TrustEdge Agent  
2. **Collector → Batch → Compress** — on-device telemetry pipeline  
3. **Secure upload** — HTTPS to Agent API  
4. **Agent API → Stream** — validate, persist, publish  
5. **Detection Attack → Alert** — rules engine + dashboard alerts  

**VPN / DNS path**

```text
Client → WireGuard → dnsmasq → log watcher → API → WebSocket → Dashboard
Policy:  Dashboard → API → RDS → host agents → dns-sync → dnsmasq reload
Enroll:  TrustEdgeClient → POST /v1/enroll → WireGuard config
```

Deep dive: [System architecture](docs/SYSTEM_ARCHITECTURE.md) · [Design](docs/DESIGN.md)

---

## Platform at a glance

| Capability | Implementation |
|------------|----------------|
| Security observability | Network map, client map, live telemetry, endpoint posture, attack alerts |
| Endpoint telemetry | TrustEdge Agent: process, app focus, network posture |
| Detection | Kafka-backed rules on agent events |
| What-if simulation | Preview global pack impact before apply |
| Secure access | WireGuard VPN, enrollment API, IP pool |
| Desired-state policy | Packs, profiles, schedules, geo rules |
| Behavior intelligence | Per-device baselines, drift scoring |
| Enforcement | Host agent + dns-sync (opt-in) |
| AI operations | Optional network / behavior summaries |
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

Application logic runs in Docker on EC2; WireGuard, iptables, and dnsmasq stay on the **host**.

<p align="center">
  <img width="90%" alt="TrustEdge system architecture" src="https://github.com/user-attachments/assets/bab37178-52c4-4f6d-b4ac-1500230d0af5" />
</p>

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Edge clients** | Laptops, phones, enrolled devices | DNS / traffic via WireGuard |
| **Endpoint agents** | TrustEdge Agent | Process, app, network posture |
| **EC2 host** | WireGuard, dnsmasq, iptables | VPN, DNS, quarantine |
| **Host agents** | `trustedge-wg-agent`, `trustedge-log-watcher` | Peer apply, block, log ingest |
| **Application** | FastAPI, dns-sync, detection-engine, React | Policy, ingest, detection, UI |
| **Data** | PostgreSQL (RDS), Redis, Kafka/Redpanda, ECR | State, live usage, event bus, images |

**Design notes**

- **Generated dnsmasq config** — RDS is source of truth  
- **Selective DNS persistence** — blocked queries by default (`PERSIST_ALL_DNS` opt-in)  
- **Rules for security, LLM for explanation** — scoring stays deterministic  
- **Observability-first enforcement** — DNS blocking off until operators opt in  

---

## Tech stack

| Area | Technologies |
|------|----------------|
| Frontend | React 19, TypeScript, Material UI 7, MUI X Charts |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2 |
| Endpoint agent | Go 1.22 ([TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)) |
| Real-time | WebSocket, Redis, Kafka/Redpanda |
| Data | PostgreSQL 16 (RDS) |
| Network | WireGuard, dnsmasq, iptables |
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
