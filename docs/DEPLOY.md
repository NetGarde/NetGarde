# <img src="assets/icons/platforms.svg" width="28" height="28" align="absmiddle" alt="" /> Production deployment

TrustEdge production runs on **AWS** with **GitHub Actions** CI/CD. This document covers infrastructure for the **endpoint observability** control plane.

**See also:** [ENV_SETUP.md](ENV_SETUP.md) · [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)

---

## <img src="assets/icons/platforms.svg" width="22" height="22" align="absmiddle" alt="" /> Infrastructure

| AWS service | Role |
|-------------|------|
| **EC2** | Docker — FastAPI backend, detection-engine, Redis, Kafka/Redpanda (or managed stream) |
| **RDS** | PostgreSQL — alerts, devices, twin state |
| **S3 + CloudFront** | React dashboard static hosting + HTTPS |
| **ECR** | Backend / detection images |
| **Redis** (on EC2 or managed) | Live mirrors / short-lived caches |

Sibling services (often co-deployed):

| Service | Repo |
|---------|------|
| Agent API | [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) |
| Endpoint agents | [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) |

---

## CI/CD pipelines

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `deploy-backend.yml` | Push to `main` / `develop` | pytest → ECR build → SSH deploy → Alembic migrate → restart |
| `deploy-frontend.yml` | Push to `main` / `develop` | npm build → S3 sync → CloudFront invalidation |
| `deploy-develop.yml` | Develop branch | Combined develop pipeline |

---

## Runtime on EC2

Typical containers (see `docker-compose.yml`):

- `trustedge-api` — FastAPI backend  
- `detection-engine` — Kafka consumer / rules  
- `redis` — caches  
- `redpanda` (or external Kafka) — agent event stream  

Configuration: `/etc/trustedge/backend.env` (survives deploys). See [ENV_SETUP.md](ENV_SETUP.md).

---

## Tech stack reference

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript, MUI 7 |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| Data | PostgreSQL 16, Redis 7, Kafka/Redpanda |
| Ops | Docker Compose, CloudWatch structured logs |
