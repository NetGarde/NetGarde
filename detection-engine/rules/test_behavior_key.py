from rules.alerts import SecurityAlert
from rules.behavior_key import behavior_from_alert
from rules.constants import (
    ALERT_NEW_PUBLIC_IP,
    ALERT_SHELL_SPAWNS_DOWNLOADER,
    ALERT_TEMP_PATH_EXECUTION,
)


def test_behavior_key_skips_shell_downloader_chain():
    """Chain-style alerts are not baselined (no parent>child keys saved)."""
    alert = SecurityAlert(
        timestamp="2026-07-25T12:00:00Z",
        device_id="dev_x",
        alert_type=ALERT_SHELL_SPAWNS_DOWNLOADER,
        severity="high",
        message="Shell spawned network downloader (curl)",
        event_id="evt_1",
        event_type="process_start",
        detail='{"parent_comm":"zsh","child_comm":"curl"}',
    )
    assert behavior_from_alert(alert) is None


def test_behavior_key_from_temp_path():
    alert = SecurityAlert(
        timestamp="2026-07-25T12:00:00Z",
        device_id="dev_x",
        alert_type=ALERT_TEMP_PATH_EXECUTION,
        severity="high",
        message="Process started from suspicious path",
        event_id="evt_1",
        event_type="process_start",
        detail='{"executable":"/tmp/evil","comm":"evil"}',
    )
    kind, key, meta = behavior_from_alert(alert)
    assert kind == "temp_path"
    assert key == "evil"
    assert meta["executable"] == "evil"


def test_behavior_key_skips_network_alerts():
    alert = SecurityAlert(
        timestamp="2026-07-25T12:00:00Z",
        device_id="dev_x",
        alert_type=ALERT_NEW_PUBLIC_IP,
        severity="high",
        message="Public IP changed",
        event_id="evt_2",
        event_type="network_summary",
        detail='{"from":"1.1.1.1","to":"8.8.8.8"}',
    )
    assert behavior_from_alert(alert) is None
