from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.features.devices.models.device import Device
from app.features.vpn.models.vpn_enroll_event import VpnEnrollEvent
from app.features.vpn.models.ip_pool import IpPool
from app.features.vpn.models.vpn_peer import VpnPeer
from app.features.vpn.repositories.ip_pool_repository import IpPoolRepository
from app.features.vpn.repositories.vpn_peer_repository import VpnPeerRepository
from app.features.vpn.schemas.enroll import EnrollRequest
from app.features.vpn.services.ip_allocation_service import IpAllocationService
from app.features.vpn.services.wireguard_agent_client import apply_peer_on_host
from app.shared.config import settings
from app.shared.device_identity import DeviceTokenError, create_device_token
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class EnrollService:
    def __init__(self, db: Session):
        self.db = db
        self.pools = IpPoolRepository(db)
        self.peers = VpnPeerRepository(db)
        self.alloc = IpAllocationService(db)

    def _get_or_create_default_pool(self) -> IpPool:
        name = settings.VPN_POOL_NAME
        pool = self.pools.get_active_by_name(name)
        if pool:
            return pool

        if not settings.VPN_ENDPOINT or not settings.VPN_SERVER_PUBLIC_KEY:
            raise RuntimeError("VPN_ENDPOINT and VPN_SERVER_PUBLIC_KEY must be set")

        pool = IpPool(
            name=name,
            cidr=settings.VPN_POOL_CIDR,
            gateway_ip=settings.VPN_GATEWAY_IP,
            dns_ip=settings.VPN_DNS_IP,
            mtu=settings.VPN_MTU,
            allowed_ips=settings.VPN_ALLOWED_IPS,
            endpoint=settings.VPN_ENDPOINT,
            server_public_key=settings.VPN_SERVER_PUBLIC_KEY,
            persistent_keepalive=settings.VPN_PERSISTENT_KEEPALIVE,
            is_active=True,
        )
        return self.pools.create(pool)

    def _sync_device_for_lease(
        self,
        lease_row,
        hostname: Optional[str],
        mac_address: Optional[str],
    ) -> Optional[Device]:
        dev = self.db.query(Device).filter(Device.ip_lease_id == lease_row.id).first()
        if dev is not None:
            if hostname is not None:
                dev.hostname = hostname
            if mac_address is not None:
                dev.mac_address = mac_address
            return dev

        mac = (mac_address or "").strip().lower() or None
        if mac:
            by_mac = self.db.query(Device).filter(Device.mac_address == mac).first()
            if by_mac is not None:
                by_mac.ip_lease_id = lease_row.id
                by_mac.source = "vpn_enroll"
                if hostname is not None:
                    by_mac.hostname = hostname
                return by_mac

        dev = Device(
            ip_lease_id=lease_row.id,
            source="vpn_enroll",
            hostname=hostname,
            mac_address=mac,
        )
        self.db.add(dev)
        return dev

    def _validate_peer_identity(self, device_id: str, public_key: str) -> None:
        by_device = self.peers.get_by_device_id(device_id)
        if by_device is not None and by_device.public_key != public_key:
            raise ValueError("device_id already registered with a different public key")

        by_key = self.peers.get_by_public_key(public_key)
        if by_key is not None and by_key.device_id != device_id:
            raise ValueError("public_key already registered to another device")

    def enroll(self, payload: EnrollRequest, *, connect_ip: Optional[str] = None) -> dict:
        device_id = payload.device_id.strip()
        public_key = payload.public_key.strip()

        from app.features.policy.services.vpn_login_geo_block_service import VpnLoginGeoBlockService

        VpnLoginGeoBlockService().assert_enroll_allowed(
            connect_ip=connect_ip,
            client_reported_ip=payload.client_public_ip,
        )

        self._validate_peer_identity(device_id, public_key)

        pool = self._get_or_create_default_pool()

        peer = self.peers.get_by_device_id(device_id) or self.peers.get_by_public_key(public_key)
        if not peer:
            peer = self.peers.create(VpnPeer(device_id=device_id, public_key=public_key, pool_id=pool.id))

        lease = self.alloc.ensure_peer_lease(peer, pool)

        lease_row = self.alloc.leases.get_active_by_peer_id(peer.id)
        if lease_row is None:
            raise RuntimeError("Lease row missing after allocation")
        dev = self._sync_device_for_lease(lease_row, payload.hostname, payload.mac_address)
        self.db.flush()
        if dev:
            from app.features.policy.services.policy_service import PolicyService

            PolicyService(self.db).assign_profile_by_slug_on_enroll(
                dev.id, payload.policy_profile_slug
            )
        self.db.add(
            VpnEnrollEvent(
                peer_id=peer.id,
                device_id=dev.id if dev else None,
                event_type="enroll",
                lease_ip=lease.ip,
                hostname=payload.hostname,
                mac_address=payload.mac_address,
            )
        )

        if dev:
            from app.features.devices.services.device_login_geo_service import DeviceLoginGeoService

            DeviceLoginGeoService(self.db).record_vpn_enroll(
                device_id=dev.id,
                peer_id=peer.id,
                connect_ip=connect_ip,
                client_reported_ip=payload.client_public_ip,
                client_ip_label=lease.ip,
            )

        # Persist allocation before touching host WireGuard state.
        self.db.commit()

        # Apply (or refresh) the live WireGuard peer on the EC2 host.
        apply_peer_on_host(public_key=peer.public_key, allowed_ip=lease.ip)

        allowed_ips = [s.strip() for s in (pool.allowed_ips or "").split(",") if s.strip()]
        if not allowed_ips:
            allowed_ips = ["0.0.0.0/0", "::/0"]

        try:
            device_token = create_device_token(device_id=device_id, public_key=public_key)
        except DeviceTokenError as exc:
            raise RuntimeError(str(exc)) from exc

        logger.info(
            "VPN enroll succeeded",
            extra=structured_extra(
                "enroll_success",
                device_id=device_id,
                lease_ip=lease.ip,
            ),
        )

        return {
            "address": f"{lease.ip}/32",
            "dns": [pool.dns_ip],
            "mtu": pool.mtu or settings.VPN_MTU,
            "server_public_key": pool.server_public_key,
            "endpoint": pool.endpoint,
            "allowed_ips": allowed_ips,
            "persistent_keepalive": pool.persistent_keepalive,
            "device_token": device_token,
        }

