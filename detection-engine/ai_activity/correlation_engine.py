"""Correlate AI-session activity into higher-level findings."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from ai_activity.catalog import (
    FINDING_CLOUD_CLI,
    FINDING_CONTAINER_DEPLOY,
    FINDING_MULTI_TOOL_BURST,
    FINDING_SECRETS_ACCESS,
    FINDING_SHELL_NETWORK_EXFIL,
    FINDING_TERMINAL_TOOL_CHAIN,
    MULTI_TOOL_BURST_THRESHOLD,
    MULTI_TOOL_BURST_WINDOW_SECONDS,
    ROLE_SHELL,
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
from ai_activity.models import AISession, SessionFinding
from ai_activity.terminal_tracker import session_has_pty_or_shell
from rules.chain import parse_ts
from rules.constants import SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_SCORE


def evaluate_session(
    session: AISession,
    *,
    trigger: str,
    timestamp: str,
    context: dict[str, Any] | None = None,
) -> list[SessionFinding]:
    """Run incremental correlation rules; return newly created findings."""
    ctx = context or {}
    new_findings: list[SessionFinding] = []

    def once(finding_type: str) -> bool:
        return finding_type not in session._emitted_finding_types

    # 1) Terminal → tool chain
    if trigger in ("tool", "process_start") and once(FINDING_TERMINAL_TOOL_CHAIN):
        if session_has_pty_or_shell(session) and _has_interesting_tool(session):
            path = _tool_path_labels(session)
            finding = SessionFinding(
                finding_type=FINDING_TERMINAL_TOOL_CHAIN,
                severity=SEVERITY_MEDIUM,
                score=SEVERITY_SCORE[SEVERITY_MEDIUM],
                message=f"AI session ({session.app_name}) terminal tool chain: {' → '.join(path)}",
                timestamp=timestamp,
                detail={
                    "app_name": session.app_name,
                    "session_id": session.session_id,
                    "execution_path": path,
                },
            )
            new_findings.append(finding)

    # 2) Shell + curl/wget + external network
    if trigger in ("network", "tool") and once(FINDING_SHELL_NETWORK_EXFIL):
        if _shell_downloader_network(session):
            domains = list(session.external_domains[-5:])
            finding = SessionFinding(
                finding_type=FINDING_SHELL_NETWORK_EXFIL,
                severity=SEVERITY_HIGH,
                score=SEVERITY_SCORE[SEVERITY_HIGH],
                message=(
                    f"AI session ({session.app_name}) shell downloader reached "
                    f"{', '.join(domains) or 'external host'}"
                ),
                timestamp=timestamp,
                detail={
                    "app_name": session.app_name,
                    "session_id": session.session_id,
                    "domains": domains,
                    "execution_path": _tool_path_labels(session),
                },
            )
            new_findings.append(finding)

    # 3) Secrets access
    if trigger in ("file", "process_start", "tool") and once(FINDING_SECRETS_ACCESS):
        if session.secrets_accessed:
            finding = SessionFinding(
                finding_type=FINDING_SECRETS_ACCESS,
                severity=SEVERITY_HIGH,
                score=SEVERITY_SCORE[SEVERITY_HIGH],
                message=(
                    f"AI session ({session.app_name}) accessed sensitive paths: "
                    f"{', '.join(session.secrets_accessed[:3])}"
                ),
                timestamp=timestamp,
                detail={
                    "app_name": session.app_name,
                    "session_id": session.session_id,
                    "secrets": list(session.secrets_accessed),
                    "execution_path": _tool_path_labels(session),
                },
            )
            new_findings.append(finding)

    # 4) Cloud CLI (aws / kubectl / ssh)
    if trigger in ("tool", "process_start") and once(FINDING_CLOUD_CLI):
        if session.cloud_activity or session.k8s_activity or _has_tool_classes(
            session, {TOOL_AWS, TOOL_SSH, TOOL_KUBECTL}
        ):
            finding = SessionFinding(
                finding_type=FINDING_CLOUD_CLI,
                severity=SEVERITY_HIGH,
                score=SEVERITY_SCORE[SEVERITY_HIGH],
                message=f"AI session ({session.app_name}) invoked cloud/infra CLI tools",
                timestamp=timestamp,
                detail={
                    "app_name": session.app_name,
                    "session_id": session.session_id,
                    "cloud_activity": list(session.cloud_activity),
                    "k8s_activity": list(session.k8s_activity),
                    "execution_path": _tool_path_labels(session),
                },
            )
            new_findings.append(finding)

    # 5) Docker build/deploy + kubectl
    if trigger in ("tool", "process_start") and once(FINDING_CONTAINER_DEPLOY):
        has_docker = bool(session.docker_activity) or _has_tool_classes(session, {TOOL_DOCKER})
        has_k8s = bool(session.k8s_activity) or _has_tool_classes(session, {TOOL_KUBECTL})
        if has_docker and has_k8s:
            finding = SessionFinding(
                finding_type=FINDING_CONTAINER_DEPLOY,
                severity=SEVERITY_HIGH,
                score=SEVERITY_SCORE[SEVERITY_HIGH],
                message=f"AI session ({session.app_name}) container build/deploy activity",
                timestamp=timestamp,
                detail={
                    "app_name": session.app_name,
                    "session_id": session.session_id,
                    "docker_activity": list(session.docker_activity),
                    "k8s_activity": list(session.k8s_activity),
                    "execution_path": _tool_path_labels(session),
                },
            )
            new_findings.append(finding)

    # 6) Multi-tool burst
    if trigger in ("tool", "process_start") and once(FINDING_MULTI_TOOL_BURST):
        classes = _recent_tool_classes(session, timestamp, MULTI_TOOL_BURST_WINDOW_SECONDS)
        if len(classes) >= MULTI_TOOL_BURST_THRESHOLD:
            finding = SessionFinding(
                finding_type=FINDING_MULTI_TOOL_BURST,
                severity=SEVERITY_MEDIUM,
                score=SEVERITY_SCORE[SEVERITY_MEDIUM],
                message=(
                    f"AI session ({session.app_name}) ran {len(classes)} tool classes "
                    f"in {MULTI_TOOL_BURST_WINDOW_SECONDS}s"
                ),
                timestamp=timestamp,
                detail={
                    "app_name": session.app_name,
                    "session_id": session.session_id,
                    "tool_classes": sorted(classes),
                    "execution_path": _tool_path_labels(session),
                },
            )
            new_findings.append(finding)

    for finding in new_findings:
        session.findings.append(finding)
        session._emitted_finding_types.add(finding.finding_type)
        if finding.finding_type not in session.risk_factors:
            session.risk_factors.append(finding.finding_type)

    return new_findings


def _has_interesting_tool(session: AISession) -> bool:
    interesting = {
        TOOL_GIT,
        TOOL_DOCKER,
        TOOL_SSH,
        TOOL_AWS,
        TOOL_KUBECTL,
        TOOL_NPM,
        TOOL_PIP,
        TOOL_PYTHON,
        TOOL_CURL,
    }
    return any(t.tool_class in interesting for t in session.tools)


def _has_tool_classes(session: AISession, classes: set[str]) -> bool:
    return any(t.tool_class in classes for t in session.tools)


def _tool_path_labels(session: AISession, *, limit: int = 10) -> list[str]:
    path = [session.app_name]
    for t in session.tools[-limit:]:
        label = t.name or t.tool_class
        if label and path[-1] != label:
            path.append(label)
    return path


def _shell_downloader_network(session: AISession) -> bool:
    has_shell = any(n.role == ROLE_SHELL for n in session.processes.values())
    has_curl = any(t.tool_class == TOOL_CURL for t in session.tools)
    has_ext = any(n.is_external for n in session.networks)
    return has_shell and has_curl and has_ext


def _recent_tool_classes(session: AISession, timestamp: str, window_s: int) -> set[str]:
    try:
        end = parse_ts(timestamp)
    except Exception:
        return {t.tool_class for t in session.tools if t.tool_class}
    start = end - timedelta(seconds=window_s)
    out: set[str] = set()
    for t in session.tools:
        if not t.tool_class:
            continue
        try:
            ts = parse_ts(t.timestamp)
        except Exception:
            out.add(t.tool_class)
            continue
        if start <= ts <= end:
            out.add(t.tool_class)
    return out
