from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.shared.database import Base


class Agent(Base):
    """Durable registry row for a TrustEdge Agent install."""

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(128), nullable=False, unique=True, index=True)
    hostname = Column(String(255), nullable=True, index=True)
    os = Column(String(64), nullable=True)
    os_version = Column(String(128), nullable=True)
    arch = Column(String(64), nullable=True)
    agent_version = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="registered")
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
