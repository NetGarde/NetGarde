"""Attach network_connection events to AI sessions."""

from __future__ import annotations

from typing import Any

from ai_activity.detector import is_notable_domain, is_private_ip
from ai_activity.dns_enrichment import resolve_network_name
from ai_activity.models import AISession, NetworkActivity, TimelineEvent


def record_network(
    session: AISession,
    *,
    process_id: str,
    payload: dict[str, Any],
    timestamp: str,
) -> NetworkActivity:
    remote_addr = str(
        payload.get("remote_addr")
        or payload.get("dest_ip")
        or payload.get("remote_ip")
        or ""
    ).strip()
    remote_port = int(payload.get("remote_port") or payload.get("dest_port") or 0)
    protocol = str(payload.get("protocol") or "").strip().lower()
    direction = str(payload.get("direction") or "").strip().lower()
    domain = resolve_network_name(remote_addr, payload=payload)
    external = not is_private_ip(remote_addr)

    bytes_sent = int(payload.get("bytes_sent") or payload.get("tx_bytes") or 0)
    bytes_recv = int(payload.get("bytes_recv") or payload.get("rx_bytes") or 0)

    activity = NetworkActivity(
        process_id=process_id,
        remote_addr=remote_addr,
        remote_port=remote_port,
        protocol=protocol,
        direction=direction,
        domain=domain,
        timestamp=timestamp,
        is_external=external,
        bytes_sent=max(0, bytes_sent),
        bytes_recv=max(0, bytes_recv),
    )
    session.networks.append(activity)
    session.counters.network_connections = len(session.networks)

    if external and domain:
        session.add_domain(domain)
    elif external and remote_addr:
        session.add_domain(remote_addr)

    display = domain or remote_addr or "unknown"
    label = display
    if remote_port:
        label = f"{label}:{remote_port}"
    # Keep IP visible in the timeline when we resolved a hostname.
    if domain and remote_addr and domain != remote_addr:
        summary = f"network {direction or 'conn'} {label} ({remote_addr})"
    else:
        summary = f"network {direction or 'conn'} {label}"
    notable = is_notable_domain(domain)
    session.append_timeline(
        TimelineEvent(
            kind="network",
            timestamp=timestamp,
            process_id=process_id,
            summary=summary,
            artifacts={
                "remote_addr": remote_addr,
                "remote_port": remote_port,
                "protocol": protocol,
                "direction": direction,
                "domain": domain,
                "external": external,
                "notable": notable,
            },
        )
    )
    return activity
