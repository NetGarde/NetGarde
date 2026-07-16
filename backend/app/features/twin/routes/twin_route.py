from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.features.twin.schemas.connected_agent import ConnectedAgentListResponse
from app.features.twin.schemas.security_alert import (
    SecurityAlertCreate,
    SecurityAlertExplainRequest,
    SecurityAlertExplainResponse,
    SecurityAlertListResponse,
)
from app.features.twin.services.alert_explain_service import explain_security_alert
from app.features.twin.services.connected_agent_service import ConnectedAgentService
from app.features.twin.services.security_alert_service import SecurityAlertService
from app.shared.admin_auth import verify_admin_api_token
from app.shared.dependencies import get_db
from app.shared.service_auth import verify_ingest_service

router = APIRouter(prefix="/security", tags=["Security Observability"])


def get_security_alert_service(db: Session = Depends(get_db)) -> SecurityAlertService:
    return SecurityAlertService(db)


def get_connected_agent_service() -> ConnectedAgentService:
    return ConnectedAgentService()


@router.get("/alerts", response_model=SecurityAlertListResponse)
def list_security_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    alert_type: Optional[str] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    _: None = Depends(verify_admin_api_token),
    service: SecurityAlertService = Depends(get_security_alert_service),
):
    """List TrustEdge Agent detection alerts."""
    return service.list_alerts(
        page=page,
        page_size=page_size,
        alert_type=alert_type,
        device_id=device_id,
        severity=severity,
    )


@router.post("/alerts/explain", response_model=SecurityAlertExplainResponse)
def explain_security_alert_route(
    body: SecurityAlertExplainRequest,
    _: None = Depends(verify_admin_api_token),
):
    """Ask the local Ollama model to explain a security alert for an operator."""
    try:
        return explain_security_alert(body)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/alerts/ingest")
def ingest_security_alerts(
    body: list[SecurityAlertCreate],
    _: None = Depends(verify_ingest_service),
    service: SecurityAlertService = Depends(get_security_alert_service),
):
    """Ingest alerts from detection-engine (service token)."""
    if not body:
        return {"created": 0}
    created = service.ingest(body)
    return {"created": created}


@router.get("/agents", response_model=ConnectedAgentListResponse)
def list_connected_agents(
    connected_within_sec: int = Query(default=300, ge=30, le=86400),
    _: None = Depends(verify_admin_api_token),
    service: ConnectedAgentService = Depends(get_connected_agent_service),
):
    """List connected TrustEdge agents from live Redis state."""
    return service.list_connected_agents(connected_within_sec=connected_within_sec)
