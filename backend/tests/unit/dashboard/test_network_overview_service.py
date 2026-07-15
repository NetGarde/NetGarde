from unittest.mock import patch

from app.features.dashboard.services.network_overview_service import NetworkOverviewService
from datetime import datetime, timezone
from tests.helpers.factories import seed_policy_catalog


@patch("app.features.vpn.services.usage_service.UsageService.list_usage_history")
@patch("app.features.vpn.services.usage_service.UsageService.list_live_bandwidth")
def test_build_overview_template_mode(mock_live, mock_history, db_session, dashboard_env, seed_policy):
    from app.features.vpn.schemas.usage_history import UsageHistoryPoint, UsageHistoryResponse
    from app.features.vpn.schemas.usage_live import DeviceUsageLiveResponse

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

    overview = NetworkOverviewService(db_session).build_overview(period_minutes=60)
    assert overview.source == "template"
    assert overview.review_mode == "template"
    assert overview.stats.blocked_queries == 0
    assert len(overview.bullets) > 0
