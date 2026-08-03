"""Detection pipeline: Rule + Behavioral + Threat Intel → scored findings."""

from __future__ import annotations

from pipeline.orchestrator import process_event
from pipeline.types import EngineHit

__all__ = ["EngineHit", "process_event"]
