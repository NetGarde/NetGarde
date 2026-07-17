from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rules.constants import COOLDOWN_SECONDS

__all__ = ["SecurityAlert", "alert_fingerprint"]


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
