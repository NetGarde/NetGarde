from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, JSON, String, UniqueConstraint

from app.shared.database import Base


class DeviceBehavior(Base):
    """Learned per-device behavior counters for detection baseline suppression."""

    __tablename__ = "device_behaviors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(128), nullable=False, index=True)
    behavior_kind = Column(String(64), nullable=False)
    behavior_key = Column(String(255), nullable=False)
    alert_type = Column(String(64), nullable=True)
    count = Column(BigInteger, nullable=False, default=1)
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_alert_at = Column(DateTime(timezone=True), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "behavior_kind",
            "behavior_key",
            name="uq_device_behaviors_device_kind_key",
        ),
        Index("ix_device_behaviors_device_count", "device_id", "count"),
    )
