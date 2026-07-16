from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from app.features.devices.models.device import Device
from app.features.devices.schemas.device import DeviceCreate, DeviceUpdate


class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: DeviceCreate) -> Device:
        device = Device(**data.model_dump())
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_all(self) -> List[Device]:
        return self.db.query(Device).order_by(Device.hostname.asc().nullslast(), Device.id.asc()).all()

    def get_by_id(self, device_id: int) -> Optional[Device]:
        return self.db.query(Device).filter(Device.id == device_id).first()

    def get_by_external_id(self, external_id: str) -> Optional[Device]:
        return (
            self.db.query(Device)
            .filter(Device.external_id == external_id.strip())
            .first()
        )

    def get_by_mac_address(self, mac_address: str) -> Optional[Device]:
        return (
            self.db.query(Device)
            .filter(Device.mac_address == mac_address.lower())
            .first()
        )

    def update(self, device_id: int, data: DeviceUpdate) -> Optional[Device]:
        device = self.get_by_id(device_id)
        if not device:
            return None

        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(device, key, value)

        device.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete(self, device_id: int) -> bool:
        device = self.get_by_id(device_id)
        if not device:
            return False

        self.db.delete(device)
        self.db.commit()
        return True

    def touch_last_seen(self, device_id: int) -> None:
        device = self.get_by_id(device_id)
        if not device:
            return
        now = datetime.now(timezone.utc)
        device.last_seen_at = now
        device.updated_at = now
        self.db.commit()
