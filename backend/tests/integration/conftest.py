import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.dependencies import get_db

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
def device_token_env(monkeypatch):
    """Enable device-token auth (network attribution, etc.) in tests."""
    monkeypatch.setattr("app.shared.config.settings.DEVICE_TOKEN_SECRET", "test-device-token-secret")
