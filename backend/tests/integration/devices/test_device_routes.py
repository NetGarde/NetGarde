def test_list_devices_empty(api_client):
    response = api_client.get("/devices")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_device(api_client, sample_device):
    response = api_client.get("/devices")
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 1
    assert devices[0]["id"] == sample_device.id
    assert devices[0]["external_id"] == sample_device.external_id
    assert devices[0]["hostname"] == "test-laptop"


def test_create_device_via_api(api_client, db_session):
    response = api_client.post(
        "/devices",
        json={
            "external_id": "dev-api-created",
            "hostname": "api-created",
            "mac_address": "11:22:33:44:55:66",
            "source": "manual",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_id"] == "dev-api-created"
    assert body["hostname"] == "api-created"
