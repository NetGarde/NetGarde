from unittest.mock import patch

from app.features.devices.services.device_login_geo_service import DeviceLoginGeoService
from app.features.alerts.models.alert import Alert
from app.shared.geoip import GeoLocation
from tests.helpers.factories import create_device


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

    device = create_device(db_session, external_id="dev-login-geo", hostname="laptop")
    svc = DeviceLoginGeoService(db_session)
    svc.record_vpn_enroll(
        device_id=device.id,
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

    device = create_device(db_session, external_id="dev-login-geo-2", hostname="laptop")
    svc = DeviceLoginGeoService(db_session)
    svc.record_vpn_enroll(device_id=device.id, connect_ip="8.8.8.8")
    svc.record_vpn_enroll(device_id=device.id, connect_ip="1.1.1.1")
    db_session.commit()

    alerts = (
        db_session.query(Alert)
        .filter(Alert.alert_type == "new_vpn_login_country", Alert.device_id == device.id)
        .all()
    )
    assert len(alerts) == 1
