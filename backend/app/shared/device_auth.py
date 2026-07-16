"""FastAPI dependencies for device-authenticated requests."""

from __future__ import annotations

from typing import Optional

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.features.vpn.repositories.vpn_peer_repository import VpnPeerRepository
from app.shared.config import settings
from app.shared.dependencies import get_db
from app.shared.device_identity import DeviceTokenError, verify_device_token


@dataclass(frozen=True)
class AuthenticatedDevice:
    device_id: str
    public_key: str


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return token


def verify_enroll_bootstrap(authorization: Optional[str] = Header(default=None)) -> None:
    """Require shared bootstrap token for enroll when ENROLL_BOOTSTRAP_TOKEN is set."""
    expected = settings.ENROLL_BOOTSTRAP_TOKEN.strip()
    if not expected:
        return
    token = _extract_bearer(authorization)
    if not hmac_compare(token, expected):
        raise HTTPException(status_code=403, detail="Invalid enroll credentials")


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

    peer = VpnPeerRepository(db).get_by_device_id(claims.device_id)
    if peer is None or peer.public_key != claims.public_key:
        raise HTTPException(status_code=401, detail="Device not registered or key mismatch")

    return AuthenticatedDevice(device_id=peer.device_id, public_key=peer.public_key)
