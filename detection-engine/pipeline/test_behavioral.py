"""BehavioralEngine novelty + suppress (in-memory baseline)."""

from __future__ import annotations

from pipeline.baseline_store import BaselineStore
from pipeline.behavioral import BehavioralEngine
from pipeline.score import score_for
from pipeline.types import ENGINE_RULE, EngineHit
from rules.constants import ALERT_NOVEL_PROCESS, TYPE_PROCESS_START
from rules.state import StateStore


def _process_start(*, device_id: str = "dev_n", comm: str = "evil", event_id: str = "e1") -> dict:
    return {
        "device_id": device_id,
        "event_id": event_id,
        "type": TYPE_PROCESS_START,
        "ts": "2026-07-30T12:00:00Z",
        "payload": {
            "pid": 42,
            "ppid": 1,
            "comm": comm,
            "executable": f"/tmp/{comm}",
            "parent_comm": "bash",
        },
    }


def _rule_hit(*, alert_type: str, detail: str, severity: str = "high") -> EngineHit:
    return EngineHit(
        engine=ENGINE_RULE,
        alert_type=alert_type,
        severity=severity,
        score=score_for(severity),
        message="test",
        device_id="dev_n",
        timestamp="2026-07-30T12:00:00Z",
        event_id="e1",
        event_type=TYPE_PROCESS_START,
        detail=detail,
    )


def test_novel_when_profile_warm():
    baseline = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=2)
    engine = BehavioralEngine(baseline)
    store = StateStore()
    # Warm with one other key first.
    baseline.observe("dev_n", "process_comm", "chrome", now=1_000_000.0)
    store.record_event(_process_start())
    beh, kept = engine.evaluate(_process_start(), [], store)
    assert len(beh) == 1
    assert beh[0].alert_type == ALERT_NOVEL_PROCESS
    assert beh[0].score == 50
    assert kept == []


def test_no_novel_when_cold():
    baseline = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=30)
    engine = BehavioralEngine(baseline)
    store = StateStore()
    store.record_event(_process_start(comm="chrome"))
    beh, _kept = engine.evaluate(_process_start(comm="chrome"), [], store)
    assert beh == []


def test_debounce_skips_second_observe():
    baseline = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=2)
    engine = BehavioralEngine(baseline)
    store = StateStore()
    baseline.observe("dev_n", "process_comm", "seed", now=1_000_000.0)
    payload = _process_start(comm="node")
    store.record_event(payload)
    first, _ = engine.evaluate(payload, [], store)
    second, _ = engine.evaluate(payload, [], store)
    assert len(first) == 1
    assert second == []


def test_suppress_drops_established_temp_path():
    baseline = BaselineStore(suppress_count=2, suppress_age_hours=1, profile_min_keys=30)
    engine = BehavioralEngine(baseline)
    store = StateStore()
    now = 1_000_000.0
    baseline.observe("dev_n", "temp_path", "evil", now=now)
    # Age past suppress window with enough count.
    baseline.observe("dev_n", "temp_path", "evil", now=now + 3600 + 10)

    hit = _rule_hit(
        alert_type="temp_path_execution",
        detail='{"executable":"/tmp/evil","comm":"evil"}',
    )
    beh, kept = engine.evaluate({"type": "network_summary", "device_id": "dev_n"}, [hit], store)
    assert beh == []
    assert kept == []


def test_keeps_chain_alerts_without_baseline():
    engine = BehavioralEngine(BaselineStore())
    store = StateStore()
    hit = _rule_hit(
        alert_type="shell_spawns_downloader",
        detail='{"parent_comm":"zsh","child_comm":"curl"}',
    )
    _beh, kept = engine.evaluate({"type": "network_summary", "device_id": "dev_n"}, [hit], store)
    assert kept == [hit]
