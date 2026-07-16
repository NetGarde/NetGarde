from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.features.devices.schemas.device import DeviceCreate, DeviceUpdate
from app.features.client_behavior.schemas.behavior import (
    BehaviorProfileRead,
    BehaviorReviewRead,
    BehaviorRecomputeResult,
    BlockedClientsListResponse,
    ClientBlockedDomainCreate,
    ClientBlockedDomainRead,
    DeviceSecurityPolicyRead,
    DeviceSecurityPolicyUpdate,
    QuarantineActionResponse,
    QuarantineStartRequest,
)
from app.features.client_behavior.services.client_behavior_api_service import ClientBehaviorApiService
from app.features.policy.schemas.policy import AssignPolicyProfileRequest, DevicePolicyAssignmentRead
from app.features.policy.services.policy_service import PolicyService
from app.features.devices.controllers.device_controller import (
    create_device_controller,
    get_devices_controller,
    update_device_controller,
    delete_device_controller,
)
from app.features.devices.dependencies import get_device_service
from app.features.devices.schemas.device_country import (
    DeviceCountryBreakdownRead,
    DeviceCountrySummaryList,
)
from app.features.devices.schemas.device_login_geo import (
    DeviceLoginGeoRead,
    DeviceLoginGeoSummaryList,
)
from app.features.devices.services.device_country_service import DeviceCountryService
from app.features.devices.services.device_login_geo_service import DeviceLoginGeoService
from app.features.devices.services.device_service_interface import IDeviceService
from app.shared.dependencies import get_db
from app.shared.admin_auth import verify_admin_api_token
from app.shared.utils.logging import get_logger

router = APIRouter(prefix="/devices", tags=["Devices"])
logger = get_logger(__name__)


def get_client_behavior_service(db: Session = Depends(get_db)) -> ClientBehaviorApiService:
    return ClientBehaviorApiService(db)


def get_policy_service(db: Session = Depends(get_db)) -> PolicyService:
    return PolicyService(db)


def get_device_country_service(db: Session = Depends(get_db)) -> DeviceCountryService:
    return DeviceCountryService(db)


def get_device_login_geo_service(db: Session = Depends(get_db)) -> DeviceLoginGeoService:
    return DeviceLoginGeoService(db)


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


@router.get("/blocked-clients", response_model=BlockedClientsListResponse)
def list_blocked_clients_endpoint(
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    """Devices with active quarantine or per-device domain blocks."""
    return behavior.list_blocked_clients()


@router.get("/countries/summary", response_model=DeviceCountrySummaryList)
def list_device_countries_summary_endpoint(
    period_hours: int = Query(default=168, ge=1, le=24 * 30),
    _: None = Depends(verify_admin_api_token),
    service: DeviceCountryService = Depends(get_device_country_service),
):
    """Primary inferred country per device from DNS domain TLDs (last N hours)."""
    return service.list_summaries(period_hours=period_hours)


@router.get("/login-locations/summary", response_model=DeviceLoginGeoSummaryList)
def list_device_login_locations_summary_endpoint(
    _: None = Depends(verify_admin_api_token),
    service: DeviceLoginGeoService = Depends(get_device_login_geo_service),
):
    """Latest VPN login location per device (GeoIP from public IP at enroll)."""
    return service.list_summaries()


@router.get("/{device_id}/login-location", response_model=DeviceLoginGeoRead)
def get_device_login_location_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    service: DeviceLoginGeoService = Depends(get_device_login_geo_service),
):
    """Physical location at last VPN enroll(s) for this device."""
    return service.get_device_login_geo(device_id)


@router.post("/recompute-behavior-baselines", response_model=BehaviorRecomputeResult)
def recompute_behavior_baselines_endpoint(
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    updated = behavior.recompute_baselines()
    return BehaviorRecomputeResult(devices_updated=updated)


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


@router.get("/{device_id}/dns-countries", response_model=DeviceCountryBreakdownRead)
def get_device_dns_countries_endpoint(
    device_id: int,
    period_hours: int = Query(default=168, ge=1, le=24 * 30),
    _: None = Depends(verify_admin_api_token),
    service: DeviceCountryService = Depends(get_device_country_service),
):
    """Country breakdown for one device from DNS domains (ccTLD / suffix heuristics)."""
    return service.get_breakdown(device_id, period_hours=period_hours)


@router.get("/{device_id}/behavior-profile", response_model=BehaviorProfileRead)
def get_behavior_profile_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.get_behavior_profile(device_id)


@router.get("/{device_id}/behavior-review", response_model=BehaviorReviewRead)
def get_behavior_review_endpoint(
    device_id: int,
    refresh: bool = Query(default=False),
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.get_behavior_review(device_id, refresh=refresh)


@router.get("/{device_id}/behavior-events")
def get_behavior_events_endpoint(
    device_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.get_behavior_events(device_id, page=page, page_size=page_size)


@router.get("/{device_id}/security-policy", response_model=DeviceSecurityPolicyRead)
def get_security_policy_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.get_security_policy(device_id)


@router.put("/{device_id}/security-policy", response_model=DeviceSecurityPolicyRead)
def update_security_policy_endpoint(
    device_id: int,
    data: DeviceSecurityPolicyUpdate,
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.update_security_policy(device_id, data)


@router.get("/{device_id}/client-blocks", response_model=list[ClientBlockedDomainRead])
def list_client_blocks_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.list_client_blocks(device_id)


@router.post("/{device_id}/client-blocks", response_model=ClientBlockedDomainRead)
def create_client_block_endpoint(
    device_id: int,
    body: ClientBlockedDomainCreate,
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    """Manually block a domain for one client (merged into dnsmasq per-device rules)."""
    return behavior.create_client_block(device_id, body)


@router.delete("/{device_id}/client-blocks/{block_id}")
def revoke_client_block_endpoint(
    device_id: int,
    block_id: int,
    _: None = Depends(verify_admin_api_token),
    behavior: ClientBehaviorApiService = Depends(get_client_behavior_service),
):
    return behavior.revoke_client_block(device_id, block_id)


@router.post("/{device_id}/quarantine", response_model=QuarantineActionResponse)
def start_device_quarantine_endpoint(
    device_id: int,
    body: QuarantineStartRequest,
    _: None = Depends(verify_admin_api_token),
    service: PolicyService = Depends(get_policy_service),
):
    """Block all client network access (VPN iptables drop) for the given duration."""
    return service.start_device_quarantine(device_id, hours=body.hours)


@router.delete("/{device_id}/quarantine", response_model=QuarantineActionResponse)
def end_device_quarantine_endpoint(
    device_id: int,
    _: None = Depends(verify_admin_api_token),
    service: PolicyService = Depends(get_policy_service),
):
    """Release client from quarantine early."""
    return service.end_device_quarantine(device_id)
