"""Process helpers and unregistered windowed rules.

Registered process detections live in rules/definitions/process.yml
and are compiled by rules.dsl.
"""

from __future__ import annotations

from datetime import timedelta

from rules.alerts import SecurityAlert
from rules.chain import (
    ChainEvent,
    DeviceChain,
    payload_int,
    payload_str,
    ts_iso,
)
from rules.constants import (
    ALERT_PROCESS_BURST,
    SEVERITY_MEDIUM,
    TYPE_PROCESS_START,
)

PARENT_WINDOW = timedelta(minutes=5)
PROCESS_BURST_THRESHOLD = 25
PROCESS_BURST_SAMPLE_LIMIT = 15
PROCESS_BURST_TOP_COMMS = 8
PROCESS_BURST_CMDLINE_MAX = 200


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


def _comm(ev: ChainEvent) -> str:
    raw = payload_str(ev.payload.get("comm")) or payload_str(ev.payload.get("executable"))
    return raw.lower().split("/")[-1]


def _executable(ev: ChainEvent) -> str:
    return payload_str(ev.payload.get("executable") or ev.payload.get("comm")).lower()


def _cmdline(ev: ChainEvent) -> str:
    return payload_str(ev.payload.get("cmdline"))


def _trigger_process(chain: DeviceChain) -> ChainEvent | None:
    latest = chain.latest()
    if latest is None or latest.event_type != TYPE_PROCESS_START:
        return chain.latest(TYPE_PROCESS_START)
    return latest


def _find_parent(chain: DeviceChain, child: ChainEvent) -> ChainEvent | None:
    """Resolve a single parent by ppid within the recent process window."""
    ppid = payload_int(child.payload.get("ppid"))
    if ppid <= 0:
        return None
    for ev in reversed(chain.of_type(TYPE_PROCESS_START, PARENT_WINDOW)):
        if payload_int(ev.payload.get("pid")) == ppid:
            return ev
    return None


def _truncate_cmdline(value: str) -> str:
    text = (value or "").strip()
    if len(text) <= PROCESS_BURST_CMDLINE_MAX:
        return text
    return text[: PROCESS_BURST_CMDLINE_MAX - 1] + "…"


def _burst_process_sample(ev: ChainEvent, *, parent: ChainEvent | None = None) -> dict:
    sample: dict = {
        "pid": payload_int(ev.payload.get("pid")),
        "ppid": payload_int(ev.payload.get("ppid")),
        "comm": _comm(ev) or "unknown",
    }
    exe = _executable(ev)
    if exe and exe != sample["comm"]:
        sample["executable"] = exe
    cmdline = _truncate_cmdline(_cmdline(ev))
    if cmdline:
        sample["cmdline"] = cmdline
    parent_comm = payload_str(ev.payload.get("parent_comm"))
    if not parent_comm and parent is not None:
        parent_comm = _comm(parent)
    if parent_comm:
        sample["parent_comm"] = parent_comm.lower().split("/")[-1]
    return sample


def _burst_top_comms(starts: list[ChainEvent], *, limit: int = PROCESS_BURST_TOP_COMMS) -> list[dict]:
    counts: dict[str, int] = {}
    for ev in starts:
        name = _comm(ev) or "unknown"
        counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"comm": name, "count": count} for name, count in ranked[:limit]]


def _burst_process_samples(chain: DeviceChain, starts: list[ChainEvent]) -> list[dict]:
    """Build graph samples, resolving parent names and including known ancestors."""
    window_starts = starts[-PROCESS_BURST_SAMPLE_LIMIT:]
    samples: list[dict] = []
    seen_pids: set[int] = set()
    ancestors: list[dict] = []

    for ev in window_starts:
        parent = _find_parent(chain, ev)
        sample = _burst_process_sample(ev, parent=parent)
        samples.append(sample)
        pid = sample.get("pid")
        if isinstance(pid, int) and pid > 0:
            seen_pids.add(pid)

        if parent is None:
            continue
        parent_pid = payload_int(parent.payload.get("pid"))
        if parent_pid <= 0 or parent_pid in seen_pids:
            continue
        ancestors.append(_burst_process_sample(parent))
        seen_pids.add(parent_pid)

    return ancestors + samples


def rule_process_burst(chain: DeviceChain) -> list[SecurityAlert]:
    """Many new processes in a short window (possible malware sweep or unpacker)."""
    window = timedelta(minutes=2)
    starts = chain.of_type(TYPE_PROCESS_START, window)
    if len(starts) >= PROCESS_BURST_THRESHOLD:
        source = _trigger_process(chain) or starts[-1]
        samples = _burst_process_samples(chain, starts)
        return [
            _alert(
                chain,
                source=source,
                alert_type=ALERT_PROCESS_BURST,
                severity=SEVERITY_MEDIUM,
                message=f"Process creation burst ({len(starts)} starts in 2 minutes)",
                detail={
                    "count": len(starts),
                    "window_minutes": 2,
                    "sample_limit": PROCESS_BURST_SAMPLE_LIMIT,
                    "top_comms": _burst_top_comms(starts),
                    "processes": samples,
                },
            )
        ]
    return []
