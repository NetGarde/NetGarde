# <img src="assets/icons/privacy.svg" width="28" height="28" align="absmiddle" alt="" /> CloudWatch logging (TrustEdge EC2)

TrustEdge ships **structured JSON** operational logs to stdout. On EC2, the **CloudWatch Agent** forwards Docker and systemd logs to CloudWatch Logs.

See also: [ENV_SETUP.md](ENV_SETUP.md) (`LOG_JSON`, `LOG_LEVEL`) · [docs index](README.md)

Detection alerts and device state live in PostgreSQL / the dashboard — they are not CloudWatch application logs.

## Log sources

| Log group | Source | Retention |
|-----------|--------|-----------|
| `/trustedge/prod/backend` | Docker `trustedge-api` | **30 days** |
| `/trustedge/prod/wg-agent` | systemd `trustedge-wg-agent` | **14 days** |

Legacy log groups for `dns-sync` / `log-watcher` may still exist in AWS but are unused after DNS removal.

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

## One-time EC2 setup

**IAM:** EC2 instance role needs CloudWatch Logs permissions, for example:

- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `logs:DescribeLogStreams`
- `logs:PutRetentionPolicy`

**Install agent** (after deploy):

```bash
cd ~/trustedge
sudo bash scripts/ec2-setup-cloudwatch.sh
```

This installs the agent, applies [`scripts/cloudwatch/amazon-cloudwatch-agent.json`](../scripts/cloudwatch/amazon-cloudwatch-agent.json), sets retention, and enables `LOG_JSON` in `backend.env`.

## CloudWatch Logs Insights examples

**Recent errors:**

```
fields @timestamp, level, service, event, message, request_id
| filter level = "ERROR"
| sort @timestamp desc
| limit 50
```

**Enroll issues:**

```
fields @timestamp, message, event, reason, request_id
| filter event like /enroll/
| sort @timestamp desc
```

**Slow API requests (>500ms):**

```
fields @timestamp, http_method, http_path, status_code, duration_ms
| filter event = "http_request" and duration_ms > 500
| sort duration_ms desc
```

## What not to log

- Tokens, secrets, device tokens, full enroll payloads
- Full alert / event payloads that may contain sensitive endpoint detail
