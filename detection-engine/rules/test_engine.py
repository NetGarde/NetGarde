from rules.chain_rules import CHAIN_RULES, evaluate_chain
from rules.engine import evaluate_event
from rules.state import StateStore


def _network_event(
    device_id: str,
    network_type: str,
    public_ip: str,
    ts: str = "2026-07-11T12:00:00Z",
    **extra_payload,
):
    payload = {"network_type": network_type, "public_ip": public_ip, **extra_payload}
    return {
        "event_id": f"evt_{ts}",
        "device_id": device_id,
        "type": "network_summary",
        "ts": ts,
        "payload": payload,
    }


def _action_event(device_id: str, presence: str, ts: str = "2026-07-11T12:00:00Z"):
    return {
        "device_id": device_id,
        "type": "action_summary",
        "ts": ts,
        "payload": {"presence": presence},
    }


def _client_event(device_id: str, ts: str = "2026-07-11T12:00:00Z"):
    return {
        "device_id": device_id,
        "type": "client_details",
        "ts": ts,
        "payload": {"hostname": "test-host"},
    }


def _security_event(device_id: str, event_type: str, ts: str = "2026-07-11T12:00:00Z", **payload):
    return {
        "event_id": f"evt_{event_type}_{ts}",
        "device_id": device_id,
        "type": event_type,
        "ts": ts,
        "payload": payload,
    }


