"""Shared test data builders for unit and integration tests."""

from __future__ import annotations

from typing import Optional

from app.features.devices.models.device import Device
from app.features.policy.models.policy_profile import PolicyProfile


def seed_policy_catalog(db_session) -> PolicyProfile:
    """Insert minimal builtin policy profiles (mirrors migration seed)."""
    teen = PolicyProfile(
        slug="teen",
        name="Teen",
        description="Default teen profile",
        enabled_pack_slugs=[],
        extra_block_domains=[],
        allowlist_domains=[],
        schedule_rules=[],
        behavior_sensitivity="medium",
        quarantine_on_abnormal=True,
        quarantine_hours=4,
        is_builtin=True,
    )
    work = PolicyProfile(
        slug="work",
        name="Work",
        description="Custom work profile",
        enabled_pack_slugs=[],
        extra_block_domains=[],
        allowlist_domains=[],
        schedule_rules=[],
        behavior_sensitivity="low",
        quarantine_on_abnormal=False,
        quarantine_hours=2,
        is_builtin=False,
    )
    db_session.add_all([teen, work])
    db_session.commit()
    db_session.refresh(teen)
    return teen


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
