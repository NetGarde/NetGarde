from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from app.features.twin.schemas.security_alert import SecurityAlertListResponse
from app.features.twin.schemas.device_baseline import (
    DeviceBaselineClearResponse,
    DeviceBaselineResponse,
)
from app.features.twin.schemas.ai_activity import (
    AiProcessLookupResponse,
    AiSessionChainResponse,
    AiSessionDetailResponse,
    AiSessionGraphResponse,
    AiSessionListResponse,
    AiSessionTimelineResponse,
)
from app.shared.config import settings
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


def _engine_base() -> str:
    base = settings.DETECTION_ENGINE_URL.strip().rstrip("/")
    if not base:
        raise RuntimeError("DETECTION_ENGINE_URL is not configured")
    return base


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read()[:500]
        logger.error("detection-engine request failed: %s %s %s", url, exc.code, body)
        raise
    except Exception as exc:
        logger.error("detection-engine request error: %s %s", url, exc)
        raise


def fetch_security_alerts(
    *,
    page: int = 1,
    page_size: int = 50,
    alert_type: Optional[str] = None,
    device_id: Optional[str] = None,
    severity: Optional[str] = None,
) -> SecurityAlertListResponse:
    base = _engine_base()

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
    payload = _get_json(url)
    return SecurityAlertListResponse.model_validate(payload)


def fetch_device_baseline(*, device_id: str, limit: int = 100) -> DeviceBaselineResponse:
    base = _engine_base()

    params = {
        "device_id": device_id.strip(),
        "limit": str(limit),
    }
    url = f"{base}/baseline?{urllib.parse.urlencode(params)}"
    payload = _get_json(url)
    return DeviceBaselineResponse.model_validate(payload)


def clear_device_baseline(*, device_id: str) -> DeviceBaselineClearResponse:
    base = _engine_base()

    params = {"device_id": device_id.strip()}
    url = f"{base}/baseline?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read()[:500]
        logger.error("detection-engine baseline clear failed: %s %s", exc.code, body)
        raise
    except Exception as exc:
        logger.error("detection-engine baseline clear error: %s", exc)
        raise

    return DeviceBaselineClearResponse.model_validate(payload)


def fetch_ai_sessions(
    *,
    device_id: str,
    limit: int = 50,
    include_closed: bool = True,
) -> AiSessionListResponse:
    base = _engine_base()
    params = {
        "device_id": device_id.strip(),
        "limit": str(limit),
        "include_closed": "1" if include_closed else "0",
    }
    url = f"{base}/ai_activity/sessions?{urllib.parse.urlencode(params)}"
    return AiSessionListResponse.model_validate(_get_json(url))


def fetch_ai_session(session_id: str) -> AiSessionDetailResponse:
    base = _engine_base()
    sid = urllib.parse.quote(session_id.strip(), safe="")
    url = f"{base}/ai_activity/sessions/{sid}"
    return AiSessionDetailResponse.model_validate(_get_json(url))


def fetch_ai_session_graph(session_id: str) -> AiSessionGraphResponse:
    base = _engine_base()
    sid = urllib.parse.quote(session_id.strip(), safe="")
    url = f"{base}/ai_activity/sessions/{sid}/graph"
    return AiSessionGraphResponse.model_validate(_get_json(url))


def fetch_ai_session_timeline(session_id: str, *, limit: int = 200) -> AiSessionTimelineResponse:
    base = _engine_base()
    sid = urllib.parse.quote(session_id.strip(), safe="")
    params = {"limit": str(limit)}
    url = f"{base}/ai_activity/sessions/{sid}/timeline?{urllib.parse.urlencode(params)}"
    return AiSessionTimelineResponse.model_validate(_get_json(url))


def fetch_ai_session_chain(session_id: str) -> AiSessionChainResponse:
    base = _engine_base()
    sid = urllib.parse.quote(session_id.strip(), safe="")
    url = f"{base}/ai_activity/sessions/{sid}/chain"
    return AiSessionChainResponse.model_validate(_get_json(url))


def fetch_ai_process_lookup(process_id: str) -> AiProcessLookupResponse:
    base = _engine_base()
    pid = urllib.parse.quote(process_id.strip(), safe="")
    url = f"{base}/ai_activity/process/{pid}"
    return AiProcessLookupResponse.model_validate(_get_json(url))
