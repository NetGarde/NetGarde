"""Classify and record tool executions under an AI session."""

from __future__ import annotations

from ai_activity.catalog import (
    TOOL_AWS,
    TOOL_DOCKER,
    TOOL_GIT,
    TOOL_KUBECTL,
    TOOL_SSH,
)
from ai_activity.detector import (
    extract_cloud_activity,
    extract_docker_activity,
    extract_git_repo,
    extract_k8s_activity,
)
from ai_activity.models import AISession, ProcessNode, TimelineEvent, ToolExecution


def record_tool(session: AISession, node: ProcessNode, timestamp: str) -> ToolExecution | None:
    if not node.tool_class:
        return None

    summary = _summarize(node)
    execution = ToolExecution(
        tool_class=node.tool_class,
        process_id=node.process_id,
        pid=node.pid,
        name=node.name,
        cmdline=node.cmdline,
        timestamp=timestamp or node.start_time,
        summary=summary,
    )
    session.tools.append(execution)
    session.counters.tool_executions = len(session.tools)

    _enrich_buckets(session, node)

    session.append_timeline(
        TimelineEvent(
            kind="tool",
            timestamp=execution.timestamp,
            process_id=node.process_id,
            summary=summary,
            artifacts={
                "tool_class": node.tool_class,
                "cmdline": (node.cmdline or "")[:500],
            },
        )
    )
    return execution


def _summarize(node: ProcessNode) -> str:
    name = node.name or node.tool_class or "tool"
    cmd = (node.cmdline or "").strip()
    if cmd:
        short = cmd if len(cmd) <= 80 else cmd[:77] + "..."
        return f"{name}: {short}"
    return name


def _enrich_buckets(session: AISession, node: ProcessNode) -> None:
    cmd = node.cmdline or ""
    tc = node.tool_class
    if tc == TOOL_GIT:
        repo = extract_git_repo(cmd)
        if repo:
            session.add_unique(session.git_repos, repo)
        elif cmd:
            parts = cmd.split()
            session.add_unique(session.git_repos, " ".join(parts[:3]) if parts else "git")
    elif tc == TOOL_DOCKER:
        act = extract_docker_activity(cmd)
        if act:
            session.add_unique(session.docker_activity, act)
    elif tc == TOOL_KUBECTL:
        act = extract_k8s_activity(cmd)
        if act:
            session.add_unique(session.k8s_activity, act)
    elif tc in (TOOL_AWS, TOOL_SSH):
        act = extract_cloud_activity(cmd, tc)
        if act:
            session.add_unique(session.cloud_activity, act)
