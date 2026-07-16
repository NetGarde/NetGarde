from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.features.client_behavior.repositories.device_security_policy_repository import (
    DeviceSecurityPolicyRepository,
)
from app.features.client_behavior.schemas.behavior import QuarantineActionResponse
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.policy.repositories.policy_repository import PolicyRepository
from app.features.policy.schemas.policy import DevicePolicyAssignmentRead
from app.features.policy.sensitivity import block_threshold_for_sensitivity
from app.features.vpn.services.wireguard_agent_client import block_client_on_host, unblock_client_on_host
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class PolicyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PolicyRepository(db)
        self.device_repo = DeviceRepository(db)
        self.security_repo = DeviceSecurityPolicyRepository(db)

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
        self._sync_security_policy_from_profile(device_id, profile.behavior_sensitivity)
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
        self._sync_security_policy_from_profile(device_id, profile.behavior_sensitivity)

    def _sync_security_policy_from_profile(self, device_id: int, sensitivity: str) -> None:
        policy = self.security_repo.get_or_create(device_id)
        from app.shared.config import settings

        policy.auto_block_enabled = True
        policy.auto_block_threshold = block_threshold_for_sensitivity(sensitivity)
        policy.max_blocks_per_day = settings.BEHAVIOR_MAX_BLOCKS_PER_DAY

    def start_device_quarantine(self, device_id: int, *, hours: int = 4) -> QuarantineActionResponse:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        if not self._client_vpn_ip(device):
            raise HTTPException(
                status_code=400,
                detail="Device has no active VPN IP lease; block requires an enrolled WireGuard client",
            )
        self.repo.start_quarantine(device_id, score=None, hours=hours)
        self.db.commit()
        self._apply_full_network_block(device)
        quarantine = self.repo.get_active_quarantine(device_id)
        return QuarantineActionResponse(
            device_id=device_id,
            in_quarantine=True,
            quarantine_expires_at=quarantine.expires_at if quarantine else None,
            message=f"Client blocked for {hours} hour(s); VPN enforcement applied",
        )

    def end_device_quarantine(self, device_id: int) -> QuarantineActionResponse:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        ended = self.repo.end_quarantine(device_id)
        if not ended:
            raise HTTPException(status_code=404, detail="No active quarantine for this device")
        self.db.commit()
        self._release_full_network_block(device)
        return QuarantineActionResponse(
            device_id=device_id,
            in_quarantine=False,
            quarantine_expires_at=None,
            message="Client unblocked; VPN access restored",
        )

    def _client_vpn_ip(self, device) -> Optional[str]:
        lease = getattr(device, "ip_lease", None)
        if lease is None or not lease.ip:
            return None
        return str(lease.ip).strip()

    def _apply_full_network_block(self, device) -> None:
        client_ip = self._client_vpn_ip(device)
        if not client_ip:
            return
        try:
            block_client_on_host(client_ip=client_ip)
        except RuntimeError as exc:
            logger.warning(
                "VPN traffic block skipped",
                extra=structured_extra(
                    "admin_block_vpn_skipped",
                    device_id=device.id,
                    client_ip=client_ip,
                    error=str(exc),
                ),
            )

    def _release_full_network_block(self, device) -> None:
        client_ip = self._client_vpn_ip(device)
        if not client_ip:
            return
        try:
            unblock_client_on_host(client_ip=client_ip)
        except RuntimeError as exc:
            logger.warning(
                "VPN traffic unblock skipped",
                extra=structured_extra(
                    "admin_unblock_vpn_skipped",
                    device_id=device.id,
                    client_ip=client_ip,
                    error=str(exc),
                ),
            )
