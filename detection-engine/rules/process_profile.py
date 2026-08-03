"""Build process frequency profile keys from process_start events."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from rules.alerts import SecurityAlert
from rules.chain import DeviceChain, payload_int, payload_str, ts_iso
from rules.constants import (
    ALERT_NOVEL_PROCESS,
    SEVERITY_MEDIUM,
    TYPE_PROCESS_START,
)
from rules.state import StateStore

KIND_PROCESS_COMM = "process_comm"
KIND_PROCESS_CHAIN = "process_chain"
PARENT_WINDOW = timedelta(minutes=5)


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return text


def _comm_from_payload(payload: dict[str, Any]) -> str:
    raw = payload_str(payload.get("comm")) or payload_str(payload.get("executable"))
    return _norm(raw)


def _executable_from_payload(payload: dict[str, Any]) -> str:
    return _norm(payload_str(payload.get("executable") or payload.get("comm")))


def _find_parent_comm(chain: DeviceChain, child_payload: dict[str, Any]) -> str:
    """Resolve parent process basename via ppid within the recent window."""
    parent_comm = _norm(payload_str(child_payload.get("parent_comm")))
    if parent_comm:
        return parent_comm
    ppid = payload_int(child_payload.get("ppid"))
    if ppid <= 0:
        return ""
    for ev in reversed(chain.of_type(TYPE_PROCESS_START, PARENT_WINDOW)):
        if payload_int(ev.payload.get("pid")) == ppid:
            return _comm_from_payload(ev.payload)
    return ""


def profile_keys_from_event(
    event: dict[str, Any],
    store: StateStore,
) -> list[tuple[str, str, dict[str, Any]]]:
    """Return [(kind, key, meta), ...] for process_start profile learning."""
    if payload_str(event.get("type")) != TYPE_PROCESS_START:
        return []
    device_id = payload_str(event.get("device_id"))
    if not device_id:
        return []
    raw_payload = event.get("payload") or {}
    if not isinstance(raw_payload, dict):
        raw_payload = {}

    comm = _comm_from_payload(raw_payload)
    if not comm:
        return []

    exe = _executable_from_payload(raw_payload)
    meta: dict[str, Any] = {"comm": comm}
    if exe:
        meta["executable"] = exe

    keys: list[tuple[str, str, dict[str, Any]]] = [
        (KIND_PROCESS_COMM, comm, meta),
    ]

    chain = store.get_chain(device_id)
    parent = _find_parent_comm(chain, raw_payload)
    if parent:
        chain_key = f"{parent}>{comm}"
        chain_meta = dict(meta)
        chain_meta.update({"parent_comm": parent, "child_comm": comm})
        keys.append((KIND_PROCESS_CHAIN, chain_key, chain_meta))

    return keys


def novel_process_alert(
    event: dict[str, Any],
    *,
    behavior_key: str,
    meta: dict[str, Any],
) -> Optional[SecurityAlert]:
    """Build a medium-severity novel_process alert for a first-seen process identity."""
    device_id = payload_str(event.get("device_id"))
    if not device_id:
        return None
    raw_payload = event.get("payload") or {}
    if not isinstance(raw_payload, dict):
        raw_payload = {}
    comm = _norm(meta.get("comm")) or _comm_from_payload(raw_payload)
    if not comm:
        return None

    detail = {
        "behavior_kind": KIND_PROCESS_COMM,
        "behavior_key": behavior_key,
        "comm": comm,
        **{k: v for k, v in meta.items() if k not in ("comm",)},
    }
    cmdline = payload_str(raw_payload.get("cmdline"))
    if cmdline:
        detail["cmdline"] = cmdline
    pid = payload_int(raw_payload.get("pid"))
    if pid:
        detail["pid"] = pid

    return SecurityAlert(
        timestamp=ts_iso(
            __import__("rules.chain", fromlist=["parse_ts"]).parse_ts(event.get("ts"))
        ),
        device_id=device_id,
        event_id=payload_str(event.get("event_id")) or None,
        event_type=TYPE_PROCESS_START,
        alert_type=ALERT_NOVEL_PROCESS,
        severity=SEVERITY_MEDIUM,
        message=f"Novel process for this device: {comm}",
        detail=DeviceChain.detail_json(detail),
    )
