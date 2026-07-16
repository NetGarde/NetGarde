from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def test_list_connected_agents(api_client):
    now = datetime.now(timezone.utc)
    with patch("app.features.twin.services.trusttwin_store.list_latest") as mock_latest:
        from app.features.twin.services.trusttwin_store import TwinDeviceLatest

        mock_latest.return_value = [
            TwinDeviceLatest(
                device_id="dev_connected",
                last_seen_at=now - timedelta(seconds=30),
                client_details={"hostname": "mbp-1", "os": "macOS", "agent_version": "1.2.3"},
                network_summary={"public_ip": "203.0.113.10", "network_type": "wifi"},
                action_summary={"presence": "active"},
            ),
            TwinDeviceLatest(
                device_id="dev_idle",
                last_seen_at=now - timedelta(minutes=20),
                client_details={"hostname": "srv-1", "os": "Linux"},
                network_summary={"public_ip": "198.51.100.10"},
                action_summary={},
            ),
        ]

        response = api_client.get("/security/agents?connected_within_sec=300")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["connected_within_sec"] == 300
    assert body["items"][0]["device_id"] == "dev_connected"
    assert body["items"][0]["connected"] is True
    assert body["items"][1]["device_id"] == "dev_idle"
    assert body["items"][1]["connected"] is False

