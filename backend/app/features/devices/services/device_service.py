from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.devices.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceRead,
)
from app.features.devices.errors.device import DeviceAlreadyExistsError, DeviceNotFoundError
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class DeviceService:
    """Implementation of IDeviceService."""

    @staticmethod
    def _to_read(device) -> DeviceRead:
        return DeviceRead.model_validate(device)

    def create_device(self, data: DeviceCreate, db: Session) -> DeviceRead:
        repository = DeviceRepository(db)
        try:
            device = repository.create(data)
            return self._to_read(device)
        except IntegrityError as exc:
            logger.warning(
                "Device already exists",
                extra=structured_extra("device_already_exists", external_id=data.external_id),
            )
            raise DeviceAlreadyExistsError(data.external_id) from exc

    def get_devices(self, db: Session) -> List[DeviceRead]:
        repository = DeviceRepository(db)
        devices = repository.get_all()
        return [self._to_read(device) for device in devices]

    def update_device(self, device_id: int, data: DeviceUpdate, db: Session) -> DeviceRead:
        repository = DeviceRepository(db)
        try:
            device = repository.update(device_id, data)
            if not device:
                raise DeviceNotFoundError(str(device_id))
            return self._to_read(device)
        except IntegrityError as exc:
            raise DeviceAlreadyExistsError(str(device_id)) from exc

    def delete_device(self, device_id: int, db: Session) -> dict:
        repository = DeviceRepository(db)
        deleted = repository.delete(device_id)
        if not deleted:
            raise DeviceNotFoundError(str(device_id))
        return {"message": "Device deleted successfully", "device_id": device_id}
