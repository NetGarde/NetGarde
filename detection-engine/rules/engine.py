from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from rules.alerts import SecurityAlert
from rules.chain import ChainEvent, DeviceChain, payload_int, payload_str, ts_iso
from rules.chain_rules import evaluate_chain
from rules.constants import SEVERITY_RANK, SEVERITY_SCORE, TYPE_PROCESS_START
from rules.process_correlation import evaluate_process_correlations
from rules.state import ProcessState, StateStore

__all__ = ["SecurityAlert", "evaluate_event", "with_alert_context"]


PROCESS_CONTEXT_WINDOW = timedelta(minutes=5)
# Cap processes in the reconstructed spawn tree so alert payloads stay bounded.
MAX_SESSION_TREE = 80


def _resolve_process_for_event(
    store: StateStore,
    device_id: str,
    event: dict[str, Any],
) -> ProcessState | None:
    payload = event.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    for key in ("process_id", "process_guid", "guid"):
        explicit = payload_str(payload.get(key))
        if explicit:
            found = store.get_process(device_id, explicit)
            if found is not None:
                return found
    pid = payload_int(payload.get("pid"))
    if pid > 0:
        return store.get_process_by_pid(device_id, pid)
    return None


def _apply_rule_matches(
    store: StateStore,
    device_id: str,
    event: dict[str, Any],
    alerts: list[SecurityAlert],
) -> ProcessState | None:
    """Attribute alerts onto ProcessState (matched_rules + risk score)."""
    proc = _resolve_process_for_event(store, device_id, event)
    if proc is None:
        return None
    for alert in alerts:
        delta = SEVERITY_SCORE.get((alert.severity or "").strip().lower(), 0)
        proc.note_rule_match(alert.alert_type, score_delta=delta)
    return proc


def _merge_alerts(*groups: list[SecurityAlert]) -> list[SecurityAlert]:
    """Dedupe by alert_type, keeping the highest severity."""
    by_type: dict[str, SecurityAlert] = {}
    for group in groups:
        for alert in group:
            existing = by_type.get(alert.alert_type)
            if existing is None or SEVERITY_RANK.get(alert.severity, 0) > SEVERITY_RANK.get(
                existing.severity, 0
            ):
                by_type[alert.alert_type] = alert
    return list(by_type.values())


def _source_event(chain: DeviceChain, alert: SecurityAlert) -> ChainEvent | None:
    if alert.event_id:
        for item in reversed(chain.events):
            if item.event_id == alert.event_id:
                return item
    for item in reversed(chain.events):
        if alert.event_type and item.event_type != alert.event_type:
            continue
        if ts_iso(item.ts) == alert.timestamp:
            return item
    return chain.latest()


def _parent_event(starts: list[ChainEvent], child: ChainEvent) -> ChainEvent | None:
    ppid = payload_int(child.payload.get("ppid"))
    if ppid <= 0:
        return None
    for item in reversed(starts):
        if item.ts <= child.ts and payload_int(item.payload.get("pid")) == ppid:
            return item
    return None


def _process_sample(
    item: ChainEvent,
    *,
    source: ChainEvent | None,
    parent: ChainEvent | None,
) -> dict[str, Any]:
    payload = item.payload
    executable = payload_str(payload.get("executable"))
    comm = payload_str(payload.get("comm")) or executable.rsplit("/", 1)[-1]
    sample: dict[str, Any] = {
        "event_id": item.event_id,
        "pid": payload_int(payload.get("pid")),
        "ppid": payload_int(payload.get("ppid")),
        "comm": comm or "unknown",
        "started_at": ts_iso(item.ts),
        "role": "trigger" if item is source else "context",
    }
    for key in ("parent_comm", "executable", "cmdline"):
        value = payload_str(payload.get(key))
        if value:
            sample[key] = value
    if "parent_comm" not in sample and parent is not None:
        parent_executable = payload_str(parent.payload.get("executable"))
        parent_comm = payload_str(parent.payload.get("comm")) or parent_executable.rsplit("/", 1)[-1]
        if parent_comm:
            sample["parent_comm"] = parent_comm
    return sample


