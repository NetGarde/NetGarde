"""Multi-event detection rules for TrustEdge Agent telemetry.

Rules are registered by trigger event type (network, process, security, …).
evaluate_chain runs only the matching lane plus cross-cutting ALWAYS_RULES.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Callable

from rules.alerts import SecurityAlert
from rules.chain import (
    ChainEvent,
    DeviceChain,
    payload_int,
    payload_str,
    ts_iso,
)
from rules.constants import (
    ALERT_ACTIVE_IP_CHURN,
    ALERT_DOUBLE_IP_CHANGE_10M,
    ALERT_ESTABLISHED_COUNT_SPIKE,
    ALERT_EVENT_BURST,
    ALERT_FOREGROUND_CONNECTIONS_SPIKE,
    ALERT_HIGH_LISTENING_WHILE_ACTIVE,
    ALERT_IDLE_WITH_NETWORK_ACTIVITY,
    ALERT_IP_CHANGE_WHILE_IDLE,
    ALERT_LISTENING_PORT_SPIKE,
    ALERT_MISSING_NETWORK_TELEMETRY,
    ALERT_NETWORK_CHANGE_WHILE_ACTIVE,
    ALERT_NETWORK_FLAP_5M,
    ALERT_NETWORK_TYPE_CHANGE,
    ALERT_NETWORK_TYPE_FLAPPING,
    ALERT_NEW_PUBLIC_IP,
    ALERT_RAPID_PUBLIC_IP_CHANGES,
    ALERT_REPEATED_NETWORK_SUMMARY,
    ALERT_SIMULTANEOUS_IP_AND_TYPE_CHANGE,
    ALERT_STALE_CLIENT_DETAILS,
    PRESENCE_ACTIVE,
    PRESENCE_IDLE,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_RANK,
    TYPE_ACTION_SUMMARY,
    TYPE_CLIENT_DETAILS,
    TYPE_DRIVER_LOAD,
    TYPE_NETWORK_SUMMARY,
    TYPE_PROCESS_START,
    TYPE_REGISTRY_PERSISTENCE,
    TYPE_SERVICE_INSTALL,
)

from rules.process_rules import PROCESS_RULES
from rules.security_rules import (
    DRIVER_LOAD_RULES,
    REGISTRY_PERSISTENCE_RULES,
    SERVICE_INSTALL_RULES,
)

WindowRule = Callable[[DeviceChain], list[SecurityAlert]]


def _alert(
    chain: DeviceChain,
    *,
    source: ChainEvent,
    alert_type: str,
    severity: str,
    message: str,
    detail: dict | None = None,
) -> SecurityAlert:
    return SecurityAlert(
        timestamp=ts_iso(source.ts),
        device_id=chain.device_id,
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


def rule_new_public_ip(chain: DeviceChain) -> list[SecurityAlert]:
    """Public IP changed between consecutive network_summary events."""
    alerts: list[SecurityAlert] = []
    for prev, cur in _network_pairs(chain.events):
        old_ip = payload_str(prev.payload.get("public_ip"))
        new_ip = payload_str(cur.payload.get("public_ip"))
        if old_ip and new_ip and old_ip != new_ip:
            alerts.append(
                _alert(
                    chain,
                    source=cur,
                    alert_type=ALERT_NEW_PUBLIC_IP,
                    severity=SEVERITY_HIGH,
                    message=f"Public IP changed from {old_ip} to {new_ip}",
                    detail={"from": old_ip, "to": new_ip},
                )
            )
    return alerts[-1:] if alerts else []


def rule_network_type_change(chain: DeviceChain) -> list[SecurityAlert]:
    """Network type changed between consecutive network_summary events."""
    alerts: list[SecurityAlert] = []
    for prev, cur in _network_pairs(chain.events):
        old_type = payload_str(prev.payload.get("network_type"))
        new_type = payload_str(cur.payload.get("network_type"))
        if old_type and new_type and old_type != new_type:
            alerts.append(
                _alert(
                    chain,
                    source=cur,
                    alert_type=ALERT_NETWORK_TYPE_CHANGE,
                    severity=SEVERITY_MEDIUM,
                    message=f"Network type changed from {old_type} to {new_type}",
                    detail={"from": old_type, "to": new_type},
                )
            )
    return alerts[-1:] if alerts else []


def rule_network_change_while_active(chain: DeviceChain) -> list[SecurityAlert]:
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
                    alert_type=ALERT_NETWORK_CHANGE_WHILE_ACTIVE,
                    severity=SEVERITY_MEDIUM,
                    message="Network changed while user presence is active",
                    detail={"presence": PRESENCE_ACTIVE},
                )
            ]
    return []


def rule_simultaneous_ip_and_type_change(chain: DeviceChain) -> list[SecurityAlert]:
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
                    alert_type=ALERT_SIMULTANEOUS_IP_AND_TYPE_CHANGE,
                    severity=SEVERITY_HIGH,
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


def rule_rapid_public_ip_changes(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_RAPID_PUBLIC_IP_CHANGES,
                severity=SEVERITY_HIGH,
                message=f"Multiple public IPs in 15 minutes ({len(unique)} distinct)",
                detail={"ips": unique, "window_minutes": 15},
            )
        ]
    return []


def rule_double_ip_change_10m(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_DOUBLE_IP_CHANGE_10M,
                severity=SEVERITY_HIGH,
                message=f"Public IP changed {changes} times within 10 minutes",
                detail={"changes": changes, "window_minutes": 10},
            )
        ]
    return []


def rule_network_type_flapping(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_NETWORK_TYPE_FLAPPING,
                severity=SEVERITY_MEDIUM,
                message=f"Network type flapped {changes} times within 10 minutes",
                detail={"changes": changes, "window_minutes": 10},
            )
        ]
    return []


def rule_network_flap_5m(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_NETWORK_FLAP_5M,
                severity=SEVERITY_MEDIUM,
                message=f"Rapid network type changes ({changes}) within 5 minutes",
                detail={"changes": changes, "window_minutes": 5},
            )
        ]
    return []


def rule_event_burst(chain: DeviceChain) -> list[SecurityAlert]:
    """10+ events of any type within 5 minutes."""
    window = timedelta(minutes=5)
    recent = chain.in_window(window)
    if len(recent) >= 10:
        return [
            _alert(
                chain,
                source=recent[-1],
                alert_type=ALERT_EVENT_BURST,
                severity=SEVERITY_LOW,
                message=f"High event volume ({len(recent)} events in 5 minutes)",
                detail={"count": len(recent), "window_minutes": 5},
            )
        ]
    return []


def rule_repeated_network_summary(chain: DeviceChain) -> list[SecurityAlert]:
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
                    alert_type=ALERT_REPEATED_NETWORK_SUMMARY,
                    severity=SEVERITY_LOW,
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


def rule_established_count_spike(chain: DeviceChain) -> list[SecurityAlert]:
    """Established connection count jumped by 50+ between consecutive summaries."""
    hit = _net_metric_delta(chain, "established_count", min_delta=50, window=timedelta(minutes=15))
    if not hit:
        return []
    prev, cur, delta = hit
    return [
        _alert(
            chain,
            source=cur,
            alert_type=ALERT_ESTABLISHED_COUNT_SPIKE,
            severity=SEVERITY_MEDIUM,
            message=f"Established connections spiked by {delta}",
            detail={
                "from": payload_int(prev.payload.get("established_count")),
                "to": payload_int(cur.payload.get("established_count")),
            },
        )
    ]


def rule_listening_port_spike(chain: DeviceChain) -> list[SecurityAlert]:
    """Listening port count jumped by 10+ between consecutive summaries."""
    hit = _net_metric_delta(chain, "listening_count", min_delta=10, window=timedelta(minutes=15))
    if not hit:
        return []
    prev, cur, delta = hit
    return [
        _alert(
            chain,
            source=cur,
            alert_type=ALERT_LISTENING_PORT_SPIKE,
            severity=SEVERITY_MEDIUM,
            message=f"Listening ports increased by {delta}",
            detail={
                "from": payload_int(prev.payload.get("listening_count")),
                "to": payload_int(cur.payload.get("listening_count")),
            },
        )
    ]


def rule_foreground_connections_spike(chain: DeviceChain) -> list[SecurityAlert]:
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
            alert_type=ALERT_FOREGROUND_CONNECTIONS_SPIKE,
            severity=SEVERITY_MEDIUM,
            message=f"Foreground app connections spiked by {delta}",
            detail={
                "from": payload_int(prev.payload.get("foreground_app_connections")),
                "to": payload_int(cur.payload.get("foreground_app_connections")),
            },
        )
    ]


def rule_high_listening_with_active_user(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_HIGH_LISTENING_WHILE_ACTIVE,
                severity=SEVERITY_LOW,
                message=f"Many listening ports ({listening}) while user is active",
                detail={"listening_count": listening},
            )
        ]
    return []


# --- Presence correlation ----------------------------------------------------


def rule_ip_change_while_idle(chain: DeviceChain) -> list[SecurityAlert]:
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
                    alert_type=ALERT_IP_CHANGE_WHILE_IDLE,
                    severity=SEVERITY_LOW,
                    message=f"Public IP changed while idle ({old_ip} → {new_ip})",
                    detail={"from": old_ip, "to": new_ip, "presence": PRESENCE_IDLE},
                )
            ]
    return []


def rule_active_ip_churn(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_ACTIVE_IP_CHURN,
                severity=SEVERITY_HIGH,
                message=f"IP churn ({changes} changes) while user remained active",
                detail={"changes": changes, "window_minutes": 30},
            )
        ]
    return []


# --- Coverage / staleness ----------------------------------------------------


def rule_stale_client_details(chain: DeviceChain) -> list[SecurityAlert]:
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
                    alert_type=ALERT_STALE_CLIENT_DETAILS,
                    severity=SEVERITY_LOW,
                    message="Network telemetry without recent client heartbeat",
                    detail={"window_minutes": 20},
                )
            ]
    return []


def rule_missing_network_telemetry(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_MISSING_NETWORK_TELEMETRY,
                severity=SEVERITY_LOW,
                message="Client telemetry without network summary in 30 minutes",
                detail={"window_minutes": 30},
            )
        ]
    return []


def rule_long_idle_with_network(chain: DeviceChain) -> list[SecurityAlert]:
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
                alert_type=ALERT_IDLE_WITH_NETWORK_ACTIVITY,
                severity=SEVERITY_LOW,
                message="Repeated network summaries while user is idle",
                detail={"network_events": len(nets), "window_minutes": 15},
            )
        ]
    return []


# --- Registry ----------------------------------------------------------------

# Network / presence-gated detections — triggered by network_summary.
NETWORK_RULES: list[tuple[str, WindowRule]] = [
    (ALERT_NEW_PUBLIC_IP, rule_new_public_ip),
    (ALERT_NETWORK_TYPE_CHANGE, rule_network_type_change),
    (ALERT_NETWORK_CHANGE_WHILE_ACTIVE, rule_network_change_while_active),
    (ALERT_SIMULTANEOUS_IP_AND_TYPE_CHANGE, rule_simultaneous_ip_and_type_change),
    (ALERT_RAPID_PUBLIC_IP_CHANGES, rule_rapid_public_ip_changes),
    (ALERT_DOUBLE_IP_CHANGE_10M, rule_double_ip_change_10m),
    (ALERT_NETWORK_TYPE_FLAPPING, rule_network_type_flapping),
    (ALERT_NETWORK_FLAP_5M, rule_network_flap_5m),
    (ALERT_REPEATED_NETWORK_SUMMARY, rule_repeated_network_summary),
    (ALERT_ESTABLISHED_COUNT_SPIKE, rule_established_count_spike),
    (ALERT_LISTENING_PORT_SPIKE, rule_listening_port_spike),
    (ALERT_FOREGROUND_CONNECTIONS_SPIKE, rule_foreground_connections_spike),
    (ALERT_HIGH_LISTENING_WHILE_ACTIVE, rule_high_listening_with_active_user),
    (ALERT_IP_CHANGE_WHILE_IDLE, rule_ip_change_while_idle),
    (ALERT_ACTIVE_IP_CHURN, rule_active_ip_churn),
    (ALERT_STALE_CLIENT_DETAILS, rule_stale_client_details),
    (ALERT_IDLE_WITH_NETWORK_ACTIVITY, rule_long_idle_with_network),
]

# Coverage gaps — triggered by client/action telemetry without network.
COVERAGE_RULES: list[tuple[str, WindowRule]] = [
    (ALERT_MISSING_NETWORK_TELEMETRY, rule_missing_network_telemetry),
]

# Cross-cutting volume rule — runs for every event type.
ALWAYS_RULES: list[tuple[str, WindowRule]] = [
    (ALERT_EVENT_BURST, rule_event_burst),
]

# Flat list kept for discovery / tests.
CHAIN_RULES: list[tuple[str, WindowRule]] = [
    *NETWORK_RULES,
    *ALWAYS_RULES,
    *COVERAGE_RULES,
]

RULES_BY_TYPE: dict[str, list[tuple[str, object]]] = {
    TYPE_NETWORK_SUMMARY: NETWORK_RULES,
    TYPE_PROCESS_START: PROCESS_RULES,
    TYPE_ACTION_SUMMARY: COVERAGE_RULES,
    TYPE_CLIENT_DETAILS: COVERAGE_RULES,
    TYPE_DRIVER_LOAD: DRIVER_LOAD_RULES,
    TYPE_SERVICE_INSTALL: SERVICE_INSTALL_RULES,
    TYPE_REGISTRY_PERSISTENCE: REGISTRY_PERSISTENCE_RULES,
}


def evaluate_chain(
    chain: DeviceChain,
    *,
    trigger: ChainEvent | None = None,
) -> list[SecurityAlert]:
    """Run rules for the triggering event type; dedupe by alert_type keeping highest severity."""
    source = trigger or chain.latest()
    if source is None:
        return []

    typed_rules = RULES_BY_TYPE.get(source.event_type, [])
    by_type: dict[str, SecurityAlert] = {}
    for _name, rule in [*typed_rules, *ALWAYS_RULES]:
        for alert in rule(chain):
            existing = by_type.get(alert.alert_type)
            if existing is None or SEVERITY_RANK.get(alert.severity, 0) > SEVERITY_RANK.get(
                existing.severity, 0
            ):
                by_type[alert.alert_type] = alert
    return list(by_type.values())
