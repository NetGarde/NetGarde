"""Device identity tokens (HMAC-signed JWT-style credentials)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from app.shared.config import settings


class DeviceTokenError(Exception):
    pass


@dataclass(frozen=True)
class DeviceTokenClaims:
    device_id: str
    issued_at: int
    expires_at: int


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(message: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(digest)


def create_device_token(*, device_id: str, public_key: Optional[str] = None) -> str:
    """Issue a device token. public_key is accepted for compatibility but ignored."""
    del public_key  # VPN-era claim; no longer used
    secret = settings.device_token_secret
    if not secret:
        raise DeviceTokenError("DEVICE_TOKEN_SECRET is not configured")

    now = int(time.time())
    ttl = settings.DEVICE_TOKEN_TTL_SECONDS
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "device",
        "device_id": device_id.strip(),
        "iat": now,
        "exp": now + ttl,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _sign(signing_input, secret)
    return f"{header_b64}.{payload_b64}.{signature}"


def verify_device_token(token: str) -> DeviceTokenClaims:
    secret = settings.device_token_secret
    if not secret:
        raise DeviceTokenError("DEVICE_TOKEN_SECRET is not configured")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise DeviceTokenError("malformed token")

    header_b64, payload_b64, signature = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = _sign(signing_input, secret)
    if not hmac.compare_digest(expected, signature):
        raise DeviceTokenError("invalid signature")

    try:
        payload_obj: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as exc:
        raise DeviceTokenError("invalid payload") from exc

    if payload_obj.get("sub") != "device":
        raise DeviceTokenError("invalid subject")

    device_id = str(payload_obj.get("device_id") or "").strip()
    if not device_id:
        raise DeviceTokenError("missing device claims")

    exp = int(payload_obj.get("exp") or 0)
    if exp <= int(time.time()):
        raise DeviceTokenError("token expired")

    return DeviceTokenClaims(
        device_id=device_id,
        issued_at=int(payload_obj.get("iat") or 0),
        expires_at=exp,
    )
