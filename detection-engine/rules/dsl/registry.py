"""Load all YAML rule definitions and group by trigger event type."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable

from rules.alerts import SecurityAlert
from rules.chain import DeviceChain
from rules.dsl.compiler import compile_rule_file
from rules.dsl.gates import FastGate
from rules.dsl.loader import load_rule_file
from rules.dsl.schema import ALWAYS_TRIGGER, DslError

WindowRule = Callable[[DeviceChain], list[SecurityAlert]]
GatedRule = tuple[str, WindowRule, FastGate]

DEFINITIONS_DIR = Path(__file__).resolve().parent.parent / "definitions"


@lru_cache(maxsize=1)
def load_dsl_rules(
    definitions_dir: str | None = None,
) -> dict[str, list[GatedRule]]:
    """Return {event_type|'*': [(alert_type, fn, gate), ...]} from YAML definitions."""
    root = Path(definitions_dir) if definitions_dir else DEFINITIONS_DIR
    if not root.is_dir():
        raise DslError(f"definitions directory not found: {root}")

    by_type: dict[str, list[GatedRule]] = {}
    paths = sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml"))
    seen_paths: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        ordered.append(path)

    if not ordered:
        raise DslError(f"no YAML rule files in {root}")

    for path in ordered:
        rule_file = load_rule_file(path)
        for rule, fn, gate in compile_rule_file(rule_file):
            for trigger in rule.triggers:
                by_type.setdefault(trigger, []).append((rule.id, fn, gate))

    return by_type


def clear_dsl_cache() -> None:
    load_dsl_rules.cache_clear()


__all__ = ["ALWAYS_TRIGGER", "FastGate", "clear_dsl_cache", "load_dsl_rules"]
