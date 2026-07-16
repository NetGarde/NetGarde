import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_URL", "sqlite:///:memory:")

from app.shared.database import Base


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
def dns_ingest_env(monkeypatch):
    """Disable service ingest auth in tests."""
    monkeypatch.setattr("app.shared.config.settings.DNS_INGEST_TOKEN", "")


@pytest.fixture
def dashboard_env(monkeypatch):
    monkeypatch.setattr("app.shared.config.settings.NETWORK_REVIEW_MODE", "template")
