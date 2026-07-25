from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.features.twin.schemas.connected_agent import (
    AgentEventListResponse,
    AgentEventRead,
    ConnectedAgentListResponse,
    ConnectedAgentRead,
)
from app.features.twin.services import trusttwin_store


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _connected_agent_from_latest(
    row: trusttwin_store.TwinDeviceLatest,
    *,
    cutoff: datetime,
) -> ConnectedAgentRead:
    details = row.client_details or {}
    network = row.network_summary or {}
    action = row.action_summary or {}
    connected = bool(row.last_seen_at and row.last_seen_at >= cutoff)
    return ConnectedAgentRead(
        device_id=row.device_id,
        hostname=(details.get("hostname") or None),
        os=(details.get("os") or None),
        os_version=(details.get("os_version") or None),
        arch=(details.get("arch") or None),
        agent_version=(details.get("agent_version") or None),
        status=(details.get("status") or None),
        public_ip=(network.get("public_ip") or None),
        network_type=(network.get("network_type") or None),
        listening_count=_as_int(network.get("listening_count")),
        established_count=_as_int(network.get("established_count")),
        presence=(action.get("presence") or None),
        idle_sec=_as_int(action.get("idle_sec")),
        app_switches=_as_int(action.get("app_switches")),
        last_seen_at=row.last_seen_at,
        connected=connected,
        client_details=details,
        network_summary=network,
        action_summary=action,
    )


class ConnectedAgentService:
    def list_connected_agents(self, *, connected_within_sec: int = 300) -> ConnectedAgentListResponse:
        window = max(30, min(int(connected_within_sec), 86400))
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window)

        items: list[ConnectedAgentRead] = [
            _connected_agent_from_latest(row, cutoff=cutoff) for row in trusttwin_store.list_latest()
        ]

        items.sort(
            key=lambda x: (
                0 if x.connected else 1,
                -(x.last_seen_at.timestamp()) if x.last_seen_at else float("-inf"),
            )
        )
        return ConnectedAgentListResponse(
            items=items,
            total=len(items),
            connected_within_sec=window,
        )

    def get_connected_agent(
        self,
        device_id: str,
        *,
        connected_within_sec: int = 300,
    ) -> ConnectedAgentRead | None:
        row = trusttwin_store.get_latest(device_id.strip())
        if row is None:
            return None
        window = max(30, min(int(connected_within_sec), 86400))
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window)
        return _connected_agent_from_latest(row, cutoff=cutoff)

    def list_device_events(self, device_id: str, *, limit: int = 50) -> AgentEventListResponse:
        device_id = device_id.strip()
        raw_events = trusttwin_store.list_recent_events(device_id, limit=limit)
        items: list[AgentEventRead] = []
        for event in raw_events:
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            items.append(
                AgentEventRead(
                    event_id=str(event.get("event_id") or ""),
                    device_id=str(event.get("device_id") or device_id),
                    type=str(event.get("type") or ""),
                    ts=str(event.get("ts") or "") or None,
                    payload=payload,
                )
            )
        return AgentEventListResponse(items=items, total=len(items), device_id=device_id)

