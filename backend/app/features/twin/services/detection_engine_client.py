from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from app.features.twin.schemas.security_alert import SecurityAlertListResponse
from app.features.twin.schemas.device_baseline import DeviceBaselineResponse
from app.shared.config import settings
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


def fetch_security_alerts(
    *,
    page: int = 1,
    page_size: int = 50,
    alert_type: Optional[str] = None,
    device_id: Optional[str] = None,
    severity: Optional[str] = None,
) -> SecurityAlertListResponse:
    base = settings.DETECTION_ENGINE_URL.strip().rstrip("/")
    if not base:
        raise RuntimeError("DETECTION_ENGINE_URL is not configured")

    params: dict[str, str] = {
        "page": str(page),
        "page_size": str(page_size),
    }
    if alert_type:
        params["alert_type"] = alert_type
    if device_id:
        params["device_id"] = device_id
    if severity:
        params["severity"] = severity
    url = f"{base}/alerts?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read()[:500]
        logger.error("detection-engine alerts fetch failed: %s %s", exc.code, body)
        raise
    except Exception as exc:
        logger.error("detection-engine alerts fetch error: %s", exc)
        raise

    return SecurityAlertListResponse.model_validate(payload)


def fetch_device_baseline(*, device_id: str, limit: int = 100) -> DeviceBaselineResponse:
    base = settings.DETECTION_ENGINE_URL.strip().rstrip("/")
    if not base:
        raise RuntimeError("DETECTION_ENGINE_URL is not configured")

    params = {
        "device_id": device_id.strip(),
        "limit": str(limit),
    }
    url = f"{base}/baseline?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read()[:500]
        logger.error("detection-engine baseline fetch failed: %s %s", exc.code, body)
        raise
    except Exception as exc:
        logger.error("detection-engine baseline fetch error: %s", exc)
        raise

    return DeviceBaselineResponse.model_validate(payload)
