# Environment variables

Operator configuration for TrustEdge.

**Canonical catalogs:** [backend/.env.production.example](../backend/.env.production.example) · [backend/.env.example](../backend/.env.example) · [frontend/.env.example](../frontend/.env.example)

---

## Overview

| Environment | Backend file | Frontend file |
|-------------|--------------|---------------|
| Production (EC2) | `/etc/trustedge/backend.env` | Built into S3 deploy via CI |
| Production (Docker) | `backend/.env.production` | `frontend/.env.production` |

`.env` files are gitignored. Copy from the example templates.

---

## Backend (production)

On EC2 use `/etc/trustedge/backend.env` (see [DEPLOY.md](DEPLOY.md)):

```env
DB_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require

LOG_JSON=1
LOG_LEVEL=INFO
ENVIRONMENT=production

ADMIN_API_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
TRUSTEDGE_INGEST_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
REDIS_URL=redis://redis:6379/0
```

Full list: [backend/.env.production.example](../backend/.env.production.example).

---

## Frontend (production)

Set at build time in CI or `frontend/.env.production`:

```env
REACT_APP_API_BASE_URL=http://your-ec2-ip:8000
REACT_APP_ADMIN_API_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
REACT_APP_ENVIRONMENT=production
GENERATE_SOURCEMAP=false
```

`REACT_APP_API_BASE_URL` must be the **FastAPI origin** (EC2 `:8000`), not the CloudFront dashboard URL.

---

## Important notes

1. Never commit `.env` files
2. Empty `ADMIN_API_TOKEN` disables admin auth — always set in production
3. Match `ADMIN_API_TOKEN` and `REACT_APP_ADMIN_API_TOKEN`
4. Use strong secrets; `chmod 640` on `/etc/trustedge/backend.env`

---

## Reference

### Core

| Variable | Description | Production |
|----------|-------------|------------|
| `DB_URL` | PostgreSQL URL | RDS with `sslmode=require` |
| `ENVIRONMENT` | Environment name | `production` |
| `LOG_LEVEL` | Verbosity | `INFO` |
| `LOG_JSON` | Structured JSON logs | `1` (see [DEPLOY.md](DEPLOY.md#cloudwatch-logging)) |

### Security

| Variable | Used by | Notes |
|----------|---------|-------|
| `ADMIN_API_TOKEN` | Dashboard admin APIs | **Required** in production |
| `TRUSTEDGE_INGEST_TOKEN` | Agent-API, detection-engine, flow ingest | Shared service bearer |

### Redis

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Live twin / agent state | `redis://redis:6379/0` |

### Network review

| Variable | Description |
|----------|-------------|
| `NETWORK_REVIEW_MODE` | `template` \| `openai` \| `ollama` |

### Network flows (optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `NETWORK_FLOWS_ENABLED` | Enable flow ingest | `true` |
| `NETWORK_FLOWS_MAX_AGE_SEC` | Drop older samples | `300` |
| `NETWORK_FLOWS_DNS_RESOLUTION_TTL_SEC` | Name → IP TTL | `600` |

Requires `conntrack` on the host when flow watching is enabled.

### Frontend

| Variable | Description | Production |
|----------|-------------|------------|
| `REACT_APP_API_BASE_URL` | FastAPI origin | `http://<ec2-ip>:8000` |
| `REACT_APP_ADMIN_API_TOKEN` | Admin bearer | **required** |
| `REACT_APP_ENVIRONMENT` | Label | `production` |
| `GENERATE_SOURCEMAP` | Source maps | `false` |

---

## Troubleshooting

### Env not loading

1. Verify `/etc/trustedge/backend.env` exists and is readable by Docker
2. Restart: `docker compose down && docker compose up -d`

### Frontend env unchanged

- Variables must start with `REACT_APP_`
- Rebuild and redeploy after changing production build env

### Admin API 401

- Align backend `ADMIN_API_TOKEN` and frontend `REACT_APP_ADMIN_API_TOKEN`
- Redeploy frontend after changing build-time env
