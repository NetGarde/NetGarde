"""In-memory per-device behavior baseline (no Postgres)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _ts_iso(epoch: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


KIND_PROCESS_COMM = "process_comm"


@dataclass
class BaselineEntry:
    count: int
    first_seen: float
    last_seen: float


@dataclass(frozen=True)
class ObserveDecision:
    count: int
    established: bool
    profile_warm: bool
    action: str  # suppress | emit

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "established": self.established,
            "profile_warm": self.profile_warm,
            "action": self.action,
        }


class BaselineStore:
    """Process-lifetime baseline keyed by device → (kind, key)."""

    def __init__(
        self,
        *,
        suppress_count: int | None = None,
        suppress_age_hours: int | None = None,
        profile_min_keys: int | None = None,
    ) -> None:
        self.suppress_count = suppress_count if suppress_count is not None else _env_int(
            "BEHAVIOR_SUPPRESS_COUNT", 20
        )
        self.suppress_age_hours = (
            suppress_age_hours
            if suppress_age_hours is not None
            else _env_int("BEHAVIOR_SUPPRESS_AGE_HOURS", 72)
        )
        self.profile_min_keys = (
            profile_min_keys
            if profile_min_keys is not None
            else _env_int("BEHAVIOR_PROFILE_MIN_KEYS", 30)
        )
        self._devices: dict[str, dict[tuple[str, str], BaselineEntry]] = {}

    def clear(self) -> None:
        self._devices.clear()

    def snapshot(
        self,
        device_id: str,
        *,
        limit: int = 100,
        now: float | None = None,
    ) -> dict[str, Any]:
        """JSON-friendly baseline dump for one device."""
        device = (device_id or "").strip()
        ts = time.time() if now is None else now
        by_key = self._devices.get(device) or {}
        items: list[dict[str, Any]] = []
        for (kind, key), entry in sorted(
            by_key.items(),
            key=lambda kv: (-kv[1].count, kv[0][0], kv[0][1]),
        ):
            items.append(
                {
                    "behavior_kind": kind,
                    "behavior_key": key,
                    "count": entry.count,
                    "first_seen_at": _ts_iso(entry.first_seen),
                    "last_seen_at": _ts_iso(entry.last_seen),
                    "established": self._is_established(entry, ts),
                }
            )
            if len(items) >= max(1, limit):
                break
        return {
            "device_id": device,
            "profile_warm": self._profile_warm(device, ts) if device else False,
            "total": len(by_key),
            "items": items,
            "suppress_count": self.suppress_count,
            "suppress_age_hours": self.suppress_age_hours,
            "profile_min_keys": self.profile_min_keys,
        }

    def observe(
        self,
        device_id: str,
        behavior_kind: str,
        behavior_key: str,
        *,
        now: float | None = None,
    ) -> ObserveDecision:
        device = (device_id or "").strip()
        kind = (behavior_kind or "").strip()
        key = (behavior_key or "").strip()
        ts = time.time() if now is None else now

        by_key = self._devices.setdefault(device, {})
        entry = by_key.get((kind, key))
        if entry is None:
            entry = BaselineEntry(count=1, first_seen=ts, last_seen=ts)
            by_key[(kind, key)] = entry
        else:
            entry.count += 1
            entry.last_seen = ts

        established = self._is_established(entry, ts)
        return ObserveDecision(
            count=entry.count,
            established=established,
            profile_warm=self._profile_warm(device, ts),
            action="suppress" if established else "emit",
        )

    def _is_established(self, entry: BaselineEntry, now: float) -> bool:
        if entry.count < self.suppress_count:
            return False
        age_hours = (now - entry.first_seen) / 3600.0
        return age_hours >= float(self.suppress_age_hours)

    def _profile_warm(self, device_id: str, now: float) -> bool:
        by_key = self._devices.get(device_id) or {}
        comm_entries = [e for (kind, _key), e in by_key.items() if kind == KIND_PROCESS_COMM]
        if len(comm_entries) >= self.profile_min_keys:
            return True
        if not comm_entries:
            return False
        oldest = min(e.first_seen for e in comm_entries)
        age_hours = (now - oldest) / 3600.0
        return age_hours >= float(self.suppress_age_hours)
