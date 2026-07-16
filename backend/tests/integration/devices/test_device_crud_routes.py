from tests.helpers.factories import create_device


def test_update_device(api_client, sample_device):
    response = api_client.put(
        f"/devices/{sample_device.id}",
        json={"hostname": "renamed-host"},
    )
    assert response.status_code == 200
    assert response.json()["hostname"] == "renamed-host"


def test_delete_device(api_client, db_session):
    device = create_device(db_session, external_id="dev-99")
    response = api_client.delete(f"/devices/{device.id}")
    assert response.status_code == 200
    assert response.json()["device_id"] == device.id
    listed = api_client.get("/devices").json()
    assert all(d["id"] != device.id for d in listed)


def test_get_policy_assignment(api_client, seed_policy, sample_device):
    api_client.put(
        f"/devices/{sample_device.id}/policy-assignment",
        json={"policy_profile_slug": "teen"},
    )
    response = api_client.get(f"/devices/{sample_device.id}/policy-assignment")
    assert response.status_code == 200
    body = response.json()
    assert body["policy_profile_slug"] == "teen"
