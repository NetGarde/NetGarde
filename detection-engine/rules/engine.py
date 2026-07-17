from __future__ import annotations

from typing import Any

from rules.alerts import SecurityAlert
from rules.chain_rules import evaluate_chain
from rules.state import StateStore

__all__ = ["SecurityAlert", "evaluate_event"]


def evaluate_event(event: dict[str, Any], store: StateStore) -> list[SecurityAlert]:
    chain = store.record_event(event)
    if chain is None:
        return []
    trigger = chain.latest()
    return evaluate_chain(chain, trigger=trigger)
