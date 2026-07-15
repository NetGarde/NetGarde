from unittest.mock import patch

from app.features.devices.models.device import Device
from app.features.devices.services.device_login_geo_service import DeviceLoginGeoService
from app.features.alerts.models.alert import Alert
from app.features.vpn.models.ip_lease import IpLease
from app.features.vpn.models.ip_pool import IpPool
from app.features.vpn.models.vpn_peer import VpnPeer
from app.shared.geoip import GeoLocation


def _create_device(db_session, *, ip: str = "10.0.0.8") -> tuple[Device, VpnPeer]:
    pool = IpPool(
        name="pool-geo",
        cidr="10.0.0.0/24",
        gateway_ip="10.0.0.1",
        dns_ip="10.0.0.1",
        endpoint="vpn:51820",
        server_public_key="key-test",
    )
    db_session.add(pool)
    db_session.flush()
    peer = VpnPeer(device_id="dev-login-geo", public_key="pubkey-geo", pool_id=pool.id)
    db_session.add(peer)
    db_session.flush()
    lease = IpLease(pool_id=pool.id, peer_id=peer.id, ip=ip)
    db_session.add(lease)
    db_session.flush()
    device = Device(ip_lease_id=lease.id, source="vpn_enroll", hostname="laptop")
    db_session.add(device)
    db_session.commit()
    return device, peer


@patch("app.features.devices.services.device_login_geo_service.lookup_geo")
def test_record_vpn_enroll_stores_geo_and_alerts_new_country(mock_lookup, db_session, monkeypatch):
    monkeypatch.setattr("app.shared.config.settings.DEVICE_LOGIN_GEO_ENABLED", True)
    monkeypatch.setattr("app.shared.config.settings.DEVICE_LOGIN_GEO_ALERT_ENABLED", True)
    mock_lookup.return_value = GeoLocation(
        country_code="IL",
        country_name="Israel",
        region_name="Tel Aviv District",
        city="Tel Aviv",
    )

    device, peer = _create_device(db_session)
    svc = DeviceLoginGeoService(db_session)
    svc.record_vpn_enroll(
        device_id=device.id,
        peer_id=peer.id,
        connect_ip="8.8.4.4",
    )
    db_session.commit()

    read = svc.get_device_login_geo(device.id)
    assert read.latest is not None
    assert read.latest.country_code == "IL"
    assert read.latest.public_ip == "8.8.4.4"

    alerts = db_session.query(Alert).filter(Alert.alert_type == "new_vpn_login_country").all()
    assert len(alerts) == 1


@patch("app.features.devices.services.device_login_geo_service.lookup_geo")
def test_record_vpn_enroll_no_duplicate_alert_same_country(mock_lookup, db_session, monkeypatch):
    monkeypatch.setattr("app.shared.config.settings.DEVICE_LOGIN_GEO_ENABLED", True)
    monkeypatch.setattr("app.shared.config.settings.DEVICE_LOGIN_GEO_ALERT_ENABLED", True)
    mock_lookup.return_value = GeoLocation(country_code="US", country_name="United States")

    device, peer = _create_device(db_session)
    svc = DeviceLoginGeoService(db_session)
    svc.record_vpn_enroll(device_id=device.id, peer_id=peer.id, connect_ip="8.8.8.8")
    svc.record_vpn_enroll(device_id=device.id, peer_id=peer.id, connect_ip="1.1.1.1")
    db_session.commit()

    alerts = (
        db_session.query(Alert)
        .filter(Alert.alert_type == "new_vpn_login_country", Alert.device_id == device.id)
        .all()
    )
    assert len(alerts) == 1
