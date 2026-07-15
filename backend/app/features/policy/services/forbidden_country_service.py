"""Forbidden destination countries for users in a given VPN login country."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.features.client_behavior.repositories.client_blocked_domain_repository import (
    ClientBlockedDomainRepository,
)
from app.features.devices.repositories.device_login_geo_repository import DeviceLoginGeoRepository
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.dns_queries.repositories.dns_alert_repository import DnsAlertRepository
from app.features.policy.forbidden_country_rules import (
    ForbiddenCountryRule,
    blocked_countries_for_user,
)
from app.features.policy.services.geo_country_policy_service import GeoCountryPolicyService
from app.shared.config import settings
from app.shared.domain_country import dnsmasq_tld_patterns_for_country
from app.shared.domain_country import country_code_for_domain, country_display_name
from app.shared.domain_utils import extract_root_domain
from app.features.dns_queries.schemas.dns_query import DnsQueryCreate
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

_ALERT_TYPE = "forbidden_country_access"
_BLOCK_SOURCE = "forbidden_country"


class ForbiddenCountryService:
    """
    User country = last VPN login GeoIP (public IP at enroll).

    When a rule matches, block destination ccTLDs via policy DNS sync and alert on
    non-ccTLD queries whose domain still maps to a forbidden country code.
    """

    def __init__(self, db: Session):
        self.db = db
        self.geo_policy = GeoCountryPolicyService(db)
        self.login_geo = DeviceLoginGeoRepository(db)
        self.device_repo = DeviceRepository(db)
        self.block_repo = ClientBlockedDomainRepository(db)
        self.alert_repo = DnsAlertRepository(db)

    def is_enabled(self) -> bool:
        return self.geo_policy.destination_rules_enabled()

    def list_rules(self) -> List[ForbiddenCountryRule]:
        return self.geo_policy.destination_rules()

    def get_user_country(self, device_id: int) -> Optional[str]:
        """Recommended selector: last VPN enroll GeoIP country (ISO alpha-2)."""
        row = self.login_geo.get_latest(device_id)
        if row and row.country_code:
            return row.country_code.strip().upper()
        return None

    def blocked_destination_countries(self, device_id: int) -> List[str]:
        if not self.is_enabled():
            return []
        user_country = self.get_user_country(device_id)
        return blocked_countries_for_user(user_country, self.list_rules())

    def dnsmasq_tld_patterns_for_device(self, device_id: int) -> List[str]:
        patterns: Set[str] = set()
        for code in self.blocked_destination_countries(device_id):
            patterns.update(dnsmasq_tld_patterns_for_country(code))
        return sorted(patterns, key=len, reverse=True)

    def process_queries(self, queries: List[DnsQueryCreate]) -> int:
        """Alert + per-device block for explicit domains that match forbidden destination country."""
        if not self.is_enabled() or not queries:
            return 0

        rules = self.list_rules()
        if not rules:
            return 0

        alerts = 0
        by_ip: Dict[str, List[DnsQueryCreate]] = {}
        for q in queries:
            if q.blocked:
                continue
            by_ip.setdefault(q.client_ip, []).append(q)

        for client_ip, batch in by_ip.items():
            device = self.device_repo.get_by_client_ip(client_ip)
            if not device:
                continue
            user_country = self.get_user_country(device.id)
            blocked_dests = blocked_countries_for_user(user_country, rules)
            if not blocked_dests:
                continue
            blocked_set = set(blocked_dests)
            user_name = country_display_name(user_country or "")
            label = device.hostname or client_ip

            for q in batch:
                dest = country_code_for_domain(q.domain)
                if dest not in blocked_set:
                    continue
                root = extract_root_domain(q.domain)
                if settings.DNS_BLOCKING_ENABLED:
                    self.block_repo.create_block(
                        device_id=device.id,
                        domain=q.domain.lower(),
                        root_domain=root,
                        source=_BLOCK_SOURCE,
                        score=None,
                        expires_at=None,
                    )
                dest_name = country_display_name(dest)
                message = (
                    f"{label} ({user_name}) attempted DNS for {q.domain} "
                    f"(inferred region {dest_name} / {dest}), blocked by forbidden-country policy."
                )
                self.alert_repo.create(
                    timestamp=datetime.now(timezone.utc),
                    client_ip=client_ip,
                    alert_type=_ALERT_TYPE,
                    severity="high",
                    domain=q.domain,
                    root_domain=root,
                    message=message,
                    device_id=device.id,
                )
                alerts += 1
                logger.warning(
                    "Forbidden country DNS block",
                    extra=structured_extra(
                        "forbidden_country_block",
                        device_id=device.id,
                        user_country=user_country,
                        dest_country=dest,
                        domain=q.domain,
                    ),
                )

        return alerts
