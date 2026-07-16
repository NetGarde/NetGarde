from tests.helpers.factories import create_behavior_block


def test_list_blocked_clients_empty(api_client):
    response = api_client.get("/devices/blocked-clients")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_blocked_clients_with_active_block(api_client, sample_device, db_session):
    create_behavior_block(db_session, sample_device, domain="malware.test")

    response = api_client.get("/devices/blocked-clients")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["device_id"] == sample_device.id
    assert body["items"][0]["latest_blocked_domain"] == "malware.test"


def test_recompute_behavior_baselines(api_client, sample_device):
    response = api_client.post("/devices/recompute-behavior-baselines")
    assert response.status_code == 200
    body = response.json()
    assert body["devices_updated"] == 0
