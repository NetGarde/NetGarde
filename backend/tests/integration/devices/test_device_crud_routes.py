from tests.helpers.factories import create_vpn_device, seed_country_presence


def test_update_device(api_client, vpn_device):
    response = api_client.put(
        f"/devices/{vpn_device.id}",
        json={"hostname": "renamed-host"},
    )
    assert response.status_code == 200
    assert response.json()["hostname"] == "renamed-host"


def test_delete_device(api_client, db_session):
    device, _lease = create_vpn_device(db_session, device_id="dev-99")
    response = api_client.delete(f"/devices/{device.id}")
    assert response.status_code == 200
    assert response.json()["device_id"] == device.id
    listed = api_client.get("/devices").json()
    assert all(d["id"] != device.id for d in listed)


def test_get_policy_assignment(api_client, seed_policy, vpn_device):
    api_client.put(
        f"/devices/{vpn_device.id}/policy-assignment",
        json={"policy_profile_slug": "teen"},
    )
    response = api_client.get(f"/devices/{vpn_device.id}/policy-assignment")
    assert response.status_code == 200
    body = response.json()
    assert body["policy_profile_slug"] == "teen"


def test_countries_summary(api_client, vpn_device, db_session):
    seed_country_presence(db_session, vpn_device, country_code="IL", count=12)
    response = api_client.get("/devices/countries/summary", params={"period_hours": 168})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert any(item["device_id"] == vpn_device.id for item in body["items"])


def test_device_dns_countries(api_client, vpn_device, db_session):
    seed_country_presence(db_session, vpn_device, country_code="US", count=3)
    response = api_client.get(
        f"/devices/{vpn_device.id}/dns-countries",
        params={"period_hours": 168},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == vpn_device.id
    assert body["total_queries"] >= 3


def test_device_login_location_not_found(api_client, vpn_device):
    response = api_client.get(f"/devices/{vpn_device.id}/login-location")
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == vpn_device.id
    assert body["latest"] is None