def test_network_type_change_alert():
    store = StateStore()
    device = "dev_test"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(_network_event(device, "ethernet", "1.1.1.1", "2026-07-11T12:01:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "network_type_change" in types


def test_new_public_ip_alert():
    store = StateStore()
    device = "dev_test"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(_network_event(device, "wifi", "2.2.2.2", "2026-07-11T12:01:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "new_public_ip" in types


def test_network_change_while_active():
    store = StateStore()
    device = "dev_test"
    evaluate_event(_action_event(device, "active"), store)
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(_network_event(device, "ethernet", "1.1.1.1", "2026-07-11T12:02:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "network_change_while_active" in types


def test_first_network_event_no_alerts():
    store = StateStore()
    alerts = evaluate_event(_network_event("dev_new", "wifi", "1.1.1.1"), store)
    assert alerts == []


def test_chain_rules_registry_has_many_rules():
    assert len(CHAIN_RULES) >= 15
    names = {name for name, _ in CHAIN_RULES}
    assert "rapid_public_ip_changes" in names
    assert "network_type_flapping" in names
    assert "stale_client_details" in names


def test_rapid_public_ip_changes():
    store = StateStore()
    device = "dev_ip_churn"
    base = "2026-07-11T12:00:00Z"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1", base), store)
    evaluate_event(_network_event(device, "wifi", "2.2.2.2", "2026-07-11T12:02:00Z"), store)
    alerts = evaluate_event(_network_event(device, "wifi", "3.3.3.3", "2026-07-11T12:04:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "rapid_public_ip_changes" in types


def test_simultaneous_ip_and_type_change():
    store = StateStore()
    device = "dev_both"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(
        _network_event(device, "ethernet", "2.2.2.2", "2026-07-11T12:01:00Z"), store
    )
    types = {a.alert_type for a in alerts}
    assert "simultaneous_ip_and_type_change" in types


def test_stale_client_details():
    store = StateStore()
    device = "dev_stale"
    evaluate_event(_client_event(device, "2026-07-11T11:00:00Z"), store)
    evaluate_event(_network_event(device, "wifi", "1.1.1.1", "2026-07-11T12:00:00Z"), store)
    alerts = evaluate_event(_network_event(device, "wifi", "1.1.1.1", "2026-07-11T12:05:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "stale_client_details" in types


def test_established_count_spike():
    store = StateStore()
    device = "dev_sock"
    evaluate_event(
        _network_event(device, "wifi", "1.1.1.1", established_count=10),
        store,
    )
    alerts = evaluate_event(
        _network_event(
            device,
            "wifi",
            "1.1.1.1",
            "2026-07-11T12:01:00Z",
            established_count=80,
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "established_count_spike" in types


def _process_event(
    device_id: str,
    pid: int,
    ppid: int,
    comm: str,
    executable: str,
    ts: str,
    cmdline=None,
):
    payload = {
        "pid": pid,
        "ppid": ppid,
        "user": "tester",
        "comm": comm,
        "executable": executable,
    }
    if cmdline is not None:
        payload["cmdline"] = cmdline
    return {
        "event_id": f"evt_proc_{pid}_{ts}",
        "device_id": device_id,
        "type": "process_start",
        "ts": ts,
        "payload": payload,
    }


def test_shell_spawns_downloader_alert():
    store = StateStore()
    device = "dev_edr"
    evaluate_event(
        _process_event(
            device,
            100,
            1,
            "bash",
            "/bin/bash",
            "2026-07-11T12:00:00Z",
            cmdline="bash -c 'curl --limit-rate 1B https://example.com'",
        ),
        store,
    )
    alerts = evaluate_event(
        _process_event(
            device,
            200,
            100,
            "curl",
            "/usr/bin/curl",
            "2026-07-11T12:00:05Z",
            cmdline="curl --limit-rate 1B https://example.com",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "shell_spawns_downloader" in types
    alert = next(a for a in alerts if a.alert_type == "shell_spawns_downloader")
    assert alert.detail is not None
    assert "bash -c" in alert.detail
    assert "curl --limit-rate" in alert.detail


def test_temp_path_execution_alert():
    store = StateStore()
    device = "dev_tmp"
    evaluate_event(_process_event(device, 1, 0, "launchd", "launchd", "2026-07-11T12:00:00Z"), store)
    alerts = evaluate_event(
        _process_event(
            device,
            2,
            1,
            "malware",
            "/tmp/.hidden/malware",
            "2026-07-11T12:00:01Z",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "temp_path_execution" in types


def test_registry_persistence_alert():
    store = StateStore()
    alerts = evaluate_event(
        _security_event(
            "dev_security",
            "registry_persistence",
            value_name="com.example.persist",
            value="/tmp/persist.sh",
            path="/Users/test/Library/LaunchAgents/com.example.persist.plist",
        ),
        store,
    )
    alert = next(a for a in alerts if a.alert_type == "registry_persistence")
    assert alert.severity == "high"
    assert "com.example.persist" in alert.message
    assert alert.detail is not None
    assert "LaunchAgents" in alert.detail


def test_service_install_alert():
    store = StateStore()
    alerts = evaluate_event(
        _security_event(
            "dev_security",
            "service_install",
            name="com.example.daemon",
            path="/Library/LaunchDaemons/com.example.daemon.plist",
            service_type="LaunchDaemon",
        ),
        store,
    )
    alert = next(a for a in alerts if a.alert_type == "service_install")
    assert alert.severity == "medium"
    assert "com.example.daemon" in alert.message


def test_driver_load_alert():
    store = StateStore()
    alerts = evaluate_event(
        _security_event(
            "dev_security",
            "driver_load",
            name="com.example.driver",
            service_type="kext",
            version="1.0",
        ),
        store,
    )
    alert = next(a for a in alerts if a.alert_type == "driver_load")
    assert alert.severity == "high"
    assert "com.example.driver" in alert.message


def test_process_burst_includes_process_samples():
    store = StateStore()
    device = "dev_burst"
    alerts = []
    for i in range(25):
        comm = "bash" if i % 5 == 0 else "helper"
        alerts = evaluate_event(
            _process_event(
                device,
                1000 + i,
                1,
                comm,
                f"/usr/bin/{comm}",
                f"2026-07-11T12:00:{i:02d}Z",
                cmdline=f"{comm} --job {i}",
            ),
            store,
        )
    types = {a.alert_type for a in alerts}
    assert "process_burst" in types
    alert = next(a for a in alerts if a.alert_type == "process_burst")
    assert alert.detail is not None
    detail = __import__("json").loads(alert.detail)
    assert detail["count"] == 25
    assert detail["window_minutes"] == 2
    assert len(detail["processes"]) == 15
    assert detail["processes"][-1]["pid"] == 1024
    assert "cmdline" in detail["processes"][-1]
    top = {row["comm"]: row["count"] for row in detail["top_comms"]}
    assert top["helper"] == 20
    assert top["bash"] == 5


def test_process_event_does_not_rerun_network_rules():
    store = StateStore()
    device = "dev_route"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    evaluate_event(_network_event(device, "ethernet", "1.1.1.1", "2026-07-11T12:01:00Z"), store)
    alerts = evaluate_event(
        _process_event(device, 10, 1, "bash", "/bin/bash", "2026-07-11T12:01:05Z"),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "network_type_change" not in types


def test_event_burst_fingerprint_shares_cooldown_bucket():
    from rules.alerts import SecurityAlert, alert_fingerprint
    from rules.constants import ALERT_EVENT_BURST, ALERT_SHELL_SPAWNS_DOWNLOADER

    a = SecurityAlert(
        timestamp="2026-07-16T19:39:36Z",
        device_id="dev_x",
        alert_type=ALERT_EVENT_BURST,
        severity="low",
        message="High event volume (36 events in 5 minutes)",
        event_id="evt_a",
    )
    b = SecurityAlert(
        timestamp="2026-07-16T19:39:56Z",
        device_id="dev_x",
        alert_type=ALERT_EVENT_BURST,
        severity="low",
        message="High event volume (47 events in 5 minutes)",
        event_id="evt_b",
    )
    assert a.fingerprint() == b.fingerprint()

    # Point-in-time alerts still key on event_id.
    assert alert_fingerprint(
        device_id="dev_x",
        alert_type=ALERT_SHELL_SPAWNS_DOWNLOADER,
        timestamp="2026-07-16T19:39:36Z",
        event_id="evt_a",
    ) != alert_fingerprint(
        device_id="dev_x",
        alert_type=ALERT_SHELL_SPAWNS_DOWNLOADER,
        timestamp="2026-07-16T19:39:36Z",
        event_id="evt_b",
    )

