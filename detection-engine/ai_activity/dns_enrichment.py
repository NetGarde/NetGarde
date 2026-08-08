"""Hostname enrichment for network destinations (payload, PTR, cmdline URL map)."""

from __future__ import annotations

import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse

_IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$|^\[?[0-9a-fA-F:]+\]?$")
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_HOST_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9-]+\.)+(?:com|net|org|io|ai|sh|dev|cloud|app)(?![A-Za-z0-9_.-])",
    re.IGNORECASE,
)

_PTR_TTL_SEC = 3600.0
_FORWARD_TTL_SEC = 1800.0
_LOOKUP_TIMEOUT_SEC = 0.2

_lock = threading.Lock()
# ip -> (expires_at, hostname)
_ptr_cache: dict[str, tuple[float, str]] = {}
# ip -> (expires_at, hostname) from forward DNS of cmdline URLs
_forward_cache: dict[str, tuple[float, str]] = {}

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-dns")

# Prefer these service names when a PTR / forward host matches.
_SERVICE_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("openai.com", "api.openai.com"),
    ("anthropic.com", "api.anthropic.com"),
    ("claude.ai", "claude.ai"),
    ("cursor.sh", "cursor.sh"),
    ("cursor.com", "cursor.com"),
    ("github.com", "github.com"),
    ("githubusercontent.com", "githubusercontent.com"),
    ("googleapis.com", "googleapis.com"),
    ("docker.io", "docker.io"),
    ("npmjs.org", "npmjs.org"),
    ("pypi.org", "pypi.org"),
)


def is_ip_address(value: str) -> bool:
    raw = (value or "").strip().lower().strip("[]")
    if not raw:
        return False
    if _IP_RE.match(raw):
        return True
    try:
        socket.inet_pton(socket.AF_INET, raw)
        return True
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, raw)
        return True
    except OSError:
        return False


def normalize_hostname(value: str) -> str:
    host = (value or "").strip().lower().rstrip(".")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def friendly_hostname(hostname: str) -> str:
    """Map PTR / FQDN to a stable service label when possible."""
    host = normalize_hostname(hostname)
    if not host or is_ip_address(host):
        return host
    for suffix, label in _SERVICE_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return label
    # AWS / GCP style PTRs stay as hostnames (better than bare IP).
    return host


def remember_hosts_from_text(text: str) -> None:
    """Resolve hostnames found in cmdline/text and cache IP → hostname."""
    hosts = extract_hostnames(text)
    if not hosts:
        return
    for host in hosts[:8]:
        _remember_forward(host)


def extract_hostnames(text: str) -> list[str]:
    raw = text or ""
    found: list[str] = []
    seen: set[str] = set()
    for match in _URL_RE.findall(raw):
        try:
            parsed = urlparse(match)
            host = normalize_hostname(parsed.hostname or "")
        except Exception:
            host = ""
        if host and host not in seen and not is_ip_address(host):
            seen.add(host)
            found.append(host)
    for match in _HOST_TOKEN_RE.findall(raw):
        host = normalize_hostname(match)
        if host and host not in seen and not is_ip_address(host):
            seen.add(host)
            found.append(host)
    return found


def resolve_network_name(
    remote_addr: str,
    *,
    payload: dict[str, Any] | None = None,
) -> str:
    """Best display/domain name for a remote address."""
    payload = payload or {}
    for key in ("remote_hostname", "domain", "hostname", "remote_host"):
        hint = normalize_hostname(str(payload.get(key) or ""))
        if hint and not is_ip_address(hint):
            return friendly_hostname(hint)

    addr = normalize_hostname(remote_addr)
    if not addr:
        return ""
    if not is_ip_address(addr):
        return friendly_hostname(addr)

    cached = _get_forward(addr)
    if cached:
        return friendly_hostname(cached)

    ptr = _lookup_ptr(addr)
    if ptr:
        return friendly_hostname(ptr)
    return addr


def _remember_forward(hostname: str) -> None:
    host = normalize_hostname(hostname)
    if not host or is_ip_address(host):
        return

    def _resolve() -> None:
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError:
            return
        expires = time.monotonic() + _FORWARD_TTL_SEC
        with _lock:
            for info in infos:
                ip = info[4][0]
                if not ip or not is_ip_address(ip):
                    continue
                # Prefer first memorable hostname; keep shorter/service names.
                prev = _forward_cache.get(ip)
                if prev is None or len(host) <= len(prev[1]):
                    _forward_cache[ip] = (expires, host)

    try:
        _executor.submit(_resolve)
        # Also try a quick synchronous resolve for immediate mapping.
        infos = socket.getaddrinfo(host, None)
        expires = time.monotonic() + _FORWARD_TTL_SEC
        with _lock:
            for info in infos:
                ip = info[4][0]
                if ip and is_ip_address(ip):
                    _forward_cache[ip] = (expires, host)
    except OSError:
        pass


def _get_forward(ip: str) -> str:
    now = time.monotonic()
    with _lock:
        item = _forward_cache.get(ip)
        if not item:
            return ""
        expires, host = item
        if expires < now:
            _forward_cache.pop(ip, None)
            return ""
        return host


def _lookup_ptr(ip: str) -> str:
    now = time.monotonic()
    with _lock:
        item = _ptr_cache.get(ip)
        if item:
            expires, host = item
            if expires >= now:
                return host
            _ptr_cache.pop(ip, None)

    host = ""
    try:
        future = _executor.submit(socket.gethostbyaddr, ip)
        name, _, _ = future.result(timeout=_LOOKUP_TIMEOUT_SEC)
        host = normalize_hostname(name)
    except Exception:
        host = ""

    with _lock:
        _ptr_cache[ip] = (now + _PTR_TTL_SEC, host)
    return host


def clear_caches_for_tests() -> None:
    with _lock:
        _ptr_cache.clear()
        _forward_cache.clear()
