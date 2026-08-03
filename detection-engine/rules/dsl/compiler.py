"""Compile YAML RuleDef into evaluate_chain-compatible callables."""

from __future__ import annotations

import re
from typing import Any, Callable

from rules.alerts import SecurityAlert
from rules.chain import ChainEvent, DeviceChain, payload_int, payload_str, ts_iso
from rules.constants import TYPE_PROCESS_START
from rules.dsl.fields import get_int, get_string, get_value
from rules.dsl.matchers import match_all
from rules.dsl.schema import (
    DslError,
    KIND_COVERAGE,
    KIND_EMIT,
    KIND_METRIC_DELTA,
    KIND_PAIR_CHANGE,
    KIND_PROCESS_MATCH,
    KIND_THRESHOLD,
    KIND_WINDOW_CHANGES,
    KIND_WINDOW_COUNT,
    KIND_WINDOW_UNIQUE,
    RuleDef,
    RuleFile,
    SubjectWhen,
    window_minutes,
)

WindowRule = Callable[[DeviceChain], list[SecurityAlert]]

_TEMPLATE_RE = re.compile(r"\{([a-zA-Z0-9_.]+)\}")


def _trigger_event(chain: DeviceChain, trigger: str) -> ChainEvent | None:
    latest = chain.latest()
    if latest is not None and latest.event_type == trigger:
        return latest
    return chain.latest(trigger)


def _find_parent(chain: DeviceChain, child: ChainEvent, within) -> ChainEvent | None:
    ppid = payload_int(child.payload.get("ppid"))
    if ppid <= 0:
        return None
    for ev in reversed(chain.of_type(TYPE_PROCESS_START, within)):
        if payload_int(ev.payload.get("pid")) == ppid:
            return ev
    return None


def _resolve_sets(subject: SubjectWhen, sets: dict[str, frozenset[str]]) -> dict[str, frozenset[str]]:
    resolved: dict[str, frozenset[str]] = {}
    for op in subject.ops:
        if op.set_name:
            resolved[op.set_name] = sets[op.set_name]
    return resolved


