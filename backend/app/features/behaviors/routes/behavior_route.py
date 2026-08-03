from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.features.behaviors.schemas.behavior import (
    BehaviorObserveRequest,
    BehaviorObserveResponse,
    DeviceBehaviorListResponse,
)
from app.features.behaviors.services.behavior_service import BehaviorService
from app.shared.admin_auth import verify_admin_api_token
from app.shared.dependencies import get_db
from app.shared.service_auth import verify_ingest_service

router = APIRouter(tags=["Behaviors"])


def get_behavior_service(db: Session = Depends(get_db)) -> BehaviorService:
    return BehaviorService(db)


@router.post("/internal/behaviors/observe", response_model=BehaviorObserveResponse)
def observe_behavior(
    body: BehaviorObserveRequest,
    _: None = Depends(verify_ingest_service),
    service: BehaviorService = Depends(get_behavior_service),
):
    """Upsert a learned behavior and return whether detection should suppress the alert."""
    return service.observe(body)


@router.get("/behaviors", response_model=DeviceBehaviorListResponse)
def list_behaviors(
    device_id: str = Query(..., min_length=1),
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(verify_admin_api_token),
    service: BehaviorService = Depends(get_behavior_service),
):
    """List learned behaviors for a device (dashboard / debugging)."""
    return service.list_for_device(device_id, limit=limit)
