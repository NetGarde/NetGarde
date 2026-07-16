import pytest
from fastapi import HTTPException

from app.features.devices.services.device_country_service import DeviceCountryService
from tests.helpers.factories import create_device, seed_country_presence


def test_get_breakdown_with_presence(db_session):
    device = create_device(db_session, external_id="dev-60")
    seed_country_presence(db_session, device, country_code="IL", count=10)
    seed_country_presence(db_session, device, country_code="US", count=5)

    svc = DeviceCountryService(db_session)
    breakdown = svc.get_breakdown(device.id, period_hours=168)

    assert breakdown.device_id == device.id
    assert breakdown.total_queries >= 15
    assert breakdown.primary_country_code in ("IL", "US")
    assert len(breakdown.countries) >= 1


def test_get_breakdown_device_not_found(db_session):
    svc = DeviceCountryService(db_session)
    with pytest.raises(HTTPException) as exc:
        svc.get_breakdown(99999)
    assert exc.value.status_code == 404


def test_list_summaries(db_session):
    device = create_device(db_session, external_id="dev-61")
    seed_country_presence(db_session, device, country_code="DE", count=7)

    svc = DeviceCountryService(db_session)
    result = svc.list_summaries(period_hours=168)

    assert result.period_hours == 168
    assert any(item.device_id == device.id for item in result.items)
