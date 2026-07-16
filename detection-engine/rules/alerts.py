from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


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
        """Stable identity so re-evaluating the same event chain does not duplicate alerts."""
        anchor = self.event_id or self.timestamp
        raw = f"{self.device_id}|{self.alert_type}|{anchor}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

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
