from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from rules.alerts import SecurityAlert
from rules.chain import ChainEvent, DeviceChain, payload_int, payload_str, ts_iso
from rules.chain_rules import evaluate_chain
from rules.constants import ALERT_PROCESS_BURST, TYPE_PROCESS_START
from rules.state import StateStore

__all__ = ["SecurityAlert", "evaluate_event"]

PROCESS_CONTEXT_WINDOW = timedelta(minutes=5)
PROCESS_CONTEXT_SAMPLE_LIMIT = 15


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
    if source is None:
        return []
    starts = [
        item
        for item in chain.events
        if item.event_type == TYPE_PROCESS_START and item.ts <= source.ts
    ]
    if source.event_type != TYPE_PROCESS_START:
        return []

    if alert_type == ALERT_PROCESS_BURST:
        cutoff = source.ts - PROCESS_CONTEXT_WINDOW
        sampled = [item for item in starts if item.ts >= cutoff][-PROCESS_CONTEXT_SAMPLE_LIMIT:]
    else:
        # Point-in-time process alerts are causal chains, not ambient snapshots.
        sampled = [source]

    # Keep known ancestors even when they started before the context window.
    included = {id(item) for item in sampled}
    ancestors: list[ChainEvent] = []
    for child in list(sampled):
        parent = _parent_event(starts, child)
        while parent is not None and id(parent) not in included:
            ancestors.append(parent)
            included.add(id(parent))
            parent = _parent_event(starts, parent)

    ordered = sorted(ancestors + sampled, key=lambda item: item.ts)
    return [
        _process_sample(item, source=source, parent=_parent_event(starts, item))
        for item in ordered
    ]


def _with_alert_context(chain: DeviceChain, alert: SecurityAlert) -> SecurityAlert:
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
    if source is not None and source.event_type == TYPE_PROCESS_START:
        detail["process_context_kind"] = (
            "burst" if alert.alert_type == ALERT_PROCESS_BURST else "ancestry"
        )
    else:
        detail["process_context_kind"] = "none"
    detail["process_context_window_minutes"] = int(PROCESS_CONTEXT_WINDOW.total_seconds() // 60)
    detail["processes"] = _process_context(chain, source, alert_type=alert.alert_type)
    alert.detail = DeviceChain.detail_json(detail)
    return alert


def evaluate_event(event: dict[str, Any], store: StateStore) -> list[SecurityAlert]:
    chain = store.record_event(event)
    if chain is None:
        return []
    trigger = chain.latest()
    alerts = evaluate_chain(chain, trigger=trigger)
    return [_with_alert_context(chain, alert) for alert in alerts]
