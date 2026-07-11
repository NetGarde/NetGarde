from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

TYPE_CLIENT_DETAILS = "client_details"
TYPE_NETWORK_SUMMARY = "network_summary"
TYPE_ACTION_SUMMARY = "action_summary"


def parse_ts(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def ts_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def payload_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def payload_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class ChainEvent:
    event_id: str | None
    event_type: str
    ts: datetime
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_kafka(cls, event: dict[str, Any]) -> ChainEvent | None:
        device_id = payload_str(event.get("device_id"))
        if not device_id:
            return None
        event_type = payload_str(event.get("type"))
        if not event_type:
            return None
        raw_payload = event.get("payload") or {}
        if not isinstance(raw_payload, dict):
            raw_payload = {}
        return cls(
            event_id=payload_str(event.get("event_id")) or None,
            event_type=event_type,
            ts=parse_ts(event.get("ts")),
            payload=raw_payload,
        )


@dataclass
class DeviceChain:
    device_id: str
    events: list[ChainEvent] = field(default_factory=list)

    def append(self, item: ChainEvent, *, max_events: int, window: timedelta) -> None:
        self.events.append(item)
        cutoff = item.ts - window
        self.events = [ev for ev in self.events if ev.ts >= cutoff]
        if len(self.events) > max_events:
            self.events = self.events[-max_events:]

    def in_window(self, window: timedelta, *, now: datetime | None = None) -> list[ChainEvent]:
        ref = now or (self.events[-1].ts if self.events else datetime.now(timezone.utc))
        cutoff = ref - window
        return [ev for ev in self.events if ev.ts >= cutoff]

    def of_type(self, event_type: str, window: timedelta | None = None) -> list[ChainEvent]:
        items = self.in_window(window) if window else list(self.events)
        return [ev for ev in items if ev.event_type == event_type]

    def latest(self, event_type: str | None = None) -> ChainEvent | None:
        items = self.events
        if event_type:
            items = [ev for ev in items if ev.event_type == event_type]
        return items[-1] if items else None

    def latest_presence(self) -> str:
        for ev in reversed(self.events):
            if ev.event_type == TYPE_ACTION_SUMMARY:
                presence = payload_str(ev.payload.get("presence"))
                if presence:
                    return presence
        return ""

    def detail_json(data: dict[str, Any]) -> str:
        return json.dumps(data, separators=(",", ":"))
