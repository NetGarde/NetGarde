from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.features.devices.repositories.device_country_presence_repository import (
    DeviceCountryPresenceRepository,
)
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.alerts.models.alert import Alert
from app.features.alerts.repositories.alert_repository import AlertRepository
from app.shared.config import settings
from app.shared.domain_country import country_display_name
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

_ALERT_TYPE = "new_country_region"


class DeviceCountryAlertService:
    def __init__(self, db: Session):
        self.db = db
        self.presence_repo = DeviceCountryPresenceRepository(db)
        self.device_repo = DeviceRepository(db)
        self.alert_repo = AlertRepository(db)

    def record_countries_and_alert(
        self,
        device_id: int,
        client_ip: str,
        country_counts: Dict[str, int],
    ) -> int:
        """Persist country presence and create alerts for newly seen regions."""
        if not getattr(settings, "DEVICE_COUNTRY_ALERT_ENABLED", True):
            return 0

        newly_seen = self.presence_repo.record_batch(device_id, country_counts)
        if not newly_seen:
            return 0

        device = self.device_repo.get_by_id(device_id)
        label = (device.hostname if device else None) or client_ip
        alerts_created = 0

        for code in newly_seen:
            if self._recent_alert_exists(device_id, code):
                continue
            name = country_display_name(code)
            message = (
                f"{label} is using DNS patterns associated with {name} ({code}) "
                "for the first time on this network."
            )
            self.alert_repo.create(
                timestamp=datetime.now(timezone.utc),
                client_ip=client_ip,
                alert_type=_ALERT_TYPE,
                severity="medium",
                domain=None,
                root_domain=None,
                message=message,
                device_id=device_id,
            )
            alerts_created += 1
            logger.warning(
                "New country region alert",
                extra=structured_extra(
                    "new_country_region_alert",
                    device_id=device_id,
                    country_code=code,
                ),
            )

        return alerts_created

    def _recent_alert_exists(self, device_id: int, country_code: str) -> bool:
        """Avoid duplicate alerts for the same device+country within cooldown."""
        hours = max(1, int(getattr(settings, "DEVICE_COUNTRY_ALERT_COOLDOWN_HOURS", 24)))
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
