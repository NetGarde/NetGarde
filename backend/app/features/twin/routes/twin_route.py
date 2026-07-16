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
from app.features.twin.schemas.twin_alert import TwinAlertCreate, TwinAlertListResponse
from app.features.twin.schemas.twin_alert import TwinAlertCreate, TwinAlertListResponse
from app.features.twin.services.simulation_command_service import SimulationCommandService
from app.features.twin.services.twin_alert_service import TwinAlertService
from app.features.twin.services.twin_graph_service import TwinGraphService
from app.shared.admin_auth import verify_admin_api_token
from app.shared.dependencies import get_db
from app.shared.service_auth import verify_dns_ingest_service

router = APIRouter(prefix="/security", tags=["Security Observability"])


def get_twin_graph_service(db: Session = Depends(get_db)) -> TwinGraphService:
    return TwinGraphService(db)


def get_twin_alert_service(db: Session = Depends(get_db)) -> TwinAlertService:
    return TwinAlertService(db)


@router.get("/alerts", response_model=TwinAlertListResponse)
def list_twin_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    alert_type: Optional[str] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    _: None = Depends(verify_admin_api_token),
    service: TwinAlertService = Depends(get_twin_alert_service),
):
    """List TrustEdge Agent detection alerts."""
    return service.list_alerts(
        page=page,
        page_size=page_size,
        alert_type=alert_type,
        device_id=device_id,
        severity=severity,
    )


@router.post("/alerts/ingest")
def ingest_twin_alerts(
    body: list[TwinAlertCreate],
    _: None = Depends(verify_dns_ingest_service),
    service: TwinAlertService = Depends(get_twin_alert_service),
):
    """Ingest alerts from detection-engine (service token)."""
    if not body:
        return {"created": 0}
    created = service.ingest(body)
    return {"created": created}


@router.get("/graph/snapshot", response_model=TwinGraphSnapshot)
def graph_snapshot(
    minutes: int = Query(default=1, ge=1, le=60),
    include_flows: bool = Query(default=True),
    include_policy: bool = Query(default=True),
    include_trusttwin: bool = Query(default=True),
    _: None = Depends(verify_admin_api_token),
    service: TwinGraphService = Depends(get_twin_graph_service),
):
    """Canonical entity/dependency graph for security observability."""
    return service.build_snapshot(
        minutes=minutes,
        include_flows=include_flows,
        include_policy=include_policy,
        include_trusttwin=include_trusttwin,
    )


@router.post("/graph/traverse", response_model=TraverseResponse)
def graph_traverse(
    body: TraverseRequest,
    minutes: int = Query(default=1, ge=1, le=60),
    include_flows: bool = Query(default=True),
    include_policy: bool = Query(default=True),
    include_trusttwin: bool = Query(default=True),
    _: None = Depends(verify_admin_api_token),
    service: TwinGraphService = Depends(get_twin_graph_service),
):
    """Walk dependencies from seed nodes (impact analysis, blast radius, RCA)."""
    return service.traverse(
        body,
        minutes=minutes,
        include_flows=include_flows,
        include_policy=include_policy,
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
    include_policy: bool = Query(default=True),
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
        include_policy=include_policy,
        include_trusttwin=include_trusttwin,
    )



@router.post("/simulate/command", response_model=SimulationCommandResponse)
def simulate_command(
    body: SimulationCommandRequest,
    _: None = Depends(verify_admin_api_token),
):
    """Parse natural-language what-if commands (rules first, Ollama fallback)."""
    return SimulationCommandService().parse(body)
