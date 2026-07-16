"""GeoIP lookup for client public IPs at device check-in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.shared.config import settings
from app.shared.logging_context import structured_extra
from app.shared.request_client_ip import is_public_ip
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GeoLocation:
    country_code: str
    country_name: str
    region_name: Optional[str] = None
    city: Optional[str] = None


def lookup_geo(ip: str) -> Optional[GeoLocation]:
    """
    Resolve country (and optional region/city) for a public IP.

    Uses ip-api.com when GEOIP_ENABLED (non-commercial; rate-limited).
    Returns None for private/invalid IPs or when lookup is disabled/fails.
    """
    if not getattr(settings, "GEOIP_ENABLED", True):
        return None
    if not is_public_ip(ip):
        return None

    provider = (getattr(settings, "GEOIP_PROVIDER", "ip_api") or "ip_api").strip().lower()
    if provider == "none":
        return None
    if provider != "ip_api":
        logger.warning(
            "Unknown GEOIP provider; skipping lookup",
            extra=structured_extra("geoip_unknown_provider", provider=provider),
        )
        return None

    timeout = max(0.5, float(getattr(settings, "GEOIP_TIMEOUT_SEC", 3.0)))
    url = f"http://ip-api.com/json/{ip}"
    params = {"fields": "status,message,country,countryCode,regionName,city"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning(
            "GeoIP lookup failed",
            extra=structured_extra("geoip_lookup_failed", ip=ip, error=str(exc)),
        )
        return None

    if data.get("status") != "success":
        return None

    code = str(data.get("countryCode") or "").strip().upper()
    if len(code) != 2:
        return None

    country = str(data.get("country") or code).strip() or code
    region = str(data.get("regionName") or "").strip() or None
    city = str(data.get("city") or "").strip() or None
    return GeoLocation(
        country_code=code,
        country_name=country,
        region_name=region,
        city=city,
    )
