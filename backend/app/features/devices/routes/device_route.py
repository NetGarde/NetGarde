from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.features.devices.schemas.device import DeviceCreate, DeviceUpdate
from app.features.policy.schemas.policy import (
    AssignPolicyProfileRequest,
    DevicePolicyAssignmentRead,
    QuarantineActionResponse,
    QuarantineStartRequest,
)
from app.features.policy.services.policy_service import PolicyService
from app.features.devices.controllers.device_controller import (
    create_device_controller,
    get_devices_controller,
    update_device_controller,
    delete_device_controller,
)
from app.features.devices.dependencies import get_device_service
from app.features.devices.services.device_service_interface import IDeviceService
from app.shared.dependencies import get_db
from app.shared.admin_auth import verify_admin_api_token
from app.shared.utils.logging import get_logger

router = APIRouter(prefix="/devices", tags=["Devices"])
logger = get_logger(__name__)


def get_policy_service(db: Session = Depends(get_db)) -> PolicyService:
    return PolicyService(db)


@router.post("")
def create_device_endpoint(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_api_token),
    service: IDeviceService = Depends(get_device_service),
):
    return create_device_controller(data, db, service)


@router.get("")
def get_devices_endpoint(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_api_token),
    service: IDeviceService = Depends(get_device_service),
):
    return get_devices_controller(db, service)


@router.put("/{device_id}")
def update_device_endpoint(
    device_id: int,
    data: DeviceUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_api_token),
    service: IDeviceService = Depends(get_device_service),
):
    return update_device_controller(device_id, data, db, service)


@router.delete("/{device_id}")
def delete_device_endpoint(
    device_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_api_token),
    service: IDeviceService = Depends(get_device_service),
):
    return delete_device_controller(device_id, db, service)


@router.get("/{device_id}/policy-assignment", response_model=DevicePolicyAssignmentRead)
def get_device_policy_assignment_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    service: PolicyService = Depends(get_policy_service),
):
    return service.get_device_policy(device_id)


@router.put("/{device_id}/policy-assignment", response_model=DevicePolicyAssignmentRead)
def assign_device_policy_profile_endpoint(
    device_id: int,
    body: AssignPolicyProfileRequest,
    _: None = Depends(verify_admin_api_token),
    service: PolicyService = Depends(get_policy_service),
):
    return service.assign_profile_to_device(device_id, body.policy_profile_slug)


@router.post("/{device_id}/quarantine", response_model=QuarantineActionResponse)
def start_device_quarantine_endpoint(
    device_id: int,
    body: QuarantineStartRequest,
    _: None = Depends(verify_admin_api_token),
    service: PolicyService = Depends(get_policy_service),
):
    """Flag the device as quarantined for the given duration (soft quarantine)."""
    return service.start_device_quarantine(device_id, hours=body.hours)


@router.delete("/{device_id}/quarantine", response_model=QuarantineActionResponse)
def end_device_quarantine_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    service: PolicyService = Depends(get_policy_service),
):
    """Release client from quarantine early."""
    return service.end_device_quarantine(device_id)
