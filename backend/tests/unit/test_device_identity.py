import time

import pytest

from app.shared.device_identity import (
    DeviceTokenError,
    create_device_token,
    verify_device_token,
)


@pytest.fixture(autouse=True)
def device_token_secret(monkeypatch):
    from app.shared.config import settings

    monkeypatch.setattr(settings, "DEVICE_TOKEN_SECRET", "test-device-secret-for-unit-tests")
    monkeypatch.setattr(settings, "DEVICE_TOKEN_TTL_DAYS", 7)
    return settings


def test_create_and_verify_device_token(device_token_secret):
    token = create_device_token(device_id="abc123device")
    claims = verify_device_token(token)
    assert claims.device_id == "abc123device"
    assert claims.expires_at > int(time.time())


def test_reject_tampered_token(device_token_secret):
    token = create_device_token(device_id="d1")
    parts = token.split(".")
    parts[2] = "badsignature"
    with pytest.raises(DeviceTokenError, match="invalid signature"):
        verify_device_token(".".join(parts))
