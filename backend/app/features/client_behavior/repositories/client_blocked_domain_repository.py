from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.features.client_behavior.models.client_blocked_domain import ClientBlockedDomain
from app.features.devices.models.device import Device


class ClientBlockedDomainRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_block(
        self,
        *,
        device_id: int,
        domain: str,
        root_domain: Optional[str],
        source: str,
        score: Optional[int],
        expires_at: Optional[datetime],
    ) -> ClientBlockedDomain:
        existing = (
            self.db.query(ClientBlockedDomain)
            .filter(
                ClientBlockedDomain.device_id == device_id,
                ClientBlockedDomain.domain == domain.lower(),
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if existing:
            if existing.revoked_at is not None:
                existing.revoked_at = None
            existing.expires_at = expires_at
            existing.score = score
            existing.source = source
            existing.root_domain = root_domain
            return existing
        row = ClientBlockedDomain(
            device_id=device_id,
            domain=domain.lower(),
            root_domain=root_domain,
            source=source,
            score=score,
            expires_at=expires_at,
            created_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def count_blocks_today(self, device_id: int) -> int:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(ClientBlockedDomain)
            .filter(
                ClientBlockedDomain.device_id == device_id,
                ClientBlockedDomain.source == "behavior_auto",
                ClientBlockedDomain.created_at >= start,
                ClientBlockedDomain.revoked_at.is_(None),
            )
            .count()
        )

    def revoke(self, block_id: int, device_id: Optional[int] = None) -> bool:
        query = self.db.query(ClientBlockedDomain).filter(ClientBlockedDomain.id == block_id)
        if device_id is not None:
            query = query.filter(ClientBlockedDomain.device_id == device_id)
        row = query.first()
        if not row:
            return False
        row.revoked_at = datetime.now(timezone.utc)
        return True

    def list_active_for_device(self, device_id: int) -> List[ClientBlockedDomain]:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ClientBlockedDomain)
            .filter(
                ClientBlockedDomain.device_id == device_id,
                ClientBlockedDomain.revoked_at.is_(None),
                or_(ClientBlockedDomain.expires_at.is_(None), ClientBlockedDomain.expires_at > now),
            )
            .order_by(ClientBlockedDomain.created_at.desc())
            .all()
        )

    def list_active_behavior_auto_blocks(self) -> List[ClientBlockedDomain]:
        """Active auto-blocks with device loaded (for admin blocked-clients list)."""
        return self.list_active_blocks_for_admin()

    def list_active_blocks_for_admin(self) -> List[ClientBlockedDomain]:
        """Active per-device blocks (any source) with device loaded."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ClientBlockedDomain)
            .join(Device, ClientBlockedDomain.device_id == Device.id)
            .options(
                joinedload(ClientBlockedDomain.device),  # type: ignore[arg-type]
            )
            .filter(
                ClientBlockedDomain.revoked_at.is_(None),
                or_(ClientBlockedDomain.expires_at.is_(None), ClientBlockedDomain.expires_at > now),
            )
            .order_by(ClientBlockedDomain.created_at.desc())
            .all()
        )

    def list_active_for_sync(self) -> List[ClientBlockedDomain]:
        """Active blocks with device MAC for dnsmasq sync."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ClientBlockedDomain)
            .join(Device, ClientBlockedDomain.device_id == Device.id)
            .options(joinedload(ClientBlockedDomain.device))  # type: ignore[arg-type]
            .filter(
                ClientBlockedDomain.revoked_at.is_(None),
                or_(ClientBlockedDomain.expires_at.is_(None), ClientBlockedDomain.expires_at > now),
                Device.mac_address.isnot(None),
            )
            .all()
        )
