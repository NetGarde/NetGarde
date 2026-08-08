"""AI Activity Engine — reconstruct AI-app sessions and execution graphs."""

from __future__ import annotations

__all__ = ["AISession", "AiActivityEngine", "SessionManager"]


def __getattr__(name: str):
    if name == "AiActivityEngine":
        from ai_activity.engine import AiActivityEngine

        return AiActivityEngine
    if name == "SessionManager":
        from ai_activity.session_manager import SessionManager

        return SessionManager
    if name == "AISession":
        from ai_activity.models import AISession

        return AISession
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
