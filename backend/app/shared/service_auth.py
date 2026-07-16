"""Service-to-service authentication (log watcher, automation)."""

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


def _verify_static_bearer(authorization: Optional[str], expected: str, *, detail: str) -> None:
    if not expected:
        return
    token = _extract_bearer(authorization)
    if not hmac_compare(token, expected):
        raise HTTPException(status_code=403, detail=detail)


def verify_dns_ingest_service(authorization: Optional[str] = Header(default=None)) -> None:
    """Require DNS_INGEST_TOKEN on DNS query write endpoints when configured."""
    _verify_static_bearer(
        authorization,
        settings.DNS_INGEST_TOKEN.strip(),
        detail="Invalid DNS ingest credentials",
    )
