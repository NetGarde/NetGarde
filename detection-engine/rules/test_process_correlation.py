"""Tests for process-state correlation and rule-match attribution."""

from __future__ import annotations

import json

from rules.engine import evaluate_event
from rules.state import StateStore


def _process_start(device_id, pid, ppid, comm, executable, ts, **extra):
    payload = {
        "pid": pid,
        "ppid": ppid,
        "comm": comm,
        "executable": executable,
        **extra,
    }
    return {
        "event_id": f"evt_start_{pid}_{ts}",
        "device_id": device_id,
        "type": "process_start",
        "ts": ts,
        "payload": payload,
    }


def _activity(device_id, event_type, ts, pid, **payload):
    return {
        "event_id": f"evt_{event_type}_{pid}_{ts}",
        "device_id": device_id,
        "type": event_type,
        "ts": ts,
        "payload": {"pid": pid, **payload},
    }


def test_rule_match_updates_process_risk_score():
    store = StateStore()
    device = "dev_risk"
    evaluate_event(
        _process_start(
            device, 100, 1, "bash", "/bin/bash", "2026-07-11T12:00:00Z"
        ),
        store,
    )
    alerts = evaluate_event(
        _process_start(
            device,
            200,
            100,
            "curl",
            "/usr/bin/curl",
            "2026-07-11T12:00:05Z",
            cmdline="curl https://evil.example",
        ),
        store,
    )
    assert any(a.alert_type == "shell_spawns_downloader" for a in alerts)
    proc = store.get_process_by_pid(device, 200)
    assert proc is not None
    assert "shell_spawns_downloader" in proc.matched_rules
    assert proc.current_risk_score >= 75


def test_dropper_behavior_correlates_file_and_network():
    store = StateStore()
    device = "dev_dropper"
    evaluate_event(
        _process_start(
            device,
            50,
            1,
            "malware",
            "/tmp/malware",
            "2026-07-11T12:00:00Z",
        ),
        store,
    )
    evaluate_event(
        _activity(
            device,
            "file_write",
            "2026-07-11T12:00:01Z",
            50,
            path="/tmp/payload.bin",
        ),
        store,
    )
    alerts = evaluate_event(
        _activity(
            device,
            "network_connection",
            "2026-07-11T12:00:02Z",
            50,
            remote_ip="203.0.113.9",
            remote_port=443,
            protocol="tcp",
            direction="outbound",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "dropper_behavior" in types
    alert = next(a for a in alerts if a.alert_type == "dropper_behavior")
    detail = json.loads(alert.detail or "{}")
    assert detail["created_file_count"] == 1
    assert detail["network_connection_count"] == 1
    assert any(
        (isinstance(item, dict) and item.get("path") == "/tmp/payload.bin")
        or item == "/tmp/payload.bin"
        for item in detail["created_files"]
    )
    # Graph payload: process sample + full network connection records
    assert detail["processes"]
    trigger = next(row for row in detail["processes"] if row.get("role") == "trigger")
    assert trigger["pid"] == 50
    assert detail["network_connections"]
    assert detail["network_connections"][0]["remote_addr"] == "203.0.113.9"
    assert detail["network_connections"][0]["remote_port"] == 443

    proc = store.get_process_by_pid(device, 50)
    assert proc is not None
    assert "dropper_behavior" in proc.matched_rules

    # Second activity must not re-emit the same correlation alert.
    alerts2 = evaluate_event(
        _activity(
            device,
            "network_connection",
            "2026-07-11T12:00:03Z",
            50,
            remote_ip="203.0.113.10",
            remote_port=80,
        ),
        store,
    )
    assert "dropper_behavior" not in {a.alert_type for a in alerts2}


def test_persistence_with_network_correlation():
    store = StateStore()
    device = "dev_persist"
    evaluate_event(
        _process_start(
            device, 77, 1, "updater", "/tmp/updater", "2026-07-11T12:00:00Z"
        ),
        store,
    )
    reg_alerts = evaluate_event(
        _activity(
            device,
            "registry_persistence",
            "2026-07-11T12:00:01Z",
            77,
            registry_key="HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            value_name="Updater",
        ),
        store,
    )
    assert "registry_persistence" in {a.alert_type for a in reg_alerts}
    alerts = evaluate_event(
        _activity(
            device,
            "network_connection",
            "2026-07-11T12:00:02Z",
            77,
            remote_ip="198.51.100.2",
            remote_port=443,
        ),
        store,
    )
    assert "persistence_with_network" in {a.alert_type for a in alerts}


def test_process_network_activity_after_prior_rule_match():
    store = StateStore()
    device = "dev_net_activity"
    evaluate_event(
        _process_start(
            device, 100, 1, "bash", "/bin/bash", "2026-07-11T12:00:00Z"
        ),
        store,
    )
    evaluate_event(
        _process_start(
            device,
            200,
            100,
            "curl",
            "/usr/bin/curl",
            "2026-07-11T12:00:05Z",
            cmdline="curl https://example.com",
        ),
        store,
    )
    proc = store.get_process_by_pid(device, 200)
    assert proc is not None
    assert "shell_spawns_downloader" in proc.matched_rules

    alerts = evaluate_event(
        _activity(
            device,
            "network_connection",
            "2026-07-11T12:00:10Z",
            200,
            remote_ip="203.0.113.9",
            remote_port=443,
            protocol="tcp",
            direction="outbound",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "process_network_activity" in types
    alert = next(a for a in alerts if a.alert_type == "process_network_activity")
    detail = json.loads(alert.detail or "{}")
    assert detail["network_connections"]
    assert detail["network_connections"][0]["remote_addr"] == "203.0.113.9"
    assert detail["processes"]


def test_elevated_process_risk_after_accumulated_hits():
    store = StateStore()
    device = "dev_elevated"
    # Parent shell + AI tool → shell_spawns_ai_tool (high=75) + ai_tool_execution (medium=50)
    evaluate_event(
        _process_start(
            device, 100, 1, "zsh", "/bin/zsh", "2026-07-11T12:00:00Z"
        ),
        store,
    )
    alerts = evaluate_event(
        _process_start(
            device,
            200,
            100,
            "ollama",
            "/usr/local/bin/ollama",
            "2026-07-11T12:00:05Z",
            cmdline="ollama run llama3",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "shell_spawns_ai_tool" in types
    assert "ai_tool_execution" in types
    assert "elevated_process_risk" in types
    proc = store.get_process_by_pid(device, 200)
    assert proc is not None
    assert proc.current_risk_score >= 100
