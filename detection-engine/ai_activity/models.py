"""Dataclasses for AI sessions, graphs, timeline, and findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ai_activity.catalog import (
    DEFAULT_MAX_GRAPH_NODES,
    DEFAULT_MAX_TIMELINE_EVENTS,
    ROLE_UNKNOWN,
)


@dataclass
class ProcessNode:
    """One process in an AI session spawn tree."""

    process_id: str
    pid: int
    ppid: int = 0
    name: str = ""
    cmdline: str = ""
    role: str = ROLE_UNKNOWN
    tool_class: str | None = None
    parent_process_id: str | None = None
    children: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str | None = None
    terminated: bool = False
    hash_sha256: str = ""
    signature_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolExecution:
    """A classified tool invocation under a session."""

    tool_class: str
    process_id: str
    pid: int
    name: str
    cmdline: str
    timestamp: str
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkActivity:
    process_id: str
    remote_addr: str
    remote_port: int
    protocol: str
    direction: str
    domain: str
    timestamp: str
    is_external: bool = True
    bytes_sent: int = 0
    bytes_recv: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FileActivity:
    process_id: str
    path: str
    operation: str  # read | write | inferred
    timestamp: str
    is_secret: bool = False
    inferred: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEvent:
    kind: str
    timestamp: str
    process_id: str
    summary: str
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphNode:
    id: str
    label: str
    kind: str
    role: str = ROLE_UNKNOWN
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str  # spawns | network | file | uses_tool
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass
class SessionFinding:
    """Correlation finding attached to a session (may become an EngineHit)."""

    finding_type: str
    severity: str
    score: int
    message: str
    timestamp: str
    detail: dict[str, Any] = field(default_factory=dict)
    emitted_alert: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionCounters:
    tool_executions: int = 0
    files_read: int = 0
    files_modified: int = 0
    network_connections: int = 0
    process_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AISession:
    """Reconstructed AI application session on one device."""

    session_id: str
    device_id: str
    app_name: str
    root_process_id: str
    root_pid: int
    start_time: str
    end_time: str | None = None
    status: str = "active"  # active | closed
    processes: dict[str, ProcessNode] = field(default_factory=dict)
    # pid → process_id within this session (active only)
    pid_index: dict[int, str] = field(default_factory=dict)
    timeline: list[TimelineEvent] = field(default_factory=list)
    tools: list[ToolExecution] = field(default_factory=list)
    networks: list[NetworkActivity] = field(default_factory=list)
    files: list[FileActivity] = field(default_factory=list)
    external_domains: list[str] = field(default_factory=list)
    secrets_accessed: list[str] = field(default_factory=list)
    git_repos: list[str] = field(default_factory=list)
    docker_activity: list[str] = field(default_factory=list)
    k8s_activity: list[str] = field(default_factory=list)
    cloud_activity: list[str] = field(default_factory=list)
    counters: SessionCounters = field(default_factory=SessionCounters)
    risk_score: int = 0
    risk_factors: list[str] = field(default_factory=list)
    findings: list[SessionFinding] = field(default_factory=list)
    # finding_type → first-seen, for once-per-session dedupe of alert emission
    _emitted_finding_types: set[str] = field(default_factory=set, repr=False)
    max_timeline: int = DEFAULT_MAX_TIMELINE_EVENTS
    max_graph_nodes: int = DEFAULT_MAX_GRAPH_NODES

    @property
    def duration_ms(self) -> int | None:
        if not self.start_time:
            return None
        end = self.end_time or self.start_time
        try:
            from rules.chain import parse_ts

            delta = parse_ts(end) - parse_ts(self.start_time)
            return max(0, int(delta.total_seconds() * 1000))
        except Exception:
            return None

    def append_timeline(self, event: TimelineEvent) -> None:
        self.timeline.append(event)
        if len(self.timeline) > self.max_timeline:
            overflow = len(self.timeline) - self.max_timeline
            del self.timeline[:overflow]

    def add_domain(self, domain: str) -> None:
        d = (domain or "").strip().lower()
        if d and d not in self.external_domains:
            self.external_domains.append(d)

    def add_secret(self, path: str) -> None:
        p = (path or "").strip()
        if p and p not in self.secrets_accessed:
            self.secrets_accessed.append(p)

    def add_unique(self, bucket: list[str], value: str) -> None:
        v = (value or "").strip()
        if v and v not in bucket:
            bucket.append(v)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "app_name": self.app_name,
            "root_process_id": self.root_process_id,
            "root_pid": self.root_pid,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "counters": self.counters.to_dict(),
            "external_domains": list(self.external_domains),
            "secrets_accessed": list(self.secrets_accessed),
            "git_repos": list(self.git_repos),
            "docker_activity": list(self.docker_activity),
            "k8s_activity": list(self.k8s_activity),
            "cloud_activity": list(self.cloud_activity),
            "risk_score": self.risk_score,
            "risk_factors": list(self.risk_factors),
            "finding_count": len(self.findings),
            "process_count": len(self.processes),
        }

    def detail_dict(self) -> dict[str, Any]:
        out = self.summary_dict()
        out["processes"] = {pid: node.to_dict() for pid, node in self.processes.items()}
        out["tools"] = [t.to_dict() for t in self.tools[-100:]]
        out["findings"] = [f.to_dict() for f in self.findings]
        return out
