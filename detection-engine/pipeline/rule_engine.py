"""Rule engine adapter: YAML DSL alerts → EngineHit list."""

from __future__ import annotations

from typing import Any

from rules.alerts import SecurityAlert
from rules.engine import evaluate_event
from rules.state import StateStore

from pipeline.score import score_for
from pipeline.types import ENGINE_RULE, EngineHit


def alert_to_hit(alert: SecurityAlert, *, engine: str = ENGINE_RULE) -> EngineHit:
    return EngineHit(
        engine=engine,
        alert_type=alert.alert_type,
        severity=alert.severity,
        score=score_for(alert.severity),
        message=alert.message,
        device_id=alert.device_id,
        timestamp=alert.timestamp,
        event_id=alert.event_id,
        event_type=alert.event_type,
        detail=alert.detail,
    )


def evaluate(event: dict[str, Any], store: StateStore) -> list[EngineHit]:
    """Record event into the chain and evaluate DSL rules."""
    alerts = evaluate_event(event, store)
    return [alert_to_hit(alert) for alert in alerts]
