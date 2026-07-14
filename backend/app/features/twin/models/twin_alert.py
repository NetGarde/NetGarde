from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.shared.database import Base


class TwinAlert(Base):
    __tablename__ = "twin_alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    event_id = Column(String(64), nullable=True)
    event_type = Column(String(32), nullable=True)
    alert_type = Column(String(32), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="medium")
    message = Column(Text, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_twin_alerts_type_ts", "alert_type", "timestamp"),
        Index("ix_twin_alerts_device_ts", "device_id", "timestamp"),
    )
