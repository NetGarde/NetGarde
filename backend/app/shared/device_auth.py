"""Shared HMAC helpers (legacy module name kept for import stability)."""

from __future__ import annotations


def hmac_compare(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)
