# <img src="assets/icons/config.svg" width="28" height="28" align="absmiddle" alt="" /> Environment variables

How to configure TrustEdge for production.

**Canonical references:** [backend/.env.production.example](../backend/.env.production.example), [backend/.env.example](../backend/.env.example), and [frontend/.env.example](../frontend/.env.example).

## Overview

| Environment | Backend file | Frontend file |
|-------------|--------------|---------------|
| Production (EC2 host) | `/etc/trustedge/backend.env` | Built into S3 deploy via CI |
| Production (Docker) | `backend/.env.production` | `frontend/.env.production` |

`.env` files are gitignored. Copy from `.env.example` / `.env.production.example` templates.

## Backend (production)

On EC2 the live file is `/etc/trustedge/backend.env` (see [DEPLOY.md](DEPLOY.md)). Minimum required groups:

```env
DB_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require

LOG_JSON=1
LOG_LEVEL=INFO
ENVIRONMENT=production

ADMIN_API_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
TRUSTEDGE_INGEST_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
REDIS_URL=redis://redis:6379/0
```

Full catalog: [backend/.env.production.example](../backend/.env.production.example).

## Frontend (production)

Set at build time in CI or `frontend/.env.production`:

```env
REACT_APP_API_BASE_URL=http://your-ec2-ip:8000
REACT_APP_ADMIN_API_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
REACT_APP_ENVIRONMENT=production
GENERATE_SOURCEMAP=false
```

`REACT_APP_API_BASE_URL` must be the **FastAPI origin** (EC2 `:8000`), not the CloudFront dashboard URL.

## Docker Compose

`docker-compose.yml` loads `/etc/trustedge/backend.env` on EC2. See [DEPLOY.md](DEPLOY.md).

## Important notes

1. **Never commit `.env` files** — they are in `.gitignore`
2. **Set all security tokens** in production — empty `ADMIN_API_TOKEN` disables admin auth
3. **Match tokens** across backend, frontend (`REACT_APP_ADMIN_API_TOKEN`), and flow/alert ingest services
4. **Use strong random secrets** — store in `/etc/trustedge/backend.env` with `chmod 640`

## Environment variable reference

### Core (backend)

| Variable | Description | Production |
|----------|-------------|------------|
| `DB_URL` | PostgreSQL connection string | RDS URL with `sslmode=require` |
| `ENVIRONMENT` | Environment name | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_JSON` | Structured JSON logs | `1` (see [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)) |

### Security tokens (backend)

| Variable | Used by | Notes |
|----------|---------|-------|
| `ADMIN_API_TOKEN` | Dashboard admin APIs | **Required** in production |
| `TRUSTEDGE_INGEST_TOKEN` | Agent-API upsert, detection-engine, flow ingest | Shared service-to-service bearer |

Frontend: set `REACT_APP_ADMIN_API_TOKEN` to the same value as `ADMIN_API_TOKEN`.

### Redis (backend)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis for TrustEdge Agent live state / twin keys | `redis://redis:6379/0` |

### Network review (backend)

| Variable | Description |
|----------|-------------|
| `NETWORK_REVIEW_MODE` | Dashboard AI review: `template` \| `openai` \| `ollama` |

### Network flows (backend)

Optional L4 session visibility from host conntrack.

| Variable | Description | Default |
|----------|-------------|---------|
| `NETWORK_FLOWS_ENABLED` | Enable flow ingest and map merge | `true` |
| `NETWORK_FLOWS_MAX_AGE_SEC` | Drop flow samples older than this | `300` |
| `NETWORK_FLOWS_DNS_RESOLUTION_TTL_SEC` | Name → IP cache TTL | `600` |
| `NETWORK_FLOWS_MAP_LIMIT` | Max flow nodes merged into map | `80` |

Requires `conntrack` on the host (`apt install conntrack`) when flow watching is enabled.

### Frontend

| Variable | Description | Production |
|----------|-------------|------------|
| `REACT_APP_API_BASE_URL` | FastAPI origin (not CloudFront UI URL) | `http://<ec2-ip>:8000` |
| `REACT_APP_ADMIN_API_TOKEN` | Admin bearer token | **required** |
| `REACT_APP_ENVIRONMENT` | Environment label | `production` |
| `GENERATE_SOURCEMAP` | Source maps | `false` |

## Troubleshooting

### Environment variables not loading

1. On EC2, verify `/etc/trustedge/backend.env` exists and is readable by Docker
2. Restart containers after changing env files:
   ```bash
   docker compose down
   docker compose up -d
   ```

### Frontend variables not working

- React requires variables to start with `REACT_APP_`
- Rebuild and redeploy the frontend after changing production env

### Admin API returns 401

- Set `ADMIN_API_TOKEN` in backend and `REACT_APP_ADMIN_API_TOKEN` in frontend to the same value
- Redeploy frontend after changing build-time env

### Quarantine

Quarantine is a soft dashboard/API flag after VPN removal. Agent-side network isolation is not yet enforced.
