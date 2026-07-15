from datetime import datetime, timezone

from app.features.client_behavior.schemas.behavior import (
    ClientBlockedDomainCreate,
    DeviceSecurityPolicyUpdate,
)
from app.features.client_behavior.services.client_behavior_api_service import ClientBehaviorApiService
from app.features.alerts.models.alert import Alert
from tests.helpers.factories import create_behavior_block, create_vpn_device


def test_list_blocked_clients(db_session):
    device, _ = create_vpn_device(db_session, ip="10.0.0.50")
    create_behavior_block(db_session, device, domain="evil.test")
    svc = ClientBehaviorApiService(db_session)
    result = svc.list_blocked_clients()
    assert result.total == 1
    assert result.items[0].device_id == device.id


def test_get_behavior_profile(db_session):
    device, _ = create_vpn_device(db_session, ip="10.0.0.51")
    svc = ClientBehaviorApiService(db_session)
    profile = svc.get_behavior_profile(device.id)
    assert profile.device_id == device.id
    assert profile.profile_ready is False


def test_security_policy_update(db_session):
    device, _ = create_vpn_device(db_session, ip="10.0.0.52")
    svc = ClientBehaviorApiService(db_session)
    updated = svc.update_security_policy(
        device.id,
        DeviceSecurityPolicyUpdate(auto_block_threshold=80),
    )
    assert updated.auto_block_threshold == 80


def test_create_client_block_manual(db_session):
    device, _ = create_vpn_device(db_session, ip="10.0.0.55")
    svc = ClientBehaviorApiService(db_session)
    created = svc.create_client_block(
        device.id,
        ClientBlockedDomainCreate(domain="manual.block.test"),
    )
    assert created.source == "admin_manual"
    assert created.domain == "manual.block.test"


def test_revoke_client_block(db_session):
    device, _ = create_vpn_device(db_session, ip="10.0.0.53")
    block = create_behavior_block(db_session, device, domain="revoke.test")
    svc = ClientBehaviorApiService(db_session)
    result = svc.revoke_client_block(device.id, block.id)
    assert result["revoked"] is True


def test_get_behavior_events(db_session):
    device, _ = create_vpn_device(db_session, ip="10.0.0.54")
    db_session.add(
        Alert(
            timestamp=datetime.now(timezone.utc),
            client_ip="10.0.0.54",
            device_id=device.id,
            alert_type="behavior_anomaly",
            severity="low",
            domain="evt.test",
            message="test",
        )
    )
    db_session.commit()
    svc = ClientBehaviorApiService(db_session)
    events = svc.get_behavior_events(device.id)
    assert events["total"] == 1
