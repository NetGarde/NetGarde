"""Template sentences for the dashboard network review (no LLM)."""

from typing import Any

_ALERT_TYPE_LABELS: dict[str, str] = {
    "attack": "attack alerts",
    "malware": "malware alerts",
    "suspicious": "suspicious activity",
    "behavior_anomaly": "behavior anomalies",
}


def _format_alert_breakdown(by_type: dict[str, int]) -> str:
    parts: list[str] = []
    for alert_type, count in sorted(by_type.items(), key=lambda x: (-x[1], x[0])):
        if count <= 0:
            continue
        label = _ALERT_TYPE_LABELS.get(alert_type, alert_type.replace("_", " "))
        parts.append(f"{count} {label}")
    return ", ".join(parts)


def build_network_overview_bullets(snapshot: dict[str, Any]) -> list[str]:
    """Turn a metrics snapshot into human-readable review bullets."""
    period = int(snapshot.get("period_minutes") or 60)
    bullets: list[str] = []

    live = snapshot.get("live") or {}
    reporting = int(live.get("reporting") or 0)
    if reporting > 0:
        bullets.append(
            f"{reporting} device{'s' if reporting != 1 else ''} active in the last {period} minutes."
        )
    else:
        bullets.append(f"No devices reported activity in the last {period} minutes.")

    alerts = snapshot.get("alerts") or {}
    alert_total = int(alerts.get("total") or 0)
    by_type: dict[str, int] = alerts.get("by_type") or {}
    if alert_total > 0:
        breakdown = _format_alert_breakdown(by_type)
        detail = f" ({breakdown})" if breakdown else ""
        bullets.append(
            f"{alert_total} security alert{'s' if alert_total != 1 else ''} "
            f"in the last {period} minutes{detail}."
        )
    else:
        bullets.append(f"No security alerts in the last {period} minutes.")

    return bullets
