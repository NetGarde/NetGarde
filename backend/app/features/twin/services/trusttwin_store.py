"""Read TrustEdge Agent live device state from Redis (written by trustedge-agent-api).

Key contract (shared with TrustEdge Agent Go store):
  twin:devices                  SET of device_id
  twin:device:{id}:latest       JSON DeviceLatest
  twin:device:{id}:events       ZSET of event envelopes (score = unix ms)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.shared.redis_client import get_redis, redis_available

DEVICES_KEY = "twin:devices"
LATEST_KEY_FMT = "twin:device:{device_id}:latest"
EVENTS_KEY_FMT = "twin:device:{device_id}:events"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class TwinDeviceLatest:
    device_id: str
    last_seen_at: Optional[datetime] = None
    client_details: dict[str, Any] = field(default_factory=dict)
    network_summary: dict[str, Any] = field(default_factory=dict)
    action_summary: dict[str, Any] = field(default_factory=dict)


def twin_device_node_id(device_id: str) -> str:
    """Graph node id for a TrustTwin agent (avoids collision with VPN device:{pk})."""
    return f"device:twin:{device_id}"


def app_slug_from_focus(entry: dict[str, Any]) -> str:
    bundle = str(entry.get("bundle_id") or "").strip().lower()
    if bundle:
        return _SLUG_RE.sub("-", bundle).strip("-") or "unknown"
    name = str(entry.get("app_name") or "unknown").strip().lower()
    return _SLUG_RE.sub("-", name).strip("-") or "unknown"


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_latest(raw: str, device_id: str) -> Optional[TwinDeviceLatest]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return TwinDeviceLatest(
        device_id=str(data.get("device_id") or device_id),
        last_seen_at=_parse_ts(data.get("last_seen_at")),
        client_details=_as_dict(data.get("client_details")),
        network_summary=_as_dict(data.get("network_summary")),
        action_summary=_as_dict(data.get("action_summary")),
    )


def list_latest() -> list[TwinDeviceLatest]:
    """Return live TrustTwin device documents from Redis."""
    if not redis_available():
        return []
    r = get_redis()
    try:
        device_ids = sorted(r.smembers(DEVICES_KEY) or [])
    except Exception:
        return []
    if not device_ids:
        return []

    keys = [LATEST_KEY_FMT.format(device_id=did) for did in device_ids]
    try:
        values = r.mget(keys)
    except Exception:
        return []

    out: list[TwinDeviceLatest] = []
    for device_id, raw in zip(device_ids, values):
        if not raw:
            continue
        doc = _parse_latest(raw, device_id)
        if doc is not None:
            out.append(doc)
    return out


def get_latest(device_id: str) -> Optional[TwinDeviceLatest]:
    if not device_id or not redis_available():
        return None
    try:
        raw = get_redis().get(LATEST_KEY_FMT.format(device_id=device_id))
    except Exception:
        return None
    if not raw:
        return None
    return _parse_latest(raw, device_id)


def list_recent_events(device_id: str, limit: int = 50) -> list[dict[str, Any]]:
    if not device_id or not redis_available():
        return []
    limit = max(1, min(int(limit), 200))
    try:
        rows = get_redis().zrevrange(
            EVENTS_KEY_FMT.format(device_id=device_id),
            0,
            limit - 1,
        )
    except Exception:
        return []
    events: list[dict[str, Any]] = []
    for raw in rows:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events
