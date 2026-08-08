"""Detection pipeline: Rule + Behavioral + Threat Intel + AI Activity → scored findings."""

from __future__ import annotations

__all__ = ["EngineHit", "process_event"]


def __getattr__(name: str):
    if name == "EngineHit":
        from pipeline.types import EngineHit

        return EngineHit
    if name == "process_event":
        from pipeline.orchestrator import process_event

        return process_event
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
