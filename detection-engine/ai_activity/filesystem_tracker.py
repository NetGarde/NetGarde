"""Filesystem activity: cmdline-inferred paths + real file open/write events."""

from __future__ import annotations

import re
from typing import Any

from ai_activity.detector import extract_secret_paths
from ai_activity.models import AISession, FileActivity, TimelineEvent

_FILE_READER_BASENAMES = frozenset(
    {"cat", "head", "tail", "less", "more", "bat", "rg", "grep", "find", "fd", "stat", "file", "wc"}
)
_PATH_TOKEN_RE = re.compile(r"(?:~|/|\./|\.\./)[^\s:;|&]+")


def record_inferred_from_cmdline(
    session: AISession,
    *,
    process_id: str,
    cmdline: str,
    timestamp: str,
    process_name: str = "",
) -> list[FileActivity]:
    """Infer path access from command-line arguments (secrets + reader tools)."""
    out: list[FileActivity] = []
    seen: set[str] = set()

    for path in extract_secret_paths(cmdline):
        if path in seen:
            continue
        seen.add(path)
        out.append(
            _record_inferred(
                session,
                process_id=process_id,
                path=path,
                timestamp=timestamp,
                is_secret=True,
            )
        )

    base = (process_name or "").strip().lower()
    if not base and cmdline:
        base = cmdline.split()[0].rsplit("/", 1)[-1].lower()
    is_reader = base in _FILE_READER_BASENAMES or any(
        (cmdline or "").lstrip().startswith(f"{b} ") for b in _FILE_READER_BASENAMES
    )
    if is_reader:
        for match in _PATH_TOKEN_RE.findall(cmdline or ""):
            path = match.strip("\"'")
            if not path or path in seen or len(path) < 2:
                continue
            seen.add(path)
            is_secret = bool(extract_secret_paths(path))
            out.append(
                _record_inferred(
                    session,
                    process_id=process_id,
                    path=path,
                    timestamp=timestamp,
                    is_secret=is_secret,
                )
            )
    return out


def _record_inferred(
    session: AISession,
    *,
    process_id: str,
    path: str,
    timestamp: str,
    is_secret: bool,
) -> FileActivity:
    activity = FileActivity(
        process_id=process_id,
        path=path,
        operation="read",
        timestamp=timestamp,
        is_secret=is_secret,
        inferred=True,
    )
    session.files.append(activity)
    if is_secret:
        session.add_secret(path)
    session.counters.files_read += 1
    summary = f"secret path (inferred): {path}" if is_secret else f"file read (inferred): {path}"
    session.append_timeline(
        TimelineEvent(
            kind="file",
            timestamp=timestamp,
            process_id=process_id,
            summary=summary,
            artifacts={"path": path, "inferred": True, "is_secret": is_secret},
        )
    )
    return activity


def record_file_access(
    session: AISession,
    *,
    process_id: str,
    payload: dict[str, Any],
    timestamp: str,
    default_operation: str = "open",
) -> FileActivity | None:
    """Ingest a real file_open / file_write event when the agent emits one."""
    path = str(
        payload.get("path")
        or payload.get("file_path")
        or payload.get("target_path")
        or ""
    ).strip()
    if not path:
        return None
    operation = (
        str(payload.get("operation") or default_operation).strip().lower()
        or default_operation
    )
    secrets = extract_secret_paths(path)
    is_secret = bool(secrets)
    activity = FileActivity(
        process_id=process_id,
        path=path,
        operation=operation,
        timestamp=timestamp,
        is_secret=is_secret,
        inferred=False,
    )
    session.files.append(activity)
    if operation in ("write", "create", "modify", "delete"):
        session.counters.files_modified += 1
    else:
        session.counters.files_read += 1
    if is_secret:
        session.add_secret(path)
    session.append_timeline(
        TimelineEvent(
            kind="file",
            timestamp=timestamp,
            process_id=process_id,
            summary=f"file {operation}: {path}",
            artifacts={"path": path, "operation": operation, "is_secret": is_secret},
        )
    )
    return activity


def record_file_write(
    session: AISession,
    *,
    process_id: str,
    payload: dict[str, Any],
    timestamp: str,
) -> FileActivity | None:
    """Ingest a real file_write event when the agent emits one."""
    return record_file_access(
        session,
        process_id=process_id,
        payload=payload,
        timestamp=timestamp,
        default_operation="write",
    )
