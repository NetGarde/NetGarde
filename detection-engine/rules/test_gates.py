"""Tests for fast gates and process comm indexing."""

from __future__ import annotations

from rules.dsl.gates import FastGate, gate_allows, process_comm_index
from rules.engine import evaluate_event
from rules.metrics import METRICS
from rules.state import StateStore


def _process_event(device_id, pid, ppid, comm, executable, ts):
    return {
        "event_id": f"evt_{pid}_{ts}",
        "device_id": device_id,
        "type": "process_start",
        "ts": ts,
        "payload": {
            "pid": pid,
            "ppid": ppid,
            "comm": comm,
            "executable": executable,
        },
    }


def _network_event(device_id, network_type, public_ip, ts="2026-07-11T12:00:00Z"):
    return {
        "event_id": f"evt_{ts}",
        "device_id": device_id,
        "type": "network_summary",
        "ts": ts,
        "payload": {"network_type": network_type, "public_ip": public_ip},
    }


def test_gate_skips_on_comm_mismatch():
    gate = FastGate(child_comm_in=frozenset({"curl", "wget"}))
    store = StateStore()
    chain = store.record_event(
        _process_event("d", 1, 0, "bash", "/bin/bash", "2026-07-11T12:00:00Z")
    )
    assert chain is not None
    assert gate_allows(gate, chain, chain.latest()) is False


def test_gate_allows_matching_comm():
    gate = FastGate(child_comm_in=frozenset({"curl", "wget"}))
    store = StateStore()
    chain = store.record_event(
        _process_event("d", 1, 0, "curl", "/usr/bin/curl", "2026-07-11T12:00:00Z")
    )
    assert chain is not None
    assert gate_allows(gate, chain, chain.latest()) is True


def test_gate_skips_pair_change_without_history():
    gate = FastGate(min_typed_events=2, typed_event="network_summary")
    store = StateStore()
    chain = store.record_event(_network_event("d", "wifi", "1.1.1.1"))
    assert chain is not None
    assert gate_allows(gate, chain, chain.latest()) is False


def test_process_comm_index_routes_downloaders():
    rules = [
        ("shell_spawns_downloader", lambda c: [], FastGate(child_comm_in=frozenset({"curl"}))),
        ("temp_path_execution", lambda c: [], FastGate(child_exe_contains_any=frozenset({"/tmp/"}))),
    ]
    by_comm, always = process_comm_index(rules)
    assert "curl" in by_comm
    assert by_comm["curl"][0][0] == "shell_spawns_downloader"
    assert always[0][0] == "temp_path_execution"


def test_non_downloader_process_still_skips_shell_rule():
    """Indexed evaluation must not emit shell_spawns_downloader for unrelated comms."""
    store = StateStore()
    evaluate_event(
        _process_event("d", 100, 1, "bash", "/bin/bash", "2026-07-11T12:00:00Z"),
        store,
    )
    alerts = evaluate_event(
        _process_event("d", 200, 100, "ls", "/bin/ls", "2026-07-11T12:00:01Z"),
        store,
    )
    assert "shell_spawns_downloader" not in {a.alert_type for a in alerts}


def test_metrics_increment_on_evaluate():
    METRICS.reset()
    store = StateStore()
    evaluate_event(_network_event("metrics_dev", "wifi", "1.1.1.1"), store)
    snap = METRICS.snapshot()
    assert snap.events == 1
    assert snap.rules_selected >= 1
    assert snap.rules_run + snap.rules_gated == snap.rules_selected
