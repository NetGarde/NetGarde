from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.features.agents.models.agent import Agent
from app.features.agents.schemas.agent import AgentUpsertRequest


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_agent_id(self, agent_id: str) -> Optional[Agent]:
        return self.db.query(Agent).filter(Agent.agent_id == agent_id.strip()).first()

    def list_all(self) -> List[Agent]:
        return self.db.query(Agent).order_by(Agent.last_seen_at.desc(), Agent.id.desc()).all()

    def upsert(self, data: AgentUpsertRequest) -> Agent:
        now = datetime.now(timezone.utc)
        agent_id = data.agent_id.strip()
        row = self.get_by_agent_id(agent_id)
        if row is None:
            row = Agent(
                agent_id=agent_id,
                hostname=(data.hostname or None),
                os=(data.os or None),
                os_version=(data.os_version or None),
                arch=(data.arch or None),
                agent_version=(data.agent_version or None),
                status=(data.status or "registered").strip() or "registered",
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
        else:
            if data.hostname:
                row.hostname = data.hostname
            if data.os:
                row.os = data.os
            if data.os_version:
                row.os_version = data.os_version
            if data.arch:
                row.arch = data.arch
            if data.agent_version:
                row.agent_version = data.agent_version
            if data.status:
                row.status = data.status.strip() or row.status
            row.last_seen_at = now
            row.updated_at = now

        self.db.commit()
        self.db.refresh(row)
        return row
