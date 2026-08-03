from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any


class DslError(ValueError):
    """Invalid YAML rule definition."""


KIND_PROCESS_MATCH = "process_match"
KIND_EMIT = "emit"
KIND_PAIR_CHANGE = "pair_change"
KIND_WINDOW_UNIQUE = "window_unique"
KIND_WINDOW_CHANGES = "window_changes"
KIND_WINDOW_COUNT = "window_count"
KIND_METRIC_DELTA = "metric_delta"
KIND_THRESHOLD = "threshold"
KIND_COVERAGE = "coverage"

KNOWN_KINDS = frozenset(
    {
        KIND_PROCESS_MATCH,
        KIND_EMIT,
        KIND_PAIR_CHANGE,
        KIND_WINDOW_UNIQUE,
        KIND_WINDOW_CHANGES,
        KIND_WINDOW_COUNT,
        KIND_METRIC_DELTA,
        KIND_THRESHOLD,
        KIND_COVERAGE,
    }
)

ALWAYS_TRIGGER = "*"


@dataclass(frozen=True)
class FieldOp:
    """A single field matcher (basename_in, contains_any, …)."""

    op: str
    field: str | None = None
    set_name: str | None = None
    values: tuple[str, ...] = ()
    left: str | None = None
    right: str | None = None


@dataclass(frozen=True)
class SubjectWhen:
    ops: tuple[FieldOp, ...] = ()
    resolve: str | None = None
    within: timedelta | None = None


@dataclass(frozen=True)
class RuleDef:
    id: str
    kind: str
    triggers: tuple[str, ...]
    severity: str
    message: str
    # process_match
    child: SubjectWhen | None = None
    parent: SubjectWhen | None = None
    detail: dict[str, str] = field(default_factory=dict)
    # emit
    label_fields: tuple[str, ...] = ()
    detail_mode: str = "mapped"  # mapped | payload
    # shared network/window
    event_type: str | None = None
    within: timedelta | None = None
    presence: str | None = None
    change_fields: tuple[str, ...] = ()
    change_mode: str = "any"  # any | all
    match_policy: str = "latest"  # latest | first
    field: str | None = None
    min_unique: int | None = None
    min_changes: int | None = None
    min_count: int | None = None
    count_type: str | None = None
    absent_type: str | None = None
    min_delta: int | None = None
    min_value: int | None = None
    require_type: str | None = None
    require_min: int | None = None
    require_any: tuple[str, ...] = ()
    min_events: int | None = None


@dataclass(frozen=True)
class RuleFile:
    version: int
    sets: dict[str, frozenset[str]]
    rules: tuple[RuleDef, ...]
    source: str = ""


def parse_duration(raw: Any) -> timedelta:
    """Parse durations like 5m, 30s, 2h."""
    text = str(raw or "").strip().lower()
    if not text:
        raise DslError("empty duration")
    if text[-1].isdigit():
        raise DslError(f"duration must include unit (s/m/h): {raw!r}")
    unit = text[-1]
    try:
        amount = int(text[:-1])
    except ValueError as exc:
        raise DslError(f"invalid duration: {raw!r}") from exc
    if amount < 0:
        raise DslError(f"duration must be non-negative: {raw!r}")
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    raise DslError(f"unknown duration unit in {raw!r} (use s, m, or h)")


def window_minutes(td: timedelta | None) -> int:
    if td is None:
        return 0
    return int(td.total_seconds() // 60)
