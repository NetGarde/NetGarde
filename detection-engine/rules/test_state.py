"""Unit tests for the in-memory process StateStore."""

from __future__ import annotations

from rules.state import ProcessState, StateStore


def _event(
    device_id: str,
    event_type: str,
    ts: str,
    *,
    pid: int = 0,
    ppid: int = 0,
    **payload,
):
    body = dict(payload)
    if pid:
        body["pid"] = pid
    if ppid:
        body["ppid"] = ppid
    return {
        "event_id": f"evt_{event_type}_{pid}_{ts}",
        "device_id": device_id,
        "type": event_type,
        "ts": ts,
        "payload": body,
    }


def test_create_process_builds_process_state():
    store = StateStore()
    proc = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=100,
            ppid=1,
            comm="bash",
            executable="/bin/bash",
            cmdline="bash -lc whoami",
        )
    )
    assert proc is not None
    assert isinstance(proc, ProcessState)
    assert proc.pid == 100
    assert proc.ppid == 1
    assert proc.process_name == "bash"
    assert proc.command_line == "bash -lc whoami"
    assert proc.start_time == "2026-07-11T12:00:00Z"
    assert proc.current_risk_score == 0
    assert proc.matched_rules == []
    assert store.get_process_by_pid("dev1", 100) is proc


def test_create_process_links_parent_child():
    store = StateStore()
    parent = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=100,
            ppid=1,
            comm="bash",
            executable="/bin/bash",
        )
    )
    child = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:01Z",
            pid=200,
            ppid=100,
            comm="curl",
            executable="/usr/bin/curl",
        )
    )
    assert parent is not None and child is not None
    assert child.parent_process_id == parent.process_id
    assert child.process_id in parent.children_processes


def test_create_process_mutates_same_object_on_revisit():
    store = StateStore()
    first = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=42,
            ppid=1,
            process_id="guid-42",
            comm="python",
        )
    )
    second = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=42,
            ppid=1,
            process_id="guid-42",
            comm="python",
            cmdline="python evil.py",
        )
    )
    assert first is second
    assert second is not None
    assert second.command_line == "python evil.py"


def test_activity_events_update_existing_process():
    store = StateStore()
    proc = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=50,
            ppid=1,
            comm="malware",
            executable="/tmp/malware",
        )
    )
    assert proc is not None

    net = store.process_network_connection(
        _event(
            "dev1",
            "network_connection",
            "2026-07-11T12:00:05Z",
            pid=50,
            remote_ip="1.2.3.4",
            remote_port=443,
            protocol="tcp",
            direction="outbound",
        )
    )
    file_ev = store.process_file_write(
        _event(
            "dev1",
            "file_write",
            "2026-07-11T12:00:06Z",
            pid=50,
            path="/tmp/drop.bin",
        )
    )
    reg = store.process_registry_change(
        _event(
            "dev1",
            "registry_persistence",
            "2026-07-11T12:00:07Z",
            pid=50,
            registry_key="HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            value_name="Updater",
            operation="set",
        )
    )

    assert net is proc
    assert file_ev is proc
    assert reg is proc
    assert len(proc.network_connections) == 1
    assert proc.network_connections[0].remote_addr == "1.2.3.4"
    assert proc.network_connections[0].remote_port == 443
    assert proc.created_files[0].path == "/tmp/drop.bin"
    assert "CurrentVersion\\Run" in proc.modified_registry_keys[0].key


def test_terminate_process_removes_from_active():
    store = StateStore()
    store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=9,
            ppid=1,
            comm="sleep",
            executable="/bin/sleep",
        )
    )
    ended = store.terminate_process(
        _event(
            "dev1",
            "process_exit",
            "2026-07-11T12:01:00Z",
            pid=9,
        )
    )
    assert ended is not None
    assert ended.terminated is True
    assert ended.end_time == "2026-07-11T12:01:00Z"
    assert store.get_process_by_pid("dev1", 9) is None
    # Retained for correlation after exit
    assert store.get_process("dev1", ended.process_id) is ended


def test_record_event_wires_process_lifecycle():
    store = StateStore()
    store.record_event(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=7,
            ppid=1,
            comm="zsh",
            executable="/bin/zsh",
        )
    )
    assert store.get_process_by_pid("dev1", 7) is not None
    store.record_event(
        _event(
            "dev1",
            "process_exit",
            "2026-07-11T12:00:30Z",
            pid=7,
        )
    )
    assert store.get_process_by_pid("dev1", 7) is None


def test_note_rule_match_updates_risk():
    store = StateStore()
    proc = store.create_process(
        _event(
            "dev1",
            "process_start",
            "2026-07-11T12:00:00Z",
            pid=1,
            ppid=0,
            comm="curl",
            executable="/usr/bin/curl",
        )
    )
    assert proc is not None
    proc.note_rule_match("shell_spawns_downloader", score_delta=40)
    proc.note_rule_match("shell_spawns_downloader", score_delta=10)
    assert proc.matched_rules == ["shell_spawns_downloader"]
    assert proc.current_risk_score == 50


def test_devices_are_isolated():
    store = StateStore()
    store.create_process(
        _event("a", "process_start", "2026-07-11T12:00:00Z", pid=1, ppid=0, comm="a")
    )
    store.create_process(
        _event("b", "process_start", "2026-07-11T12:00:00Z", pid=1, ppid=0, comm="b")
    )
    assert store.get_process_by_pid("a", 1).process_name == "a"
    assert store.get_process_by_pid("b", 1).process_name == "b"
