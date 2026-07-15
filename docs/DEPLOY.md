# <img src="assets/icons/platforms.svg" width="28" height="28" align="absmiddle" alt="" /> Production deployment

TrustEdge production runs on **AWS** with **GitHub Actions** CI/CD. This document covers infrastructure layout and host services.

**See also:** [ENV_SETUP.md](ENV_SETUP.md) · [host-agent/README.md](../host-agent/README.md) · [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)

---

## <img src="assets/icons/platforms.svg" width="22" height="22" align="absmiddle" alt="" /> Infrastructure

| AWS service | Role |
|-------------|------|
| **EC2** | WireGuard, iptables, Docker (backend, detection), host agent |
| **RDS** | PostgreSQL — devices, alerts, behavior state |
| **S3 + CloudFront** | React dashboard static hosting + HTTPS |
| **ECR** | Backend Docker image registry |
| **Redis** (on EC2) | Rolling window for live VPN throughput |

---

## CI/CD pipelines

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `deploy-backend.yml` | Push to `main` / `develop` | pytest → ECR build → SSH deploy → Alembic migrate → restart |
| `deploy-frontend.yml` | Push to `main` / `develop` | npm build → S3 sync → CloudFront invalidation |
| `deploy-develop.yml` | Develop branch | Combined develop pipeline |

---

## EC2 host services

Run alongside Docker on the instance:

```bash
sudo systemctl status trustedge-wg-agent      # peers + quarantine
sudo systemctl status wg-quick@wg0
```

Configuration: `/etc/trustedge/backend.env` (survives deploys). See [ENV_SETUP.md](ENV_SETUP.md).

---

## Key paths

| Path | Purpose |
|------|---------|
| `/etc/wireguard/wg0.conf` | WireGuard server |
| `/etc/trustedge/backend.env` | Backend secrets and config |

---

## Tech stack reference

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript, MUI 7 |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| Data | PostgreSQL 16, Redis 7 |
| Network | WireGuard, iptables |
| Ops | Docker Compose, CloudWatch structured logs |
