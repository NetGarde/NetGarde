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


def test_get_connected_agent_and_events(api_client):
    now = datetime.now(timezone.utc)
    with patch("app.features.twin.services.trusttwin_store.get_latest") as mock_get:
        with patch("app.features.twin.services.trusttwin_store.list_recent_events") as mock_events:
            from app.features.twin.services.trusttwin_store import TwinDeviceLatest

            mock_get.return_value = TwinDeviceLatest(
                device_id="dev_one",
                last_seen_at=now - timedelta(seconds=10),
                client_details={"hostname": "mbp", "os": "darwin"},
                network_summary={"public_ip": "1.2.3.4", "listening_count": 8},
                action_summary={"presence": "active", "idle_sec": 0},
            )
            mock_events.return_value = [
                {
                    "event_id": "evt_1",
                    "device_id": "dev_one",
                    "type": "network_summary",
                    "ts": now.isoformat().replace("+00:00", "Z"),
                    "payload": {"public_ip": "1.2.3.4"},
                }
            ]

            detail = api_client.get("/security/agents/dev_one")
            events = api_client.get("/security/agents/dev_one/events?limit=20")

    assert detail.status_code == 200
    body = detail.json()
    assert body["device_id"] == "dev_one"
    assert body["hostname"] == "mbp"
    assert body["connected"] is True
    assert body["network_summary"]["public_ip"] == "1.2.3.4"

    assert events.status_code == 200
    event_body = events.json()
    assert event_body["device_id"] == "dev_one"
    assert event_body["total"] == 1
    assert event_body["items"][0]["type"] == "network_summary"

    with patch("app.features.twin.services.trusttwin_store.get_latest", return_value=None):
        missing = api_client.get("/security/agents/missing")
    assert missing.status_code == 404

