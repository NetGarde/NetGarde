"""FastAPI dependencies for device-authenticated requests."""

from __future__ import annotations

from typing import Optional

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.features.devices.repositories.device_repository import DeviceRepository
from app.shared.dependencies import get_db
from app.shared.device_identity import DeviceTokenError, verify_device_token


@dataclass(frozen=True)
class AuthenticatedDevice:
    device_id: str
    device_pk: int


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return token


def hmac_compare(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)


def get_authenticated_device(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthenticatedDevice:
    token = _extract_bearer(authorization)
    try:
        claims = verify_device_token(token)
    except DeviceTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    device = DeviceRepository(db).get_by_external_id(claims.device_id)
    if device is None:
        raise HTTPException(status_code=401, detail="Device not registered")

    return AuthenticatedDevice(device_id=device.external_id, device_pk=device.id)
