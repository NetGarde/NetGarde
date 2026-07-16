from fastapi import APIRouter, Depends, Query

from app.features.twin.schemas.connected_agent import ConnectedAgentListResponse
from app.features.twin.services.connected_agent_service import ConnectedAgentService
from app.shared.admin_auth import verify_admin_api_token

router = APIRouter(prefix="/security", tags=["Security Observability"])


def get_connected_agent_service() -> ConnectedAgentService:
    return ConnectedAgentService()


@router.get("/agents", response_model=ConnectedAgentListResponse)
def list_connected_agents(
    connected_within_sec: int = Query(default=300, ge=30, le=86400),
    _: None = Depends(verify_admin_api_token),
    service: ConnectedAgentService = Depends(get_connected_agent_service),
):
    """List connected TrustEdge agents from live Redis state."""
    return service.list_connected_agents(connected_within_sec=connected_within_sec)
