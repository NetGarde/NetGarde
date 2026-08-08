"""ThreatIntelEngine stub always returns no hits."""

from __future__ import annotations

from pipeline import threat_intel


def test_threat_intel_empty():
    assert threat_intel.evaluate({"type": "process_start", "device_id": "d1"}) == []
    assert threat_intel.evaluate({}, None) == []
