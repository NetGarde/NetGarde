# <img src="assets/icons/privacy.svg" width="28" height="28" align="absmiddle" alt="" /> CloudWatch logging (TrustEdge EC2)

TrustEdge ships **structured JSON** operational logs to stdout. On EC2, the **CloudWatch Agent** forwards Docker logs to CloudWatch Logs.

See also: [ENV_SETUP.md](ENV_SETUP.md) (`LOG_JSON`, `LOG_LEVEL`) · [docs index](README.md)

---

## Log sources

| Log group | Source | Retention |
|-----------|--------|-----------|
| `/trustedge/prod/backend` | Docker `trustedge-api` | **30 days** |
| `/trustedge/prod/detection-engine` | Docker detection consumer | **14 days** (if configured) |

Add groups for Agent API / Redpanda if those run on the same host.

---

## Backend environment

In `/etc/trustedge/backend.env`:

```env
LOG_JSON=1
LOG_LEVEL=INFO
LOG_TO_FILE=0
LOG_SERVICE=backend
PYTHONUNBUFFERED=1
```

Each HTTP request gets an `X-Request-ID` header and `request_id` on log lines. Access lines use `event=http_request` (except `/health`).

---

## What not to log

Do **not** emit to application logs:

- Admin tokens, device tokens, enroll secrets  
- Full raw event payloads with sensitive cmdline data (prefer redaction)  

Alerts and twin graph state belong in **RDS / the dashboard**, not as high-volume debug dumps.

---

## Related

- [DEPLOY.md](DEPLOY.md)  
- [ENV_SETUP.md](ENV_SETUP.md)  
