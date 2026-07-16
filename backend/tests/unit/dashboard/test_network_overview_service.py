from app.features.dashboard.services.network_overview_service import NetworkOverviewService


def test_build_overview_template_mode(db_session, dashboard_env, seed_policy):
    overview = NetworkOverviewService(db_session).build_overview(period_minutes=60)
    assert overview.source == "template"
    assert overview.review_mode == "template"
    assert overview.stats.blocked_queries == 0
    assert overview.stats.reporting_clients == 0
    assert len(overview.bullets) > 0
