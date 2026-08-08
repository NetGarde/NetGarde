"""Field accessors for process and generic payload fields."""

from __future__ import annotations

from typing import Any

from rules.chain import ChainEvent, payload_int, payload_str

# Process fields with special normalization (basename / lowercase).
PROCESS_STRING_FIELDS = frozenset({"comm", "executable", "cmdline"})
PROCESS_INT_FIELDS = frozenset({"pid", "ppid"})
KNOWN_PROCESS_FIELDS = PROCESS_STRING_FIELDS | PROCESS_INT_FIELDS


def basename(value: str) -> str:
    text = (value or "").strip().lower()
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return text


def field_comm(ev: ChainEvent) -> str:
    raw = payload_str(ev.payload.get("comm")) or payload_str(ev.payload.get("executable"))
    return basename(raw)


def field_executable(ev: ChainEvent) -> str:
    return payload_str(ev.payload.get("executable") or ev.payload.get("comm")).lower()


def field_cmdline(ev: ChainEvent) -> str:
    return payload_str(ev.payload.get("cmdline"))


def get_string(ev: ChainEvent, name: str) -> str:
    if name == "comm":
        return field_comm(ev)
    if name == "executable":
        return field_executable(ev)
    if name == "cmdline":
        return field_cmdline(ev)
    return payload_str(ev.payload.get(name))


def get_int(ev: ChainEvent, name: str) -> int:
    return payload_int(ev.payload.get(name))


def get_value(ev: ChainEvent, name: str) -> Any:
    if name in PROCESS_INT_FIELDS or name.endswith("_count") or name.endswith("_connections"):
        return get_int(ev, name)
    if name in {"pid", "ppid"}:
        return get_int(ev, name)
    return get_string(ev, name)


# Back-compat alias used by process matcher validation.
KNOWN_FIELDS = KNOWN_PROCESS_FIELDS
