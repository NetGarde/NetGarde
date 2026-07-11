"""Multi-event (chain) detection rules for TrustTwin telemetry.

Each rule inspects recent events for one device and may emit zero or more alerts.
Rules are intentionally explicit and auditable (no LLM).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Callable

from rules.alerts import TwinAlert
from rules.chain import (
    TYPE_ACTION_SUMMARY,
    TYPE_CLIENT_DETAILS,
    TYPE_NETWORK_SUMMARY,
    ChainEvent,
    DeviceChain,
    payload_int,
    payload_str,
    ts_iso,
)

PRESENCE_ACTIVE = "active"
PRESENCE_IDLE = "idle"

WindowRule = Callable[[DeviceChain], list[TwinAlert]]


def _alert(
    chain: DeviceChain,
    *,
    source: ChainEvent,
    alert_type: str,
    severity: str,
    message: str,
    detail: dict | None = None,
) -> TwinAlert:
    return TwinAlert(
        timestamp=ts_iso(source.ts),
        trusttwin_device_id=chain.device_id,
        event_id=source.event_id,
        event_type=source.event_type,
        alert_type=alert_type,
        severity=severity,
        message=message,
        detail=DeviceChain.detail_json(detail) if detail else None,
    )


def _network_pairs(events: list[ChainEvent]) -> list[tuple[ChainEvent, ChainEvent]]:
    nets = [ev for ev in events if ev.event_type == TYPE_NETWORK_SUMMARY]
    return [(nets[i - 1], nets[i]) for i in range(1, len(nets))]


# --- Single-step (last two network events) -----------------------------------


def rule_new_public_ip(chain: DeviceChain) -> list[TwinAlert]:
    """Public IP changed between consecutive network_summary events."""
    alerts: list[TwinAlert] = []
    for prev, cur in _network_pairs(chain.events):
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        if old_ip and new_ip and old_ip != new_ip:
            alerts.append(
                _alert(
                    chain,
                    source=cur,
                    alert_type="new_public_ip",
                    severity="high",
                    message=f"Public IP changed from {old_ip} to {new_ip}",
                    detail={"from": old_ip, "to": new_ip},
                )
            )
    return alerts[-1:] if alerts else []


def rule_network_type_change(chain: DeviceChain) -> list[TwinAlert]:
    """Network type changed between consecutive network_summary events."""
    alerts: list[TwinAlert] = []
    for prev, cur in _network_pairs(chain.events):
        old_type = payload_str(prev.payload.get("network_type"))
        new_type = payload_str(cur.payload.get("network_type"))
        if old_type and new_type and old_type != new_type:
            alerts.append(
                _alert(
                    chain,
                    source=cur,
                    alert_type="network_type_change",
                    severity="medium",
                    message=f"Network type changed from {old_type} to {new_type}",
                    detail={"from": old_type, "to": new_type},
                )
            )
    return alerts[-1:] if alerts else []


def rule_network_change_while_active(chain: DeviceChain) -> list[TwinAlert]:
    """Any network field change while latest presence is active."""
    if chain.latest_presence() != PRESENCE_ACTIVE:
        return []
    for prev, cur in _network_pairs(chain.events):
        old_type = payload_str(prev.payload.get("network_type"))
        new_type = payload_str(cur.payload.get("network_type"))
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        changed = (old_type and new_type and old_type != new_type) or (
            old_ip and new_ip and old_ip != new_ip
        )
        if changed:
            return [
                _alert(
                    chain,
                    source=cur,
                    alert_type="network_change_while_active",
                    severity="medium",
                    message="Network changed while user presence is active",
                    detail={"presence": PRESENCE_ACTIVE},
                )
            ]
    return []


def rule_simultaneous_ip_and_type_change(chain: DeviceChain) -> list[TwinAlert]:
    """Both public IP and network type changed on the same network_summary step."""
    for prev, cur in _network_pairs(chain.events):
        old_type = payload_str(prev.payload.get("network_type"))
        new_type = payload_str(cur.payload.get("network_type"))
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        if (
            old_type
            and new_type
            and old_type != new_type
            and old_ip
            and new_ip
            and old_ip != new_ip
        ):
            return [
                _alert(
                    chain,
                    source=cur,
                    alert_type="simultaneous_ip_and_type_change",
                    severity="high",
                    message="Public IP and network type changed together",
                    detail={
                        "from_ip": old_ip,
                        "to_ip": new_ip,
                        "from_type": old_type,
                        "to_type": new_type,
                    },
                )
            ]
    return []


# --- Windowed frequency / churn ----------------------------------------------


def rule_rapid_public_ip_changes(chain: DeviceChain) -> list[TwinAlert]:
    """3+ distinct public IPs within 15 minutes."""
    window = timedelta(minutes=15)
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    unique = list(
        dict.fromkeys(
            payload_str(ev.payload.get("public_ip"))
            for ev in nets
            if payload_str(ev.payload.get("public_ip"))
        )
    )
    if len(unique) >= 3:
        latest = nets[-1]
        return [
            _alert(
                chain,
                source=latest,
                alert_type="rapid_public_ip_changes",
                severity="high",
                message=f"Multiple public IPs in 15 minutes ({len(unique)} distinct)",
                detail={"ips": unique, "window_minutes": 15},
            )
        ]
    return []


def rule_double_ip_change_10m(chain: DeviceChain) -> list[TwinAlert]:
    """2+ IP changes (edges) within 10 minutes."""
    window = timedelta(minutes=10)
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    changes = 0
    for prev, cur in _network_pairs(nets):
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        if old_ip and new_ip and old_ip != new_ip:
            changes += 1
    if changes >= 2:
        return [
            _alert(
                chain,
                source=nets[-1],
                alert_type="double_ip_change_10m",
                severity="high",
                message=f"Public IP changed {changes} times within 10 minutes",
                detail={"changes": changes, "window_minutes": 10},
            )
        ]
    return []


def rule_network_type_flapping(chain: DeviceChain) -> list[TwinAlert]:
    """3+ network type changes within 10 minutes."""
    window = timedelta(minutes=10)
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    changes = 0
    for prev, cur in _network_pairs(nets):
        old_type = payload_str(prev.payload.get("network_type"))
        new_type = payload_str(cur.payload.get("network_type"))
        if old_type and new_type and old_type != new_type:
            changes += 1
    if changes >= 3:
        return [
            _alert(
                chain,
                source=nets[-1],
                alert_type="network_type_flapping",
                severity="medium",
                message=f"Network type flapped {changes} times within 10 minutes",
                detail={"changes": changes, "window_minutes": 10},
            )
        ]
    return []


def rule_network_flap_5m(chain: DeviceChain) -> list[TwinAlert]:
    """2+ network type changes within 5 minutes."""
    window = timedelta(minutes=5)
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    changes = 0
    for prev, cur in _network_pairs(nets):
        old_type = payload_str(prev.payload.get("network_type"))
        new_type = payload_str(cur.payload.get("network_type"))
        if old_type and new_type and old_type != new_type:
            changes += 1
    if changes >= 2:
        return [
            _alert(
                chain,
                source=nets[-1],
                alert_type="network_flap_5m",
                severity="medium",
                message=f"Rapid network type changes ({changes}) within 5 minutes",
                detail={"changes": changes, "window_minutes": 5},
            )
        ]
    return []


def rule_event_burst(chain: DeviceChain) -> list[TwinAlert]:
    """10+ events of any type within 5 minutes."""
    window = timedelta(minutes=5)
    recent = chain.in_window(window)
    if len(recent) >= 10:
        return [
            _alert(
                chain,
                source=recent[-1],
                alert_type="event_burst",
                severity="low",
                message=f"High event volume ({len(recent)} events in 5 minutes)",
                detail={"count": len(recent), "window_minutes": 5},
            )
        ]
    return []


def rule_repeated_network_summary(chain: DeviceChain) -> list[TwinAlert]:
    """6+ network_summary events in 10 minutes with no action_summary between."""
    window = timedelta(minutes=10)
    recent = chain.in_window(window)
    net_count = sum(1 for ev in recent if ev.event_type == TYPE_NETWORK_SUMMARY)
    action_count = sum(1 for ev in recent if ev.event_type == TYPE_ACTION_SUMMARY)
    if net_count >= 6 and action_count == 0:
        latest = chain.latest(TYPE_NETWORK_SUMMARY)
        if latest:
            return [
                _alert(
                    chain,
                    source=latest,
                    alert_type="repeated_network_summary",
                    severity="low",
                    message="Many network summaries without action context",
                    detail={"network_events": net_count, "window_minutes": 10},
                )
            ]
    return []


# --- Posture / socket anomalies ----------------------------------------------


def _net_metric_delta(
    chain: DeviceChain, field: str, *, min_delta: int, window: timedelta
) -> tuple[ChainEvent, ChainEvent, int] | None:
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    for prev, cur in _network_pairs(nets):
        old_val = payload_int(prev.payload.get(field))
        new_val = payload_int(cur.payload.get(field))
        if new_val - old_val >= min_delta:
            return prev, cur, new_val - old_val
    return None


def rule_established_count_spike(chain: DeviceChain) -> list[TwinAlert]:
    """Established connection count jumped by 50+ between consecutive summaries."""
    hit = _net_metric_delta(chain, "established_count", min_delta=50, window=timedelta(minutes=15))
    if not hit:
        return []
    prev, cur, delta = hit
    return [
        _alert(
            chain,
            source=cur,
            alert_type="established_count_spike",
            severity="medium",
            message=f"Established connections spiked by {delta}",
            detail={
                "from": payload_int(prev.payload.get("established_count")),
                "to": payload_int(cur.payload.get("established_count")),
            },
        )
    ]


def rule_listening_port_spike(chain: DeviceChain) -> list[TwinAlert]:
    """Listening port count jumped by 10+ between consecutive summaries."""
    hit = _net_metric_delta(chain, "listening_count", min_delta=10, window=timedelta(minutes=15))
    if not hit:
        return []
    prev, cur, delta = hit
    return [
        _alert(
            chain,
            source=cur,
            alert_type="listening_port_spike",
            severity="medium",
            message=f"Listening ports increased by {delta}",
            detail={
                "from": payload_int(prev.payload.get("listening_count")),
                "to": payload_int(cur.payload.get("listening_count")),
            },
        )
    ]


def rule_foreground_connections_spike(chain: DeviceChain) -> list[TwinAlert]:
    """Foreground app connections jumped by 20+ between consecutive summaries."""
    hit = _net_metric_delta(
        chain, "foreground_app_connections", min_delta=20, window=timedelta(minutes=15)
    )
    if not hit:
        return []
    prev, cur, delta = hit
    return [
        _alert(
            chain,
            source=cur,
            alert_type="foreground_connections_spike",
            severity="medium",
            message=f"Foreground app connections spiked by {delta}",
            detail={
                "from": payload_int(prev.payload.get("foreground_app_connections")),
                "to": payload_int(cur.payload.get("foreground_app_connections")),
            },
        )
    ]


def rule_high_listening_with_active_user(chain: DeviceChain) -> list[TwinAlert]:
    """User active and listening_count >= 20 on latest network summary."""
    if chain.latest_presence() != PRESENCE_ACTIVE:
        return []
    latest = chain.latest(TYPE_NETWORK_SUMMARY)
    if not latest:
        return []
    listening = payload_int(latest.payload.get("listening_count"))
    if listening >= 20:
        return [
            _alert(
                chain,
                source=latest,
                alert_type="high_listening_while_active",
                severity="low",
                message=f"Many listening ports ({listening}) while user is active",
                detail={"listening_count": listening},
            )
        ]
    return []


# --- Presence correlation ----------------------------------------------------


def rule_ip_change_while_idle(chain: DeviceChain) -> list[TwinAlert]:
    """IP changed while presence is idle (lower severity signal)."""
    if chain.latest_presence() != PRESENCE_IDLE:
        return []
    for prev, cur in _network_pairs(chain.events):
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        if old_ip and new_ip and old_ip != new_ip:
            return [
                _alert(
                    chain,
                    source=cur,
                    alert_type="ip_change_while_idle",
                    severity="low",
                    message=f"Public IP changed while idle ({old_ip} → {new_ip})",
                    detail={"from": old_ip, "to": new_ip, "presence": PRESENCE_IDLE},
                )
            ]
    return []


def rule_active_ip_churn(chain: DeviceChain) -> list[TwinAlert]:
    """2+ IP changes in 30 minutes while user stayed active."""
    if chain.latest_presence() != PRESENCE_ACTIVE:
        return []
    window = timedelta(minutes=30)
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    changes = 0
    for prev, cur in _network_pairs(nets):
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        if old_ip and new_ip and old_ip != new_ip:
            changes += 1
    if changes >= 2:
        return [
            _alert(
                chain,
                source=nets[-1],
                alert_type="active_ip_churn",
                severity="high",
                message=f"IP churn ({changes} changes) while user remained active",
                detail={"changes": changes, "window_minutes": 30},
            )
        ]
    return []


# --- Coverage / staleness ----------------------------------------------------


def rule_stale_client_details(chain: DeviceChain) -> list[TwinAlert]:
    """Network events in last 20 minutes but no client_details in that window."""
    window = timedelta(minutes=20)
    recent = chain.in_window(window)
    if not recent:
        return []
    nets = [ev for ev in recent if ev.event_type == TYPE_NETWORK_SUMMARY]
    has_client = any(ev.event_type == TYPE_CLIENT_DETAILS for ev in recent)
    if len(nets) >= 2 and not has_client:
        latest = chain.latest(TYPE_NETWORK_SUMMARY)
        if latest:
            return [
                _alert(
                    chain,
                    source=latest,
                    alert_type="stale_client_details",
                    severity="low",
                    message="Network telemetry without recent client heartbeat",
                    detail={"window_minutes": 20},
                )
            ]
    return []


def rule_missing_network_telemetry(chain: DeviceChain) -> list[TwinAlert]:
    """Client/action events in 30 minutes but no network_summary."""
    window = timedelta(minutes=30)
    recent = chain.in_window(window)
    if len(recent) < 3:
        return []
    has_net = any(ev.event_type == TYPE_NETWORK_SUMMARY for ev in recent)
    has_other = any(
        ev.event_type in (TYPE_CLIENT_DETAILS, TYPE_ACTION_SUMMARY) for ev in recent
    )
    if has_other and not has_net:
        latest = recent[-1]
        return [
            _alert(
                chain,
                source=latest,
                alert_type="missing_network_telemetry",
                severity="low",
                message="Client telemetry without network summary in 30 minutes",
                detail={"window_minutes": 30},
            )
        ]
    return []


def rule_long_idle_with_network(chain: DeviceChain) -> list[TwinAlert]:
    """Latest presence idle but network summaries keep arriving (3+ in 15m)."""
    if chain.latest_presence() != PRESENCE_IDLE:
        return []
    window = timedelta(minutes=15)
    nets = chain.of_type(TYPE_NETWORK_SUMMARY, window)
    if len(nets) >= 3:
        return [
            _alert(
                chain,
                source=nets[-1],
                alert_type="idle_with_network_activity",
                severity="low",
                message="Repeated network summaries while user is idle",
                detail={"network_events": len(nets), "window_minutes": 15},
            )
        ]
    return []


# --- Registry ----------------------------------------------------------------

CHAIN_RULES: list[tuple[str, WindowRule]] = [
    ("new_public_ip", rule_new_public_ip),
    ("network_type_change", rule_network_type_change),
    ("network_change_while_active", rule_network_change_while_active),
    ("simultaneous_ip_and_type_change", rule_simultaneous_ip_and_type_change),
    ("rapid_public_ip_changes", rule_rapid_public_ip_changes),
    ("double_ip_change_10m", rule_double_ip_change_10m),
    ("network_type_flapping", rule_network_type_flapping),
    ("network_flap_5m", rule_network_flap_5m),
    ("event_burst", rule_event_burst),
    ("repeated_network_summary", rule_repeated_network_summary),
    ("established_count_spike", rule_established_count_spike),
    ("listening_port_spike", rule_listening_port_spike),
    ("foreground_connections_spike", rule_foreground_connections_spike),
    ("high_listening_while_active", rule_high_listening_with_active_user),
    ("ip_change_while_idle", rule_ip_change_while_idle),
    ("active_ip_churn", rule_active_ip_churn),
    ("stale_client_details", rule_stale_client_details),
    ("missing_network_telemetry", rule_missing_network_telemetry),
    ("idle_with_network_activity", rule_long_idle_with_network),
]


def evaluate_chain(chain: DeviceChain) -> list[TwinAlert]:
    """Run all chain rules; dedupe by alert_type keeping highest severity."""
    severity_rank = {"low": 1, "medium": 2, "high": 3}
    by_type: dict[str, TwinAlert] = {}
    for _name, rule in CHAIN_RULES:
        for alert in rule(chain):
            existing = by_type.get(alert.alert_type)
            if existing is None or severity_rank.get(alert.severity, 0) > severity_rank.get(
                existing.severity, 0
            ):
                by_type[alert.alert_type] = alert
    return list(by_type.values())
