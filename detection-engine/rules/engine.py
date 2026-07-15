from __future__ import annotations

from typing import Any

from rules.alerts import TwinAlert
from rules.chain_rules import evaluate_chain
from rules.state import StateStore

__all__ = ["TwinAlert", "evaluate_event"]


def evaluate_event(event: dict[str, Any], store: StateStore) -> list[TwinAlert]:
    chain = store.record_event(event)
    if chain is None:
        return []
    return evaluate_chain(chain)
