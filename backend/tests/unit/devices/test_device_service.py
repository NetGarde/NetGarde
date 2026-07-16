import pytest

from app.features.devices.errors.device import DeviceAlreadyExistsError, DeviceNotFoundError
from app.features.devices.schemas.device import DeviceCreate, DeviceUpdate
from app.features.devices.services.device_service import DeviceService
from tests.helpers.factories import create_device


def test_create_device(db_session):
    svc = DeviceService()
    created = svc.create_device(
        DeviceCreate(external_id="dev-new", hostname="new-host", source="manual"),
        db_session,
    )
    assert created.external_id == "dev-new"
    assert created.hostname == "new-host"


def test_create_device_duplicate_external_id(db_session):
    device = create_device(db_session, external_id="dev-dup")
    svc = DeviceService()
    with pytest.raises(DeviceAlreadyExistsError):
        svc.create_device(
            DeviceCreate(external_id=device.external_id, hostname="dup"),
            db_session,
        )


def test_get_devices(db_session):
    create_device(db_session, external_id="dev-listed", hostname="listed")
    svc = DeviceService()
    devices = svc.get_devices(db_session)
    assert len(devices) == 1
    assert devices[0].hostname == "listed"


def test_update_device(db_session):
    device = create_device(db_session, external_id="dev-33")
    svc = DeviceService()
    updated = svc.update_device(device.id, DeviceUpdate(hostname="renamed"), db_session)
    assert updated.hostname == "renamed"


def test_update_device_not_found(db_session):
    svc = DeviceService()
    with pytest.raises(DeviceNotFoundError):
        svc.update_device(999, DeviceUpdate(hostname="missing"), db_session)


def test_delete_device(db_session):
    device = create_device(db_session, external_id="dev-34")
    svc = DeviceService()
    result = svc.delete_device(device.id, db_session)
    assert result["device_id"] == device.id
    assert svc.get_devices(db_session) == []
