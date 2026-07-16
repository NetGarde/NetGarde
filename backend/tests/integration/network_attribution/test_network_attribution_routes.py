from datetime import datetime, timezone

from app.shared.device_identity import create_device_token
from tests.helpers.factories import create_device


def _attribution_payload(device_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "device_id": device_id,
        "intervals": [
            {
                "started_at": now.isoformat(),
                "duration_sec": 30,
                "bundle_id": "us.zoom.xos",
                "app_name": "zoom.us",
            }
        ],
    }


def test_network_attribution_ingest_and_summary(
    api_client,
    db_session,
    seed_policy,
    device_token_env,
):
    device = create_device(db_session, external_id="attr-client", hostname="attr-host")
    token = create_device_token(device_id=device.external_id)

    response = api_client.post(
        "/v1/network-attribution",
        json=_attribution_payload(device.external_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["intervals_received"] == 1

    summary = api_client.get(f"/devices/{device.id}/network-attribution/summary", params={"hours": 24})
    assert summary.status_code == 200
    items = summary.json()["items"]
    assert any(i["app_slug"] == "zoom" for i in items)


def test_network_attribution_map(
    api_client,
    db_session,
    seed_policy,
    device_token_env,
):
    device = create_device(db_session, external_id="attr-map", hostname="map-host")
    token = create_device_token(device_id=device.external_id)

    api_client.post(
        "/v1/network-attribution",
        json=_attribution_payload(device.external_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    response = api_client.get("/network-attribution/map", params={"minutes": 15})
    assert response.status_code == 200
    body = response.json()
    node_types = {n["type"] for n in body["nodes"]}
    assert "device" in node_types
    assert "app" in node_types
    assert any(n.get("app_slug") == "zoom" for n in body["nodes"] if n["type"] == "app")
    assert any(e["kind"] == "foreground" for e in body["edges"])
