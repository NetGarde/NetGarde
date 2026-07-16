"""Shared test data builders for unit and integration tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.features.client_behavior.models.client_blocked_domain import ClientBlockedDomain
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


def seed_country_presence(db_session, device: Device, *, country_code: str = "IL", count: int = 5):
    from app.features.devices.repositories.device_country_presence_repository import (
        DeviceCountryPresenceRepository,
    )

    repo = DeviceCountryPresenceRepository(db_session)
    repo.record_batch(device.id, {country_code: count})
    db_session.commit()


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


def create_behavior_block(
    db_session,
    device: Device,
    *,
    domain: str = "bad.example.com",
    score: int = 85,
) -> ClientBlockedDomain:
    block = ClientBlockedDomain(
        device_id=device.id,
        domain=domain,
        root_domain="example.com",
        source="behavior_auto",
        score=score,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)
    return block
