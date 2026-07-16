from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Windowed / threshold rules re-match on every subsequent event while the
# condition holds. Fingerprint by time bucket so we emit once per cooldown.
COOLDOWN_SECONDS: dict[str, int] = {
    "event_burst": 5 * 60,
    "process_burst": 2 * 60,
    "rapid_public_ip_changes": 15 * 60,
    "double_ip_change_10m": 10 * 60,
    "network_type_flapping": 10 * 60,
    "network_flap_5m": 5 * 60,
    "repeated_network_summary": 10 * 60,
    "established_count_spike": 15 * 60,
    "listening_port_spike": 15 * 60,
    "foreground_connections_spike": 15 * 60,
    "high_listening_while_active": 5 * 60,
    "network_change_while_active": 5 * 60,
    "ip_change_while_idle": 5 * 60,
    "active_ip_churn": 30 * 60,
    "stale_client_details": 20 * 60,
    "missing_network_telemetry": 30 * 60,
    "idle_with_network_activity": 15 * 60,
}


def _parse_ts(raw: str) -> datetime:
    text = (raw or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def alert_fingerprint(
    *,
    device_id: str,
    alert_type: str,
    timestamp: str,
    event_id: str | None = None,
) -> str:
    """Stable identity for dedupe / cooldown.

    Point-in-time alerts (e.g. shell→curl) key on event_id.
    Windowed alerts key on a time bucket matching the rule window.
    """
    cooldown = COOLDOWN_SECONDS.get(alert_type)
    if cooldown:
        epoch = int(_parse_ts(timestamp).timestamp())
        bucket = epoch // cooldown
        anchor = f"bucket:{bucket}"
    else:
        anchor = event_id or timestamp
    raw = f"{device_id}|{alert_type}|{anchor}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


@dataclass
class SecurityAlert:
    timestamp: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    event_id: str | None = None
    event_type: str | None = None
    detail: str | None = None

    def fingerprint(self) -> str:
        return alert_fingerprint(
            device_id=self.device_id,
            alert_type=self.alert_type,
            timestamp=self.timestamp,
            event_id=self.event_id,
        )

    def to_api(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "fingerprint": self.fingerprint(),
        }
        if self.event_id:
            out["event_id"] = self.event_id
        if self.event_type:
            out["event_type"] = self.event_type
        if self.detail:
            out["detail"] = self.detail
        return out
