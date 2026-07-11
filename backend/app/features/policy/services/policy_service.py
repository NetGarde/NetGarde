from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.features.client_behavior.repositories.device_security_policy_repository import (
    DeviceSecurityPolicyRepository,
)
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.policy.pack_common import BUILTIN_PACK_SLUGS, REMOTE_PACK_SLUGS
from app.features.policy.pack_fetch import list_pack_domains_page
from app.features.policy.pack_loader import (
    load_all_packs,
    pack_domain_count_sources,
    pack_domain_counts,
    refresh_pack,
)
from app.features.policy.repositories.policy_repository import PolicyRepository
from app.features.policy.repositories.policy_sync_repository import PolicySyncRepository
from app.features.client_behavior.schemas.behavior import QuarantineActionResponse
from app.features.policy.schemas.policy import (
    DevicePolicyAssignmentRead,
    PolicyApplyResponse,
    PolicyPackDomainsPage,
    PolicyPackRead,
    PolicyPackRefreshResponse,
    PolicyProfileRead,
    PolicyProfileUpdate,
    PolicySyncStatusRead,
)
from app.features.policy.sensitivity import block_threshold_for_sensitivity
from app.features.vpn.services.wireguard_agent_client import (
    block_client_on_host,
    sync_dns_policy_on_host,
    unblock_client_on_host,
)
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class PolicyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PolicyRepository(db)
        self.device_repo = DeviceRepository(db)
        self.security_repo = DeviceSecurityPolicyRepository(db)
        self.sync_repo = PolicySyncRepository(db)

    def list_packs(self) -> List[PolicyPackRead]:
        counts = pack_domain_counts()
        sources = pack_domain_count_sources()
        return [
            PolicyPackRead(
                id=p.id,
                slug=p.slug,
                name=p.name,
                description=p.description,
                enabled_globally=p.enabled_globally,
                domain_count=counts.get(p.slug, 0),
                blocked_sites_count=counts.get(p.slug, 0) if p.enabled_globally else 0,
                domain_list_source=sources.get(p.slug, "empty"),
            )
            for p in self.repo.list_packs()
        ]

    def list_pack_domains(
        self,
        slug: str,
        *,
        q: str = "",
        skip: int = 0,
        limit: int = 50,
    ) -> PolicyPackDomainsPage:
        slug = slug.strip().lower()
        if slug not in BUILTIN_PACK_SLUGS:
            raise HTTPException(status_code=404, detail=f"Pack {slug} not found")
        limit = max(1, min(limit, 200))
        skip = max(0, skip)
        domains, total, source = list_pack_domains_page(slug, q=q, skip=skip, limit=limit)
        return PolicyPackDomainsPage(
            slug=slug,
            domains=domains,
            total=total,
            skip=skip,
            limit=limit,
            domain_list_source=source,
            query=q.strip(),
        )

    def refresh_pack_domains(self, slug: str) -> PolicyPackRefreshResponse:
        slug = slug.strip().lower()
        if slug not in BUILTIN_PACK_SLUGS:
            raise HTTPException(status_code=404, detail=f"Pack {slug} not found")
        if slug not in REMOTE_PACK_SLUGS:
            raise HTTPException(
                status_code=400,
                detail=f"Pack {slug} has no remote list configured",
            )
        try:
            count = refresh_pack(slug)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to refresh pack: {e}") from e
        return PolicyPackRefreshResponse(
            slug=slug,
            domain_count=count,
            message=f"Refreshed {count} domains for pack {slug}",
        )

    def set_pack_enabled_globally(self, slug: str, enabled: bool) -> PolicyPackRead:
        pack = self.repo.update_pack_global(slug, enabled)
        if not pack:
            raise HTTPException(status_code=404, detail=f"Pack {slug} not found")
        self.db.commit()
        counts = pack_domain_counts()
        sources = pack_domain_count_sources()
        return PolicyPackRead(
            id=pack.id,
            slug=pack.slug,
            name=pack.name,
            description=pack.description,
            enabled_globally=pack.enabled_globally,
            domain_count=counts.get(pack.slug, 0),
            blocked_sites_count=counts.get(pack.slug, 0) if pack.enabled_globally else 0,
            domain_list_source=sources.get(pack.slug, "empty"),
        )

    def list_profiles(self) -> List[PolicyProfileRead]:
        return [PolicyProfileRead.model_validate(p) for p in self.repo.list_profiles()]

    def update_profile(self, profile_id: int, data: PolicyProfileUpdate) -> PolicyProfileRead:
        profile = self.repo.update_profile(profile_id, **data.model_dump(exclude_unset=True))
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found or builtin")
        self.db.commit()
        return PolicyProfileRead.model_validate(profile)

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

    def get_sync_status(self) -> PolicySyncStatusRead:
        return self.sync_repo.get_status()

    def record_sync_report(self, *, success: bool, message: Optional[str] = None) -> PolicySyncStatusRead:
        return self.sync_repo.record_sync(success=success, message=message)

    def apply_policy_now(self) -> PolicyApplyResponse:
        """Push dns-sync on the EC2 host via wg-agent (runs run-sync.sh)."""
        from app.shared.config import settings

        if not settings.DNS_BLOCKING_ENABLED:
            return PolicyApplyResponse(
                queued=False,
                message="DNS blocking is disabled on this deployment",
            )
        self.sync_repo.notify_policy_changed(source="manual_apply")
        if self._run_host_dns_sync("manual_apply"):
            return PolicyApplyResponse(
                queued=True,
                message="Policy DNS sync completed; dnsmasq reloaded on host",
            )
        return PolicyApplyResponse(
            queued=True,
            message="Policy sync queued in DB; host dns-sync failed or WG_AGENT not configured",
        )

    def start_device_quarantine(self, device_id: int, *, hours: int = 4) -> QuarantineActionResponse:
        from app.shared.config import settings

        if not settings.DNS_BLOCKING_ENABLED:
            raise HTTPException(status_code=403, detail="DNS blocking is disabled")
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        if not self._client_vpn_ip(device):
            raise HTTPException(
                status_code=400,
                detail="Device has no active VPN IP lease; block requires a enrolled WireGuard client",
            )
        self.repo.start_quarantine(device_id, score=None, hours=hours)
        self.db.commit()
        self.sync_repo.notify_policy_changed(source="admin_quarantine")
        self._apply_full_network_block(device)
        dns_synced = self._run_host_dns_sync("admin_quarantine")
        quarantine = self.repo.get_active_quarantine(device_id)
        if dns_synced:
            msg = f"Client blocked for {hours} hour(s); VPN and DNS enforcement applied"
        else:
            msg = (
                f"Client blocked for {hours} hour(s) in database; "
                "run dns-sync on host if sites are still reachable"
            )
        return QuarantineActionResponse(
            device_id=device_id,
            in_quarantine=True,
            quarantine_expires_at=quarantine.expires_at if quarantine else None,
            message=msg,
        )

    def end_device_quarantine(self, device_id: int) -> QuarantineActionResponse:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        ended = self.repo.end_quarantine(device_id)
        if not ended:
            raise HTTPException(status_code=404, detail="No active quarantine for this device")
        self.db.commit()
        self.sync_repo.notify_policy_changed(source="admin_quarantine_release")
        self._release_full_network_block(device)
        dns_synced = self._run_host_dns_sync("admin_quarantine_release")
        if dns_synced:
            msg = "Client unblocked; VPN and DNS access restored"
        else:
            msg = "Client unblocked in database; run dns-sync on host if DNS rules linger"
        return QuarantineActionResponse(
            device_id=device_id,
            in_quarantine=False,
            quarantine_expires_at=None,
            message=msg,
        )

    def _client_vpn_ip(self, device) -> Optional[str]:
        lease = getattr(device, "ip_lease", None)
        if lease is None or not lease.ip:
            return None
        return str(lease.ip).strip()

    def _run_host_dns_sync(self, source: str) -> bool:
        from app.shared.config import settings

        if not settings.DNS_BLOCKING_ENABLED:
            return False
        try:
            sync_dns_policy_on_host()
            return True
        except RuntimeError as exc:
            logger.warning(
                "Host DNS sync skipped",
                extra=structured_extra("host_dns_sync_skipped", source=source, error=str(exc)),
            )
            return False

    def _apply_full_network_block(self, device) -> None:
        from app.shared.config import settings

        if not settings.DNS_BLOCKING_ENABLED:
            return
        client_ip = self._client_vpn_ip(device)
        if not client_ip:
            return
        try:
            block_client_on_host(client_ip=client_ip)
        except RuntimeError as exc:
            logger.warning(
                "VPN traffic block skipped (DNS block still applies)",
                extra=structured_extra(
                    "admin_block_vpn_skipped",
                    device_id=device.id,
                    client_ip=client_ip,
                    error=str(exc),
                ),
            )

    def _release_full_network_block(self, device) -> None:
        from app.shared.config import settings

        if not settings.DNS_BLOCKING_ENABLED:
            return
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
