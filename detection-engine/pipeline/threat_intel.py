"""Threat intel engine — empty stub for v1 (slot reserved in the pipeline)."""

from __future__ import annotations

from typing import Any

from rules.chain import DeviceChain

from pipeline.types import EngineHit


def evaluate(
    event: dict[str, Any],
    chain: DeviceChain | None = None,
) -> list[EngineHit]:
    """No IOC matching yet — always returns no hits."""
    del event, chain
    return []
