"""YAML declarative rules DSL for the detection engine."""

from rules.dsl.registry import clear_dsl_cache, load_dsl_rules
from rules.dsl.schema import ALWAYS_TRIGGER
from rules.dsl.gates import FastGate, gate_allows

__all__ = [
    "ALWAYS_TRIGGER",
    "FastGate",
    "clear_dsl_cache",
    "gate_allows",
    "load_dsl_rules",
]
