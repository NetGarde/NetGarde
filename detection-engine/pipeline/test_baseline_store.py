"""BaselineStore in-memory observe / warm / established."""

from __future__ import annotations

from pipeline.baseline_store import BaselineStore, KIND_PROCESS_COMM


def test_observe_increments_count():
    store = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=30)
    now = 1_000_000.0
    d1 = store.observe("dev_a", KIND_PROCESS_COMM, "chrome", now=now)
    assert d1.count == 1
    assert d1.established is False
    assert d1.action == "emit"
    assert d1.profile_warm is False

    d2 = store.observe("dev_a", KIND_PROCESS_COMM, "chrome", now=now + 1)
    assert d2.count == 2


def test_established_requires_count_and_age():
    store = BaselineStore(suppress_count=3, suppress_age_hours=1, profile_min_keys=100)
    now = 1_000_000.0
    store.observe("dev_b", "temp_path", "evil", now=now)
    store.observe("dev_b", "temp_path", "evil", now=now + 1)
    mid = store.observe("dev_b", "temp_path", "evil", now=now + 2)
    assert mid.count == 3
    assert mid.established is False  # age < 1h

    aged = store.observe("dev_b", "temp_path", "evil", now=now + 3600 + 10)
    assert aged.count == 4
    assert aged.established is True
    assert aged.action == "suppress"


def test_profile_warm_by_key_count():
    store = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=3)
    now = 1_000_000.0
    store.observe("dev_c", KIND_PROCESS_COMM, "a", now=now)
    store.observe("dev_c", KIND_PROCESS_COMM, "b", now=now)
    cold = store.observe("dev_c", KIND_PROCESS_COMM, "c", now=now)
    # After 3 distinct keys, profile is warm (checked after increment).
    assert cold.profile_warm is True


def test_profile_warm_by_age():
    store = BaselineStore(suppress_count=20, suppress_age_hours=1, profile_min_keys=100)
    now = 1_000_000.0
    store.observe("dev_d", KIND_PROCESS_COMM, "old", now=now)
    later = store.observe("dev_d", KIND_PROCESS_COMM, "new", now=now + 3600 + 5)
    assert later.profile_warm is True


def test_snapshot_device():
    store = BaselineStore(suppress_count=20, suppress_age_hours=72, profile_min_keys=30)
    now = 1_700_000_000.0
    store.observe("dev_s", KIND_PROCESS_COMM, "chrome", now=now)
    store.observe("dev_s", KIND_PROCESS_COMM, "chrome", now=now + 10)
    snap = store.snapshot("dev_s", now=now + 20)
    assert snap["device_id"] == "dev_s"
    assert snap["total"] == 1
    assert snap["items"][0]["behavior_key"] == "chrome"
    assert snap["items"][0]["count"] == 2
    assert snap["items"][0]["first_seen_at"].endswith("Z")
    assert snap["profile_warm"] is False
