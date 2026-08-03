"""Process-local handle to the live BaselineStore for HTTP dumps."""

from __future__ import annotations

from typing import Any, Optional

from pipeline.baseline_store import BaselineStore

_store: Optional[BaselineStore] = None


def bind(store: BaselineStore) -> None:
    global _store
    _store = store


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
            "suppress_age_hours": 72,
            "profile_min_keys": 30,
        }
    return store.snapshot(device_id, limit=limit)
