"""Security lifecycle rules — authored in rules/definitions/security.yml."""

from __future__ import annotations

from rules.chain_rules import (
    DRIVER_LOAD_RULES,
    REGISTRY_PERSISTENCE_RULES,
    SERVICE_INSTALL_RULES,
)

SECURITY_RULES: list[tuple[str, object]] = [
    *DRIVER_LOAD_RULES,
    *SERVICE_INSTALL_RULES,
    *REGISTRY_PERSISTENCE_RULES,
]
