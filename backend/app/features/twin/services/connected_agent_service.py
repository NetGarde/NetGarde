from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.features.twin.schemas.connected_agent import ConnectedAgentListResponse, ConnectedAgentRead
from app.features.twin.services import trusttwin_store


class ConnectedAgentService:
    def list_connected_agents(self, *, connected_within_sec: int = 300) -> ConnectedAgentListResponse:
        window = max(30, min(int(connected_within_sec), 86400))
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window)

        items: list[ConnectedAgentRead] = []
        for row in trusttwin_store.list_latest():
            details = row.client_details or {}
            network = row.network_summary or {}
            action = row.action_summary or {}
            connected = bool(row.last_seen_at and row.last_seen_at >= cutoff)

            items.append(
                ConnectedAgentRead(
                    device_id=row.device_id,
                    hostname=(details.get("hostname") or None),
                    os=(details.get("os") or None),
                    os_version=(details.get("os_version") or None),
                    arch=(details.get("arch") or None),
                    agent_version=(details.get("agent_version") or None),
                    status=(details.get("status") or None),
                    public_ip=(network.get("public_ip") or None),
                    network_type=(network.get("network_type") or None),
                    listening_count=network.get("listening_count"),
                    established_count=network.get("established_count"),
                    presence=(action.get("presence") or None),
                    idle_sec=action.get("idle_sec"),
                    app_switches=action.get("app_switches"),
                    last_seen_at=row.last_seen_at,
                    connected=connected,
                )
            )

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