def _process_context(
    chain: DeviceChain,
    source: ChainEvent | None,
    *,
    alert_type: str,
) -> list[dict[str, Any]]:
    del alert_type  # retained for call-site compatibility
    if source is None:
        return []
    if source.event_type != TYPE_PROCESS_START:
        return []

    # All process starts at or before the trigger (siblings after the trigger
    # are not in the chain yet when this alert is emitted).
    starts = [
        item
        for item in chain.events
        if item.event_type == TYPE_PROCESS_START and item.ts <= source.ts
    ]

    sampled = [source]
    included = {id(item) for item in sampled}

    # Ancestors (parent shell / grandparents) for the causal spine.
    ancestors: list[ChainEvent] = []
    parent = _parent_event(starts, source)
    while parent is not None and id(parent) not in included:
        ancestors.append(parent)
        included.add(id(parent))
        parent = _parent_event(starts, parent)

    # Root of the ancestry spine (top-most known parent), else the trigger itself.
    root = ancestors[-1] if ancestors else source
    root_pid = payload_int(root.payload.get("pid"))
    spine_pids = {payload_int(item.payload.get("pid")) for item in ancestors}
    spine_pids.add(payload_int(source.payload.get("pid")))
    spine_pids.add(root_pid)
    spine_pids.discard(0)

    # Full spawn tree under that root within the recent window: any process whose
    # parent walk reaches the root / ancestry spine (not only same-ppid siblings).
    cutoff = source.ts - PROCESS_CONTEXT_WINDOW

    def _reaches_spine(item: ChainEvent) -> bool:
        seen: set[int] = set()
        current: ChainEvent | None = item
        for _ in range(24):
            if current is None:
                return False
            pid = payload_int(current.payload.get("pid"))
            if pid <= 0 or pid in seen:
                return False
            if pid in spine_pids:
                return True
            seen.add(pid)
            current = _parent_event(starts, current)
        return False

    tree_members: list[ChainEvent] = []
    for item in starts:
        if item.ts < cutoff:
            continue
        if id(item) in included:
            continue
        if _reaches_spine(item):
            tree_members.append(item)
            included.add(id(item))

    # Prefer processes closer to the trigger time if the tree is huge.
    if len(tree_members) > MAX_SESSION_TREE:
        tree_members = sorted(tree_members, key=lambda item: item.ts)[-MAX_SESSION_TREE:]

    ordered = sorted(ancestors + tree_members + sampled, key=lambda item: item.ts)
    # Deduplicate by event identity while preserving order
    seen_ids: set[int] = set()
    unique: list[ChainEvent] = []
    for item in ordered:
        if id(item) in seen_ids:
            continue
        seen_ids.add(id(item))
        unique.append(item)

    return [
        _process_sample(item, source=source, parent=_parent_event(starts, item))
        for item in unique
    ]


def _process_state_sample(proc: ProcessState, *, role: str = "trigger") -> dict[str, Any]:
    sample: dict[str, Any] = {
        "pid": proc.pid,
        "ppid": proc.ppid,
        "comm": proc.process_name or "unknown",
        "started_at": proc.start_time,
        "role": role,
        "process_id": proc.process_id,
    }
    if proc.command_line:
        sample["cmdline"] = proc.command_line
    return sample


def _serialize_network_connections(proc: ProcessState) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for conn in proc.network_connections:
        item: dict[str, Any] = {
            "pid": proc.pid,
            "remote_addr": conn.remote_addr,
            "remote_port": conn.remote_port,
            "local_addr": conn.local_addr,
            "local_port": conn.local_port,
            "protocol": conn.protocol,
            "direction": conn.direction,
            "timestamp": conn.timestamp,
        }
        out.append(item)
    return out


def _serialize_created_files(proc: ProcessState) -> list[dict[str, Any]]:
    return [
        {
            "pid": proc.pid,
            "path": item.path,
            "operation": item.operation,
            "timestamp": item.timestamp,
        }
        for item in proc.created_files
    ]


