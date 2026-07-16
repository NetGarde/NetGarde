from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.features.devices.models.device import Device
from app.features.policy.models.device_quarantine import DeviceQuarantine
from app.features.policy.models.policy_profile import PolicyProfile


class PolicyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_profiles(self) -> List[PolicyProfile]:
        return self.db.query(PolicyProfile).order_by(PolicyProfile.slug).all()

    def get_profile_by_id(self, profile_id: int) -> Optional[PolicyProfile]:
        return self.db.query(PolicyProfile).filter(PolicyProfile.id == profile_id).first()

    def get_profile_by_slug(self, slug: str) -> Optional[PolicyProfile]:
        return self.db.query(PolicyProfile).filter(PolicyProfile.slug == slug).first()

    def get_default_profile(self) -> Optional[PolicyProfile]:
        return self.get_profile_by_slug("teen")

    def assign_profile_to_device(self, device_id: int, profile_id: Optional[int]) -> Optional[Device]:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return None
        device.policy_profile_id = profile_id
        return device

    def get_active_quarantine(self, device_id: int) -> Optional[DeviceQuarantine]:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(DeviceQuarantine)
            .filter(
                DeviceQuarantine.device_id == device_id,
                DeviceQuarantine.ended_at.is_(None),
                DeviceQuarantine.expires_at > now,
            )
            .order_by(DeviceQuarantine.expires_at.desc())
            .first()
        )

    def start_quarantine(self, device_id: int, score: int, hours: int) -> DeviceQuarantine:
        now = datetime.now(timezone.utc)
        existing = self.get_active_quarantine(device_id)
        expires = now + timedelta(hours=hours)
        if existing:
            existing.score = score
            if existing.expires_at < expires:
                existing.expires_at = expires
            return existing
        row = DeviceQuarantine(device_id=device_id, score=score, started_at=now, expires_at=expires)
        self.db.add(row)
        self.db.flush()
        return row

    def end_expired_quarantines(self) -> int:
        now = datetime.now(timezone.utc)
        rows = (
            self.db.query(DeviceQuarantine)
            .filter(DeviceQuarantine.ended_at.is_(None), DeviceQuarantine.expires_at <= now)
            .all()
        )
        for row in rows:
            row.ended_at = now
        return len(rows)

    def end_quarantine(self, device_id: int) -> bool:
        row = self.get_active_quarantine(device_id)
        if not row:
            return False
        row.ended_at = datetime.now(timezone.utc)
        return True

    def list_active_quarantines(self) -> List[DeviceQuarantine]:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(DeviceQuarantine)
            .filter(
                DeviceQuarantine.ended_at.is_(None),
                DeviceQuarantine.expires_at > now,
            )
            .order_by(DeviceQuarantine.started_at.desc())
            .all()
        )
