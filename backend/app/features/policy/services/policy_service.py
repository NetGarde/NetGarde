from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.policy.repositories.policy_repository import PolicyRepository
from app.features.policy.schemas.policy import (
    DevicePolicyAssignmentRead,
    QuarantineActionResponse,
)
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class PolicyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PolicyRepository(db)
        self.device_repo = DeviceRepository(db)

    def get_device_policy(self, device_id: int) -> DevicePolicyAssignmentRead:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        profile = None
        if device.policy_profile_id:
            profile = self.repo.get_profile_by_id(device.policy_profile_id)
        quarantine = self.repo.get_active_quarantine(device_id)
        return DevicePolicyAssignmentRead(
            device_id=device_id,
            policy_profile_id=profile.id if profile else None,
            policy_profile_slug=profile.slug if profile else None,
            policy_profile_name=profile.name if profile else None,
            in_quarantine=quarantine is not None,
            quarantine_expires_at=quarantine.expires_at if quarantine else None,
        )

    def assign_profile_to_device(self, device_id: int, profile_slug: str) -> DevicePolicyAssignmentRead:
        profile = self.repo.get_profile_by_slug(profile_slug)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_slug} not found")
        device = self.repo.assign_profile_to_device(device_id, profile.id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        self.db.commit()
        return self.get_device_policy(device_id)

    def assign_profile_by_slug_on_enroll(self, device_id: int, profile_slug: Optional[str]) -> None:
        if not profile_slug:
            profile = self.repo.get_default_profile()
        else:
            profile = self.repo.get_profile_by_slug(profile_slug)
        if not profile:
            return
        self.repo.assign_profile_to_device(device_id, profile.id)

    def start_device_quarantine(self, device_id: int, *, hours: int = 4) -> QuarantineActionResponse:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        self.repo.start_quarantine(device_id, score=None, hours=hours)
        self.db.commit()
        logger.info(
            "Device quarantine started (soft; no network enforcement)",
            extra=structured_extra("device_quarantine_started", device_id=device_id, hours=hours),
        )
        quarantine = self.repo.get_active_quarantine(device_id)
        return QuarantineActionResponse(
            device_id=device_id,
            in_quarantine=True,
            quarantine_expires_at=quarantine.expires_at if quarantine else None,
            message=f"Device quarantined for {hours} hour(s) (soft flag; agent isolation not yet enforced)",
        )

    def end_device_quarantine(self, device_id: int) -> QuarantineActionResponse:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        ended = self.repo.end_quarantine(device_id)
        if not ended:
            raise HTTPException(status_code=404, detail="No active quarantine for this device")
        self.db.commit()
        logger.info(
            "Device quarantine ended",
            extra=structured_extra("device_quarantine_ended", device_id=device_id),
        )
        return QuarantineActionResponse(
            device_id=device_id,
            in_quarantine=False,
            quarantine_expires_at=None,
            message="Device released from quarantine",
        )
