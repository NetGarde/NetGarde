"""Cheap pre-filters so evaluate_chain can skip rules before full evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from rules.chain import ChainEvent, DeviceChain
from rules.dsl.fields import field_comm, field_executable
from rules.dsl.schema import (
    KIND_PAIR_CHANGE,
    KIND_PROCESS_MATCH,
    KIND_THRESHOLD,
    KIND_WINDOW_CHANGES,
    KIND_WINDOW_COUNT,
    KIND_WINDOW_UNIQUE,
    KIND_METRIC_DELTA,
    KIND_COVERAGE,
    RuleDef,
)


@dataclass(frozen=True)
class FastGate:
    """Optional predicates evaluated before the compiled rule body runs."""

    presence: str | None = None
    child_comm_in: frozenset[str] | None = None
    child_exe_contains_any: frozenset[str] | None = None
    min_typed_events: int | None = None
    typed_event: str | None = None


def build_gate(rule: RuleDef, sets: dict[str, frozenset[str]]) -> FastGate:
    """Derive a fast gate from the rule definition (compile-time)."""
    presence = rule.presence
    child_comm_in: frozenset[str] | None = None
    child_exe_contains_any: frozenset[str] | None = None
    min_typed_events: int | None = None
    typed_event: str | None = None

    if rule.kind == KIND_PROCESS_MATCH and rule.child is not None:
        for op in rule.child.ops:
            if op.op == "basename_in" and op.field == "comm" and op.set_name:
                values = sets.get(op.set_name, frozenset(op.values))
                child_comm_in = values if child_comm_in is None else (child_comm_in & values)
            elif op.op == "contains_any" and op.field == "executable" and op.set_name:
                values = sets.get(op.set_name, frozenset(op.values))
                child_exe_contains_any = (
                    values if child_exe_contains_any is None else (child_exe_contains_any | values)
                )

    if rule.kind in {
        KIND_PAIR_CHANGE,
        KIND_WINDOW_UNIQUE,
        KIND_WINDOW_CHANGES,
        KIND_METRIC_DELTA,
    }:
        typed_event = rule.event_type
        min_typed_events = 2 if rule.kind == KIND_PAIR_CHANGE else 1

    if rule.kind == KIND_THRESHOLD:
        typed_event = rule.event_type or (rule.triggers[0] if rule.triggers else None)
        min_typed_events = 1

    if rule.kind == KIND_WINDOW_COUNT and rule.count_type:
        typed_event = rule.count_type
        min_typed_events = rule.min_count

    if rule.kind == KIND_COVERAGE and rule.require_type:
        typed_event = rule.require_type
        min_typed_events = rule.require_min or 1

    return FastGate(
        presence=presence,
        child_comm_in=child_comm_in,
        child_exe_contains_any=child_exe_contains_any,
        min_typed_events=min_typed_events,
        typed_event=typed_event,
    )


def gate_allows(gate: FastGate, chain: DeviceChain, trigger: ChainEvent | None) -> bool:
    """Return False when the rule cannot possibly match (skip full evaluation)."""
    if gate.presence is not None and chain.latest_presence() != gate.presence:
        return False

    if gate.min_typed_events is not None and gate.typed_event:
        # Cheap length check against full chain (window rules still re-filter by time).
        count = sum(1 for ev in chain.events if ev.event_type == gate.typed_event)
        if count < gate.min_typed_events:
            return False

    if trigger is None:
        return True

    if gate.child_comm_in is not None:
        if field_comm(trigger) not in gate.child_comm_in:
            return False

    if gate.child_exe_contains_any is not None:
        exe = field_executable(trigger)
        if not exe or not any(marker in exe for marker in gate.child_exe_contains_any):
            return False

    return True


def process_comm_index(
    rules: list[tuple[str, object, FastGate]],
) -> tuple[dict[str, list[tuple[str, object, FastGate]]], list[tuple[str, object, FastGate]]]:
    """Split process rules into comm→rules index and always-run rules.

    Rules with a child_comm_in gate are indexed; others run on every process_start.
    """
    by_comm: dict[str, list[tuple[str, object, FastGate]]] = {}
    always: list[tuple[str, object, FastGate]] = []
    for item in rules:
        _name, _fn, gate = item
        if gate.child_comm_in:
            for comm in gate.child_comm_in:
                by_comm.setdefault(comm, []).append(item)
        else:
            always.append(item)
    return by_comm, always
