# <img src="assets/icons/config.svg" width="28" height="28" align="absmiddle" alt="" /> Environment variables

How to configure TrustEdge for the **endpoint observability** control plane.

**Canonical references:** [backend/.env.production.example](../backend/.env.production.example), [backend/.env.example](../backend/.env.example), and [frontend/.env.example](../frontend/.env.example).

Agent-side knobs live in [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent/blob/main/docs/configuration.md).  
Ingest API knobs live in [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API/blob/main/docs/configuration.md).

---

## Overview

| Environment | Backend file | Frontend file |
|-------------|--------------|---------------|
| Production (EC2 host) | `/etc/trustedge/backend.env` | Built into S3 deploy via CI |
| Production (Docker) | `backend/.env.production` | `frontend/.env.production` |

`.env` files are gitignored. Copy from `.env.example` / `.env.production.example` templates.

---

## Backend (production)

On EC2 the live file is `/etc/trustedge/backend.env` (see [DEPLOY.md](DEPLOY.md)). Minimum groups:

```env
DB_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require

LOG_JSON=1
LOG_LEVEL=INFO
ENVIRONMENT=production

ADMIN_API_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET

REDIS_URL=redis://redis:6379/0
```

Add stream / detection settings as required by your compose stack (Kafka brokers, alert ingest shared secrets). Prefer placeholders in docs — never commit real tokens.

Full catalog: [backend/.env.production.example](../backend/.env.production.example).

---

## Frontend (production)

Set at build time in CI or `frontend/.env.production`:

```env
REACT_APP_API_BASE_URL=https://your-api.example
REACT_APP_ADMIN_API_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
REACT_APP_ENVIRONMENT=production
GENERATE_SOURCEMAP=false
```

`REACT_APP_API_BASE_URL` must be the **FastAPI origin**, not the CloudFront dashboard URL.

---

## Important notes

1. **Never commit `.env` files** — they are in `.gitignore`  
2. **Set `ADMIN_API_TOKEN` in production** — empty disables admin auth  
3. **Match tokens** across backend and frontend (`REACT_APP_ADMIN_API_TOKEN`)  
4. **Use strong random secrets** — store in `/etc/trustedge/backend.env` with `chmod 640`  

---

## Core backend variables

| Variable | Description | Production |
|----------|-------------|------------|
| `DB_URL` | PostgreSQL connection string | RDS URL with `sslmode=require` |
| `ENVIRONMENT` | Environment name | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_JSON` | Structured JSON logs | `1` (see [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)) |
| `ADMIN_API_TOKEN` | Admin REST / dashboard | **Required** |
| `REDIS_URL` | Redis connection | Compose or managed Redis |

Frontend: set `REACT_APP_ADMIN_API_TOKEN` to the same value as `ADMIN_API_TOKEN`.

---

## AI (optional)

| Variable | Description |
|----------|-------------|
| AI provider keys / Ollama URL | Optional network / device summaries — see backend `.env` examples |

Detection does **not** require an LLM.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Dashboard 401s | `REACT_APP_ADMIN_API_TOKEN` matches `ADMIN_API_TOKEN` |
| No alerts | detection-engine running? Kafka topic receiving agent events? |
| Empty twin graph | Agent uploading? Backend receiving alert / device state? |

---

## Related

- [DEPLOY.md](DEPLOY.md)  
- [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md)  
- [TrustEdge-Agent configuration](https://github.com/TrustEdgeOrg/TrustEdge-Agent/blob/main/docs/configuration.md)  
- [TrustEdge-Agent-API configuration](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API/blob/main/docs/configuration.md)  
