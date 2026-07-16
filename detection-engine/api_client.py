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
    token = _env("DNS_INGEST_TOKEN", "")
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
                extra=structured_extra("twin_alerts_posted", created=payload.get("created", 0)),
            )
            return True
    except urllib.error.HTTPError as exc:
        LOG.error(
            "alert ingest failed",
            extra=structured_extra("twin_alerts_post_failed", status=exc.code, body=exc.read()[:500]),
        )
        return False
    except Exception as exc:
        LOG.exception("alert ingest error: %s", exc)
        return False
