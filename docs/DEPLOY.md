# Production deployment

TrustEdge production runs on **AWS** with **GitHub Actions** CI/CD.

**See also:** [ENV_SETUP.md](ENV_SETUP.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [aws/README.md](../aws/README.md)

---

## Infrastructure

<p align="center">
  <img width="100%" alt="TrustEdge AWS production architecture" src="assets/aws-architecture.svg" />
</p>

| AWS service | Role |
|-------------|------|
| **EC2** | Docker Compose — backend, detection-engine, agent-api, Redis, Kafka/Redpanda |
| **RDS** | PostgreSQL — agents, alerts, behavior state |
| **S3 + CloudFront** | React dashboard (static) + HTTPS |
| **ECR** | Service Docker images |
| **Redis** (on EC2) | Live agent / twin state |

---

## CI/CD

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `deploy-backend.yml` | Push to `main` / `develop` | pytest → ECR build → SSH deploy → Alembic migrate → restart |
| `deploy-frontend.yml` | Push to `main` / `develop` | npm build → S3 sync → CloudFront invalidation |
| `deploy-develop.yml` | Develop branch | Combined develop pipeline |

---

## EC2 host

| Path | Purpose |
|------|---------|
| `/etc/trustedge/backend.env` | Backend secrets and config (survives deploys) |

See [ENV_SETUP.md](ENV_SETUP.md) for variables.

---

## CloudWatch logging

Structured JSON logs go to stdout. On EC2, the **CloudWatch Agent** forwards Docker logs to CloudWatch Logs.

| Log group | Source | Retention |
|-----------|--------|-----------|
| `/trustedge/prod/backend` | Docker `trustedge-api` | 30 days |

Detection alerts live in PostgreSQL / the dashboard — not as CloudWatch application events.

### Backend env

```env
LOG_JSON=1
LOG_LEVEL=INFO
LOG_TO_FILE=0
LOG_SERVICE=backend
PYTHONUNBUFFERED=1
```

Each HTTP request gets `X-Request-ID` and `request_id` on log lines (`event=http_request`, except `/health`).

### One-time EC2 setup

EC2 instance role needs CloudWatch Logs permissions (`CreateLogGroup`, `CreateLogStream`, `PutLogEvents`, `DescribeLogStreams`, `PutRetentionPolicy`).

```bash
cd ~/trustedge
sudo bash scripts/ec2-setup-cloudwatch.sh
```

Applies [`scripts/cloudwatch/amazon-cloudwatch-agent.json`](../scripts/cloudwatch/amazon-cloudwatch-agent.json) and enables `LOG_JSON` in `backend.env`.

### Insights examples

**Recent errors:**

```
fields @timestamp, level, service, event, message, request_id
| filter level = "ERROR"
| sort @timestamp desc
| limit 50
```

**Slow API requests (>500ms):**

```
fields @timestamp, http_method, http_path, status_code, duration_ms
| filter event = "http_request" and duration_ms > 500
| sort duration_ms desc
```

### Do not log

- Tokens, secrets, device tokens
- Full alert / event payloads that may contain sensitive endpoint detail

---

## Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript, MUI 7 |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| Data | PostgreSQL 16, Redis 7 |
| Ops | Docker Compose, CloudWatch structured logs |
