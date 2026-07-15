#!/usr/bin/env python3
"""
TrustEdge WireGuard host agent (runs on the EC2 host as root).

Purpose:
  Apply WireGuard peer AllowedIPs updates to the host wg interface after /v1/enroll.

Security:
  - Binds only to TRUSTEDGE_WG_AGENT_BIND (default: 172.17.0.1)
  - Requires Authorization: Bearer <TRUSTEDGE_WG_AGENT_TOKEN>
  - Validates WireGuard public keys and IPv4 addresses strictly
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

WG_PUBKEY_RE = re.compile(r"^[A-Za-z0-9+/]{43}=$")


def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or not str(v).strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return str(v).strip()


def _validate_pubkey(pub: str) -> str:
    pub = pub.strip()
    if not WG_PUBKEY_RE.match(pub):
        raise ValueError("invalid wireguard public key")
    return pub


def _validate_ipv4(ip: str, pool_cidr: str) -> str:
    ip = ip.strip()
    addr = ipaddress.ip_address(ip)
    if not isinstance(addr, ipaddress.IPv4Address):
        raise ValueError("only IPv4 allowed_ip is supported")
    net = ipaddress.ip_network(pool_cidr, strict=False)
    if addr not in net:
        raise ValueError("allowed_ip not within configured pool CIDR")
    return str(addr)


def _wg_list_peers(iface: str) -> list[Dict[str, Any]]:
    cmd = ["wg", "show", iface, "dump"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "wg show dump failed")
    lines = [ln for ln in p.stdout.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    peers: list[Dict[str, Any]] = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        endpoint = parts[2] if parts[2] != "(none)" else None
        latest = int(parts[4]) if parts[4] else 0
        peers.append(
            {
                "public_key": parts[0],
                "endpoint": endpoint,
                "allowed_ips": parts[3],
                "latest_handshake": latest,
                "rx_bytes": int(parts[5]) if parts[5] else 0,
                "tx_bytes": int(parts[6]) if parts[6] else 0,
            }
        )
    return peers


BLOCK_CHAIN = "TRUSTEDGE_BLOCK"


def _ensure_block_chain() -> None:
    subprocess.run(["iptables", "-N", BLOCK_CHAIN], capture_output=True, text=True)
    check = subprocess.run(
        ["iptables", "-C", "FORWARD", "-j", BLOCK_CHAIN],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        insert = subprocess.run(
            ["iptables", "-I", "FORWARD", "1", "-j", BLOCK_CHAIN],
            capture_output=True,
            text=True,
        )
        if insert.returncode != 0:
            raise RuntimeError(insert.stderr.strip() or insert.stdout.strip() or "iptables insert failed")


def _iptables_add_block(client_ip: str) -> None:
    _ensure_block_chain()
    for args in (["-s", client_ip], ["-d", client_ip]):
        check = subprocess.run(
            ["iptables", "-C", BLOCK_CHAIN, *args, "-j", "DROP"],
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            add = subprocess.run(
                ["iptables", "-A", BLOCK_CHAIN, *args, "-j", "DROP"],
                capture_output=True,
                text=True,
            )
            if add.returncode != 0:
                raise RuntimeError(add.stderr.strip() or add.stdout.strip() or "iptables add failed")


def _iptables_remove_block(client_ip: str) -> None:
    for args in (["-s", client_ip], ["-d", client_ip]):
        while True:
            check = subprocess.run(
                ["iptables", "-C", BLOCK_CHAIN, *args, "-j", "DROP"],
                capture_output=True,
                text=True,
            )
            if check.returncode != 0:
                break
            delete = subprocess.run(
                ["iptables", "-D", BLOCK_CHAIN, *args, "-j", "DROP"],
                capture_output=True,
                text=True,
            )
            if delete.returncode != 0:
                raise RuntimeError(delete.stderr.strip() or delete.stdout.strip() or "iptables delete failed")



def _wg_set_peer_allowed_ips(iface: str, pubkey: str, allowed_ip: str) -> None:
    # `wg set` updates are in-memory; persistence is intentionally out of scope here.
    cmd = ["wg", "set", iface, "peer", pubkey, "allowed-ips", f"{allowed_ip}/32"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "wg set failed")


class Handler(BaseHTTPRequestHandler):
    server_version = "TrustEdgeWgAgent/1.0"

    def _json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Keep logs simple on systemd journal
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        server: "AgentServer" = self.server  # type: ignore[assignment]
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"status": "ok"})
            return
        if parsed.path == "/v1/peers":
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {server.token}":
                self._json(401, {"detail": "unauthorized"})
                return
            try:
                peers = _wg_list_peers(server.iface)
            except Exception as e:
                self._json(500, {"detail": str(e)})
                return
            self._json(200, {"interface": server.iface, "peers": peers})
            return
        self._json(404, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        server: "AgentServer" = self.server  # type: ignore[assignment]
        parsed = urlparse(self.path)
        allowed_paths = (
            "/v1/apply-peer",
            "/v1/block-client",
            "/v1/unblock-client",
        )
        if parsed.path not in allowed_paths:
            self._json(404, {"detail": "not found"})
            return

        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {server.token}":
            self._json(401, {"detail": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0 or length > 64_000:
            self._json(400, {"detail": "invalid body"})
            return

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._json(400, {"detail": "invalid json"})
            return

        if not isinstance(data, dict):
            self._json(400, {"detail": "invalid json"})
            return

        if parsed.path in ("/v1/block-client", "/v1/unblock-client"):
            try:
                client_ip = _validate_ipv4(str(data.get("client_ip", "")), server.pool_cidr)
            except Exception as e:
                self._json(400, {"detail": str(e)})
                return
            try:
                if parsed.path == "/v1/block-client":
                    _iptables_add_block(client_ip)
                else:
                    _iptables_remove_block(client_ip)
            except Exception as e:
                self._json(500, {"detail": str(e)})
                return
            self._json(200, {"applied": True, "client_ip": client_ip, "blocked": parsed.path == "/v1/block-client"})
            return

        try:
            pubkey = _validate_pubkey(str(data.get("public_key", "")))
            allowed_ip = _validate_ipv4(str(data.get("allowed_ip", "")), server.pool_cidr)
        except Exception as e:
            self._json(400, {"detail": str(e)})
            return

        try:
            _wg_set_peer_allowed_ips(server.iface, pubkey, allowed_ip)
        except Exception as e:
            self._json(500, {"detail": str(e)})
            return

        self._json(200, {"applied": True, "interface": server.iface, "public_key": pubkey, "allowed_ip": allowed_ip})


class AgentServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, *, token: str, iface: str, pool_cidr: str):
        super().__init__(server_address, RequestHandlerClass)
        self.token = token
        self.iface = iface
        self.pool_cidr = pool_cidr


def main() -> int:
    bind = os.getenv("TRUSTEDGE_WG_AGENT_BIND", "172.17.0.1")
    port = int(os.getenv("TRUSTEDGE_WG_AGENT_PORT", "9109"))
    token = _env("TRUSTEDGE_WG_AGENT_TOKEN")
    iface = os.getenv("TRUSTEDGE_WG_INTERFACE", "wg0")
    pool_cidr = os.getenv("TRUSTEDGE_WG_POOL_CIDR", "10.0.0.0/24")

    httpd = AgentServer((bind, port), Handler, token=token, iface=iface, pool_cidr=pool_cidr)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
