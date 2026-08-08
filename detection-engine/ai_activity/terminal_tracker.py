"""Track Pty Host → terminal → shell relationships within a session."""

from __future__ import annotations

from ai_activity.catalog import ROLE_PTY_HOST, ROLE_SHELL, ROLE_TERMINAL
from ai_activity.models import AISession, ProcessNode, TimelineEvent


def note_terminal_role(session: AISession, node: ProcessNode) -> None:
    """Record terminal-related process appearances on the timeline."""
    if node.role not in (ROLE_PTY_HOST, ROLE_TERMINAL, ROLE_SHELL):
        return
    labels = {
        ROLE_PTY_HOST: "Pty Host",
        ROLE_TERMINAL: "Terminal",
        ROLE_SHELL: "Shell",
    }
    session.append_timeline(
        TimelineEvent(
            kind="terminal",
            timestamp=node.start_time,
            process_id=node.process_id,
            summary=f"{labels.get(node.role, node.role)}: {node.name}",
            artifacts={
                "role": node.role,
                "pid": node.pid,
                "cmdline": (node.cmdline or "")[:500],
            },
        )
    )


def session_has_pty_or_shell(session: AISession) -> bool:
    return any(
        n.role in (ROLE_PTY_HOST, ROLE_TERMINAL, ROLE_SHELL) for n in session.processes.values()
    )


def shells_in_session(session: AISession) -> list[ProcessNode]:
    return [n for n in session.processes.values() if n.role == ROLE_SHELL]
