"""Consumer / pipeline integration for scored findings."""

from __future__ import annotations

import json
from unittest.mock import patch

import consumer
from pipeline.baseline_store import BaselineStore
from pipeline.behavioral import BehavioralEngine
from pipeline.orchestrator import Pipeline
from rules.constants import ALERT_NOVEL_PROCESS, ALERT_TEMP_PATH_EXECUTION, TYPE_PROCESS_START
from rules.state import StateStore


def _process_start(
    *,
    device_id: str = "dev_n",
    comm: str = "evil",
    executable: str = "/tmp/evil",
    event_id: str = "e1",
) -> dict:
    return {
        "device_id": device_id,
        "event_id": event_id,
        "type": TYPE_PROCESS_START,
        "ts": "2026-07-30T12:00:00Z",
        "payload": {
            "pid": 42,
            "ppid": 1,
            "comm": comm,
            "executable": executable,
            "parent_comm": "bash",
            "cmdline": executable,
        },
    }


def setup_function() -> None:
    consumer._pipeline = Pipeline()
    consumer._seen_fingerprints.clear()


def test_pipeline_scores_temp_path_rule():
    pipe = Pipeline()
    finding = pipe.process_event(_process_start())
    assert finding is not None
    assert finding.alert_type == ALERT_TEMP_PATH_EXECUTION
    assert finding.score == 75
    assert finding.severity == "high"
    assert any(e["engine"] == "rule" for e in (finding.engines or []))


def test_pipeline_emits_novel_when_warm():
    baseline = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=2)
    baseline.observe("dev_n", "process_comm", "seed", now=1_000_000.0)
    pipe = Pipeline(
        store=StateStore(),
        baseline=baseline,
        behavioral=BehavioralEngine(baseline),
    )
    finding = pipe.process_event(
        _process_start(comm="brandnew", executable="/usr/local/bin/brandnew", event_id="e2")
    )
    assert finding is not None
    assert finding.alert_type == ALERT_NOVEL_PROCESS
    assert finding.score == 50
    assert any(e["engine"] == "behavioral" for e in (finding.engines or []))


def test_consumer_process_event_emits_scored_alert():
    remembered: list[dict] = []

    def _remember(api: dict) -> None:
        remembered.append(api)

    with patch.object(consumer, "remember_alert", side_effect=_remember):
        consumer._process_event(json.dumps(_process_start(event_id="e99")))

    assert len(remembered) == 1
    assert remembered[0]["score"] == 75
    assert remembered[0]["alert_type"] == ALERT_TEMP_PATH_EXECUTION
    assert "engines" in remembered[0]
