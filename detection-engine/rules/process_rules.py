"""Process (EDR-lite) chain rules for TrustEdge Agent process_start / process_exit events."""

from __future__ import annotations

from datetime import timedelta

from rules.alerts import SecurityAlert
from rules.chain import (
    TYPE_PROCESS_START,
    ChainEvent,
    DeviceChain,
    payload_int,
    payload_str,
    ts_iso,
)

SHELL_COMMS = frozenset({"sh", "bash", "zsh", "fish", "dash", "ksh"})
DOWNLOAD_COMMS = frozenset({"curl", "wget", "fetch"})
SCRIPT_COMMS = frozenset({"osascript", "python", "python3", "perl", "ruby", "node"})
SUSPICIOUS_PATH_MARKERS = ("/tmp/", "/var/tmp/", "/downloads/", "/.hidden/", "/private/tmp/")


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


def _pid_map(chain: DeviceChain, window: timedelta | None = None) -> dict[int, ChainEvent]:
    events = chain.of_type(TYPE_PROCESS_START, window) if window else chain.of_type(TYPE_PROCESS_START)
    out: dict[int, ChainEvent] = {}
    for ev in events:
        pid = payload_int(ev.payload.get("pid"))
        if pid > 0:
            out[pid] = ev
    return out


def rule_temp_path_execution(chain: DeviceChain) -> list[SecurityAlert]:
    """Process started from /tmp, /var/tmp, or Downloads."""
    latest = chain.latest(TYPE_PROCESS_START)
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
                alert_type="temp_path_execution",
                severity="high",
                message=f"Process started from suspicious path: {exe}",
                detail=_with_cmdlines(
                    {"executable": exe, "pid": payload_int(latest.payload.get("pid"))},
                    ("cmdline", latest),
                ),
            )
        ]
    return []


def rule_shell_spawns_downloader(chain: DeviceChain) -> list[SecurityAlert]:
    """Shell parent process spawned curl/wget."""
    window = timedelta(minutes=5)
    parents = _pid_map(chain, window)
    for child in chain.of_type(TYPE_PROCESS_START, window):
        comm = _comm(child)
        if comm not in DOWNLOAD_COMMS:
            continue
        ppid = payload_int(child.payload.get("ppid"))
        parent = parents.get(ppid)
        if parent is None:
            continue
        if _comm(parent) in SHELL_COMMS:
            return [
                _alert(
                    chain,
                    source=child,
                    alert_type="shell_spawns_downloader",
                    severity="high",
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
    return []


def rule_script_spawns_shell(chain: DeviceChain) -> list[SecurityAlert]:
    """Script interpreter spawned a shell (common phishing / automation chain)."""
    window = timedelta(minutes=5)
    parents = _pid_map(chain, window)
    for child in chain.of_type(TYPE_PROCESS_START, window):
        if _comm(child) not in SHELL_COMMS:
            continue
        ppid = payload_int(child.payload.get("ppid"))
        parent = parents.get(ppid)
        if parent is None:
            continue
        if _comm(parent) in SCRIPT_COMMS:
            return [
                _alert(
                    chain,
                    source=child,
                    alert_type="script_spawns_shell",
                    severity="medium",
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
    return []


def rule_process_burst(chain: DeviceChain) -> list[SecurityAlert]:
    """Many new processes in a short window (possible malware sweep or unpacker)."""
    window = timedelta(minutes=2)
    starts = chain.of_type(TYPE_PROCESS_START, window)
    if len(starts) >= 25:
        return [
            _alert(
                chain,
                source=starts[-1],
                alert_type="process_burst",
                severity="medium",
                message=f"Process creation burst ({len(starts)} starts in 2 minutes)",
                detail={"count": len(starts), "window_minutes": 2},
            )
        ]
    return []


def rule_unsigned_system_binary_impersonation(chain: DeviceChain) -> list[SecurityAlert]:
    """Comm looks like a system tool but path is outside /usr or /System."""
    latest = chain.latest(TYPE_PROCESS_START)
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
            alert_type="binary_path_mismatch",
            severity="medium",
            message=f"Process name {comm} running outside system paths ({exe})",
            detail=_with_cmdlines(
                {"comm": comm, "executable": exe},
                ("cmdline", latest),
            ),
        )
    ]


PROCESS_RULES: list[tuple[str, object]] = [
    ("temp_path_execution", rule_temp_path_execution),
    ("shell_spawns_downloader", rule_shell_spawns_downloader),
    ("script_spawns_shell", rule_script_spawns_shell),
    ("process_burst", rule_process_burst),
    ("binary_path_mismatch", rule_unsigned_system_binary_impersonation),
]
