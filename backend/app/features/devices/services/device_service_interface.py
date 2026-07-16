from typing import Protocol, List
from app.features.devices.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceRead,
)
from sqlalchemy.orm import Session


class IDeviceService(Protocol):
    def create_device(self, data: DeviceCreate, db: Session) -> DeviceRead:
        ...

    def get_devices(self, db: Session) -> List[DeviceRead]:
        ...

    def update_device(self, device_id: int, data: DeviceUpdate, db: Session) -> DeviceRead:
        ...

    def delete_device(self, device_id: int, db: Session) -> dict:
        ...
