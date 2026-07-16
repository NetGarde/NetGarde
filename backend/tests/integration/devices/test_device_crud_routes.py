from tests.helpers.factories import create_device, seed_country_presence


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


def test_countries_summary(api_client, sample_device, db_session):
    seed_country_presence(db_session, sample_device, country_code="IL", count=12)
    response = api_client.get("/devices/countries/summary", params={"period_hours": 168})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert any(item["device_id"] == sample_device.id for item in body["items"])


def test_device_dns_countries(api_client, sample_device, db_session):
    seed_country_presence(db_session, sample_device, country_code="US", count=3)
    response = api_client.get(
        f"/devices/{sample_device.id}/dns-countries",
        params={"period_hours": 168},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == sample_device.id
    assert body["total_queries"] >= 3


def test_device_login_location_not_found(api_client, sample_device):
    response = api_client.get(f"/devices/{sample_device.id}/login-location")
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == sample_device.id
    assert body["latest"] is None
