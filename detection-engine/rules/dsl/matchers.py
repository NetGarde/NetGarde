"""Operator implementations for YAML rule matchers."""

from __future__ import annotations

from rules.chain import ChainEvent
from rules.dsl.fields import get_string
from rules.dsl.schema import DslError, FieldOp

OPS_WITH_SET = frozenset(
    {
        "basename_in",
        "contains_any",
        "startswith_any",
        "not_startswith_any",
    }
)
OPS_FIELD_COMPARE = frozenset({"field_ne"})
KNOWN_OPS = OPS_WITH_SET | OPS_FIELD_COMPARE


def match_op(ev: ChainEvent, op: FieldOp, values: frozenset[str]) -> bool:
    if op.op == "basename_in":
        if not op.field:
            raise DslError("basename_in requires field")
        return get_string(ev, op.field) in values

    if op.op == "contains_any":
        if not op.field:
            raise DslError("contains_any requires field")
        text = get_string(ev, op.field)
        if not text:
            return False
        return any(marker in text for marker in values)

    if op.op == "startswith_any":
        if not op.field:
            raise DslError("startswith_any requires field")
        text = get_string(ev, op.field)
        if not text:
            return False
        return any(text.startswith(prefix) for prefix in values)

    if op.op == "not_startswith_any":
        if not op.field:
            raise DslError("not_startswith_any requires field")
        text = get_string(ev, op.field)
        if not text:
            return False
        return not any(text.startswith(prefix) for prefix in values)

    if op.op == "field_ne":
        if not op.left or not op.right:
            raise DslError("field_ne requires left and right")
        return get_string(ev, op.left) != get_string(ev, op.right)

    raise DslError(f"unknown operator: {op.op}")


def match_all(ev: ChainEvent, ops: tuple[FieldOp, ...], resolved: dict[str, frozenset[str]]) -> bool:
    for op in ops:
        values = resolved.get(op.set_name or "", frozenset())
        if not match_op(ev, op, values):
            return False
    return True
