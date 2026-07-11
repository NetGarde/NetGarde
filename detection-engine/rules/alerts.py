from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TwinAlert:
    timestamp: str
    trusttwin_device_id: str
    alert_type: str
    severity: str
    message: str
    event_id: str | None = None
    event_type: str | None = None
    detail: str | None = None

    def to_api(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "timestamp": self.timestamp,
            "trusttwin_device_id": self.trusttwin_device_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
        }
        if self.event_id:
            out["event_id"] = self.event_id
        if self.event_type:
            out["event_type"] = self.event_type
        if self.detail:
            out["detail"] = self.detail
        return out
