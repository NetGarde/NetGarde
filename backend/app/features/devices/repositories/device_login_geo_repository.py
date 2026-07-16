from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.features.devices.models.device_login_geo import DeviceLoginGeoObservation


class DeviceLoginGeoRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        *,
        device_id: int,
        public_ip: str,
        country_code: Optional[str],
        country_name: Optional[str],
        region_name: Optional[str],
        city: Optional[str],
        source: str = "enroll",
    ) -> DeviceLoginGeoObservation:
        row = DeviceLoginGeoObservation(
            device_id=device_id,
            public_ip=public_ip,
            country_code=country_code,
            country_name=country_name,
            region_name=region_name,
            city=city,
            source=source,
            observed_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_latest(self, device_id: int) -> Optional[DeviceLoginGeoObservation]:
        return (
            self.db.query(DeviceLoginGeoObservation)
            .filter(DeviceLoginGeoObservation.device_id == device_id)
            .order_by(desc(DeviceLoginGeoObservation.observed_at))
            .first()
        )

    def list_recent(self, device_id: int, *, limit: int = 20) -> List[DeviceLoginGeoObservation]:
        limit = max(1, min(limit, 100))
        return (
            self.db.query(DeviceLoginGeoObservation)
            .filter(DeviceLoginGeoObservation.device_id == device_id)
            .order_by(desc(DeviceLoginGeoObservation.observed_at))
            .limit(limit)
            .all()
        )

    def has_prior_country(self, device_id: int, country_code: str) -> bool:
        if not country_code:
            return False
        code = country_code.strip().upper()
        existing = (
            self.db.query(DeviceLoginGeoObservation.id)
            .filter(
                DeviceLoginGeoObservation.device_id == device_id,
                DeviceLoginGeoObservation.country_code == code,
            )
            .first()
        )
        return existing is not None

    def list_latest_per_device(self) -> List[DeviceLoginGeoObservation]:
        """Most recent observation per device_id."""
        subq = (
            self.db.query(
                DeviceLoginGeoObservation.device_id.label("device_id"),
                func.max(DeviceLoginGeoObservation.observed_at).label("max_observed"),
            )
            .group_by(DeviceLoginGeoObservation.device_id)
            .subquery()
        )
        return (
            self.db.query(DeviceLoginGeoObservation)
            .join(
                subq,
                (DeviceLoginGeoObservation.device_id == subq.c.device_id)
                & (DeviceLoginGeoObservation.observed_at == subq.c.max_observed),
            )
            .all()
        )
