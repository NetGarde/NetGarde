from __future__ import annotations

from sqlalchemy.orm import Session

from app.features.agents.repositories.agent_repository import AgentRepository
from app.features.agents.schemas.agent import (
    AgentListResponse,
    AgentRead,
    AgentUpsertRequest,
)
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    def __init__(self, db: Session):
        self.repo = AgentRepository(db)

    def upsert(self, data: AgentUpsertRequest) -> AgentRead:
        row = self.repo.upsert(data)
        logger.info(
            "Agent registry upserted",
            extra=structured_extra(
                "agent_registry_upserted",
                agent_id=row.agent_id,
                hostname=row.hostname,
            ),
        )
        return AgentRead.model_validate(row)

    def list_agents(self) -> AgentListResponse:
        rows = self.repo.list_all()
        items = [AgentRead.model_validate(row) for row in rows]
        return AgentListResponse(items=items, total=len(items))
