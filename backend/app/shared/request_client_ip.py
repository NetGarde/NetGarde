"""Resolve the client's public IP from an HTTP request (proxy-aware)."""

from __future__ import annotations

from typing import Optional, Union

import ipaddress

from starlette.requests import Request


def _parse_ip(value: str) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    value = value.strip()
    if not value:
        return None
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def is_public_ip(ip: str) -> bool:
    addr = _parse_ip(ip)
    if addr is None:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _first_public_from_csv(header_value: str) -> Optional[str]:
    for part in header_value.split(","):
        candidate = part.strip()
        if is_public_ip(candidate):
            return candidate
    return None


def client_ip_from_request(request: Request) -> Optional[str]:
    """
    Best-effort public client IP.

    Order: X-Forwarded-For (first public), X-Real-IP, request.client.host.
    ProxyHeadersMiddleware should already adjust client.host when trusted.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        found = _first_public_from_csv(forwarded)
        if found:
            return found

    real_ip = request.headers.get("X-Real-IP")
    if real_ip and is_public_ip(real_ip.strip()):
        return real_ip.strip()

    if request.client and request.client.host:
        host = request.client.host.strip()
        if is_public_ip(host):
            return host
    return None
