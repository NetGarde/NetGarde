"""Load and validate YAML rule definition files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from rules.constants import (
    PRESENCE_ACTIVE,
    PRESENCE_IDLE,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from rules.dsl.fields import KNOWN_PROCESS_FIELDS
from rules.dsl.matchers import KNOWN_OPS, OPS_FIELD_COMPARE, OPS_WITH_SET
from rules.dsl.schema import (
    ALWAYS_TRIGGER,
    DslError,
    FieldOp,
    KIND_COVERAGE,
    KIND_EMIT,
    KIND_METRIC_DELTA,
    KIND_PAIR_CHANGE,
    KIND_PROCESS_MATCH,
    KIND_THRESHOLD,
    KIND_WINDOW_CHANGES,
    KIND_WINDOW_COUNT,
    KIND_WINDOW_UNIQUE,
    KNOWN_KINDS,
    RuleDef,
    RuleFile,
    SubjectWhen,
    parse_duration,
)

SUPPORTED_VERSION = 1
VALID_SEVERITIES = frozenset({SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH})
VALID_PRESENCE = frozenset({PRESENCE_ACTIVE, PRESENCE_IDLE})
META_PARENT_KEYS = frozenset({"resolve", "within"})


def _as_dict(raw: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DslError(f"{label} must be a mapping")
    return raw


def _as_list(raw: Any, *, label: str) -> list[Any]:
    if not isinstance(raw, list):
        raise DslError(f"{label} must be a list")
    return raw


def _require_str(data: dict[str, Any], key: str, *, label: str) -> str:
    value = str(data.get(key) or "").strip()
    if not value:
        raise DslError(f"{label}: {key} is required")
    return value


def _optional_int(raw: Any, *, label: str) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise DslError(f"{label} must be an int") from exc


def _parse_triggers(data: dict[str, Any], *, rule_id: str, kind: str) -> tuple[str, ...]:
    if data.get("always") is True or str(data.get("trigger") or "").strip() == ALWAYS_TRIGGER:
        return (ALWAYS_TRIGGER,)

    if "triggers" in data:
        items = _as_list(data.get("triggers"), label=f"rule {rule_id}.triggers")
        triggers = tuple(str(t).strip() for t in items if str(t).strip())
        if not triggers:
            raise DslError(f"rule {rule_id}: triggers must be non-empty")
        return triggers

    trigger = str(data.get("trigger") or "").strip()
    if not trigger:
        raise DslError(f"rule {rule_id}: trigger is required")
    return (trigger,)


def _parse_field_op(op_name: str, raw: Any, sets: dict[str, frozenset[str]]) -> FieldOp:
    if op_name not in KNOWN_OPS:
        raise DslError(f"unknown operator: {op_name}")

    spec = _as_dict(raw, label=op_name)

    if op_name in OPS_FIELD_COMPARE:
        left = str(spec.get("left") or "").strip()
        right = str(spec.get("right") or "").strip()
        if not left or not right:
            raise DslError(f"{op_name} requires left and right fields")
        if left not in KNOWN_PROCESS_FIELDS or right not in KNOWN_PROCESS_FIELDS:
            raise DslError(f"{op_name} references unknown field(s): {left!r}, {right!r}")
        return FieldOp(op=op_name, left=left, right=right)

    if op_name in OPS_WITH_SET:
        field_name = str(spec.get("field") or "").strip()
        set_name = str(spec.get("set") or "").strip()
        if not field_name:
            raise DslError(f"{op_name} requires field")
        if field_name not in KNOWN_PROCESS_FIELDS:
            raise DslError(f"{op_name} references unknown field: {field_name!r}")
        if not set_name:
            raise DslError(f"{op_name} requires set")
        if set_name not in sets:
            raise DslError(f"{op_name} references unknown set: {set_name!r}")
        return FieldOp(
            op=op_name,
            field=field_name,
            set_name=set_name,
            values=tuple(sorted(sets[set_name])),
        )

    raise DslError(f"unhandled operator: {op_name}")


def _parse_subject(
    raw: Any,
    *,
    label: str,
    sets: dict[str, frozenset[str]],
    is_parent: bool,
) -> SubjectWhen:
    data = _as_dict(raw, label=label)
    resolve = str(data.get("resolve") or "").strip() or None
    within_raw = data.get("within")
    within = parse_duration(within_raw) if within_raw is not None else None

    if is_parent:
        if resolve != "ppid":
            raise DslError(f"{label}.resolve must be 'ppid'")
        if within is None:
            raise DslError(f"{label}.within is required")
    elif resolve is not None or within is not None:
        raise DslError(f"{label} does not support resolve/within")

    ops: list[FieldOp] = []
    for key, value in data.items():
        if key in META_PARENT_KEYS:
            continue
        ops.append(_parse_field_op(key, value, sets))

    if not ops:
        raise DslError(f"{label} must include at least one matcher")
    return SubjectWhen(ops=tuple(ops), resolve=resolve, within=within)


def _parse_detail_mapped(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if raw == "payload":
        return {}
    data = _as_dict(raw, label="detail")
    out: dict[str, str] = {}
    for key, value in data.items():
        ref = str(value or "").strip()
        if not ref:
            raise DslError(f"detail.{key} must be a non-empty reference")
        out[str(key)] = ref
    return out


def _parse_presence(raw: Any, *, rule_id: str) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if value not in VALID_PRESENCE:
        raise DslError(f"rule {rule_id}: invalid presence {raw!r}")
    return value


def _infer_kind(data: dict[str, Any]) -> str:
    explicit = str(data.get("kind") or "").strip()
    if explicit:
        return explicit
    if "when" in data:
        return KIND_PROCESS_MATCH
    raise DslError("rule.kind is required (or provide when: for process_match)")


def _parse_process_match(data: dict[str, Any], *, rule_id: str, sets: dict[str, frozenset[str]]) -> dict[str, Any]:
    when = _as_dict(data.get("when"), label=f"rule {rule_id}.when")
    if "child" not in when:
        raise DslError(f"rule {rule_id}: when.child is required")
    child = _parse_subject(when["child"], label=f"rule {rule_id}.when.child", sets=sets, is_parent=False)
    parent = None
    if "parent" in when:
        parent = _parse_subject(
            when["parent"],
            label=f"rule {rule_id}.when.parent",
            sets=sets,
            is_parent=True,
        )
    detail = _parse_detail_mapped(data.get("detail"))
    if parent is None:
        for key, ref in detail.items():
            if ref.startswith("parent."):
                raise DslError(f"rule {rule_id}: detail.{key} references parent without when.parent")
    return {"child": child, "parent": parent, "detail": detail, "detail_mode": "mapped"}


def _parse_emit(data: dict[str, Any], *, rule_id: str) -> dict[str, Any]:
    labels = data.get("label_fields") or []
    if not isinstance(labels, list):
        raise DslError(f"rule {rule_id}: label_fields must be a list")
    detail_raw = data.get("detail", "payload")
    detail_mode = "payload" if detail_raw == "payload" else "mapped"
    detail = {} if detail_mode == "payload" else _parse_detail_mapped(detail_raw)
    return {
        "label_fields": tuple(str(x).strip() for x in labels if str(x).strip()),
        "detail_mode": detail_mode,
        "detail": detail,
    }


def _parse_pair_change(data: dict[str, Any], *, rule_id: str) -> dict[str, Any]:
    event_type = str(data.get("event_type") or data.get("trigger") or "").strip()
    if not event_type or event_type == ALWAYS_TRIGGER:
        raise DslError(f"rule {rule_id}: event_type is required")
    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        raise DslError(f"rule {rule_id}: fields must be a non-empty list")
    mode = str(data.get("require") or "any").strip().lower()
    if mode not in {"any", "all"}:
        raise DslError(f"rule {rule_id}: require must be any or all")
    match_policy = str(data.get("match") or "latest").strip().lower()
    if match_policy not in {"latest", "first"}:
        raise DslError(f"rule {rule_id}: match must be latest or first")
    return {
        "event_type": event_type,
        "change_fields": tuple(str(f).strip() for f in fields if str(f).strip()),
        "change_mode": mode,
        "match_policy": match_policy,
        "presence": _parse_presence(data.get("presence"), rule_id=rule_id),
        "detail": _parse_detail_mapped(data.get("detail")),
        "detail_mode": "mapped",
    }


def _parse_window_common(data: dict[str, Any], *, rule_id: str) -> dict[str, Any]:
    within_raw = data.get("within")
    if within_raw is None:
        raise DslError(f"rule {rule_id}: within is required")
    return {
        "within": parse_duration(within_raw),
        "presence": _parse_presence(data.get("presence"), rule_id=rule_id),
        "event_type": str(data.get("event_type") or "").strip() or None,
        "detail": _parse_detail_mapped(data.get("detail")),
        "detail_mode": "mapped",
    }


def _parse_rule(raw: Any, sets: dict[str, frozenset[str]]) -> RuleDef:
    data = _as_dict(raw, label="rule")
    rule_id = _require_str(data, "id", label="rule")
    kind = _infer_kind(data)
    if kind not in KNOWN_KINDS:
        raise DslError(f"rule {rule_id}: unknown kind {kind!r}")

    severity = str(data.get("severity") or "").strip().lower()
    if severity not in VALID_SEVERITIES:
        raise DslError(f"rule {rule_id}: invalid severity {severity!r}")

    message = _require_str(data, "message", label=f"rule {rule_id}")
    triggers = _parse_triggers(data, rule_id=rule_id, kind=kind)

    extras: dict[str, Any] = {
        "child": None,
        "parent": None,
        "detail": {},
        "detail_mode": "mapped",
        "label_fields": (),
        "event_type": None,
        "within": None,
        "presence": None,
        "change_fields": (),
        "change_mode": "any",
        "match_policy": "latest",
        "field": None,
        "min_unique": None,
        "min_changes": None,
        "min_count": None,
        "count_type": None,
        "absent_type": None,
        "min_delta": None,
        "min_value": None,
        "require_type": None,
        "require_min": None,
        "require_any": (),
        "min_events": None,
    }

    if kind == KIND_PROCESS_MATCH:
        extras.update(_parse_process_match(data, rule_id=rule_id, sets=sets))
    elif kind == KIND_EMIT:
        extras.update(_parse_emit(data, rule_id=rule_id))
    elif kind == KIND_PAIR_CHANGE:
        extras.update(_parse_pair_change(data, rule_id=rule_id))
    elif kind == KIND_WINDOW_UNIQUE:
        extras.update(_parse_window_common(data, rule_id=rule_id))
        field_name = str(data.get("field") or "").strip()
        if not field_name:
            raise DslError(f"rule {rule_id}: field is required")
        min_unique = _optional_int(data.get("min_unique"), label=f"rule {rule_id}.min_unique")
        if min_unique is None or min_unique < 1:
            raise DslError(f"rule {rule_id}: min_unique must be >= 1")
        extras["field"] = field_name
        extras["min_unique"] = min_unique
        if not extras["event_type"]:
            extras["event_type"] = triggers[0] if triggers[0] != ALWAYS_TRIGGER else None
        if not extras["event_type"]:
            raise DslError(f"rule {rule_id}: event_type is required")
    elif kind == KIND_WINDOW_CHANGES:
        extras.update(_parse_window_common(data, rule_id=rule_id))
        field_name = str(data.get("field") or "").strip()
        if not field_name:
            raise DslError(f"rule {rule_id}: field is required")
        min_changes = _optional_int(data.get("min_changes"), label=f"rule {rule_id}.min_changes")
        if min_changes is None or min_changes < 1:
            raise DslError(f"rule {rule_id}: min_changes must be >= 1")
        extras["field"] = field_name
        extras["min_changes"] = min_changes
        if not extras["event_type"]:
            extras["event_type"] = triggers[0] if triggers[0] != ALWAYS_TRIGGER else None
        if not extras["event_type"]:
            raise DslError(f"rule {rule_id}: event_type is required")
    elif kind == KIND_WINDOW_COUNT:
        extras.update(_parse_window_common(data, rule_id=rule_id))
        min_count = _optional_int(data.get("min_count"), label=f"rule {rule_id}.min_count")
        if min_count is None or min_count < 1:
            raise DslError(f"rule {rule_id}: min_count must be >= 1")
        extras["min_count"] = min_count
        extras["count_type"] = str(data.get("count_type") or "").strip() or None
        extras["absent_type"] = str(data.get("absent_type") or "").strip() or None
    elif kind == KIND_METRIC_DELTA:
        extras.update(_parse_window_common(data, rule_id=rule_id))
        field_name = str(data.get("field") or "").strip()
        if not field_name:
            raise DslError(f"rule {rule_id}: field is required")
        min_delta = _optional_int(data.get("min_delta"), label=f"rule {rule_id}.min_delta")
        if min_delta is None or min_delta < 1:
            raise DslError(f"rule {rule_id}: min_delta must be >= 1")
        extras["field"] = field_name
        extras["min_delta"] = min_delta
        if not extras["event_type"]:
            extras["event_type"] = triggers[0] if triggers[0] != ALWAYS_TRIGGER else None
        if not extras["event_type"]:
            raise DslError(f"rule {rule_id}: event_type is required")
    elif kind == KIND_THRESHOLD:
        field_name = str(data.get("field") or "").strip()
        if not field_name:
            raise DslError(f"rule {rule_id}: field is required")
        min_value = _optional_int(data.get("min"), label=f"rule {rule_id}.min")
        if min_value is None:
            raise DslError(f"rule {rule_id}: min is required")
        extras["field"] = field_name
        extras["min_value"] = min_value
        extras["presence"] = _parse_presence(data.get("presence"), rule_id=rule_id)
        extras["event_type"] = str(data.get("event_type") or triggers[0]).strip() or None
        extras["detail"] = _parse_detail_mapped(data.get("detail"))
    elif kind == KIND_COVERAGE:
        extras.update(_parse_window_common(data, rule_id=rule_id))
        extras["require_type"] = str(data.get("require_type") or "").strip() or None
        extras["require_min"] = _optional_int(data.get("require_min"), label=f"rule {rule_id}.require_min")
        require_any = data.get("require_any") or []
        if require_any and not isinstance(require_any, list):
            raise DslError(f"rule {rule_id}: require_any must be a list")
        extras["require_any"] = tuple(str(x).strip() for x in require_any if str(x).strip())
        extras["absent_type"] = str(data.get("absent_type") or "").strip() or None
        extras["min_events"] = _optional_int(data.get("min_events"), label=f"rule {rule_id}.min_events")
        if not extras["require_type"] and not extras["require_any"]:
            raise DslError(f"rule {rule_id}: require_type or require_any is required")
        if not extras["absent_type"]:
            raise DslError(f"rule {rule_id}: absent_type is required")

    return RuleDef(
        id=rule_id,
        kind=kind,
        triggers=triggers,
        severity=severity,
        message=message,
        **extras,
    )


def _parse_sets(raw: Any) -> dict[str, frozenset[str]]:
    if raw is None:
        return {}
    data = _as_dict(raw, label="sets")
    out: dict[str, frozenset[str]] = {}
    for name, values in data.items():
        items = _as_list(values, label=f"sets.{name}")
        out[str(name)] = frozenset(str(v).strip().lower() for v in items if str(v).strip())
    return out


def parse_rule_document(raw: Any, *, source: str = "") -> RuleFile:
    data = _as_dict(raw, label="rule file")
    version = data.get("version", SUPPORTED_VERSION)
    try:
        version_int = int(version)
    except (TypeError, ValueError) as exc:
        raise DslError(f"invalid version: {version!r}") from exc
    if version_int != SUPPORTED_VERSION:
        raise DslError(f"unsupported DSL version {version_int} (expected {SUPPORTED_VERSION})")

    sets = _parse_sets(data.get("sets"))
    rules_raw = _as_list(data.get("rules") or [], label="rules")
    rules = tuple(_parse_rule(item, sets) for item in rules_raw)
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise DslError("duplicate rule ids in definition file")
    return RuleFile(version=version_int, sets=sets, rules=rules, source=source)


def load_rule_file(path: Path | str) -> RuleFile:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DslError(f"cannot read rule file {path}: {exc}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DslError(f"invalid YAML in {path}: {exc}") from exc
    if raw is None:
        raise DslError(f"empty rule file: {path}")
    return parse_rule_document(raw, source=str(path))
