from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.features.vpn.models.ip_pool import IpPool
from app.features.vpn.schemas.usage_history import UsageHistoryPoint, UsageHistoryResponse
from app.features.vpn.schemas.usage_live import DeviceUsageLiveResponse
from app.main import app
from app.shared.dependencies import get_db
from tests.helpers.integration import enroll_payload

pytestmark = pytest.mark.integration


@pytest.fixture
def api_client(db_session, monkeypatch):
    """FastAPI TestClient with in-memory DB and admin auth disabled."""
    monkeypatch.setattr("app.shared.config.settings.ADMIN_API_TOKEN", "")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()



@pytest.fixture
def enroll_device(api_client):
    def _enroll(**kwargs):
        return api_client.post("/v1/enroll", json=enroll_payload(**kwargs))

    return _enroll


@pytest.fixture
def active_vpn_pool(db_session, enroll_env):
    pool = IpPool(
        name="default",
        cidr="10.8.0.0/24",
        gateway_ip="10.8.0.1",
        dns_ip="10.8.0.1",
        endpoint="vpn.test.example:51820",
        server_public_key="serverPubKeyTest=",
        is_active=True,
    )
    db_session.add(pool)
    db_session.commit()
    return pool


@pytest.fixture
def forbidden_country_defaults(monkeypatch):
    monkeypatch.setattr("app.shared.config.settings.VPN_LOGIN_GEO_BLOCK_ENABLED", False)
    monkeypatch.setattr("app.shared.config.settings.BLOCKED_VPN_LOGIN_COUNTRIES", "")
    monkeypatch.setattr("app.shared.config.settings.FORBIDDEN_COUNTRY_RULES", "[]")


@pytest.fixture
def mock_apply_peer_on_host():
    with patch("app.features.vpn.services.enroll_service.apply_peer_on_host") as mock:
        yield mock


@pytest.fixture
def mock_record_vpn_enroll():
    with patch(
        "app.features.devices.services.device_login_geo_service.DeviceLoginGeoService.record_vpn_enroll"
    ) as mock:
        yield mock


@pytest.fixture
def mock_wireguard_peers():
    with patch(
        "app.features.vpn.services.vpn_topology_service.list_peers_on_host",
        return_value=[],
    ) as mock:
        yield mock


@pytest.fixture
def mock_usage_redis_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.features.vpn.services.usage_service.redis_available",
        lambda: False,
    )



@pytest.fixture
def mock_policy_notify():
    with patch(
        "app.features.policy.repositories.policy_sync_repository.PolicySyncRepository.notify_policy_changed"
    ) as mock:
        yield mock


@pytest.fixture
def mock_host_dns_sync():
    with patch("app.features.policy.services.policy_service.sync_dns_policy_on_host") as mock:
        yield mock


@pytest.fixture
def mock_host_client_block():
    with patch(
        "app.features.policy.services.policy_service.block_client_on_host"
    ) as block_mock, patch(
        "app.features.policy.services.policy_service.unblock_client_on_host"
    ) as unblock_mock:
        yield block_mock, unblock_mock


@pytest.fixture
def mock_refresh_pack():
    with patch("app.features.policy.services.policy_service.refresh_pack") as mock:
        mock.return_value = 42
        yield mock


@pytest.fixture
def mock_usage_ws_service():
    with patch("app.features.devices.routes.device_route.UsageService") as mock_cls:
        mock_cls.return_value.list_usage_history.return_value = UsageHistoryResponse(
            points=[], minutes=60
        )
        mock_cls.return_value.list_live_bandwidth.return_value = DeviceUsageLiveResponse(
            items=[], max_age_sec=60
        )
        yield mock_cls


@pytest.fixture
def mock_dashboard_usage():
    with patch(
        "app.features.vpn.services.usage_service.UsageService.list_live_bandwidth"
    ) as mock_live, patch(
        "app.features.vpn.services.usage_service.UsageService.list_usage_history"
    ) as mock_history:
        mock_live.return_value = DeviceUsageLiveResponse(items=[], max_age_sec=60)
        mock_history.return_value = UsageHistoryResponse(
            points=[
                UsageHistoryPoint(
                    recorded_at=datetime.now(timezone.utc),
                    rx_mib_per_sec=0.0,
                    tx_mib_per_sec=0.0,
                    total_mib_per_sec=0.0,
                    reporting_clients=0,
                )
            ],
            minutes=60,
        )
        yield mock_live, mock_history
