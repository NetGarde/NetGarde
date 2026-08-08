"""Attach process_start / process_exit into an AI session spawn tree."""

from __future__ import annotations

from typing import Any

from ai_activity.detector import ProcessClassification
from ai_activity.models import AISession, ProcessNode, TimelineEvent


def upsert_process(
    session: AISession,
    *,
    process_id: str,
    pid: int,
    ppid: int,
    name: str,
    cmdline: str,
    role: str,
    tool_class: str | None,
    parent_process_id: str | None,
    start_time: str,
    classification: ProcessClassification | None = None,
    hash_sha256: str = "",
    signature_status: str = "",
) -> ProcessNode:
    existing = session.processes.get(process_id)
    if existing is None:
        node = ProcessNode(
            process_id=process_id,
            pid=pid,
            ppid=ppid,
            name=name,
            cmdline=cmdline,
            role=role,
            tool_class=tool_class,
            parent_process_id=parent_process_id,
            start_time=start_time,
            hash_sha256=hash_sha256,
            signature_status=signature_status,
        )
        session.processes[process_id] = node
        session.counters.process_count = len(session.processes)
    else:
        node = existing
        node.pid = pid
        node.ppid = ppid
        if name:
            node.name = name
        if cmdline:
            node.cmdline = cmdline
        if role:
            node.role = role
        if tool_class:
            node.tool_class = tool_class
        if parent_process_id:
            node.parent_process_id = parent_process_id
        if hash_sha256:
            node.hash_sha256 = hash_sha256
        if signature_status:
            node.signature_status = signature_status
        node.terminated = False
        node.end_time = None

    session.pid_index[pid] = process_id

    if parent_process_id and parent_process_id in session.processes:
        parent = session.processes[parent_process_id]
        if process_id not in parent.children:
            parent.children.append(process_id)

    return node


def terminate_process(session: AISession, process_id: str, end_time: str) -> ProcessNode | None:
    node = session.processes.get(process_id)
    if node is None:
        return None
    node.terminated = True
    node.end_time = end_time
    if session.pid_index.get(node.pid) == process_id:
        del session.pid_index[node.pid]
    return node


def timeline_process_start(session: AISession, node: ProcessNode) -> None:
    summary = f"{node.role}: {node.name or node.process_id}"
    if node.tool_class:
        summary = f"{node.tool_class}: {node.name}"
    session.append_timeline(
        TimelineEvent(
            kind="process_start",
            timestamp=node.start_time,
            process_id=node.process_id,
            summary=summary,
            artifacts={
                "pid": node.pid,
                "ppid": node.ppid,
                "role": node.role,
                "tool_class": node.tool_class,
                "cmdline": node.cmdline[:500] if node.cmdline else "",
            },
        )
    )


def timeline_process_exit(session: AISession, node: ProcessNode) -> None:
    session.append_timeline(
        TimelineEvent(
            kind="process_exit",
            timestamp=node.end_time or "",
            process_id=node.process_id,
            summary=f"exit: {node.name or node.process_id}",
            artifacts={"pid": node.pid, "role": node.role},
        )
    )


def payload_hash_sig(payload: dict[str, Any]) -> tuple[str, str]:
    h = str(
        payload.get("sha256")
        or payload.get("hash_sha256")
        or payload.get("hash")
        or ""
    ).strip()
    sig = str(
        payload.get("signature_status")
        or payload.get("code_signature")
        or payload.get("signed")
        or ""
    ).strip()
    return h, sig
