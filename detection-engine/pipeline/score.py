"""Simple severity → score mapping and multi-engine fusion."""

from __future__ import annotations

from rules.alerts import SecurityAlert
from rules.constants import SEVERITY_RANK, SEVERITY_SCORE

from pipeline.types import ENGINE_TIE_RANK, EngineHit, ScoredFinding

# Re-export for callers that import score.SEVERITY_SCORE.
__all__ = ["SEVERITY_SCORE", "finding_to_alert", "fuse", "score_for"]


def score_for(severity: str) -> int:
    return SEVERITY_SCORE.get((severity or "").strip().lower(), 0)


def _hit_rank(hit: EngineHit) -> tuple[int, int, int]:
    """Higher tuple wins: score, severity rank, engine preference."""
    return (
        hit.score,
        SEVERITY_RANK.get(hit.severity, 0),
        ENGINE_TIE_RANK.get(hit.engine, 0),
    )


def fuse(hits: list[EngineHit]) -> ScoredFinding | None:
    """Fuse engine hits into one finding. Empty → None."""
    if not hits:
        return None
    winner = max(hits, key=_hit_rank)
    return ScoredFinding(
        timestamp=winner.timestamp,
        device_id=winner.device_id,
        alert_type=winner.alert_type,
        severity=winner.severity,
        message=winner.message,
        score=winner.score,
        engines=[h.to_engine_dict() for h in hits],
        event_id=winner.event_id,
        event_type=winner.event_type,
        detail=winner.detail,
    )


def finding_to_alert(finding: ScoredFinding) -> SecurityAlert:
    return SecurityAlert(
        timestamp=finding.timestamp,
        device_id=finding.device_id,
        alert_type=finding.alert_type,
        severity=finding.severity,
        message=finding.message,
        event_id=finding.event_id,
        event_type=finding.event_type,
        detail=finding.detail,
        score=finding.score,
        engines=list(finding.engines),
    )
