from datetime import datetime, timezone

from app.features.alerts.models.alert import Alert
from tests.helpers.factories import create_behavior_block


def test_behavior_profile(api_client, vpn_device, behavior_env):
    response = api_client.get(f"/devices/{vpn_device.id}/behavior-profile")
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == vpn_device.id
    assert body["profile_ready"] is False


def test_behavior_review_template(api_client, vpn_device, behavior_env):
    response = api_client.get(f"/devices/{vpn_device.id}/behavior-review")
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == vpn_device.id
    assert body["source"] == "template"
    assert "summary" in body


def test_behavior_events_empty(api_client, vpn_device):
    response = api_client.get(f"/devices/{vpn_device.id}/behavior-events")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_behavior_events_with_alert(api_client, vpn_device, db_session):
    db_session.add(
        Alert(
            timestamp=datetime.now(timezone.utc),
            client_ip="10.0.0.10",
            device_id=vpn_device.id,
            alert_type="behavior_anomaly",
            severity="medium",
            domain="suspicious.test",
            message="Unusual DNS pattern",
        )
    )
    db_session.commit()

    response = api_client.get(f"/devices/{vpn_device.id}/behavior-events")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["domain"] == "suspicious.test"


def test_security_policy_get_and_update(api_client, vpn_device):
    get_resp = api_client.get(f"/devices/{vpn_device.id}/security-policy")
    assert get_resp.status_code == 200

    put_resp = api_client.put(
        f"/devices/{vpn_device.id}/security-policy",
        json={"auto_block_enabled": True, "auto_block_threshold": 75},
    )
    assert put_resp.status_code == 200
    body = put_resp.json()
    assert body["auto_block_enabled"] is True
    assert body["auto_block_threshold"] == 75


def test_client_blocks_list_and_revoke(api_client, vpn_device, db_session):
    block = create_behavior_block(db_session, vpn_device, domain="blockme.test")

    listed = api_client.get(f"/devices/{vpn_device.id}/client-blocks")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["domain"] == "blockme.test"

    revoked = api_client.delete(f"/devices/{vpn_device.id}/client-blocks/{block.id}")
    assert revoked.status_code == 200
    assert revoked.json()["revoked"] is True


def test_create_client_block_manual(api_client, vpn_device):
    response = api_client.post(
        f"/devices/{vpn_device.id}/client-blocks",
        json={"domain": "https://Bad.Example.COM/path"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "bad.example.com"
    assert body["source"] == "admin_manual"

    listed = api_client.get(f"/devices/{vpn_device.id}/client-blocks")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_start_and_end_quarantine(api_client, vpn_device, db_session):
    start = api_client.post(
        f"/devices/{vpn_device.id}/quarantine",
        json={"hours": 2},
    )
    assert start.status_code == 200
    body = start.json()
    assert body["in_quarantine"] is True
    assert body["quarantine_expires_at"] is not None

    assignment = api_client.get(f"/devices/{vpn_device.id}/policy-assignment")
    assert assignment.status_code == 200
    assert assignment.json()["in_quarantine"] is True

    blocked = api_client.get("/devices/blocked-clients")
    assert blocked.status_code == 200
    items = blocked.json()["items"]
    assert any(i["device_id"] == vpn_device.id and i["in_quarantine"] for i in items)

    end = api_client.delete(f"/devices/{vpn_device.id}/quarantine")
    assert end.status_code == 200
    assert end.json()["in_quarantine"] is False

    assignment2 = api_client.get(f"/devices/{vpn_device.id}/policy-assignment")
    assert assignment2.json()["in_quarantine"] is False


def test_quarantine_works_without_vpn_lease(api_client, db_session):
    from tests.helpers.factories import create_device

    device = create_device(
        db_session,
        external_id="soft-quarantine",
        hostname="no-lease",
        mac_address="aa:bb:cc:dd:ee:99",
    )

    response = api_client.post(f"/devices/{device.id}/quarantine", json={"hours": 1})
    assert response.status_code == 200
    assert response.json()["in_quarantine"] is True
