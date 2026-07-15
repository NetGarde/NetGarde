from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.features.devices.models.device_login_geo import DeviceLoginGeoObservation
from app.features.devices.repositories.device_login_geo_repository import DeviceLoginGeoRepository
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.devices.schemas.device_login_geo import (
    DeviceLoginGeoObservationRead,
    DeviceLoginGeoRead,
    DeviceLoginGeoSummaryItem,
    DeviceLoginGeoSummaryList,
)
from app.features.alerts.models.alert import Alert
from app.features.alerts.repositories.alert_repository import AlertRepository
from app.shared.config import settings
from app.shared.geoip import lookup_geo
from app.shared.request_client_ip import is_public_ip
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

_ALERT_TYPE = "new_vpn_login_country"


class DeviceLoginGeoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DeviceLoginGeoRepository(db)
        self.device_repo = DeviceRepository(db)
        self.alert_repo = AlertRepository(db)

    def record_vpn_enroll(
        self,
        *,
        device_id: int,
        peer_id: Optional[int],
        connect_ip: Optional[str],
        client_reported_ip: Optional[str] = None,
        client_ip_label: str = "",
    ) -> Optional[DeviceLoginGeoObservation]:
        """
        Store geo from the client's public IP at enroll and alert on new login countries.
        """
        if not getattr(settings, "DEVICE_LOGIN_GEO_ENABLED", True):
            return None

        public_ip = self._resolve_public_ip(connect_ip, client_reported_ip)
        if not public_ip:
            return None

        geo = lookup_geo(public_ip)
        country_code = geo.country_code if geo else None
        country_name = geo.country_name if geo else None
        region_name = geo.region_name if geo else None
        city = geo.city if geo else None

        is_new_country = bool(
            country_code
            and not self.repo.has_prior_country(device_id, country_code)
        )

        row = self.repo.add(
            device_id=device_id,
            peer_id=peer_id,
            public_ip=public_ip,
            country_code=country_code,
            country_name=country_name,
            region_name=region_name,
            city=city,
            source="enroll",
        )

        if is_new_country and getattr(settings, "DEVICE_LOGIN_GEO_ALERT_ENABLED", True):
            self._maybe_alert_new_login_country(
                device_id=device_id,
                country_code=country_code,
                country_name=country_name or country_code,
                public_ip=public_ip,
                client_ip_label=client_ip_label,
            )

        return row

    @staticmethod
    def _resolve_public_ip(
        connect_ip: Optional[str],
        client_reported_ip: Optional[str],
    ) -> Optional[str]:
        if client_reported_ip and is_public_ip(client_reported_ip.strip()):
            return client_reported_ip.strip()
        if connect_ip and is_public_ip(connect_ip.strip()):
            return connect_ip.strip()
        return None

    def get_device_login_geo(self, device_id: int, *, history_limit: int = 10) -> DeviceLoginGeoRead:
        latest = self.repo.get_latest(device_id)
        history = self.repo.list_recent(device_id, limit=history_limit)
        return DeviceLoginGeoRead(
            device_id=device_id,
            latest=self._to_read(latest) if latest else None,
            history=[self._to_read(r) for r in history],
        )

    def list_summaries(self) -> DeviceLoginGeoSummaryList:
        rows = self.repo.list_latest_per_device()
        items = [
            DeviceLoginGeoSummaryItem(
                device_id=r.device_id,
                country_code=r.country_code,
                country_name=r.country_name,
                public_ip=r.public_ip,
                observed_at=r.observed_at,
            )
            for r in rows
        ]
        return DeviceLoginGeoSummaryList(items=items)

    def _maybe_alert_new_login_country(
        self,
        *,
        device_id: int,
        country_code: str,
        country_name: str,
        public_ip: str,
        client_ip_label: str,
    ) -> None:
        if self._recent_login_country_alert_exists(device_id, country_code):
            return

        device = self.device_repo.get_by_id(device_id)
        label = (device.hostname if device else None) or client_ip_label or public_ip
        message = (
            f"{label} connected to the VPN from {country_name} ({country_code}) "
            f"for the first time (public IP {public_ip})."
        )
        self.alert_repo.create(
            timestamp=datetime.now(timezone.utc),
            client_ip=public_ip,
            alert_type=_ALERT_TYPE,
            severity="high",
            domain=None,
            root_domain=None,
            message=message,
            device_id=device_id,
        )
        logger.warning(
            "New VPN login country alert",
            extra=structured_extra(
                "new_vpn_login_country",
                device_id=device_id,
                country_code=country_code,
            ),
        )

    def _recent_login_country_alert_exists(self, device_id: int, country_code: str) -> bool:
        hours = max(1, int(getattr(settings, "DEVICE_LOGIN_GEO_ALERT_COOLDOWN_HOURS", 24)))
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        needle = f"({country_code})"
        existing = (
            self.db.query(Alert)
            .filter(
                Alert.device_id == device_id,
                Alert.alert_type == _ALERT_TYPE,
                Alert.timestamp >= since,
                Alert.message.like(f"%{needle}%"),
            )
            .first()
        )
        return existing is not None

    @staticmethod
    def _to_read(row: DeviceLoginGeoObservation) -> DeviceLoginGeoObservationRead:
        return DeviceLoginGeoObservationRead(
            device_id=row.device_id,
            public_ip=row.public_ip,
            country_code=row.country_code,
            country_name=row.country_name,
            region_name=row.region_name,
            city=row.city,
            observed_at=row.observed_at,
            source=row.source,
        )
