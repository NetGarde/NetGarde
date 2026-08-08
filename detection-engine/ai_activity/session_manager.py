"""Thread-safe AI session registry and process→session index."""

from __future__ import annotations

import hashlib
import threading
from typing import Any

from ai_activity.catalog import DEFAULT_MAX_CLOSED_SESSIONS_PER_DEVICE
from ai_activity.models import AISession


class SessionManager:
    """Owns all AISession objects for the detection-engine process."""

    def __init__(
        self,
        *,
        max_closed_per_device: int = DEFAULT_MAX_CLOSED_SESSIONS_PER_DEVICE,
    ) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, AISession] = {}
        # (device_id, process_id) → session_id
        self._process_index: dict[tuple[str, str], str] = {}
        # (device_id, pid) → session_id for active pids in AI trees
        self._pid_index: dict[tuple[str, int], str] = {}
        self._max_closed_per_device = max_closed_per_device

    def create_session(
        self,
        *,
        device_id: str,
        app_name: str,
        root_process_id: str,
        root_pid: int,
        start_time: str,
    ) -> AISession:
        with self._lock:
            session_id = _make_session_id(device_id, root_process_id)
            existing = self._sessions.get(session_id)
            if existing is not None and existing.status == "active":
                return existing
            session = AISession(
                session_id=session_id,
                device_id=device_id,
                app_name=app_name,
                root_process_id=root_process_id,
                root_pid=root_pid,
                start_time=start_time,
            )
            self._sessions[session_id] = session
            self._index_process(device_id, root_process_id, root_pid, session_id)
            return session

    def get(self, session_id: str) -> AISession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def session_for_process(self, device_id: str, process_id: str) -> AISession | None:
        with self._lock:
            sid = self._process_index.get((device_id, process_id))
            if not sid:
                return None
            return self._sessions.get(sid)

    def session_for_pid(self, device_id: str, pid: int) -> AISession | None:
        with self._lock:
            if pid <= 0:
                return None
            sid = self._pid_index.get((device_id, pid))
            if not sid:
                return None
            return self._sessions.get(sid)

    def attach_process(
        self,
        session: AISession,
        *,
        process_id: str,
        pid: int,
    ) -> None:
        with self._lock:
            self._index_process(session.device_id, process_id, pid, session.session_id)

    def resolve_by_ancestry(
        self,
        device_id: str,
        *,
        process_id: str | None,
        pid: int,
        ppid: int,
        parent_process_id: str | None,
        walk_parent_pids: list[int] | None = None,
    ) -> AISession | None:
        """Find session for this process via direct index or parent walk."""
        with self._lock:
            if process_id:
                sid = self._process_index.get((device_id, process_id))
                if sid:
                    return self._sessions.get(sid)
            if pid > 0:
                sid = self._pid_index.get((device_id, pid))
                if sid:
                    return self._sessions.get(sid)
            if parent_process_id:
                sid = self._process_index.get((device_id, parent_process_id))
                if sid:
                    return self._sessions.get(sid)
            if ppid > 0:
                sid = self._pid_index.get((device_id, ppid))
                if sid:
                    return self._sessions.get(sid)
            for ancestor_pid in walk_parent_pids or []:
                if ancestor_pid <= 0:
                    continue
                sid = self._pid_index.get((device_id, ancestor_pid))
                if sid:
                    return self._sessions.get(sid)
            return None

    def close_session(self, session: AISession, end_time: str) -> None:
        with self._lock:
            session.status = "closed"
            session.end_time = end_time
            # Drop active pid index entries for this session
            drop_pids = [
                key for key, sid in self._pid_index.items() if sid == session.session_id
            ]
            for key in drop_pids:
                del self._pid_index[key]
            self._evict_closed(session.device_id)

    def list_sessions(
        self,
        device_id: str,
        *,
        include_closed: bool = True,
        limit: int = 100,
    ) -> list[AISession]:
        with self._lock:
            items = [
                s
                for s in self._sessions.values()
                if s.device_id == device_id
                and (include_closed or s.status == "active")
            ]
            items.sort(key=lambda s: s.start_time, reverse=True)
            return items[: max(1, limit)]

    def all_session_ids(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def lock(self) -> threading.RLock:
        return self._lock

    def _index_process(
        self, device_id: str, process_id: str, pid: int, session_id: str
    ) -> None:
        self._process_index[(device_id, process_id)] = session_id
        if pid > 0:
            self._pid_index[(device_id, pid)] = session_id

    def _evict_closed(self, device_id: str) -> None:
        closed = [
            s
            for s in self._sessions.values()
            if s.device_id == device_id and s.status == "closed"
        ]
        closed.sort(key=lambda s: s.end_time or s.start_time)
        overflow = len(closed) - self._max_closed_per_device
        for session in closed[: max(0, overflow)]:
            self._drop_session(session)

    def _drop_session(self, session: AISession) -> None:
        self._sessions.pop(session.session_id, None)
        drop_proc = [
            key
            for key, sid in self._process_index.items()
            if sid == session.session_id
        ]
        for key in drop_proc:
            del self._process_index[key]
        drop_pid = [
            key for key, sid in self._pid_index.items() if sid == session.session_id
        ]
        for key in drop_pid:
            del self._pid_index[key]


def _make_session_id(device_id: str, root_process_id: str) -> str:
    digest = hashlib.sha1(f"{device_id}|{root_process_id}".encode("utf-8")).hexdigest()[:16]
    return f"ais_{digest}"
