"""Admin API authentication for dashboard-accessed endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from app.shared.config import settings
from app.shared.device_auth import hmac_compare


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return token


def verify_admin_api_token(authorization: Optional[str] = Header(default=None)) -> None:
    """
    Require ADMIN_API_TOKEN when configured.
    If ADMIN_API_TOKEN is empty, admin auth is disabled (dev convenience).
    """
    expected = settings.ADMIN_API_TOKEN.strip()
    if not expected:
        return
    token = _extract_bearer(authorization)
    if not hmac_compare(token, expected):
        raise HTTPException(status_code=403, detail="Invalid admin credentials")

