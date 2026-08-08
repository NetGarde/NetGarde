from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from log_config import setup_logging, structured_extra

LOG = setup_logging(service=os.getenv("LOG_SERVICE", "detection-engine"), logger_name=__name__)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def post_alerts(alerts: list[dict[str, Any]]) -> bool:
    if not alerts:
        return True
    base = _env("API_BASE_URL", "http://backend:8000").rstrip("/")
    token = _env("TRUSTEDGE_INGEST_TOKEN", "")
    url = f"{base}/security/alerts/ingest"
    body = json.dumps(alerts).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            LOG.info(
                "alerts ingested",
                extra=structured_extra("alerts_posted", created=payload.get("created", 0)),
            )
            return True
    except urllib.error.HTTPError as exc:
        LOG.error(
            "alert ingest failed",
            extra=structured_extra("alerts_post_failed", status=exc.code, body=exc.read()[:500]),
        )
        return False
    except Exception as exc:
        LOG.exception("alert ingest error: %s", exc)
        return False


def observe_behavior(
    *,
    device_id: str,
    behavior_kind: str,
    behavior_key: str,
    alert_type: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Record a behavior observation; returns suppress decision or None on failure/disabled."""
    if _env("TRUSTEDGE_BEHAVIOR_BASELINE", "1").lower() in ("0", "false", "no", "off"):
        return None
    base = _env("API_BASE_URL", "http://backend:8000").rstrip("/")
    token = _env("TRUSTEDGE_INGEST_TOKEN", "")
    url = f"{base}/internal/behaviors/observe"
    payload = {
        "device_id": device_id,
        "behavior_kind": behavior_kind,
        "behavior_key": behavior_key,
        "alert_type": alert_type,
        "meta": meta or {},
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            LOG.info(
                "behavior observed",
                extra=structured_extra(
                    "behavior_observed",
                    device_id=device_id,
                    behavior_kind=behavior_kind,
                    behavior_key=behavior_key,
                    count=result.get("count"),
                    action=result.get("action"),
                ),
            )
            return result
    except urllib.error.HTTPError as exc:
        LOG.error(
            "behavior observe failed",
            extra=structured_extra(
                "behavior_observe_failed",
                status=exc.code,
                body=exc.read()[:500],
            ),
        )
        return None
    except Exception as exc:
        LOG.exception("behavior observe error: %s", exc)
        return None
