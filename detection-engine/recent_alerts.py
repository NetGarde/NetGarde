from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any, Optional

_lock = Lock()
_store: deque[dict[str, Any]] = deque(maxlen=1000)
_next_id = 1


def append(alert: dict[str, Any]) -> dict[str, Any]:
    global _next_id
    with _lock:
        row = dict(alert)
        for key in ("timestamp", "created_at"):
            val = row.get(key)
            if hasattr(val, "isoformat"):
                row[key] = val.isoformat()
        row["id"] = _next_id
        _next_id += 1
        if "created_at" not in row:
            row["created_at"] = row.get("timestamp")
        _store.appendleft(row)
        return row


def list_alerts(
    *,
    page: int = 1,
    page_size: int = 50,
    alert_type: Optional[str] = None,
    device_id: Optional[str] = None,
    severity: Optional[str] = None,
) -> dict[str, Any]:
    with _lock:
        rows = list(_store)

    if alert_type:
        rows = [r for r in rows if r.get("alert_type") == alert_type]
    if device_id:
        rows = [r for r in rows if r.get("device_id") == device_id]
    if severity:
        rows = [r for r in rows if (r.get("severity") or "").lower() == severity.lower()]

    total = len(rows)
    offset = (page - 1) * page_size
    page_items = rows[offset : offset + page_size]
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
