from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Index
from datetime import datetime, timezone
from app.shared.database import Base


class Alert(Base):
    __tablename__ = "dns_alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    client_ip = Column(String(45), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_type = Column(String(32), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="medium")
    domain = Column(String(255), nullable=True, index=True)
    root_domain = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_dns_alerts_type_ts", "alert_type", "timestamp"),
    )
