from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.features.agents.schemas.agent import AgentListResponse, AgentRead, AgentUpsertRequest
from app.features.agents.services.agent_service import AgentService
from app.shared.admin_auth import verify_admin_api_token
from app.shared.dependencies import get_db
from app.shared.service_auth import verify_dns_ingest_service

router = APIRouter(tags=["Agents"])


def get_agent_service(db: Session = Depends(get_db)) -> AgentService:
    return AgentService(db)


@router.post("/internal/agents/upsert", response_model=AgentRead)
def upsert_agent(
    body: AgentUpsertRequest,
    _: None = Depends(verify_dns_ingest_service),
    service: AgentService = Depends(get_agent_service),
):
    """Upsert a registered agent (called by Agent-API with service token)."""
    return service.upsert(body)


@router.get("/agents", response_model=AgentListResponse)
def list_agents(
    _: None = Depends(verify_admin_api_token),
    service: AgentService = Depends(get_agent_service),
):
    """List registered agents for the dashboard."""
    return service.list_agents()
