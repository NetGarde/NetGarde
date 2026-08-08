"""Correlate accumulated ProcessState artifacts into multi-signal alerts.

These rules read the in-memory process graph (network / files / registry /
risk score) rather than a single Kafka event in isolation.
"""

from __future__ import annotations

from typing import Any

from rules.alerts import SecurityAlert
from rules.chain import ChainEvent, DeviceChain, payload_int, payload_str, ts_iso
from rules.constants import (
    ALERT_DROPPER_BEHAVIOR,
    ALERT_ELEVATED_PROCESS_RISK,
    ALERT_PERSISTENCE_WITH_NETWORK,
    ALERT_PROCESS_NETWORK_ACTIVITY,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_SCORE,
)
from rules.state import ProcessState, StateStore

# Accumulated risk: one high hit alone is not enough; need more signal.
ELEVATED_RISK_THRESHOLD = 100


def _process_detail(proc: ProcessState) -> dict[str, Any]:
    return {
        "process_id": proc.process_id,
        "pid": proc.pid,
        "ppid": proc.ppid,
        "process_name": proc.process_name,
        "command_line": proc.command_line or None,
        "current_risk_score": proc.current_risk_score,
        "matched_rules": list(proc.matched_rules),
        "network_connection_count": len(proc.network_connections),
        "created_file_count": len(proc.created_files),
        "registry_change_count": len(proc.modified_registry_keys),
        "created_files": [f.path for f in proc.created_files[:5]],
        "remote_addrs": [
            c.remote_addr for c in proc.network_connections[:5] if c.remote_addr
        ],
        "registry_keys": [r.key for r in proc.modified_registry_keys[:5]],
    }


def _alert(
    *,
    device_id: str,
    proc: ProcessState,
    alert_type: str,
    severity: str,
    message: str,
    source: ChainEvent | None,
    extra: dict[str, Any] | None = None,
) -> SecurityAlert:
    detail = _process_detail(proc)
    if extra:
        detail.update(extra)
    ts = ts_iso(source.ts) if source is not None else (proc.end_time or proc.start_time)
    return SecurityAlert(
        timestamp=ts,
        device_id=device_id,
        event_id=source.event_id if source is not None else None,
        event_type=source.event_type if source is not None else None,
        alert_type=alert_type,
        severity=severity,
        message=message,
        detail=DeviceChain.detail_json(detail),
    )


def _should_emit(proc: ProcessState, alert_type: str) -> bool:
    """Emit each correlation alert at most once per process lifetime."""
    return alert_type not in proc.matched_rules


def _emit(
    *,
    device_id: str,
    proc: ProcessState,
    alert_type: str,
    severity: str,
    message: str,
    source: ChainEvent | None,
    extra: dict[str, Any] | None = None,
) -> SecurityAlert | None:
    if not _should_emit(proc, alert_type):
        return None
    delta = SEVERITY_SCORE.get(severity, 0)
    proc.note_rule_match(alert_type, score_delta=delta)
    return _alert(
        device_id=device_id,
        proc=proc,
        alert_type=alert_type,
        severity=severity,
        message=message,
        source=source,
        extra=extra,
    )


def evaluate_dropper_behavior(proc: ProcessState) -> bool:
    return bool(proc.created_files) and bool(proc.network_connections)


def evaluate_persistence_with_network(proc: ProcessState) -> bool:
    return bool(proc.modified_registry_keys) and bool(proc.network_connections)


def evaluate_elevated_risk(proc: ProcessState) -> bool:
    return proc.current_risk_score >= ELEVATED_RISK_THRESHOLD


def evaluate_process_correlations(
    store: StateStore,
    device_id: str,
    *,
    trigger: ChainEvent | None = None,
    event: dict[str, Any] | None = None,
) -> list[SecurityAlert]:
    """Run process-state correlation rules for the process tied to this event."""
    device_id = (device_id or "").strip()
    if not device_id:
        return []

    proc: ProcessState | None = None
    payload: dict[str, Any] = {}
    if event and isinstance(event.get("payload"), dict):
        payload = event["payload"]
    elif trigger is not None:
        payload = trigger.payload

    for key in ("process_id", "process_guid", "guid"):
        explicit = payload_str(payload.get(key))
        if explicit:
            proc = store.get_process(device_id, explicit)
            if proc is not None:
                break

    if proc is None:
        pid = payload_int(payload.get("pid"))
        if pid > 0:
            proc = store.get_process_by_pid(device_id, pid)

    if proc is None:
        return []

    alerts: list[SecurityAlert] = []
    name = proc.process_name or f"pid:{proc.pid}"

    if evaluate_dropper_behavior(proc):
        alert = _emit(
            device_id=device_id,
            proc=proc,
            alert_type=ALERT_DROPPER_BEHAVIOR,
            severity=SEVERITY_HIGH,
            message=(
                f"Process {name} wrote files and opened network connections "
                "(possible dropper)"
            ),
            source=trigger,
        )
        if alert is not None:
            alerts.append(alert)

    if evaluate_persistence_with_network(proc):
        alert = _emit(
            device_id=device_id,
            proc=proc,
            alert_type=ALERT_PERSISTENCE_WITH_NETWORK,
            severity=SEVERITY_HIGH,
            message=(
                f"Process {name} modified persistence artifacts and used the network"
            ),
            source=trigger,
        )
        if alert is not None:
            alerts.append(alert)

    # First outbound/established socket on a process that already matched a rule
    # (so the graph can show the connection after process_start alerts).
    if (
        proc.matched_rules
        and proc.network_connections
        and _should_emit(proc, ALERT_PROCESS_NETWORK_ACTIVITY)
    ):
        alert = _emit(
            device_id=device_id,
            proc=proc,
            alert_type=ALERT_PROCESS_NETWORK_ACTIVITY,
            severity=SEVERITY_MEDIUM,
            message=f"Process {name} opened a network connection after prior detections",
            source=trigger,
        )
        if alert is not None:
            alerts.append(alert)

    if evaluate_elevated_risk(proc):
        alert = _emit(
            device_id=device_id,
            proc=proc,
            alert_type=ALERT_ELEVATED_PROCESS_RISK,
            severity=SEVERITY_MEDIUM,
            message=(
                f"Process {name} accumulated elevated risk "
                f"(score={proc.current_risk_score})"
            ),
            source=trigger,
            extra={"threshold": ELEVATED_RISK_THRESHOLD},
        )
        if alert is not None:
            alerts.append(alert)

    return alerts
