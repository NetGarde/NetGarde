"""HTTP snapshot helpers for AI sessions (bound from consumer)."""

from __future__ import annotations

from typing import Any, Optional

from ai_activity.behavior_chain import build_behavior_chain
from ai_activity.graph_builder import build_execution_graph, spawn_tree_dict
from ai_activity.session_manager import SessionManager

_manager: Optional[SessionManager] = None


def bind(manager: SessionManager) -> None:
    global _manager
    _manager = manager


def get_manager() -> Optional[SessionManager]:
    return _manager


def list_sessions(device_id: str, *, limit: int = 50, include_closed: bool = True) -> dict[str, Any]:
    device = (device_id or "").strip()
    mgr = _manager
    if mgr is None or not device:
        return {"device_id": device, "total": 0, "items": []}
    items = mgr.list_sessions(device, include_closed=include_closed, limit=limit)
    return {
        "device_id": device,
        "total": len(items),
        "items": [s.summary_dict() for s in items],
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    mgr = _manager
    if mgr is None:
        return None
    session = mgr.get((session_id or "").strip())
    if session is None:
        return None
    detail = session.detail_dict()
    detail["spawn_tree"] = spawn_tree_dict(session)
    detail["activity_chain"] = [s.to_dict() for s in build_behavior_chain(session)]
    return detail


def get_session_graph(session_id: str) -> dict[str, Any] | None:
    mgr = _manager
    if mgr is None:
        return None
    session = mgr.get((session_id or "").strip())
    if session is None:
        return None
    graph = build_execution_graph(session)
    return {
        "session_id": session.session_id,
        "device_id": session.device_id,
        "app_name": session.app_name,
        "graph": graph.to_dict(),
    }


def get_session_chain(session_id: str) -> dict[str, Any] | None:
    mgr = _manager
    if mgr is None:
        return None
    session = mgr.get((session_id or "").strip())
    if session is None:
        return None
    steps = build_behavior_chain(session)
    return {
        "session_id": session.session_id,
        "device_id": session.device_id,
        "app_name": session.app_name,
        "total": len(steps),
        "items": [s.to_dict() for s in steps],
    }


def get_session_timeline(session_id: str, *, limit: int = 200) -> dict[str, Any] | None:
    mgr = _manager
    if mgr is None:
        return None
    session = mgr.get((session_id or "").strip())
    if session is None:
        return None
    events = session.timeline[-max(1, limit) :]
    return {
        "session_id": session.session_id,
        "device_id": session.device_id,
        "total": len(session.timeline),
        "items": [e.to_dict() for e in events],
    }


def lookup_process(process_id: str) -> dict[str, Any] | None:
    mgr = _manager
    if mgr is None:
        return None
    pid = (process_id or "").strip()
    if not pid:
        return None
    for sid in mgr.all_session_ids():
        session = mgr.get(sid)
        if session is None:
            continue
        if pid in session.processes or session.root_process_id == pid:
            return {
                "process_id": pid,
                "session_id": session.session_id,
                "device_id": session.device_id,
                "app_name": session.app_name,
                "role": session.processes[pid].role if pid in session.processes else "root",
            }
    return None
