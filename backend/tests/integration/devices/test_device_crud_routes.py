from tests.helpers.factories import create_device


def test_update_device(api_client, sample_device):
    response = api_client.put(
        f"/devices/{sample_device.id}",
        json={"hostname": "renamed-host"},
    )
    assert response.status_code == 200
    assert response.json()["hostname"] == "renamed-host"


def test_delete_device(api_client, db_session):
    device = create_device(db_session, external_id="dev-to-delete", hostname="gone")
    response = api_client.delete(f"/devices/{device.id}")
    assert response.status_code == 200
    assert api_client.get("/devices").json() == []
