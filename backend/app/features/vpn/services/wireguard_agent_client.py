from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.shared.config import settings


def apply_peer_on_host(*, public_key: str, allowed_ip: str) -> None:
    """
    Notify the host WireGuard agent to apply:
      wg set <iface> peer <pubkey> allowed-ips <ip>/32
    """
    base = (settings.WG_AGENT_URL or "").strip().rstrip("/")
    token = (settings.WG_AGENT_TOKEN or "").strip()
    if not base or not token:
        raise RuntimeError("WG_AGENT_URL and WG_AGENT_TOKEN must be set")

    url = f"{base}/v1/apply-peer"
    payload = json.dumps({"public_key": public_key, "allowed_ip": allowed_ip}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status not in (200, 201):
                raise RuntimeError(f"wg agent returned {resp.status}: {body}")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"wg agent HTTP {e.code}: {err}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"wg agent URL error: {e.reason}") from e


def block_client_on_host(*, client_ip: str) -> None:
    """Drop all VPN forwarded traffic for a client IP (admin full network block)."""
    _post_wg_agent("/v1/block-client", {"client_ip": client_ip})


def unblock_client_on_host(*, client_ip: str) -> None:
    """Remove iptables drops for a client IP."""
    _post_wg_agent("/v1/unblock-client", {"client_ip": client_ip})


def _post_wg_agent(path: str, payload: dict, *, timeout_sec: int = 5) -> None:
    base = (settings.WG_AGENT_URL or "").strip().rstrip("/")
    token = (settings.WG_AGENT_TOKEN or "").strip()
    if not base or not token:
        raise RuntimeError("WG_AGENT_URL and WG_AGENT_TOKEN must be set")

    url = f"{base}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if resp.status not in (200, 201):
                raise RuntimeError(f"wg agent returned {resp.status}: {raw}")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"wg agent HTTP {e.code}: {err}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"wg agent URL error: {e.reason}") from e


def list_peers_on_host() -> list[dict]:
    """Return live WireGuard peers from the host agent (wg show dump)."""
    base = (settings.WG_AGENT_URL or "").strip().rstrip("/")
    token = (settings.WG_AGENT_TOKEN or "").strip()
    if not base or not token:
        raise RuntimeError("WG_AGENT_URL and WG_AGENT_TOKEN must be set")

    url = f"{base}/v1/peers"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status != 200:
                raise RuntimeError(f"wg agent returned {resp.status}: {body}")
            data = json.loads(body)
            peers = data.get("peers")
            if not isinstance(peers, list):
                return []
            return peers
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"wg agent HTTP {e.code}: {err}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"wg agent URL error: {e.reason}") from e
