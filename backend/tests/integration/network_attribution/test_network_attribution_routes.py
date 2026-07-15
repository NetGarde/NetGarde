from datetime import datetime, timezone


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
    enroll_env,
    seed_policy,
    mock_apply_peer_on_host,
    mock_record_vpn_enroll,
    enroll_device,
):
    enroll = enroll_device(device_id="attr-client", public_key="attrKey=")
    assert enroll.status_code == 200
    body = enroll.json()
    token = body["device_token"]
    client_ip = body["address"].split("/")[0]

    response = api_client.post(
        "/v1/network-attribution",
        json=_attribution_payload("attr-client"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["intervals_received"] == 1

    devices = api_client.get("/devices").json()
    device_id = next(d["id"] for d in devices if d.get("client_ip") == client_ip)

    summary = api_client.get(f"/devices/{device_id}/network-attribution/summary", params={"hours": 24})
    assert summary.status_code == 200
    items = summary.json()["items"]
    assert any(i["app_slug"] == "zoom" for i in items)


def test_network_attribution_map(
    api_client,
    enroll_env,
    seed_policy,
    mock_apply_peer_on_host,
    mock_record_vpn_enroll,
    enroll_device,
):
    enroll = enroll_device(device_id="attr-map", public_key="attrMapKey=")
    token = enroll.json()["device_token"]

    api_client.post(
        "/v1/network-attribution",
        json=_attribution_payload("attr-map"),
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
