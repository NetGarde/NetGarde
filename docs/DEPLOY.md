# <img src="assets/icons/platforms.svg" width="28" height="28" align="absmiddle" alt="" /> Production deployment

TrustEdge production runs on **AWS** with **GitHub Actions** CI/CD. This document covers infrastructure layout and host services.

**See also:** [ENV_SETUP.md](ENV_SETUP.md) · [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)

---

## <img src="assets/icons/platforms.svg" width="22" height="22" align="absmiddle" alt="" /> Infrastructure

<p align="center">
  <img width="100%" alt="TrustEdge AWS production architecture" src="assets/aws-architecture.png" />
</p>

| AWS service | Role |
|-------------|------|
| **EC2** | Docker Compose — backend, detection-engine, agent-api, Redis, Kafka/Redpanda |
| **RDS** | PostgreSQL — devices, alerts, behavior state |
| **S3 + CloudFront** | React dashboard static hosting + HTTPS |
| **ECR** | Backend / service Docker image registry |
| **Redis** (on EC2) | TrustEdge Agent live state / twin keys |

---

## CI/CD pipelines

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `deploy-backend.yml` | Push to `main` / `develop` | pytest → ECR build → SSH deploy → Alembic migrate → restart |
| `deploy-frontend.yml` | Push to `main` / `develop` | npm build → S3 sync → CloudFront invalidation |
| `deploy-develop.yml` | Develop branch | Combined develop pipeline |

---

## EC2 host services

Configuration: `/etc/trustedge/backend.env` (survives deploys). See [ENV_SETUP.md](ENV_SETUP.md).

---

## Key paths

| Path | Purpose |
|------|---------|
| `/etc/trustedge/backend.env` | Backend secrets and config |

---

## Tech stack reference

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript, MUI 7 |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| Data | PostgreSQL 16, Redis 7 |
| Ops | Docker Compose, CloudWatch structured logs |
