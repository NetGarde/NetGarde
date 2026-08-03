"""Consumer profile observe / novelty helpers."""

from __future__ import annotations

from unittest.mock import patch

import consumer
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


def setup_function() -> None:
    consumer._state = StateStore()
    consumer._profile_observe_seen.clear()
    consumer._seen_fingerprints.clear()


def test_collect_profile_alerts_emits_novel_when_warm():
    consumer._state.record_event(_process_start())
    with patch(
        "consumer.observe_behavior",
        return_value={
            "established": False,
            "profile_warm": True,
            "action": "emit",
            "count": 1,
        },
    ) as mocked:
        alerts = consumer._collect_profile_alerts(_process_start())
    assert len(alerts) == 1
    assert alerts[0].alert_type == ALERT_NOVEL_PROCESS
    # process_comm only (no process_chain)
    assert mocked.call_count == 1


def test_collect_profile_alerts_skips_when_cold():
    with patch(
        "consumer.observe_behavior",
        return_value={
            "established": False,
            "profile_warm": False,
            "action": "emit",
            "count": 1,
        },
    ):
        alerts = consumer._collect_profile_alerts(_process_start(comm="chrome"))
    assert alerts == []


def test_collect_profile_alerts_debounces_repeat():
    payload = _process_start(comm="node")
    with patch(
        "consumer.observe_behavior",
        return_value={
            "established": True,
            "profile_warm": True,
            "action": "suppress",
            "count": 50,
        },
    ) as mocked:
        first = consumer._collect_profile_alerts(payload)
        second = consumer._collect_profile_alerts(payload)
    assert first == []
    assert second == []
    # First call observes process_comm; second is fully debounced.
    assert mocked.call_count == 1


def test_filter_suppressed_drops_established_alert():
    from rules.alerts import SecurityAlert

    alert = SecurityAlert(
        timestamp="2026-07-30T12:00:00Z",
        device_id="dev_n",
        event_id="e1",
        event_type=TYPE_PROCESS_START,
        alert_type="temp_path_execution",
        severity="high",
        message="Process started from suspicious path",
        detail='{"executable":"/tmp/evil","comm":"evil"}',
    )
    with patch(
        "consumer.observe_behavior",
        return_value={"action": "suppress", "count": 25},
    ):
        kept = consumer._filter_suppressed([alert])
    assert kept == []


def test_filter_suppressed_keeps_chain_alerts_without_baseline():
    from rules.alerts import SecurityAlert

    alert = SecurityAlert(
        timestamp="2026-07-30T12:00:00Z",
        device_id="dev_n",
        event_id="e1",
        event_type=TYPE_PROCESS_START,
        alert_type="shell_spawns_downloader",
        severity="high",
        message="Shell spawned network downloader (curl)",
        detail='{"parent_comm":"zsh","child_comm":"curl"}',
    )
    with patch("consumer.observe_behavior") as mocked:
        kept = consumer._filter_suppressed([alert])
    assert kept == [alert]
    mocked.assert_not_called()
