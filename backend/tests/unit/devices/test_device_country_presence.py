from app.features.devices.repositories.device_country_presence_repository import (
    DeviceCountryPresenceRepository,
)
from tests.helpers.factories import create_device


def test_record_batch_returns_new_countries(db_session):
    device = create_device(db_session, external_id="dev-country")
    repo = DeviceCountryPresenceRepository(db_session)

    new = repo.record_batch(device.id, {"IL": 5, "GLOBAL": 10})
    db_session.commit()

    assert "IL" in new
    assert "GLOBAL" not in new

    again = repo.record_batch(device.id, {"IL": 1, "DE": 2})
    db_session.commit()

    assert again == ["DE"]
    assert "IL" in repo.known_codes(device.id)
