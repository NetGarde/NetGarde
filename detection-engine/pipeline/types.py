"""Shared hit / finding types for the detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE_RULE = "rule"
ENGINE_BEHAVIORAL = "behavioral"
ENGINE_THREAT_INTEL = "threat_intel"
ENGINE_AI_ACTIVITY = "ai_activity"

# Prefer rule over ai_activity over threat_intel over behavioral when scores/severities tie.
ENGINE_TIE_RANK: dict[str, int] = {
    ENGINE_RULE: 4,
    ENGINE_AI_ACTIVITY: 3,
    ENGINE_THREAT_INTEL: 2,
    ENGINE_BEHAVIORAL: 1,
}


@dataclass(frozen=True)
class EngineHit:
    engine: str
    alert_type: str
    severity: str
    score: int
    message: str
    device_id: str
    timestamp: str
    event_id: str | None = None
    event_type: str | None = None
    detail: str | None = None

    def to_engine_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "score": self.score,
        }


@dataclass
class ScoredFinding:
    """Single fused finding for an event that scored ≥1 engine hit."""

    timestamp: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    score: int
    engines: list[dict[str, Any]] = field(default_factory=list)
    event_id: str | None = None
    event_type: str | None = None
    detail: str | None = None
