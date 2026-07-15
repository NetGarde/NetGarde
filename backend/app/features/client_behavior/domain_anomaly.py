"""Heuristics for suspicious domain activity."""

from __future__ import annotations

import re
from typing import List, Set

from app.shared.domain_utils import extract_root_domain

SUSPICIOUS_TLDS: Set[str] = {
    ".ru",
    ".xyz",
    ".top",
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",
    ".su",
    ".cn",
}

_ENTROPY_LABEL = re.compile(r"^[a-z0-9]{16,}$", re.IGNORECASE)


def matched_suspicious_tld(root_domain: str) -> str | None:
    root = root_domain.lower()
    for tld in sorted(SUSPICIOUS_TLDS, key=len, reverse=True):
        if root.endswith(tld):
            return tld
    return None


def is_suspicious_tld(root_domain: str) -> bool:
    return matched_suspicious_tld(root_domain) is not None


def high_entropy_subdomain_reasons(domain: str) -> List[str]:
    labels = domain.lower().rstrip(".").split(".")
    if len(labels) < 2:
        return []

    first = labels[0]
    reasons: List[str] = []

    for segment in first.split("-"):
        if len(segment) < 16:
            continue
        digit_ratio = sum(ch.isdigit() for ch in segment) / len(segment)
        if digit_ratio >= 0.75:
            pct = int(digit_ratio * 100)
            reasons.append(
                f"Subdomain looks random: long label with many digits ({pct}% digits in '{segment}')"
            )
            break

    if len(first) >= 16 and _ENTROPY_LABEL.match(first):
        reasons.append(
            f"Subdomain looks random: long alphanumeric label ('{first}')"
        )

    return reasons


def is_high_entropy_subdomain(domain: str) -> bool:
    return bool(high_entropy_subdomain_reasons(domain))


def get_suspicious_domain_reasons(domain: str) -> List[str]:
    """Return human-readable reasons why a domain matched suspicious heuristics."""
    root = extract_root_domain(domain)
    reasons: List[str] = []

    matched_tld = matched_suspicious_tld(root)
    if matched_tld:
        reasons.append(f"Root domain uses suspicious TLD ({matched_tld})")

    reasons.extend(high_entropy_subdomain_reasons(domain))
    return reasons


def is_suspicious_domain(domain: str) -> bool:
    return bool(get_suspicious_domain_reasons(domain))
