import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_URL", "sqlite:///:memory:")

from app.shared.database import Base
from tests.helpers.factories import create_device, seed_policy_catalog

# Register all models on Base.metadata (required for create_all FK resolution)
from app.features.alerts.models.alert import Alert  # noqa: F401
from app.features.devices.models.device import Device  # noqa: F401
from app.features.devices.models.device_country_presence import DeviceCountryPresence  # noqa: F401
from app.features.devices.models.device_login_geo import DeviceLoginGeoObservation  # noqa: F401
from app.features.client_behavior.models.client_behavior_rollup import ClientBehaviorRollup  # noqa: F401
from app.features.client_behavior.models.client_behavior_profile import ClientBehaviorProfile  # noqa: F401
from app.features.client_behavior.models.client_blocked_domain import ClientBlockedDomain  # noqa: F401
from app.features.client_behavior.models.device_security_policy import DeviceSecurityPolicy  # noqa: F401
from app.features.policy.models.policy_profile import PolicyProfile  # noqa: F401
from app.features.policy.models.device_quarantine import DeviceQuarantine  # noqa: F401
from app.features.network_attribution.models.device_app_usage_rollup import DeviceAppUsageRollup  # noqa: F401
from app.features.network_attribution.models.device_network_context import DeviceNetworkContext  # noqa: F401
from app.features.twin.models.twin_alert import TwinAlert  # noqa: F401


@pytest.fixture(autouse=True)
def test_runtime_settings(monkeypatch):
    """Keep tests fast and offline."""
    monkeypatch.setattr("app.shared.config.settings.REDIS_URL", "")


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seed_policy(db_session):
    return seed_policy_catalog(db_session)


@pytest.fixture
def sample_device(db_session):
    """Return a Device with a default external_id."""
    return create_device(db_session)


@pytest.fixture
def dns_ingest_env(monkeypatch):
    """Disable service ingest auth in tests."""
    monkeypatch.setattr("app.shared.config.settings.DNS_INGEST_TOKEN", "")


@pytest.fixture
def dashboard_env(monkeypatch):
    monkeypatch.setattr("app.shared.config.settings.NETWORK_REVIEW_MODE", "template")


@pytest.fixture
def behavior_env(monkeypatch):
    monkeypatch.setattr("app.shared.config.settings.BEHAVIOR_REVIEW_MODE", "template")
