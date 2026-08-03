from rules.alerts import SecurityAlert
from rules.behavior_key import behavior_from_alert
from rules.constants import ALERT_NEW_PUBLIC_IP, ALERT_SHELL_SPAWNS_DOWNLOADER


def test_behavior_key_from_shell_downloader():
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
    kind, key, meta = behavior_from_alert(alert)
    assert kind == "process_chain"
    assert key == "zsh>curl"
    assert meta["parent_comm"] == "zsh"


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
