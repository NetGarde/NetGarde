"""Multi-event detection rules for TrustEdge Agent telemetry.

Rules are authored in rules/definitions/*.yml, compiled by rules.dsl, and
registered by trigger event type. evaluate_chain runs the matching lane plus
cross-cutting ALWAYS_RULES, with fast gates and a process comm index.
"""

from __future__ import annotations

from typing import Callable

from rules.alerts import SecurityAlert
from rules.chain import ChainEvent, DeviceChain
from rules.constants import (
    SEVERITY_RANK,
    TYPE_ACTION_SUMMARY,
    TYPE_CLIENT_DETAILS,
    TYPE_DRIVER_LOAD,
    TYPE_NETWORK_SUMMARY,
    TYPE_PROCESS_START,
    TYPE_REGISTRY_PERSISTENCE,
    TYPE_SERVICE_INSTALL,
)
from rules.dsl import ALWAYS_TRIGGER, load_dsl_rules
from rules.dsl.fields import field_comm
from rules.dsl.gates import FastGate, gate_allows, process_comm_index
from rules.metrics import METRICS, Timer

WindowRule = Callable[[DeviceChain], list[SecurityAlert]]
GatedRule = tuple[str, WindowRule, FastGate]

_DSL = load_dsl_rules()


def _as_pairs(rules: list[GatedRule]) -> list[tuple[str, WindowRule]]:
    return [(name, fn) for name, fn, _gate in rules]


ALWAYS_RULES_GATED: list[GatedRule] = list(_DSL.get(ALWAYS_TRIGGER, []))
NETWORK_RULES_GATED: list[GatedRule] = list(_DSL.get(TYPE_NETWORK_SUMMARY, []))
PROCESS_RULES_GATED: list[GatedRule] = list(_DSL.get(TYPE_PROCESS_START, []))
COVERAGE_RULES_GATED: list[GatedRule] = list(_DSL.get(TYPE_ACTION_SUMMARY, []))
DRIVER_LOAD_RULES_GATED: list[GatedRule] = list(_DSL.get(TYPE_DRIVER_LOAD, []))
SERVICE_INSTALL_RULES_GATED: list[GatedRule] = list(_DSL.get(TYPE_SERVICE_INSTALL, []))
REGISTRY_PERSISTENCE_RULES_GATED: list[GatedRule] = list(
    _DSL.get(TYPE_REGISTRY_PERSISTENCE, [])
)

# Back-compat exports used by tests / discovery (name, fn) without gates.
ALWAYS_RULES: list[tuple[str, WindowRule]] = _as_pairs(ALWAYS_RULES_GATED)
NETWORK_RULES: list[tuple[str, WindowRule]] = _as_pairs(NETWORK_RULES_GATED)
PROCESS_RULES: list[tuple[str, WindowRule]] = _as_pairs(PROCESS_RULES_GATED)
COVERAGE_RULES: list[tuple[str, WindowRule]] = _as_pairs(COVERAGE_RULES_GATED)
DRIVER_LOAD_RULES: list[tuple[str, WindowRule]] = _as_pairs(DRIVER_LOAD_RULES_GATED)
SERVICE_INSTALL_RULES: list[tuple[str, WindowRule]] = _as_pairs(SERVICE_INSTALL_RULES_GATED)
REGISTRY_PERSISTENCE_RULES: list[tuple[str, WindowRule]] = _as_pairs(
    REGISTRY_PERSISTENCE_RULES_GATED
)

CHAIN_RULES: list[tuple[str, WindowRule]] = [
    *NETWORK_RULES,
    *ALWAYS_RULES,
    *COVERAGE_RULES,
]

RULES_BY_TYPE_GATED: dict[str, list[GatedRule]] = {
    key: list(rules)
    for key, rules in _DSL.items()
    if key != ALWAYS_TRIGGER
}

for _key in (
    TYPE_NETWORK_SUMMARY,
    TYPE_PROCESS_START,
    TYPE_ACTION_SUMMARY,
    TYPE_CLIENT_DETAILS,
    TYPE_DRIVER_LOAD,
    TYPE_SERVICE_INSTALL,
    TYPE_REGISTRY_PERSISTENCE,
):
    RULES_BY_TYPE_GATED.setdefault(_key, [])

RULES_BY_TYPE: dict[str, list[tuple[str, object]]] = {
    key: _as_pairs(rules) for key, rules in RULES_BY_TYPE_GATED.items()
}

_PROCESS_BY_COMM, _PROCESS_ALWAYS = process_comm_index(PROCESS_RULES_GATED)


def _select_rules(source: ChainEvent) -> list[GatedRule]:
    """Choose candidate rules for this trigger (indexed for process_start)."""
    typed = RULES_BY_TYPE_GATED.get(source.event_type, [])
    if source.event_type != TYPE_PROCESS_START:
        return list(typed)

    # Process lane: always-run rules + only rules whose basename gate matches comm.
    selected = list(_PROCESS_ALWAYS)
    comm = field_comm(source)
    if comm:
        selected.extend(_PROCESS_BY_COMM.get(comm, []))
    # Deduplicate while preserving order (a rule could theoretically appear twice).
    seen: set[str] = set()
    unique: list[GatedRule] = []
    for item in selected:
        if item[0] in seen:
            continue
        seen.add(item[0])
        unique.append(item)
    return unique


def evaluate_chain(
    chain: DeviceChain,
    *,
    trigger: ChainEvent | None = None,
) -> list[SecurityAlert]:
    """Run gated rules for the triggering event type; dedupe keeping highest severity."""
    source = trigger or chain.latest()
    if source is None:
        return []

    timer = Timer()
    candidates = [*_select_rules(source), *ALWAYS_RULES_GATED]
    selected = len(candidates)
    gated = 0
    ran = 0

    by_type: dict[str, SecurityAlert] = {}
    for _name, rule, gate in candidates:
        if not gate_allows(gate, chain, source):
            gated += 1
            continue
        ran += 1
        for alert in rule(chain):
            existing = by_type.get(alert.alert_type)
            if existing is None or SEVERITY_RANK.get(alert.severity, 0) > SEVERITY_RANK.get(
                existing.severity, 0
            ):
                by_type[alert.alert_type] = alert

    alerts = list(by_type.values())
    METRICS.record_event(
        selected=selected,
        gated=gated,
        ran=ran,
        alerts=len(alerts),
        elapsed_ns=timer.elapsed_ns(),
    )
    return alerts
