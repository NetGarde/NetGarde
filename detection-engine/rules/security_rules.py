"""Security lifecycle rules for driver, service, and persistence artifacts."""

from __future__ import annotations

from typing import Any

from rules.alerts import SecurityAlert
from rules.chain import (
    TYPE_DRIVER_LOAD,
    TYPE_REGISTRY_PERSISTENCE,
    TYPE_SERVICE_INSTALL,
    ChainEvent,
    DeviceChain,
    payload_str,
    ts_iso,
)


def _alert(
    chain: DeviceChain,
    *,
    source: ChainEvent,
    alert_type: str,
    severity: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> SecurityAlert:
    return SecurityAlert(
        timestamp=ts_iso(source.ts),
        device_id=chain.device_id,
        event_id=source.event_id,
        event_type=source.event_type,
        alert_type=alert_type,
        severity=severity,
        message=message,
        detail=DeviceChain.detail_json(detail) if detail else None,
    )


def _latest_payload_alert(
    chain: DeviceChain,
    *,
    event_type: str,
    alert_type: str,
    severity: str,
    message_prefix: str,
    label_fields: tuple[str, ...],
) -> list[SecurityAlert]:
    latest = chain.latest(event_type)
    if not latest:
        return []
    label = ""
    for field in label_fields:
        label = payload_str(latest.payload.get(field))
        if label:
            break
    message = message_prefix if not label else f"{message_prefix}: {label}"
    return [
        _alert(
            chain,
            source=latest,
            alert_type=alert_type,
            severity=severity,
            message=message,
            detail=latest.payload,
        )
    ]


def rule_driver_load(chain: DeviceChain) -> list[SecurityAlert]:
    """Newly observed driver/kext load."""
    return _latest_payload_alert(
        chain,
        event_type=TYPE_DRIVER_LOAD,
        alert_type="driver_load",
        severity="high",
        message_prefix="Driver or kernel extension loaded",
        label_fields=("display_name", "name", "path"),
    )


def rule_service_install(chain: DeviceChain) -> list[SecurityAlert]:
    """Newly observed service or LaunchDaemon install/change."""
    return _latest_payload_alert(
        chain,
        event_type=TYPE_SERVICE_INSTALL,
        alert_type="service_install",
        severity="medium",
        message_prefix="Service or LaunchDaemon installed/changed",
        label_fields=("display_name", "name", "path", "program"),
    )


def rule_registry_persistence(chain: DeviceChain) -> list[SecurityAlert]:
    """Newly observed persistence artifact (Run key or macOS LaunchAgent)."""
    return _latest_payload_alert(
        chain,
        event_type=TYPE_REGISTRY_PERSISTENCE,
        alert_type="registry_persistence",
        severity="high",
        message_prefix="Persistence artifact installed/changed",
        label_fields=("value_name", "path", "value"),
    )


SECURITY_RULES: list[tuple[str, object]] = [
    ("driver_load", rule_driver_load),
    ("service_install", rule_service_install),
    ("registry_persistence", rule_registry_persistence),
]
