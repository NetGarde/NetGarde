from __future__ import annotations

import json
import re
from typing import Optional

from app.features.twin.schemas.simulation_command import SimulationCommandRequest, SimulationCommandResponse
from app.shared.config import settings

_HTTPS = 443
_HTTP = 80
_WELL_KNOWN = {
    "https": _HTTPS,
    "http": _HTTP,
    "dns": 53,
    "ssh": 22,
    "rdp": 3389,
}


def _rules_parse(prompt: str, active_ports: list[int]) -> Optional[SimulationCommandResponse]:
    text = prompt.strip().lower()
    if not text:
        return None

    if re.search(r"\b(clear|reset|unblock all|remove all blocks)\b", text):
        return SimulationCommandResponse(
            action="clear_simulation",
            message="Clear all simulated blocks.",
            source="rules",
        )

    unblock = re.search(r"\bunblock(?:\s+port)?\s+(\d{1,5})\b", text)
    if unblock:
        port = int(unblock.group(1))
        return SimulationCommandResponse(
            action="unblock_port",
            port=port,
            message=f"Stop simulating block on port {port}.",
            source="rules",
        )

    block = re.search(
        r"\b(?:block|deny|drop|stop)\s+(?:port\s+|tcp\s+|udp\s+)?(\d{1,5})\b",
        text,
    )
    if block:
        port = int(block.group(1))
        return SimulationCommandResponse(
            action="block_port",
            port=port,
            message=f"Simulate blocking port {port} at the EC2 gateway.",
            source="rules",
        )

    for name, port in _WELL_KNOWN.items():
        if re.search(rf"\b(?:block|deny|drop|stop)\s+{re.escape(name)}\b", text):
            return SimulationCommandResponse(
                action="block_port",
                port=port,
                message=f"Simulate blocking {name.upper()} traffic (port {port}).",
                source="rules",
            )

    if re.search(r"\b(?:block|deny|drop|stop)\s+(?:wireguard|wire\s*guard|vpn(?:\s+tunnel)?|the\s+tunnel)\b", text):
        return SimulationCommandResponse(
            action="block_tunnel",
            message="Simulate WireGuard tunnel down — DNS and VPN egress paths cut.",
            source="rules",
        )

    if re.search(r"\bunblock\s+(?:wireguard|wire\s*guard|vpn(?:\s+tunnel)?|the\s+tunnel)\b", text):
        return SimulationCommandResponse(
            action="unblock_tunnel",
            message="Restore simulated WireGuard tunnel.",
            source="rules",
        )

    if re.search(
        r"\b(?:block|deny|drop|stop)\s+(?:ec2\s+dns|dns\s+gateway|dns\s+resolver|the\s+gateway|gateway)\b",
        text,
    ):
        return SimulationCommandResponse(
            action="block_gateway",
            message="Simulate EC2 DNS gateway failure — port and session paths cut.",
            source="rules",
        )

    if re.search(r"\bunblock\s+(?:ec2\s+dns|dns\s+gateway|gateway)\b", text):
        return SimulationCommandResponse(
            action="unblock_gateway",
            message="Restore simulated EC2 DNS gateway.",
            source="rules",
        )

    only_port = re.search(r"\b(\d{1,5})\b", text)
    if only_port and re.search(r"\b(block|deny|drop|simulate)\b", text):
        port = int(only_port.group(1))
        if port in active_ports or port <= 65535:
            return SimulationCommandResponse(
                action="block_port",
                port=port,
                message=f"Simulate blocking port {port}.",
                source="rules",
            )

    if re.search(r"\bwhat[- ]?if\b", text) and re.search(r"\b(block|simulate|disable)\b", text):
        return SimulationCommandResponse(
            action="enable_what_if",
            message="Turn on what-if simulation mode.",
            source="rules",
        )

    return None


def _ollama_parse(body: SimulationCommandRequest) -> SimulationCommandResponse:
    from app.features.dashboard.services.ollama_connectivity import ensure_model_available, resolve_ollama_base_url

    import httpx

    base = resolve_ollama_base_url()
    ensure_model_available(base)

    example = (
        '{"action":"block_port","port":443,"app_slug":null,'
        '"message":"Simulate blocking HTTPS (port 443)."}'
    )
    system = (
        "You translate network operator commands into JSON for a VPN digital twin simulator. "
        "Allowed actions: block_port, unblock_port, block_tunnel, unblock_tunnel, "
        "block_gateway, unblock_gateway, clear_simulation, enable_what_if, noop, unknown. "
        "Use block_tunnel for wireguard/vpn/tunnel down. "
        "Use block_gateway for EC2 DNS / gateway failure. "
        "Use block_port with port number for port blocks. "
        "Use clear_simulation for reset/clear/unblock all. "
        "Use enable_what_if when user wants simulation mode without a specific target. "
        f"Return ONLY valid JSON like: {example}"
    )
    user = json.dumps(
        {
            "prompt": body.prompt,
            "active_ports": body.active_ports[:20],
            "active_apps": body.active_apps[:20],
            "hints": {"https": 443, "http": 80, "dns": 53},
        },
        separators=(",", ":"),
    )

    payload = {
        "model": settings.OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0.1, "num_predict": 200, "num_ctx": 2048},
    }
    timeout = httpx.Timeout(connect=15.0, read=settings.LLM_TIMEOUT_SEC, write=30.0, pool=15.0)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{base.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Ollama returned an empty message")

    parsed = json.loads(content)
    action = str(parsed.get("action") or "unknown")
    allowed = {
        "block_port", "unblock_port", "block_tunnel", "unblock_tunnel",
        "block_gateway", "unblock_gateway", "clear_simulation", "enable_what_if", "noop", "unknown",
    }
    if action not in allowed:
        action = "unknown"

    port_raw = parsed.get("port")
    port = int(port_raw) if port_raw is not None and str(port_raw).isdigit() else None
    app_slug = parsed.get("app_slug")
    if app_slug is not None:
        app_slug = str(app_slug).strip() or None

    message = str(parsed.get("message") or "Command parsed.").strip()
    return SimulationCommandResponse(
        action=action,  # type: ignore[arg-type]
        port=port,
        app_slug=app_slug,
        message=message,
        source="ollama",
    )


class SimulationCommandService:
    def parse(self, body: SimulationCommandRequest) -> SimulationCommandResponse:
        ruled = _rules_parse(body.prompt, body.active_ports)
        if ruled is not None:
            return ruled

        try:
            return _ollama_parse(body)
        except Exception as exc:
            return SimulationCommandResponse(
                action="unknown",
                message=f"Could not parse command (Ollama unavailable: {exc}). Try: block port 443",
                source="ollama",
            )
