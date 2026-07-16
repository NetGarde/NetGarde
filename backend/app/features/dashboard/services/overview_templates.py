"""Template sentences for the dashboard network review (no LLM)."""

from typing import Any

_ALERT_TYPE_LABELS: dict[str, str] = {
    "blocked_attempt": "blocked attempts",
    "new_domain": "new domains",
    "suspicious_domain": "suspicious domains",
    "bandwidth_spike": "bandwidth spikes",
    "behavior_anomaly": "behavior anomalies",
    "new_country_region": "new country regions",
    "new_vpn_login_country": "Logins from new countries",
    "forbidden_country_access": "forbidden country DNS attempts",
}


def _format_alert_breakdown(by_type: dict[str, int]) -> str:
    parts: list[str] = []
    for alert_type, count in sorted(by_type.items(), key=lambda x: (-x[1], x[0])):
        if count <= 0:
            continue
        label = _ALERT_TYPE_LABELS.get(alert_type, alert_type.replace("_", " "))
        parts.append(f"{count} {label}")
    return ", ".join(parts)


def _format_top_domains(top: list[dict[str, Any]], limit: int = 3) -> str:
    items = top[:limit]
    if not items:
        return ""
    return ", ".join(f"{row['domain']} ({row['count']})" for row in items)


def build_network_overview_bullets(snapshot: dict[str, Any]) -> list[str]:
    """Turn a metrics snapshot into human-readable review bullets."""
    period = int(snapshot.get("period_minutes") or 60)
    bullets: list[str] = []

    live = snapshot.get("live") or {}
    reporting = int(live.get("reporting") or 0)
    live_total = float(live.get("total_mib_per_sec") or 0)
    if reporting > 0:
        bullets.append(
            f"{reporting} client{'s' if reporting != 1 else ''} reporting traffic now "
            f"({live_total:.1f} MiB/s combined)."
        )
    else:
        bullets.append("No clients are reporting live bandwidth right now.")

    history = snapshot.get("history") or {}
    peak = float(history.get("peak_mib_per_sec") or 0)
    if peak > 0:
        bullets.append(f"Peak throughput in the last {period} minutes: {peak:.1f} MiB/s.")

    alerts = snapshot.get("alerts") or {}
    alert_total = int(alerts.get("total") or 0)
    by_type: dict[str, int] = alerts.get("by_type") or {}
    if alert_total > 0:
        breakdown = _format_alert_breakdown(by_type)
        detail = f" ({breakdown})" if breakdown else ""
        bullets.append(
            f"{alert_total} DNS alert{'s' if alert_total != 1 else ''} in the last {period} minutes{detail}."
        )

    blocked = snapshot.get("blocked") or {}
    blocked_count = int(blocked.get("count") or 0)
    if blocked_count > 0:
        top_line = _format_top_domains(blocked.get("top_domains") or [])
        suffix = f"; top targets: {top_line}" if top_line else ""
        bullets.append(
            f"{blocked_count} blocked DNS quer{'ies' if blocked_count != 1 else 'y'} "
            f"in the last {period} minutes{suffix}."
        )

    policy = snapshot.get("policy") or {}
    pack_names: list[str] = policy.get("enabled_pack_names") or []
    if pack_names:
        names = ", ".join(pack_names)
        bullets.append(f"Global policy packs active: {names}.")
    else:
        bullets.append("No global policy packs are enabled.")

    behavior = snapshot.get("behavior") or {}
    elevated = int(behavior.get("elevated_count") or 0)
    threshold = int(behavior.get("threshold") or 70)
    if elevated > 0:
        bullets.append(
            f"{elevated} client{'s' if elevated != 1 else ''} with elevated behavior scores "
            f"(≥{threshold})."
        )

    if alert_total == 0 and blocked_count == 0 and elevated == 0:
        bullets.append(f"No security anomalies detected in the last {period} minutes.")

    return bullets
