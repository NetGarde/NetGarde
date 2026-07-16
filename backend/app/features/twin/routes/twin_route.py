from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.features.twin.graph.schemas import (
    TraverseDirection,
    TraverseRequest,
    TraverseResponse,
    TwinGraphSnapshot,
    TwinLayer,
    TwinRelation,
)
from app.features.twin.schemas.simulation_command import SimulationCommandRequest, SimulationCommandResponse
from app.features.twin.schemas.connected_agent import ConnectedAgentListResponse
from app.features.twin.services.connected_agent_service import ConnectedAgentService
from app.features.twin.services.simulation_command_service import SimulationCommandService
from app.features.twin.services.twin_graph_service import TwinGraphService
from app.shared.admin_auth import verify_admin_api_token
from app.shared.dependencies import get_db

router = APIRouter(prefix="/security", tags=["Security Observability"])


def get_twin_graph_service(db: Session = Depends(get_db)) -> TwinGraphService:
    return TwinGraphService(db)


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


@router.get("/graph/snapshot", response_model=TwinGraphSnapshot)
def graph_snapshot(
    minutes: int = Query(default=1, ge=1, le=60),
    include_flows: bool = Query(default=True),
    include_trusttwin: bool = Query(default=True),
    _: None = Depends(verify_admin_api_token),
    service: TwinGraphService = Depends(get_twin_graph_service),
):
    """Canonical entity/dependency graph for security observability."""
    return service.build_snapshot(
        minutes=minutes,
        include_flows=include_flows,
        include_trusttwin=include_trusttwin,
    )


@router.post("/graph/traverse", response_model=TraverseResponse)
def graph_traverse(
    body: TraverseRequest,
    minutes: int = Query(default=1, ge=1, le=60),
    include_flows: bool = Query(default=True),
    include_trusttwin: bool = Query(default=True),
    _: None = Depends(verify_admin_api_token),
    service: TwinGraphService = Depends(get_twin_graph_service),
):
    """Walk dependencies from seed nodes (impact analysis, blast radius, RCA)."""
    return service.traverse(
        body,
        minutes=minutes,
        include_flows=include_flows,
        include_trusttwin=include_trusttwin,
    )


@router.get("/graph/neighbors", response_model=TraverseResponse)
def graph_neighbors(
    node_id: str = Query(min_length=1),
    direction: TraverseDirection = Query(default="both"),
    relations: Optional[List[TwinRelation]] = Query(default=None),
    layers: Optional[List[TwinLayer]] = Query(default=None),
    minutes: int = Query(default=1, ge=1, le=60),
    include_flows: bool = Query(default=True),
    include_trusttwin: bool = Query(default=True),
    _: None = Depends(verify_admin_api_token),
    service: TwinGraphService = Depends(get_twin_graph_service),
):
    """One-hop neighbors of a node in either direction."""
    return service.neighbors(
        node_id,
        direction=direction,
        relations=relations,
        layers=layers,
        minutes=minutes,
        include_flows=include_flows,
        include_trusttwin=include_trusttwin,
    )


@router.post("/simulate/command", response_model=SimulationCommandResponse)
def simulate_command(
    body: SimulationCommandRequest,
    _: None = Depends(verify_admin_api_token),
):
    """Parse natural-language what-if commands (rules first, Ollama fallback)."""
    return SimulationCommandService().parse(body)
