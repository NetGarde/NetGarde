from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timezone
from app.shared.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    # Agent / endpoint identity string
    external_id = Column(String(128), nullable=False, unique=True, index=True)
    hostname = Column(String(255), nullable=True, index=True)
    mac_address = Column(String(17), nullable=True, unique=True, index=True)  # AA:BB:CC:DD:EE:FF
    policy_profile_id = Column(
        Integer,
        ForeignKey("policy_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source = Column(String(20), nullable=False, default="manual")  # manual, agent_enroll
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
