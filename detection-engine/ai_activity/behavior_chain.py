"""Build a human-readable behavioral activity chain for an AI session.

Example:
  Cursor → Read 12 files → Opened ~/.ssh → Ran git → Connected to api.openai.com
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ai_activity.catalog import (
    TOOL_AWS,
    TOOL_CURL,
    TOOL_DOCKER,
    TOOL_GIT,
    TOOL_KUBECTL,
    TOOL_NPM,
    TOOL_PIP,
    TOOL_PYTHON,
    TOOL_SSH,
)
from ai_activity.models import AISession


@dataclass
class ChainStep:
    kind: str  # app | files | secret | tool | network | cloud | summary
    label: str
    detail: str = ""
    timestamp: str = ""
    count: int = 0
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_APP_LABELS = {
    "cursor": "Cursor",
    "claude": "Claude",
    "vscode": "VS Code",
    "windsurf": "Windsurf",
    "continue": "Continue",
    "cline": "Cline",
    "codex": "Codex",
    "chatgpt": "ChatGPT",
    "aider": "Aider",
}

_TOOL_LABELS = {
    TOOL_GIT: "Ran git",
    TOOL_DOCKER: "Ran docker",
    TOOL_SSH: "Opened SSH",
    TOOL_AWS: "Ran AWS CLI",
    TOOL_KUBECTL: "Ran kubectl",
    TOOL_NPM: "Ran npm",
    TOOL_PIP: "Ran pip",
    TOOL_PYTHON: "Ran python",
    TOOL_CURL: "Ran curl/wget",
}


def build_behavior_chain(session: AISession) -> list[ChainStep]:
    """Collapse session telemetry into a vertical narrative chain."""
    steps: list[ChainStep] = []

    app = _APP_LABELS.get(session.app_name, session.app_name.replace("_", " ").title() or "AI app")
    steps.append(
        ChainStep(
            kind="app",
            label=app,
            detail=f"session started · pid {session.root_pid}",
            timestamp=session.start_time,
            artifacts={"session_id": session.session_id, "app_name": session.app_name},
        )
    )

    # File access (inferred + real)
    file_reads = session.counters.files_read
    file_writes = session.counters.files_modified
    file_total = file_reads + file_writes
    if file_total > 0:
        parts = []
        if file_reads:
            parts.append(f"Read {file_reads} file{'s' if file_reads != 1 else ''}")
        if file_writes:
            parts.append(f"Wrote {file_writes} file{'s' if file_writes != 1 else ''}")
        steps.append(
            ChainStep(
                kind="files",
                label=" · ".join(parts) if parts else f"Touched {file_total} files",
                detail="from cmdline inference and/or file events",
                count=file_total,
                timestamp=_first_ts(session, "file"),
            )
        )

    # Secrets — one step per distinct sensitive path family
    for path in session.secrets_accessed[:12]:
        steps.append(
            ChainStep(
                kind="secret",
                label=_secret_label(path),
                detail=path,
                timestamp=_first_ts(session, "file"),
                artifacts={"path": path},
            )
        )

    # Tools — collapse by class, keep order of first appearance
    seen_tools: set[str] = set()
    for tool in session.tools:
        tc = tool.tool_class or ""
        if not tc or tc == "shell" or tc in seen_tools:
            continue
        seen_tools.add(tc)
        count = sum(1 for t in session.tools if t.tool_class == tc)
        base = _TOOL_LABELS.get(tc, f"Ran {tc}")
        label = f"{base} ×{count}" if count > 1 else base
        # Enrich with git/docker/k8s buckets when available
        extra = ""
        if tc == TOOL_GIT and session.git_repos:
            extra = session.git_repos[0]
        elif tc == TOOL_DOCKER and session.docker_activity:
            extra = session.docker_activity[0]
        elif tc == TOOL_KUBECTL and session.k8s_activity:
            extra = session.k8s_activity[0]
        elif tc in (TOOL_AWS, TOOL_SSH) and session.cloud_activity:
            extra = session.cloud_activity[0]
        steps.append(
            ChainStep(
                kind="tool",
                label=label,
                detail=extra or (tool.cmdline[:120] if tool.cmdline else ""),
                count=count,
                timestamp=tool.timestamp,
                artifacts={"tool_class": tc},
            )
        )

    # Network — notable external domains (+ optional byte volume)
    for domain in session.external_domains[:12]:
        matching = [
            n
            for n in session.networks
            if n.is_external and (n.domain == domain or n.remote_addr == domain)
        ]
        conn_count = len(matching)
        label = f"Connected to {domain}"
        if conn_count > 1:
            label = f"{label} ×{conn_count}"
        sent = sum(n.bytes_sent for n in matching)
        recv = sum(n.bytes_recv for n in matching)
        detail_parts = [f"{conn_count} connection{'s' if conn_count != 1 else ''}"]
        ips = sorted({n.remote_addr for n in matching if n.remote_addr and n.remote_addr != domain})
        if ips:
            detail_parts.append(", ".join(ips[:3]))
        if sent or recv:
            if sent:
                detail_parts.append(f"sent {_fmt_bytes(sent)}")
            if recv:
                detail_parts.append(f"recv {_fmt_bytes(recv)}")
        steps.append(
            ChainStep(
                kind="network",
                label=label,
                detail=" · ".join(detail_parts),
                count=conn_count,
                timestamp=_first_network_ts(session, domain),
                artifacts={"domain": domain, "bytes_sent": sent, "bytes_recv": recv},
            )
        )
        if sent > 0:
            steps.append(
                ChainStep(
                    kind="network",
                    label=f"Sent {_fmt_bytes(sent)}",
                    detail=domain,
                    count=sent,
                    timestamp=_first_network_ts(session, domain),
                    artifacts={"domain": domain, "bytes_sent": sent},
                )
            )

    # Cloud activity summary (if tools didn't already cover)
    if session.cloud_activity and TOOL_AWS not in seen_tools and TOOL_SSH not in seen_tools:
        steps.append(
            ChainStep(
                kind="cloud",
                label="Cloud / remote access",
                detail=", ".join(session.cloud_activity[:4]),
                count=len(session.cloud_activity),
            )
        )

    # Closing summary when session ended
    if session.status == "closed" and session.end_time:
        steps.append(
            ChainStep(
                kind="summary",
                label="Session ended",
                detail=f"risk {session.risk_score} · {session.counters.tool_executions} tools · {session.counters.network_connections} connections",
                timestamp=session.end_time,
            )
        )

    return steps


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f}KB"
    if n < 1024 * 1024 * 1024:
        mb = n / (1024 * 1024)
        return f"{mb:.0f}MB" if mb >= 10 else f"{mb:.1f}MB"
    gb = n / (1024 * 1024 * 1024)
    return f"{gb:.1f}GB"


def _secret_label(path: str) -> str:
    lower = path.lower()
    if ".ssh" in lower or "id_rsa" in lower or "id_ed25519" in lower:
        return f"Opened {path}" if path.startswith("~") or path.startswith("/") else "Opened ~/.ssh"
    if ".env" in lower:
        return f"Read {path}" if path else "Read .env"
    if ".aws" in lower or "credentials" in lower:
        return f"Opened {path}" if path else "Opened cloud credentials"
    if ".kube" in lower or "kubeconfig" in lower:
        return f"Opened {path}" if path else "Opened kubeconfig"
    return f"Accessed {path}"


def _first_ts(session: AISession, kind: str) -> str:
    for ev in session.timeline:
        if ev.kind == kind:
            return ev.timestamp
    return session.start_time


def _first_network_ts(session: AISession, domain: str) -> str:
    for n in session.networks:
        if n.domain == domain or n.remote_addr == domain:
            return n.timestamp
    return session.start_time
