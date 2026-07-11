import json

from app.features.devices.models.device import Device
from app.features.devices.models.device_login_geo import DeviceLoginGeoObservation
from app.features.policy.forbidden_country_rules import (
    blocked_countries_for_user,
    parse_forbidden_country_rules,
)
from app.features.policy.models.policy_profile import PolicyProfile
from app.features.policy.services.forbidden_country_service import ForbiddenCountryService
from app.features.policy.services.policy_dns_service import PolicyDnsService
from app.features.vpn.models.ip_lease import IpLease
from app.features.vpn.models.ip_pool import IpPool
from app.features.vpn.models.vpn_peer import VpnPeer
from app.shared.domain_country import dnsmasq_tld_patterns_for_country


def test_parse_rules():
    raw = json.dumps([{"user_country": "IL", "blocked_countries": ["IR", "SY"]}])
    rules = parse_forbidden_country_rules(raw)
    assert len(rules) == 1
    assert rules[0].user_country == "IL"
    assert "IR" in rules[0].blocked_countries


def test_blocked_countries_for_user():
    rules = parse_forbidden_country_rules(
        '[{"user_country":"IL","blocked_countries":["IR"]}]'
    )
    assert blocked_countries_for_user("IL", rules) == ["IR"]
    assert blocked_countries_for_user("US", rules) == []


def test_dnsmasq_patterns_ir():
    patterns = dnsmasq_tld_patterns_for_country("IR")
    assert ".ir" in patterns


def _device_with_login_geo(db_session, *, country: str = "IL"):
    pool = IpPool(
        name="pool-fc",
        cidr="10.0.0.0/24",
        gateway_ip="10.0.0.1",
        dns_ip="10.0.0.1",
        endpoint="vpn:51820",
        server_public_key="key",
    )
    db_session.add(pool)
    db_session.flush()
    peer = VpnPeer(device_id="fc-dev", public_key="pk-fc", pool_id=pool.id)
    db_session.add(peer)
    db_session.flush()
    lease = IpLease(pool_id=pool.id, peer_id=peer.id, ip="10.0.0.12")
    db_session.add(lease)
    db_session.flush()
    profile = PolicyProfile(
        slug="teen",
        name="Teen",
        enabled_pack_slugs=[],
        is_builtin=True,
    )
    db_session.add(profile)
    db_session.flush()
    device = Device(
        ip_lease_id=lease.id,
        mac_address="aa:bb:cc:dd:ee:01",
        source="vpn_enroll",
        policy_profile_id=profile.id,
    )
    db_session.add(device)
    db_session.flush()
    db_session.add(
        DeviceLoginGeoObservation(
            device_id=device.id,
            peer_id=peer.id,
            public_ip="8.8.8.8",
            country_code=country,
            country_name="Israel",
            source="enroll",
        )
    )
    db_session.commit()
    return device


def test_forbidden_country_tlds_for_il_user(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.shared.config.settings.FORBIDDEN_COUNTRY_RULES",
        '[{"user_country":"IL","blocked_countries":["IR"]}]',
    )
    monkeypatch.setattr("app.shared.config.settings.FORBIDDEN_COUNTRY_ENABLED", True)
    device = _device_with_login_geo(db_session)
    svc = ForbiddenCountryService(db_session)
    assert svc.get_user_country(device.id) == "IL"
    patterns = svc.dnsmasq_tld_patterns_for_device(device.id)
    assert ".ir" in patterns


def test_policy_dns_sync_includes_country_tlds(db_session, monkeypatch, dns_blocking_env):
    monkeypatch.setattr(
        "app.shared.config.settings.FORBIDDEN_COUNTRY_RULES",
        '[{"user_country":"IL","blocked_countries":["IR"]}]',
    )
    monkeypatch.setattr("app.shared.config.settings.FORBIDDEN_COUNTRY_ENABLED", True)
    device = _device_with_login_geo(db_session)
    sync = PolicyDnsService(db_session).build_dns_sync()
    entry = next(e for e in sync.entries if e.device_id == device.id)
    assert ".ir" in entry.block_country_tlds