def _format(template: str, ctx: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in ctx:
            return str(ctx[key])
        # Support dotted keys already flattened into ctx.
        return match.group(0)

    return _TEMPLATE_RE.sub(repl, template)


def _alert(
    chain: DeviceChain,
    *,
    source: ChainEvent,
    rule: RuleDef,
    message: str,
    detail: dict[str, Any] | None,
) -> SecurityAlert:
    return SecurityAlert(
        timestamp=ts_iso(source.ts),
        device_id=chain.device_id,
        event_id=source.event_id,
        event_type=source.event_type,
        alert_type=rule.id,
        severity=rule.severity,
        message=message,
        detail=DeviceChain.detail_json(detail) if detail else None,
    )


def _pairs(events: list[ChainEvent]) -> list[tuple[ChainEvent, ChainEvent]]:
    return [(events[i - 1], events[i]) for i in range(1, len(events))]


def _field_changed(prev: ChainEvent, cur: ChainEvent, field_name: str) -> bool:
    old = get_string(prev, field_name)
    new = get_string(cur, field_name)
    return bool(old and new and old != new)


def _presence_ok(chain: DeviceChain, presence: str | None) -> bool:
    if presence is None:
        return True
    return chain.latest_presence() == presence


def _resolve_detail_templates(mapping: dict[str, str], ctx: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, ref in mapping.items():
        # Literal number as string of digits
        if ref.isdigit():
            out[key] = int(ref)
            continue
        # Context key (from, to, changes, …) or dotted path already in ctx
        if ref in ctx:
            value = ctx[ref]
        elif ref.startswith("{") and ref.endswith("}"):
            value = ctx.get(ref[1:-1], "")
        else:
            value = ctx.get(ref, ref)
        if key.endswith("cmdline") and (value is None or value == ""):
            continue
        out[key] = value
    return out


def _process_detail(mapping: dict[str, str], child: ChainEvent, parent: ChainEvent | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, ref in mapping.items():
        if "." not in ref:
            continue
        subject, field_name = ref.split(".", 1)
        ev = child if subject == "child" else parent
        if ev is None:
            continue
        value = get_value(ev, field_name)
        if field_name == "cmdline" and (value is None or value == ""):
            continue
        out[key] = value
    return out


def _compile_process_match(rule: RuleDef, sets: dict[str, frozenset[str]]) -> WindowRule:
    assert rule.child is not None
    child_sets = _resolve_sets(rule.child, sets)
    parent_sets = _resolve_sets(rule.parent, sets) if rule.parent else {}
    trigger = rule.triggers[0]

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        child = _trigger_event(chain, trigger)
        if child is None:
            return []
        if not match_all(child, rule.child.ops, child_sets):
            return []

        parent: ChainEvent | None = None
        if rule.parent is not None:
            parent = _find_parent(chain, child, rule.parent.within)
            if parent is None:
                return []
            if not match_all(parent, rule.parent.ops, parent_sets):
                return []

        ctx: dict[str, Any] = {}
        for field_name in ("comm", "executable", "cmdline", "pid", "ppid"):
            ctx[f"child.{field_name}"] = get_value(child, field_name)
            if parent is not None:
                ctx[f"parent.{field_name}"] = get_value(parent, field_name)

        detail = _process_detail(rule.detail, child, parent)
        return [
            _alert(
                chain,
                source=child,
                rule=rule,
                message=_format(rule.message, ctx),
                detail=detail or None,
            )
        ]

    return evaluate


def _compile_emit(rule: RuleDef) -> WindowRule:
    trigger = rule.triggers[0]

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        source = _trigger_event(chain, trigger)
        if source is None:
            return []
        label = ""
        for field_name in rule.label_fields:
            label = payload_str(source.payload.get(field_name))
            if label:
                break
        message = rule.message if not label else f"{rule.message}: {label}"
        detail: dict[str, Any] | None
        if rule.detail_mode == "payload":
            detail = dict(source.payload)
        else:
            detail = _process_detail(rule.detail, source, None) or None
        return [_alert(chain, source=source, rule=rule, message=message, detail=detail)]

    return evaluate


def _compile_pair_change(rule: RuleDef) -> WindowRule:
    event_type = rule.event_type or ""
    fields = rule.change_fields
    mode = rule.change_mode

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        if not _presence_ok(chain, rule.presence):
            return []
        events = [ev for ev in chain.events if ev.event_type == event_type]
        alerts: list[SecurityAlert] = []
        for prev, cur in _pairs(events):
            changed = {f: _field_changed(prev, cur, f) for f in fields}
            if mode == "all":
                ok = all(changed.values())
            else:
                ok = any(changed.values())
            if not ok:
                continue
            ctx: dict[str, Any] = {"presence": rule.presence or chain.latest_presence()}
            for f in fields:
                ctx[f"prev.{f}"] = get_string(prev, f)
                ctx[f"cur.{f}"] = get_string(cur, f)
                ctx[f"from_{f}"] = get_string(prev, f)
                ctx[f"to_{f}"] = get_string(cur, f)
            # Convenience aliases for single-field rules
            if len(fields) == 1:
                f = fields[0]
                ctx["from"] = get_string(prev, f)
                ctx["to"] = get_string(cur, f)
            if "public_ip" in fields:
                ctx["from_ip"] = get_string(prev, "public_ip")
                ctx["to_ip"] = get_string(cur, "public_ip")
            if "network_type" in fields:
                ctx["from_type"] = get_string(prev, "network_type")
                ctx["to_type"] = get_string(cur, "network_type")

            detail = _resolve_detail_templates(rule.detail, ctx) if rule.detail else {
                k: ctx[k]
                for k in ("from", "to", "from_ip", "to_ip", "from_type", "to_type", "presence")
                if k in ctx
            }
            # Presence-gated "any change" rules only need presence in detail.
            if rule.presence and not rule.detail and len(fields) > 1 and mode == "any":
                detail = {"presence": rule.presence}
            alerts.append(
                _alert(
                    chain,
                    source=cur,
                    rule=rule,
                    message=_format(rule.message, ctx),
                    detail=detail or None,
                )
            )
        if not alerts:
            return []
        if rule.match_policy == "first":
            return alerts[:1]
        return alerts[-1:]

    return evaluate


def _compile_window_unique(rule: RuleDef) -> WindowRule:
    assert rule.within is not None and rule.field and rule.min_unique and rule.event_type

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        if not _presence_ok(chain, rule.presence):
            return []
        events = chain.of_type(rule.event_type, rule.within)
        unique = list(
            dict.fromkeys(
                get_string(ev, rule.field) for ev in events if get_string(ev, rule.field)
            )
        )
        if len(unique) < rule.min_unique:
            return []
        source = events[-1]
        ctx = {
            "count": len(unique),
            "unique_count": len(unique),
            "ips": unique,
            "window_minutes": window_minutes(rule.within),
        }
        detail = {"ips": unique, "window_minutes": window_minutes(rule.within)}
        return [
            _alert(
                chain,
                source=source,
                rule=rule,
                message=_format(rule.message, ctx),
                detail=detail,
            )
        ]

    return evaluate


def _compile_window_changes(rule: RuleDef) -> WindowRule:
    assert rule.within is not None and rule.field and rule.min_changes and rule.event_type

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        if not _presence_ok(chain, rule.presence):
            return []
        events = chain.of_type(rule.event_type, rule.within)
        changes = sum(1 for prev, cur in _pairs(events) if _field_changed(prev, cur, rule.field))
        if changes < rule.min_changes:
            return []
        source = events[-1]
        ctx = {
            "changes": changes,
            "window_minutes": window_minutes(rule.within),
        }
        detail = {"changes": changes, "window_minutes": window_minutes(rule.within)}
        return [
            _alert(
                chain,
                source=source,
                rule=rule,
                message=_format(rule.message, ctx),
                detail=detail,
            )
        ]

    return evaluate


def _compile_window_count(rule: RuleDef) -> WindowRule:
    assert rule.within is not None and rule.min_count is not None

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        if not _presence_ok(chain, rule.presence):
            return []
        recent = chain.in_window(rule.within)
        if rule.count_type:
            count = sum(1 for ev in recent if ev.event_type == rule.count_type)
            source = chain.latest(rule.count_type) or (recent[-1] if recent else None)
        else:
            count = len(recent)
            source = recent[-1] if recent else None
        if source is None or count < rule.min_count:
            return []
        if rule.absent_type:
            if any(ev.event_type == rule.absent_type for ev in recent):
                return []
        ctx = {
            "count": count,
            "network_events": count,
            "window_minutes": window_minutes(rule.within),
        }
        detail_key = "network_events" if rule.count_type else "count"
        detail = {detail_key: count, "window_minutes": window_minutes(rule.within)}
        return [
            _alert(
                chain,
                source=source,
                rule=rule,
                message=_format(rule.message, ctx),
                detail=detail,
            )
        ]

    return evaluate


def _compile_metric_delta(rule: RuleDef) -> WindowRule:
    assert rule.within is not None and rule.field and rule.min_delta and rule.event_type

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        events = chain.of_type(rule.event_type, rule.within)
        for prev, cur in _pairs(events):
            old_val = get_int(prev, rule.field)
            new_val = get_int(cur, rule.field)
            delta = new_val - old_val
            if delta >= rule.min_delta:
                ctx = {"delta": delta, "from": old_val, "to": new_val}
                return [
                    _alert(
                        chain,
                        source=cur,
                        rule=rule,
                        message=_format(rule.message, ctx),
                        detail={"from": old_val, "to": new_val},
                    )
                ]
        return []

    return evaluate


def _compile_threshold(rule: RuleDef) -> WindowRule:
    assert rule.field is not None and rule.min_value is not None
    event_type = rule.event_type or rule.triggers[0]

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        if not _presence_ok(chain, rule.presence):
            return []
        latest = chain.latest(event_type)
        if latest is None:
            return []
        value = get_int(latest, rule.field)
        if value < rule.min_value:
            return []
        ctx = {rule.field: value, "value": value}
        detail = {rule.field: value}
        return [
            _alert(
                chain,
                source=latest,
                rule=rule,
                message=_format(rule.message, ctx),
                detail=detail,
            )
        ]

    return evaluate


def _compile_coverage(rule: RuleDef) -> WindowRule:
    assert rule.within is not None and rule.absent_type

    def evaluate(chain: DeviceChain) -> list[SecurityAlert]:
        if not _presence_ok(chain, rule.presence):
            return []
        recent = chain.in_window(rule.within)
        if rule.min_events is not None and len(recent) < rule.min_events:
            return []
        if not recent:
            return []

        if rule.require_type:
            matched = [ev for ev in recent if ev.event_type == rule.require_type]
            need = rule.require_min or 1
            if len(matched) < need:
                return []
            source = chain.latest(rule.require_type) or recent[-1]
        else:
            if not any(ev.event_type in rule.require_any for ev in recent):
                return []
            source = recent[-1]

        if any(ev.event_type == rule.absent_type for ev in recent):
            return []

        ctx = {"window_minutes": window_minutes(rule.within)}
        detail = {"window_minutes": window_minutes(rule.within)}
        return [
            _alert(
                chain,
                source=source,
                rule=rule,
                message=_format(rule.message, ctx),
                detail=detail,
            )
        ]

    return evaluate


def compile_rule(rule: RuleDef, sets: dict[str, frozenset[str]]) -> WindowRule:
    if rule.kind == KIND_PROCESS_MATCH:
        fn = _compile_process_match(rule, sets)
    elif rule.kind == KIND_EMIT:
        fn = _compile_emit(rule)
    elif rule.kind == KIND_PAIR_CHANGE:
        fn = _compile_pair_change(rule)
    elif rule.kind == KIND_WINDOW_UNIQUE:
        fn = _compile_window_unique(rule)
    elif rule.kind == KIND_WINDOW_CHANGES:
        fn = _compile_window_changes(rule)
    elif rule.kind == KIND_WINDOW_COUNT:
        fn = _compile_window_count(rule)
    elif rule.kind == KIND_METRIC_DELTA:
        fn = _compile_metric_delta(rule)
    elif rule.kind == KIND_THRESHOLD:
        fn = _compile_threshold(rule)
    elif rule.kind == KIND_COVERAGE:
        fn = _compile_coverage(rule)
    else:
        raise DslError(f"unsupported kind: {rule.kind}")

    fn.__name__ = f"dsl_{rule.id}"
    fn.__doc__ = f"DSL rule {rule.id} ({rule.kind})"
    return fn


def compile_rule_file(rule_file: RuleFile) -> list[tuple[RuleDef, WindowRule, object]]:
    from rules.dsl.gates import build_gate

    compiled: list[tuple[RuleDef, WindowRule, object]] = []
    for rule in rule_file.rules:
        if rule.child:
            for op in rule.child.ops:
                if op.set_name and op.set_name not in rule_file.sets:
                    raise DslError(f"rule {rule.id}: missing set {op.set_name}")
        if rule.parent:
            for op in rule.parent.ops:
                if op.set_name and op.set_name not in rule_file.sets:
                    raise DslError(f"rule {rule.id}: missing set {op.set_name}")
        gate = build_gate(rule, rule_file.sets)
        compiled.append((rule, compile_rule(rule, rule_file.sets), gate))
    return compiled
