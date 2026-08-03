"""Build stable behavior keys from security alerts for baseline learning.

Does not persist process_chain (parent>child) keys — only path/mismatch styles.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from rules.alerts import SecurityAlert
from rules.constants import (
    ALERT_BINARY_PATH_MISMATCH,
    ALERT_TEMP_PATH_EXECUTION,
)

# Alert types that participate in per-device frequency baselining.
# Chain-style alerts (shell→downloader, script→shell) are intentionally excluded
# so behavioral storage never saves parent>child keys.
BASELINE_ALERT_TYPES = frozenset(
    {
        ALERT_TEMP_PATH_EXECUTION,
        ALERT_BINARY_PATH_MISMATCH,
    }
)

KIND_TEMP_PATH = "temp_path"
KIND_BINARY_MISMATCH = "binary_mismatch"


def _parse_detail(raw: Optional[str]) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return text


def behavior_from_alert(alert: SecurityAlert) -> Optional[tuple[str, str, dict[str, Any]]]:
    """Return (behavior_kind, behavior_key, meta) or None if not baseline-eligible."""
    if alert.alert_type not in BASELINE_ALERT_TYPES:
        return None

    detail = _parse_detail(alert.detail)
    meta: dict[str, Any] = {"alert_type": alert.alert_type}

    if alert.alert_type == ALERT_TEMP_PATH_EXECUTION:
        exe = _norm(detail.get("executable") or detail.get("comm"))
        if not exe:
            return None
        meta["executable"] = exe
        return KIND_TEMP_PATH, exe, meta

    if alert.alert_type == ALERT_BINARY_PATH_MISMATCH:
        comm = _norm(detail.get("comm"))
        exe = _norm(detail.get("executable"))
        if not comm:
            return None
        key = f"{comm}@{exe}" if exe else comm
        meta.update({"comm": comm, "executable": exe})
        return KIND_BINARY_MISMATCH, key, meta

    return None
