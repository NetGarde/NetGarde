from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from log_config import setup_logging, structured_extra
from recent_alerts import list_alerts
from rules.metrics import METRICS

LOG = setup_logging(service=os.getenv("LOG_SERVICE", "detection-engine"), logger_name=__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/metrics":
            snap = METRICS.snapshot()
            self._json(
                200,
                {
                    "events": snap.events,
                    "rules_selected": snap.rules_selected,
                    "rules_gated": snap.rules_gated,
                    "rules_run": snap.rules_run,
                    "alerts": snap.alerts,
                    "avg_eval_ms": round(snap.avg_eval_ms, 4),
                },
            )
            return
        if parsed.path != "/alerts":
            self._json(404, {"detail": "not found"})
            return

        qs = parse_qs(parsed.query)
        page = _query_int(qs, "page", 1, min_value=1)
        page_size = _query_int(qs, "page_size", 20, min_value=1, max_value=100)
        alert_type = _query_str(qs, "alert_type")
        device_id = _query_str(qs, "device_id")
        severity = _query_str(qs, "severity")
        body = list_alerts(
            page=page,
            page_size=page_size,
            alert_type=alert_type,
            device_id=device_id,
            severity=severity,
        )
        self._json(200, body)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _query_str(qs: dict, key: str) -> Optional[str]:
    vals = qs.get(key)
    if not vals:
        return None
    text = (vals[0] or "").strip()
    return text or None


def _query_int(
    qs: dict,
    key: str,
    default: int,
    *,
    min_value: int,
    max_value: Optional[int] = None,
) -> int:
    vals = qs.get(key)
    if not vals:
        return default
    try:
        value = int(vals[0])
    except (TypeError, ValueError):
        return default
    if value < min_value:
        return min_value
    if max_value is not None and value > max_value:
        return max_value
    return value


def serve_forever() -> None:
    host = os.getenv("ALERT_API_HOST", "0.0.0.0")
    port = _env_int("ALERT_API_PORT", 9090)
    server = ThreadingHTTPServer((host, port), _Handler)
    LOG.info(
        "alert api listening",
        extra=structured_extra("alert_api_ready", host=host, port=port),
    )
    server.serve_forever()
