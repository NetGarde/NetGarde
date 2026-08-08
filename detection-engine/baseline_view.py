"""Process-local handle to the live BaselineStore for HTTP dumps."""

from __future__ import annotations

from typing import Any, Optional

from pipeline.baseline_store import BaselineStore
from pipeline.behavioral import BehavioralEngine

_store: Optional[BaselineStore] = None
_behavioral: Optional[BehavioralEngine] = None


def bind(store: BaselineStore, behavioral: BehavioralEngine | None = None) -> None:
    global _store, _behavioral
    _store = store
    _behavioral = behavioral


def get_store() -> Optional[BaselineStore]:
    return _store


def snapshot_device(device_id: str, *, limit: int = 100) -> dict[str, Any]:
    store = _store
    if store is None:
        return {
            "device_id": (device_id or "").strip(),
            "profile_warm": False,
            "total": 0,
            "items": [],
            "suppress_count": 20,
            "suppress_age_hours": 0,
            "profile_min_keys": 5,
        }
    return store.snapshot(device_id, limit=limit)


def clear_device(device_id: str) -> dict[str, Any]:
    device = (device_id or "").strip()
    if _behavioral is not None:
        cleared = _behavioral.clear_device(device)
    elif _store is not None:
        cleared = _store.clear_device(device)
    else:
        cleared = 0
    return {"device_id": device, "cleared": cleared}
