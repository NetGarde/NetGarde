from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index
from app.shared.database import Base


class DeviceLoginGeoObservation(Base):
    """Physical location inferred from the client's public IP at VPN enroll."""

    __tablename__ = "device_login_geo_observations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)

    public_ip = Column(String(45), nullable=False)
    country_code = Column(String(8), nullable=True, index=True)
    country_name = Column(String(128), nullable=True)
    region_name = Column(String(128), nullable=True)
    city = Column(String(128), nullable=True)
    source = Column(String(32), nullable=False, default="enroll")

    observed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_device_login_geo_device_observed", "device_id", "observed_at"),
    )
