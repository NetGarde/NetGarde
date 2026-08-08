"""In-memory per-device process state store.

Events mutate an existing ``ProcessState`` for a device instead of being
analyzed as isolated snapshots. No Redis — everything lives in process memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from rules.chain import ChainEvent, DeviceChain, parse_ts, payload_int, payload_str, ts_iso
from rules.constants import (
    TYPE_ACTION_SUMMARY,
    TYPE_DRIVER_LOAD,
    TYPE_FILE_WRITE,
    TYPE_NETWORK_CONNECTION,
    TYPE_NETWORK_SUMMARY,
    TYPE_PROCESS_EXIT,
    TYPE_PROCESS_START,
    TYPE_REGISTRY_PERSISTENCE,
)


# ---------------------------------------------------------------------------
# Artifact records attached to a process over its lifetime
# ---------------------------------------------------------------------------


@dataclass
class NetworkConnection:
    remote_addr: str = ""
    remote_port: int = 0
    local_addr: str = ""
    local_port: int = 0
    protocol: str = ""
    direction: str = ""
    timestamp: str = ""


@dataclass
class FileWrite:
    path: str = ""
    operation: str = "write"
    timestamp: str = ""


@dataclass
class RegistryChange:
    key: str = ""
    value_name: str = ""
    operation: str = ""
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Process + device state
# ---------------------------------------------------------------------------


@dataclass
class ProcessState:
    """Mutable lifetime state for one process on one device."""

    process_id: str
    pid: int
    ppid: int = 0
    process_name: str = ""
    command_line: str = ""
    start_time: str = ""
    parent_process_id: str | None = None
    children_processes: list[str] = field(default_factory=list)
    network_connections: list[NetworkConnection] = field(default_factory=list)
    created_files: list[FileWrite] = field(default_factory=list)
    modified_registry_keys: list[RegistryChange] = field(default_factory=list)
    loaded_modules: list[str] = field(default_factory=list)
    current_risk_score: int = 0
    matched_rules: list[str] = field(default_factory=list)
    terminated: bool = False
    end_time: str | None = None

    def note_rule_match(self, rule_id: str, *, score_delta: int = 0) -> None:
        """Record a matched detection rule and optionally bump risk."""
        rule_id = (rule_id or "").strip()
        if rule_id and rule_id not in self.matched_rules:
            self.matched_rules.append(rule_id)
        if score_delta:
            self.current_risk_score = max(0, self.current_risk_score + score_delta)


@dataclass
class DeviceState:
    """All known process state for a single device, plus coarse device signals."""

    network_type: str | None = None
    public_ip: str | None = None
    presence: str | None = None
    # process_id → ProcessState (includes terminated processes while retained)
    processes: dict[str, ProcessState] = field(default_factory=dict)
    # pid → process_id for currently active processes only
    active_by_pid: dict[int, str] = field(default_factory=dict)

    def get_process(self, process_id: str) -> ProcessState | None:
        return self.processes.get(process_id)

    def get_by_pid(self, pid: int) -> ProcessState | None:
        process_id = self.active_by_pid.get(pid)
        if process_id is None:
            return None
        return self.processes.get(process_id)

    def active_processes(self) -> list[ProcessState]:
        return [
            proc
            for process_id in self.active_by_pid.values()
            if (proc := self.processes.get(process_id)) is not None and not proc.terminated
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event_device_id(event: dict[str, Any]) -> str:
    return payload_str(event.get("device_id"))


def _event_ts(event: dict[str, Any]) -> datetime:
    return parse_ts(event.get("ts"))


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("payload") or {}
    return raw if isinstance(raw, dict) else {}


def _process_name_from_payload(payload: dict[str, Any]) -> str:
    comm = payload_str(payload.get("comm"))
    if comm:
        return comm
    executable = payload_str(payload.get("executable") or payload.get("image"))
    if "/" in executable:
        return executable.rsplit("/", 1)[-1]
    if "\\" in executable:
        return executable.rsplit("\\", 1)[-1]
    return executable


def _derive_process_id(device_id: str, pid: int, start_time: str, payload: dict[str, Any]) -> str:
    """Stable process key: prefer agent GUID, else device+pid+start."""
    for key in ("process_id", "process_guid", "guid"):
        explicit = payload_str(payload.get(key))
        if explicit:
            return explicit
    return f"{device_id}:{pid}:{start_time}"


# ---------------------------------------------------------------------------
# StateStore
# ---------------------------------------------------------------------------


class StateStore:
    """In-memory store: device → process graph + event chain history."""

    def __init__(
        self,
        *,
        max_chain_events: int = 100,
        chain_window_minutes: int = 30,
        max_processes_per_device: int = 5_000,
    ) -> None:
        self._devices: dict[str, DeviceState] = {}
        self._chains: dict[str, DeviceChain] = {}
        self._max_chain_events = max_chain_events
        self._chain_window = timedelta(minutes=chain_window_minutes)
        self._max_processes_per_device = max_processes_per_device

    def get(self, device_id: str) -> DeviceState:
        if device_id not in self._devices:
            self._devices[device_id] = DeviceState()
        return self._devices[device_id]

    def get_chain(self, device_id: str) -> DeviceChain:
        if device_id not in self._chains:
            self._chains[device_id] = DeviceChain(device_id=device_id)
        return self._chains[device_id]

    def get_process(self, device_id: str, process_id: str) -> ProcessState | None:
        return self.get(device_id).get_process(process_id)

    def get_process_by_pid(self, device_id: str, pid: int) -> ProcessState | None:
        return self.get(device_id).get_by_pid(pid)

    # -- process lifecycle ---------------------------------------------------

    def create_process(self, event: dict[str, Any]) -> ProcessState | None:
        """Create or refresh ProcessState from a process_start-like event."""
        device_id = _event_device_id(event)
        if not device_id:
            return None

        payload = _event_payload(event)
        pid = payload_int(payload.get("pid"))
        if pid <= 0:
            return None

        start_time = ts_iso(_event_ts(event))
        process_id = _derive_process_id(device_id, pid, start_time, payload)
        device = self.get(device_id)

        existing = device.processes.get(process_id)
        if existing is not None:
            # Same identity seen again — mutate in place, do not allocate anew.
            proc = existing
            proc.terminated = False
            proc.end_time = None
        else:
            proc = ProcessState(
                process_id=process_id,
                pid=pid,
                start_time=start_time,
            )
            device.processes[process_id] = proc
            self._evict_if_needed(device)

        proc.pid = pid
        proc.ppid = payload_int(payload.get("ppid"))
        name = _process_name_from_payload(payload)
        if name:
            proc.process_name = name
        cmdline = payload_str(payload.get("cmdline") or payload.get("command_line"))
        if cmdline:
            proc.command_line = cmdline
        if not proc.start_time:
            proc.start_time = start_time

        # Link parent/child when the parent is still known on this device.
        parent = device.get_by_pid(proc.ppid) if proc.ppid > 0 else None
        if parent is not None:
            proc.parent_process_id = parent.process_id
            if process_id not in parent.children_processes:
                parent.children_processes.append(process_id)

        # PID reuse: previous occupant of this pid is no longer active.
        previous_id = device.active_by_pid.get(pid)
        if previous_id and previous_id != process_id:
            previous = device.processes.get(previous_id)
            if previous is not None and not previous.terminated:
                previous.terminated = True
                previous.end_time = start_time
        device.active_by_pid[pid] = process_id
        return proc

    def terminate_process(self, event: dict[str, Any]) -> ProcessState | None:
        """Mark a process terminated and drop it from the active PID index."""
        device_id = _event_device_id(event)
        if not device_id:
            return None

        payload = _event_payload(event)
        device = self.get(device_id)
        proc = self._resolve_process(device, payload, event)
        if proc is None:
            return None

        end_time = ts_iso(_event_ts(event))
        proc.terminated = True
        proc.end_time = end_time
        if device.active_by_pid.get(proc.pid) == proc.process_id:
            del device.active_by_pid[proc.pid]
        return proc

    # -- activity updates (mutate existing ProcessState) ---------------------

    def process_network_connection(self, event: dict[str, Any]) -> ProcessState | None:
        """Append a network connection to the owning process."""
        device_id = _event_device_id(event)
        if not device_id:
            return None

        payload = _event_payload(event)
        device = self.get(device_id)
        proc = self._resolve_process(device, payload, event)
        if proc is None:
            # Auto-create a stub if we only saw the connection first.
            stub = dict(event)
            stub.setdefault("type", TYPE_PROCESS_START)
            proc = self.create_process(stub)
            if proc is None:
                return None

        conn = NetworkConnection(
            remote_addr=payload_str(
                payload.get("remote_addr") or payload.get("dest_ip") or payload.get("remote_ip")
            ),
            remote_port=payload_int(
                payload.get("remote_port") or payload.get("dest_port")
            ),
            local_addr=payload_str(payload.get("local_addr") or payload.get("src_ip")),
            local_port=payload_int(payload.get("local_port") or payload.get("src_port")),
            protocol=payload_str(payload.get("protocol")).lower(),
            direction=payload_str(payload.get("direction")).lower(),
            timestamp=ts_iso(_event_ts(event)),
        )
        proc.network_connections.append(conn)
        return proc

    def process_file_write(self, event: dict[str, Any]) -> ProcessState | None:
        """Append a created/written file path to the owning process."""
        device_id = _event_device_id(event)
        if not device_id:
            return None

        payload = _event_payload(event)
        device = self.get(device_id)
        proc = self._resolve_process(device, payload, event)
        if proc is None:
            stub = dict(event)
            stub.setdefault("type", TYPE_PROCESS_START)
            proc = self.create_process(stub)
            if proc is None:
                return None

        path = payload_str(
            payload.get("path") or payload.get("file_path") or payload.get("target_path")
        )
        if not path:
            return proc

        proc.created_files.append(
            FileWrite(
                path=path,
                operation=payload_str(payload.get("operation")) or "write",
                timestamp=ts_iso(_event_ts(event)),
            )
        )
        return proc

    def process_registry_change(self, event: dict[str, Any]) -> ProcessState | None:
        """Append a registry modification to the owning process."""
        device_id = _event_device_id(event)
        if not device_id:
            return None

        payload = _event_payload(event)
        device = self.get(device_id)
        proc = self._resolve_process(device, payload, event)
        if proc is None:
            stub = dict(event)
            stub.setdefault("type", TYPE_PROCESS_START)
            proc = self.create_process(stub)
            if proc is None:
                return None

        key = payload_str(
            payload.get("key")
            or payload.get("registry_key")
            or payload.get("path")
        )
        if not key:
            return proc

        proc.modified_registry_keys.append(
            RegistryChange(
                key=key,
                value_name=payload_str(
                    payload.get("value_name") or payload.get("name")
                ),
                operation=payload_str(payload.get("operation")),
                timestamp=ts_iso(_event_ts(event)),
            )
        )
        return proc

    def process_module_load(self, event: dict[str, Any]) -> ProcessState | None:
        """Record a loaded module / driver path on the owning process."""
        device_id = _event_device_id(event)
        if not device_id:
            return None

        payload = _event_payload(event)
        device = self.get(device_id)
        proc = self._resolve_process(device, payload, event)
        if proc is None:
            return None

        module = payload_str(
            payload.get("module")
            or payload.get("path")
            or payload.get("image")
            or payload.get("driver")
        )
        if module and module not in proc.loaded_modules:
            proc.loaded_modules.append(module)
        return proc

    # -- event chain (existing detection pipeline) ---------------------------

    def record_event(self, event: dict[str, Any]) -> DeviceChain | None:
        chain_event = ChainEvent.from_kafka(event)
        if chain_event is None:
            return None

        device_id = _event_device_id(event)
        if not device_id:
            return None

        chain = self.get_chain(device_id)
        chain.append(
            chain_event,
            max_events=self._max_chain_events,
            window=self._chain_window,
        )

        state = self.get(device_id)
        if chain_event.event_type == TYPE_ACTION_SUMMARY:
            presence = payload_str(chain_event.payload.get("presence"))
            if presence:
                state.presence = presence
        elif chain_event.event_type == TYPE_NETWORK_SUMMARY:
            network_type = payload_str(chain_event.payload.get("network_type"))
            public_ip = payload_str(chain_event.payload.get("public_ip"))
            if network_type:
                state.network_type = network_type
            if public_ip:
                state.public_ip = public_ip
        elif chain_event.event_type == TYPE_PROCESS_START:
            self.create_process(event)
        elif chain_event.event_type == TYPE_PROCESS_EXIT:
            self.terminate_process(event)
        elif chain_event.event_type == TYPE_NETWORK_CONNECTION:
            self.process_network_connection(event)
        elif chain_event.event_type == TYPE_FILE_WRITE:
            self.process_file_write(event)
        elif chain_event.event_type == TYPE_REGISTRY_PERSISTENCE:
            self.process_registry_change(event)
        elif chain_event.event_type == TYPE_DRIVER_LOAD:
            self.process_module_load(event)

        return chain

    # -- internals -----------------------------------------------------------

    def _resolve_process(
        self,
        device: DeviceState,
        payload: dict[str, Any],
        event: dict[str, Any],
    ) -> ProcessState | None:
        """Find an existing ProcessState by process_id, then by active pid."""
        for key in ("process_id", "process_guid", "guid"):
            explicit = payload_str(payload.get(key))
            if explicit:
                found = device.get_process(explicit)
                if found is not None:
                    return found

        pid = payload_int(payload.get("pid"))
        if pid > 0:
            found = device.get_by_pid(pid)
            if found is not None:
                return found

        return None

    def _evict_if_needed(self, device: DeviceState) -> None:
        """Bound memory: drop oldest terminated processes first."""
        overflow = len(device.processes) - self._max_processes_per_device
        if overflow <= 0:
            return

        terminated = sorted(
            (p for p in device.processes.values() if p.terminated),
            key=lambda p: p.end_time or p.start_time,
        )
        for proc in terminated[:overflow]:
            device.processes.pop(proc.process_id, None)
            if device.active_by_pid.get(proc.pid) == proc.process_id:
                del device.active_by_pid[proc.pid]

        overflow = len(device.processes) - self._max_processes_per_device
        if overflow <= 0:
            return

        # Still over limit: drop oldest non-active processes.
        candidates = sorted(
            (
                p
                for p in device.processes.values()
                if device.active_by_pid.get(p.pid) != p.process_id
            ),
            key=lambda p: p.start_time,
        )
        for proc in candidates[:overflow]:
            device.processes.pop(proc.process_id, None)
