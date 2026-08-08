"""Unit tests for score fusion and severity mapping."""

from __future__ import annotations

from pipeline.score import fuse, score_for
from pipeline.types import ENGINE_BEHAVIORAL, ENGINE_RULE, ENGINE_THREAT_INTEL, EngineHit


def _hit(
    *,
    engine: str = ENGINE_RULE,
    alert_type: str = "temp_path_execution",
    severity: str = "high",
    score: int | None = None,
) -> EngineHit:
    return EngineHit(
        engine=engine,
        alert_type=alert_type,
        severity=severity,
        score=score if score is not None else score_for(severity),
        message=f"{alert_type} msg",
        device_id="dev_1",
        timestamp="2026-08-03T12:00:00Z",
        event_id="evt_1",
        event_type="process_start",
    )


def test_score_for_table():
    assert score_for("low") == 25
    assert score_for("medium") == 50
    assert score_for("high") == 75
    assert score_for("unknown") == 0


def test_fuse_empty_returns_none():
    assert fuse([]) is None


def test_fuse_single_hit():
    finding = fuse([_hit()])
    assert finding is not None
    assert finding.score == 75
    assert finding.severity == "high"
    assert finding.alert_type == "temp_path_execution"
    assert finding.engines == [
        {
            "engine": ENGINE_RULE,
            "alert_type": "temp_path_execution",
            "severity": "high",
            "score": 75,
        }
    ]


def test_fuse_max_score_wins():
    finding = fuse(
        [
            _hit(engine=ENGINE_BEHAVIORAL, alert_type="novel_process", severity="medium"),
            _hit(engine=ENGINE_RULE, alert_type="temp_path_execution", severity="high"),
        ]
    )
    assert finding is not None
    assert finding.score == 75
    assert finding.alert_type == "temp_path_execution"
    assert len(finding.engines) == 2


def test_fuse_tie_prefers_rule_engine():
    finding = fuse(
        [
            _hit(engine=ENGINE_BEHAVIORAL, alert_type="novel_process", severity="medium"),
            _hit(engine=ENGINE_THREAT_INTEL, alert_type="ioc_hit", severity="medium"),
            _hit(engine=ENGINE_RULE, alert_type="script_spawns_shell", severity="medium"),
        ]
    )
    assert finding is not None
    assert finding.alert_type == "script_spawns_shell"
    assert finding.engines[0]["engine"] == ENGINE_BEHAVIORAL  # order preserved
