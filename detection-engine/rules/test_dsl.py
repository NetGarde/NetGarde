"""Unit tests for the YAML rules DSL."""

from __future__ import annotations

from pathlib import Path

import pytest

from rules.dsl.compiler import compile_rule_file
from rules.dsl.loader import load_rule_file, parse_rule_document
from rules.dsl.registry import clear_dsl_cache, load_dsl_rules
from rules.dsl.schema import DslError, parse_duration
from rules.engine import evaluate_event
from rules.state import StateStore


def _process_event(device_id, pid, ppid, comm, executable, ts, cmdline=None):
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


def test_parse_duration():
    assert parse_duration("5m").total_seconds() == 300
    assert parse_duration("30s").total_seconds() == 30
    with pytest.raises(DslError):
        parse_duration("5")
    with pytest.raises(DslError):
        parse_duration("5x")


def test_load_bundled_process_rules():
    clear_dsl_cache()
    by_type = load_dsl_rules()
    process = by_type["process_start"]
    ids = [alert_type for alert_type, *_rest in process]
    assert ids == [
        "temp_path_execution",
        "shell_spawns_downloader",
        "script_spawns_shell",
        "binary_path_mismatch",
    ]


def test_load_bundled_network_and_security_rules():
    clear_dsl_cache()
    by_type = load_dsl_rules()
    network_ids = {alert_type for alert_type, *_rest in by_type["network_summary"]}
    assert "new_public_ip" in network_ids
    assert "rapid_public_ip_changes" in network_ids
    assert "stale_client_details" in network_ids
    assert "driver_load" in {a for a, *_r in by_type["driver_load"]}
    assert "missing_network_telemetry" in {a for a, *_r in by_type["action_summary"]}
    assert "*" not in by_type or not by_type["*"]

def test_loader_rejects_unknown_operator(tmp_path: Path):
    path = tmp_path / "bad.yml"
    path.write_text(
        """
version: 1
sets:
  shells: [bash]
rules:
  - id: bad_rule
    kind: process_match
    trigger: process_start
    severity: high
    message: "x"
    when:
      child:
        totally_fake: { field: comm, set: shells }
""",
        encoding="utf-8",
    )
    with pytest.raises(DslError, match="unknown operator"):
        load_rule_file(path)


def test_loader_rejects_missing_set():
    with pytest.raises(DslError, match="unknown set"):
        parse_rule_document(
            {
                "version": 1,
                "sets": {},
                "rules": [
                    {
                        "id": "x",
                        "kind": "process_match",
                        "trigger": "process_start",
                        "severity": "high",
                        "message": "m",
                        "when": {
                            "child": {
                                "basename_in": {"field": "comm", "set": "missing"},
                            }
                        },
                    }
                ],
            }
        )


def test_loader_rejects_bad_trigger_missing():
    with pytest.raises(DslError, match="trigger is required"):
        parse_rule_document(
            {
                "version": 1,
                "rules": [
                    {
                        "id": "x",
                        "kind": "process_match",
                        "severity": "high",
                        "message": "m",
                        "when": {
                            "child": {
                                "basename_in": {"field": "comm", "set": "shells"},
                            }
                        },
                    }
                ],
                "sets": {"shells": ["bash"]},
            }
        )


def test_script_spawns_shell_via_dsl():
    store = StateStore()
    device = "dev_script"
    evaluate_event(
        _process_event(device, 50, 1, "python3", "/usr/bin/python3", "2026-07-11T12:00:00Z"),
        store,
    )
    alerts = evaluate_event(
        _process_event(device, 51, 50, "bash", "/bin/bash", "2026-07-11T12:00:01Z"),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "script_spawns_shell" in types
    alert = next(a for a in alerts if a.alert_type == "script_spawns_shell")
    assert "python3 spawned shell (bash)" in alert.message


def test_binary_path_mismatch_via_dsl():
    store = StateStore()
    alerts = evaluate_event(
        _process_event(
            "dev_mismatch",
            9,
            1,
            "curl",
            "/tmp/curl",
            "2026-07-11T12:00:00Z",
            cmdline="/tmp/curl http://evil",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "binary_path_mismatch" in types


def test_binary_path_mismatch_skips_system_path():
    store = StateStore()
    alerts = evaluate_event(
        _process_event(
            "dev_ok",
            9,
            1,
            "curl",
            "/usr/bin/curl",
            "2026-07-11T12:00:00Z",
        ),
        store,
    )
    types = {a.alert_type for a in alerts}
    assert "binary_path_mismatch" not in types


def test_compile_custom_rule_file(tmp_path: Path):
    path = tmp_path / "custom.yml"
    path.write_text(
        """
version: 1
sets:
  markers: ["/evil/"]
rules:
  - id: evil_path
    kind: process_match
    trigger: process_start
    severity: high
    message: "Evil path {child.executable}"
    when:
      child:
        contains_any: { field: executable, set: markers }
    detail:
      executable: child.executable
""",
        encoding="utf-8",
    )
    rule_file = load_rule_file(path)
    compiled = compile_rule_file(rule_file)
    assert len(compiled) == 1
    assert compiled[0][0].id == "evil_path"

    store = StateStore()
    chain = store.record_event(
        _process_event("d", 1, 0, "x", "/evil/bin", "2026-07-11T12:00:00Z")
    )
    assert chain is not None
    alerts = compiled[0][1](chain)
    assert len(alerts) == 1
    assert alerts[0].alert_type == "evil_path"
