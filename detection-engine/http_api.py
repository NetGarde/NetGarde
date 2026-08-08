from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from log_config import setup_logging, structured_extra
from recent_alerts import list_alerts
from baseline_view import clear_device, snapshot_device
from ai_activity import view as ai_activity_view
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
                    "hits_rule": snap.hits_rule,
                    "hits_behavioral": snap.hits_behavioral,
                    "hits_threat_intel": snap.hits_threat_intel,
                    "hits_ai_activity": snap.hits_ai_activity,
                    "scored_events": snap.scored_events,
                },
            )
            return
        if parsed.path == "/baseline":
            qs = parse_qs(parsed.query)
            device_id = _query_str(qs, "device_id")
            if not device_id:
                self._json(400, {"detail": "device_id is required"})
                return
            limit = _query_int(qs, "limit", 100, min_value=1, max_value=500)
            self._json(200, snapshot_device(device_id, limit=limit))
            return
        if parsed.path == "/ai_activity/sessions":
            qs = parse_qs(parsed.query)
            device_id = _query_str(qs, "device_id")
            if not device_id:
                self._json(400, {"detail": "device_id is required"})
                return
            limit = _query_int(qs, "limit", 50, min_value=1, max_value=200)
            include_closed = (_query_str(qs, "include_closed") or "1").lower() not in (
                "0",
                "false",
                "no",
            )
            self._json(
                200,
                ai_activity_view.list_sessions(
                    device_id, limit=limit, include_closed=include_closed
                ),
            )
            return
        if parsed.path.startswith("/ai_activity/sessions/"):
            rest = parsed.path[len("/ai_activity/sessions/") :].strip("/")
            if not rest:
                self._json(404, {"detail": "not found"})
                return
            parts = rest.split("/")
            session_id = parts[0]
            if len(parts) == 1:
                body = ai_activity_view.get_session(session_id)
                if body is None:
                    self._json(404, {"detail": "session not found"})
                    return
                self._json(200, body)
                return
            if len(parts) == 2 and parts[1] == "graph":
                body = ai_activity_view.get_session_graph(session_id)
                if body is None:
                    self._json(404, {"detail": "session not found"})
                    return
                self._json(200, body)
                return
            if len(parts) == 2 and parts[1] == "timeline":
                qs = parse_qs(parsed.query)
                limit = _query_int(qs, "limit", 200, min_value=1, max_value=1000)
                body = ai_activity_view.get_session_timeline(session_id, limit=limit)
                if body is None:
                    self._json(404, {"detail": "session not found"})
                    return
                self._json(200, body)
                return
            if len(parts) == 2 and parts[1] == "chain":
                body = ai_activity_view.get_session_chain(session_id)
                if body is None:
                    self._json(404, {"detail": "session not found"})
                    return
                self._json(200, body)
                return
            self._json(404, {"detail": "not found"})
            return
        if parsed.path.startswith("/ai_activity/process/"):
            process_id = parsed.path[len("/ai_activity/process/") :].strip("/")
            if not process_id:
                self._json(400, {"detail": "process_id is required"})
                return
            body = ai_activity_view.lookup_process(process_id)
            if body is None:
                self._json(404, {"detail": "process not in any AI session"})
                return
            self._json(200, body)
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

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/baseline":
            self._json(404, {"detail": "not found"})
            return
        qs = parse_qs(parsed.query)
        device_id = _query_str(qs, "device_id")
        if not device_id:
            self._json(400, {"detail": "device_id is required"})
            return
        self._json(200, clear_device(device_id))

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