def _enrich_from_process_state(
    store: StateStore,
    device_id: str,
    event: dict[str, Any],
    detail: dict[str, Any],
    processes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach living ProcessState artifacts (network / files) for the graph UI."""
    proc = _resolve_process_for_event(store, device_id, event)
    if proc is None and detail.get("process_id"):
        proc = store.get_process(device_id, str(detail["process_id"]))
    if proc is None and detail.get("pid") is not None:
        proc = store.get_process_by_pid(device_id, payload_int(detail.get("pid")))
    if proc is None:
        # Fall back to trigger pid already present in process samples.
        for row in processes:
            if row.get("role") == "trigger":
                proc = store.get_process_by_pid(device_id, payload_int(row.get("pid")))
                if proc is not None:
                    break
    if proc is None:
        return processes

    detail["process_id"] = proc.process_id
    detail["current_risk_score"] = proc.current_risk_score
    detail["matched_rules"] = list(proc.matched_rules)
    detail["network_connections"] = _serialize_network_connections(proc)
    detail["created_files"] = _serialize_created_files(proc)

    if not processes:
        samples = [_process_state_sample(proc, role="trigger")]
        if proc.parent_process_id:
            parent = store.get_process(device_id, proc.parent_process_id)
            if parent is not None:
                parent_sample = _process_state_sample(parent, role="context")
                samples[0]["parent_comm"] = parent.process_name
                samples.insert(0, parent_sample)
        detail["process_context_kind"] = "process_state"
        return samples

    # Ensure trigger sample carries process_id for graph enrichment.
    for row in processes:
        if payload_int(row.get("pid")) == proc.pid:
            row.setdefault("process_id", proc.process_id)
            break
    return processes


def _with_alert_context(
    chain: DeviceChain,
    alert: SecurityAlert,
    *,
    store: StateStore | None = None,
    event: dict[str, Any] | None = None,
) -> SecurityAlert:
    source = _source_event(chain, alert)
    try:
        detail = json.loads(alert.detail) if alert.detail else {}
    except (TypeError, ValueError):
        detail = {}
    if not isinstance(detail, dict):
        detail = {}

    detail["source_event"] = {
        "event_id": alert.event_id,
        "type": alert.event_type,
        "timestamp": alert.timestamp,
    }
    processes = _process_context(chain, source, alert_type=alert.alert_type)
    if source is not None and source.event_type == TYPE_PROCESS_START:
        # "session" when the tree has more than the ancestry spine + trigger.
        detail["process_context_kind"] = (
            "session" if len(processes) > 2 else "ancestry"
        )
    else:
        detail["process_context_kind"] = "none"
    detail["process_context_window_minutes"] = int(PROCESS_CONTEXT_WINDOW.total_seconds() // 60)

    if store is not None and event is not None:
        processes = _enrich_from_process_state(
            store, chain.device_id, event, detail, processes
        )

    detail["processes"] = processes
    alert.detail = DeviceChain.detail_json(detail)
    return alert


def with_alert_context(
    chain: DeviceChain,
    alert: SecurityAlert,
    *,
    store: StateStore | None = None,
    event: dict[str, Any] | None = None,
) -> SecurityAlert:
    return _with_alert_context(chain, alert, store=store, event=event)


def evaluate_event(event: dict[str, Any], store: StateStore) -> list[SecurityAlert]:
    chain = store.record_event(event)
    if chain is None:
        return []

    device_id = payload_str(event.get("device_id"))
    trigger = chain.latest()
    chain_alerts = evaluate_chain(chain, trigger=trigger)

    # Attribute DSL / chain hits onto the living ProcessState first so
    # correlation rules can see the updated risk score.
    _apply_rule_matches(store, device_id, event, chain_alerts)

    correlation_alerts = evaluate_process_correlations(
        store,
        device_id,
        trigger=trigger,
        event=event,
    )
    # Correlation rules note their own matches inside _emit.

    alerts = _merge_alerts(chain_alerts, correlation_alerts)
    return [
        _with_alert_context(chain, alert, store=store, event=event) for alert in alerts
    ]
