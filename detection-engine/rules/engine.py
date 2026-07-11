from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from rules.state import StateStore

TYPE_NETWORK_SUMMARY = "network_summary"
TYPE_ACTION_SUMMARY = "action_summary"
PRESENCE_ACTIVE = "active"


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


def _parse_ts(raw: Any) -> str:
    if isinstance(raw, str) and raw:
        return raw
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _payload_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def evaluate_event(event: dict[str, Any], store: StateStore) -> list[TwinAlert]:
    device_id = _payload_str(event.get("device_id"))
    if not device_id:
        return []

    event_type = _payload_str(event.get("type"))
    payload = event.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    state = store.get(device_id)
    alerts: list[TwinAlert] = []
    ts = _parse_ts(event.get("ts"))
    event_id = _payload_str(event.get("event_id")) or None

    if event_type == TYPE_ACTION_SUMMARY:
        presence = _payload_str(payload.get("presence"))
        if presence:
            state.presence = presence
        return alerts

    if event_type != TYPE_NETWORK_SUMMARY:
        return alerts

    network_type = _payload_str(payload.get("network_type"))
    public_ip = _payload_str(payload.get("public_ip"))
    network_changed = False

    if network_type and state.network_type and network_type != state.network_type:
        alerts.append(
            TwinAlert(
                timestamp=ts,
                trusttwin_device_id=device_id,
                event_id=event_id,
                event_type=event_type,
                alert_type="network_type_change",
                severity="medium",
                message=f"Network type changed from {state.network_type} to {network_type}",
                detail=json.dumps({"from": state.network_type, "to": network_type}),
            )
        )
        network_changed = True

    if public_ip and state.public_ip and public_ip != state.public_ip:
        alerts.append(
            TwinAlert(
                timestamp=ts,
                trusttwin_device_id=device_id,
                event_id=event_id,
                event_type=event_type,
                alert_type="new_public_ip",
                severity="high",
                message=f"Public IP changed from {state.public_ip} to {public_ip}",
                detail=json.dumps({"from": state.public_ip, "to": public_ip}),
            )
        )
        network_changed = True

    if network_changed and state.presence == PRESENCE_ACTIVE:
        alerts.append(
            TwinAlert(
                timestamp=ts,
                trusttwin_device_id=device_id,
                event_id=event_id,
                event_type=event_type,
                alert_type="network_change_while_active",
                severity="medium",
                message="Network changed while user presence is active",
                detail=json.dumps({"presence": state.presence}),
            )
        )

    if network_type:
        state.network_type = network_type
    if public_ip:
        state.public_ip = public_ip

    return alerts
