# <img src="docs/assets/trustedge-icon.svg" alt="" width="36" height="36" align="absmiddle" /> TrustEdge

**Self-hosted security observability** — endpoint telemetry, rules-based detection, and attack alerts.

React dashboard · FastAPI control plane · [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) · [Agent API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) · AWS deploy with CI/CD.

[![Deploy Develop](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml/badge.svg)](https://github.com/TrustEdgeOrg/TrustEdge/actions/workflows/deploy-develop.yml)

---

## About the project

TrustEdge is a **self-hosted security observability platform**. It gives teams real endpoint signal and actionable detection without a heavyweight enterprise EDR stack.

A lightweight [TrustEdge Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) runs on macOS, Linux, and Windows. It collects process, activity, network, security-lifecycle, and AI tools inventory telemetry. Events go into a durable local queue, then are compressed and uploaded over HTTPS to [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API).

Kafka streams those events to a rules engine. This control plane surfaces **attack alerts**, the agents registry, **installed AI software**, and behavior views in a React dashboard.

Detection is **rules-based** and deterministic. Optional LLMs can explain state to operators — they never decide what is malicious.

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Endpoint → Collector → Durable queue → Compress → Secure upload → Agent API → Stream → Detection → Alert" width="1000" />
</p>

---

## Architecture

TrustEdge separates **collection** on the endpoint, **ingest and detection** in the stream path, and **operator views** in FastAPI + React.

<p align="center">
  <img width="100%" alt="TrustEdge architecture — Edge, Ingest, Stream, Detect, Operate" src="docs/assets/architecture.svg" />
</p>

| Stage | Components | Responsibility |
|-------|------------|----------------|
| **1 · Edge** | TrustEdge Agent (Go) | Collect · durable queue · compress · HTTPS |
| **2 · Ingest** | [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) (FastAPI) | Device auth · validate · publish |
| **3 · Stream** | Kafka / Redpanda | Durable `trustedge.agent.events` bus |
| **4 · Detect** | `detection-engine` | Attack / drift rules → alerts |
| **5 · Operate** | FastAPI · React dashboard | Alerts, agents, AI software, behavior |
| **Data** | PostgreSQL (RDS), Redis | Source of truth · live state |

More detail: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)

---

## How it works

1. **Endpoint** — TrustEdge Agent runs on the device  
2. **Collect → durable queue → compress** — local telemetry, no collector HTTP  
3. **Secure upload** — HTTPS to Agent API with a device token  
4. **Ingest → stream** — validate and publish to Kafka  
5. **Detect → operate** — rules create alerts; the dashboard shows them  

---

## Platform at a glance

| Capability | Implementation |
|------------|----------------|
| Endpoint telemetry | Process, activity, network, security lifecycle, AI tools inventory |
| Reliable delivery | Durable queue · compress · HTTPS · retry with backoff |
| Detection | Kafka-backed rules on agent events |
| Observability | Attack alerts, agents registry, installed AI software |
| AI operations | Optional summaries (OpenAI / Ollama / templates) |
| Production ops | EC2 + Docker Compose, RDS, S3/CloudFront, ECR, GitHub Actions |

---

## Tech stack

| Area | Technologies |
|------|----------------|
| Frontend | React 19, TypeScript, Material UI 7 |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| Endpoint agent | Go ([TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)) |
| Streaming | Kafka / Redpanda, Redis |
| Data | PostgreSQL 16 (RDS) |
| Infrastructure | AWS EC2, S3, CloudFront, ECR |
| CI/CD | GitHub Actions, Docker Compose |

---

## Quick start

```bash
git clone https://github.com/TrustEdgeOrg/TrustEdge.git
cd TrustEdge
```

- Deploy: [docs/DEPLOY.md](docs/DEPLOY.md)  
- Environment: [docs/ENV_SETUP.md](docs/ENV_SETUP.md)  
- Agent: [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)  
- Ingest API: [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)  

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Components and data flows |
| [docs/API.md](docs/API.md) | REST reference |
| [docs/ENV_SETUP.md](docs/ENV_SETUP.md) | Environment variables |
| [docs/DEPLOY.md](docs/DEPLOY.md) | AWS production deploy |

---

## Ecosystem

| Repository | Role |
|------------|------|
| **[TrustEdge](https://github.com/TrustEdgeOrg/TrustEdge)** | This control plane |
| **[TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent)** | Endpoint collector |
| **[TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API)** | Ingest · validate · Kafka |

---

Part of [TrustEdgeOrg](https://github.com/TrustEdgeOrg) · Portfolio and educational use.
