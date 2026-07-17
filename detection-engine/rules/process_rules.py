"""Process (EDR-lite) rules for TrustEdge Agent process_start events.

Rules evaluate the triggering process_start first. Parent lookup via ppid
happens only when that new process itself looks suspicious.
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
    ALERT_BINARY_PATH_MISMATCH,
    ALERT_PROCESS_BURST,
    ALERT_SCRIPT_SPAWNS_SHELL,
    ALERT_SHELL_SPAWNS_DOWNLOADER,
    ALERT_TEMP_PATH_EXECUTION,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    TYPE_PROCESS_START,
)

SHELL_COMMS = frozenset({"sh", "bash", "zsh", "fish", "dash", "ksh"})
DOWNLOAD_COMMS = frozenset({"curl", "wget", "fetch"})
SCRIPT_COMMS = frozenset({"osascript", "python", "python3", "perl", "ruby", "node"})
SUSPICIOUS_PATH_MARKERS = ("/tmp/", "/var/tmp/", "/downloads/", "/.hidden/", "/private/tmp/")
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


def _with_cmdlines(detail: dict, *events: tuple[str, ChainEvent]) -> dict:
    """Attach non-empty cmdline fields from process events."""
    out = dict(detail)
    for key, ev in events:
        cmd = _cmdline(ev)
        if cmd:
            out[key] = cmd
    return out


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


def _parent_if_suspicious(
    chain: DeviceChain,
    child: ChainEvent,
    *,
    suspicious_comms: frozenset[str],
) -> ChainEvent | None:
    """Look up parent only when the new child process is in a suspicious set."""
    if _comm(child) not in suspicious_comms:
        return None
    return _find_parent(chain, child)


def rule_temp_path_execution(chain: DeviceChain) -> list[SecurityAlert]:
    """Process started from /tmp, /var/tmp, or Downloads."""
    latest = _trigger_process(chain)
    if not latest:
        return []
    exe = _executable(latest)
    if not exe:
        return []
    if any(marker in exe for marker in SUSPICIOUS_PATH_MARKERS):
        return [
            _alert(
                chain,
                source=latest,
                alert_type=ALERT_TEMP_PATH_EXECUTION,
                severity=SEVERITY_HIGH,
                message=f"Process started from suspicious path: {exe}",
                detail=_with_cmdlines(
                    {"executable": exe, "pid": payload_int(latest.payload.get("pid"))},
                    ("cmdline", latest),
                ),
            )
        ]
    return []


def rule_shell_spawns_downloader(chain: DeviceChain) -> list[SecurityAlert]:
    """If new process is a downloader, check whether its parent is a shell."""
    child = _trigger_process(chain)
    if not child:
        return []
    parent = _parent_if_suspicious(chain, child, suspicious_comms=DOWNLOAD_COMMS)
    if parent is None or _comm(parent) not in SHELL_COMMS:
        return []
    comm = _comm(child)
    ppid = payload_int(child.payload.get("ppid"))
    return [
        _alert(
            chain,
            source=child,
            alert_type=ALERT_SHELL_SPAWNS_DOWNLOADER,
            severity=SEVERITY_HIGH,
            message=f"Shell spawned network downloader ({comm})",
            detail=_with_cmdlines(
                {
                    "child_comm": comm,
                    "parent_comm": _comm(parent),
                    "child_pid": payload_int(child.payload.get("pid")),
                    "parent_pid": ppid,
                },
                ("parent_cmdline", parent),
                ("child_cmdline", child),
            ),
        )
    ]


def rule_script_spawns_shell(chain: DeviceChain) -> list[SecurityAlert]:
    """If new process is a shell, check whether its parent is a script interpreter."""
    child = _trigger_process(chain)
    if not child:
        return []
    parent = _parent_if_suspicious(chain, child, suspicious_comms=SHELL_COMMS)
    if parent is None or _comm(parent) not in SCRIPT_COMMS:
        return []
    ppid = payload_int(child.payload.get("ppid"))
    return [
        _alert(
            chain,
            source=child,
            alert_type=ALERT_SCRIPT_SPAWNS_SHELL,
            severity=SEVERITY_MEDIUM,
            message=f"{_comm(parent)} spawned shell ({_comm(child)})",
            detail=_with_cmdlines(
                {
                    "parent_comm": _comm(parent),
                    "child_comm": _comm(child),
                    "parent_pid": ppid,
                    "child_pid": payload_int(child.payload.get("pid")),
                },
                ("parent_cmdline", parent),
                ("child_cmdline", child),
            ),
        )
    ]


def _truncate_cmdline(value: str) -> str:
    text = (value or "").strip()
    if len(text) <= PROCESS_BURST_CMDLINE_MAX:
        return text
    return text[: PROCESS_BURST_CMDLINE_MAX - 1] + "…"


def _burst_process_sample(ev: ChainEvent) -> dict:
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
    return sample


def _burst_top_comms(starts: list[ChainEvent], *, limit: int = PROCESS_BURST_TOP_COMMS) -> list[dict]:
    counts: dict[str, int] = {}
    for ev in starts:
        name = _comm(ev) or "unknown"
        counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"comm": name, "count": count} for name, count in ranked[:limit]]


def rule_process_burst(chain: DeviceChain) -> list[SecurityAlert]:
    """Many new processes in a short window (possible malware sweep or unpacker)."""
    window = timedelta(minutes=2)
    starts = chain.of_type(TYPE_PROCESS_START, window)
    if len(starts) >= PROCESS_BURST_THRESHOLD:
        source = _trigger_process(chain) or starts[-1]
        samples = [_burst_process_sample(ev) for ev in starts[-PROCESS_BURST_SAMPLE_LIMIT:]]
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


def rule_unsigned_system_binary_impersonation(chain: DeviceChain) -> list[SecurityAlert]:
    """Comm looks like a system tool but path is outside /usr or /System."""
    latest = _trigger_process(chain)
    if not latest:
        return []
    comm = _comm(latest)
    exe = _executable(latest)
    system_names = frozenset({"curl", "bash", "sh", "python", "python3", "ls", "cat"})
    if comm not in system_names:
        return []
    if exe.startswith("/usr/") or exe.startswith("/system/") or exe.startswith("/bin/"):
        return []
    if comm == exe:
        return []
    return [
        _alert(
            chain,
            source=latest,
            alert_type=ALERT_BINARY_PATH_MISMATCH,
            severity=SEVERITY_MEDIUM,
            message=f"Process name {comm} running outside system paths ({exe})",
            detail=_with_cmdlines(
                {"comm": comm, "executable": exe},
                ("cmdline", latest),
            ),
        )
    ]


PROCESS_RULES: list[tuple[str, object]] = [
    (ALERT_TEMP_PATH_EXECUTION, rule_temp_path_execution),
    (ALERT_SHELL_SPAWNS_DOWNLOADER, rule_shell_spawns_downloader),
    (ALERT_SCRIPT_SPAWNS_SHELL, rule_script_spawns_shell),
    (ALERT_PROCESS_BURST, rule_process_burst),
    (ALERT_BINARY_PATH_MISMATCH, rule_unsigned_system_binary_impersonation),
]
