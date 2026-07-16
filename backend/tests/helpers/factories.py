"""Shared test data builders for unit and integration tests."""

from __future__ import annotations

from typing import Optional

from app.features.devices.models.device import Device


def create_device(
    db_session,
    *,
    external_id: str = "dev-test",
    hostname: Optional[str] = "test-laptop",
    mac_address: Optional[str] = "aa:bb:cc:dd:ee:ff",
    source: str = "manual",
) -> Device:
    device = Device(
        external_id=external_id,
        hostname=hostname,
        mac_address=mac_address,
        source=source,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device
