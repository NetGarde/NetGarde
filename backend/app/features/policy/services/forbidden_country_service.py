"""Forbidden destination countries for users in a given VPN login country."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.features.client_behavior.repositories.client_blocked_domain_repository import (
    ClientBlockedDomainRepository,
)
from app.features.devices.repositories.device_login_geo_repository import DeviceLoginGeoRepository
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.alerts.repositories.alert_repository import AlertRepository
from app.features.policy.forbidden_country_rules import (
    ForbiddenCountryRule,
    blocked_countries_for_user,
)
from app.features.policy.services.geo_country_policy_service import GeoCountryPolicyService
from app.shared.domain_country import dnsmasq_tld_patterns_for_country
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class ForbiddenCountryService:
    """
    User country = last VPN login GeoIP (public IP at enroll).

    DNS query processing removed with DNS product; ccTLD patterns remain for policy sync.
    """

    def __init__(self, db: Session):
        self.db = db
        self.geo_policy = GeoCountryPolicyService(db)
        self.login_geo = DeviceLoginGeoRepository(db)
        self.device_repo = DeviceRepository(db)
        self.block_repo = ClientBlockedDomainRepository(db)
        self.alert_repo = AlertRepository(db)

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
        patterns: set[str] = set()
        for code in self.blocked_destination_countries(device_id):
            patterns.update(dnsmasq_tld_patterns_for_country(code))
        return sorted(patterns, key=len, reverse=True)

    def process_queries(self, queries: list) -> int:
        """No-op: DNS ingest removed."""
        return 0
