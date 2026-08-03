#!/usr/bin/env python3
"""TrustEdge Agent event consumer — evaluates rules and serves recent alerts over HTTP."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Any

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from api_client import observe_behavior, post_alerts
from http_api import serve_forever
from log_config import setup_logging, structured_extra
from recent_alerts import append as remember_alert
from rules.alerts import SecurityAlert
from rules.behavior_key import behavior_from_alert
from rules.constants import SEVERITY_HIGH, TYPE_PROCESS_START
from rules.engine import evaluate_event, with_alert_context
from rules.process_profile import (
    KIND_PROCESS_COMM,
    novel_process_alert,
    profile_keys_from_event,
)
from rules.state import StateStore

SERVICE = os.getenv("LOG_SERVICE", "detection-engine")
LOG = setup_logging(service=SERVICE, logger_name=__name__)
logging.getLogger("kafka").setLevel(logging.WARNING)

_shutdown = False
_state = StateStore()
# Fingerprints already posted this process lifetime, to avoid re-emitting the
# same alert while its source event stays inside the evaluation window.
_seen_fingerprints: dict[str, float] = {}
_SEEN_TTL_SECONDS = 30 * 60
_SEEN_MAX = 10000

# Debounce profile observes so frequent process_starts do not hammer the backend.
_profile_observe_seen: dict[str, float] = {}
_PROFILE_DEBOUNCE_SECONDS = 5 * 60
_PROFILE_DEBOUNCE_MAX = 20000


def _handle_signal(signum: int, _frame: Any) -> None:
    global _shutdown
    LOG.info("shutdown requested", extra=structured_extra("shutdown", signal=signum))
    _shutdown = True


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _brokers() -> list[str]:
    raw = _env("KAFKA_BROKERS", "redpanda:9092")
    return [b.strip() for b in raw.split(",") if b.strip()]


def _create_consumer() -> KafkaConsumer:
    topic = _env("KAFKA_TOPIC", "trustedge.agent.events")
    group_id = _env("KAFKA_GROUP_ID", "detection-engine")
    brokers = _brokers()
    LOG.info(
        "connecting to kafka",
        extra=structured_extra("kafka_connect", brokers=brokers, topic=topic, group_id=group_id),
    )
    return KafkaConsumer(
        topic,
        bootstrap_servers=brokers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=1000,
        value_deserializer=lambda v: v.decode("utf-8"),
    )


def _prune_seen(now: float) -> None:
    if len(_seen_fingerprints) < _SEEN_MAX:
        expired = [fp for fp, ts in _seen_fingerprints.items() if now - ts > _SEEN_TTL_SECONDS]
    else:
        expired = list(_seen_fingerprints.keys())
    for fp in expired:
        _seen_fingerprints.pop(fp, None)


def _mark_seen(fingerprint: str, now: float) -> bool:
    """Return True if this fingerprint is new (and record it); False if already seen."""
    if fingerprint in _seen_fingerprints:
        return False
    _seen_fingerprints[fingerprint] = now
    return True


def _prune_profile_debounce(now: float) -> None:
    if len(_profile_observe_seen) < _PROFILE_DEBOUNCE_MAX:
        expired = [
            key
            for key, ts in _profile_observe_seen.items()
            if now - ts > _PROFILE_DEBOUNCE_SECONDS
        ]
    else:
        expired = list(_profile_observe_seen.keys())
    for key in expired:
        _profile_observe_seen.pop(key, None)


def _profile_debounce_allow(device_id: str, kind: str, key: str, now: float) -> bool:
    """Return True if this profile key should be observed (not recently seen)."""
    token = f"{device_id}|{kind}|{key}"
    last = _profile_observe_seen.get(token)
    if last is not None and now - last < _PROFILE_DEBOUNCE_SECONDS:
        return False
    _profile_observe_seen[token] = now
    return True


def _post_alerts_to_backend() -> bool:
    return _env("TRUSTEDGE_POST_ALERTS_TO_BACKEND", "0").lower() in ("1", "true", "yes")


def _collect_profile_alerts(payload: dict[str, Any]) -> list[SecurityAlert]:
    """Learn process identities; optionally emit novel_process when profile is warm."""
    if str(payload.get("type") or "").strip() != TYPE_PROCESS_START:
        return []

    device_id = str(payload.get("device_id") or "").strip()
    if not device_id:
        return []

    now = time.time()
    _prune_profile_debounce(now)
    novel: list[SecurityAlert] = []

    for kind, key, meta in profile_keys_from_event(payload, _state):
        if not _profile_debounce_allow(device_id, kind, key, now):
            continue
        decision = observe_behavior(
            device_id=device_id,
            behavior_kind=kind,
            behavior_key=key,
            alert_type=None,
            meta=meta,
        )
        if decision is None:
            continue
        # Novelty is decided on process_comm only.
        if kind != KIND_PROCESS_COMM:
            continue
        established = bool(decision.get("established"))
        profile_warm = bool(decision.get("profile_warm"))
        if profile_warm and not established:
            alert = novel_process_alert(payload, behavior_key=key, meta=meta)
            if alert is not None:
                chain = _state.get_chain(device_id)
                novel.append(with_alert_context(chain, alert))
                LOG.info(
                    "novel process detected",
                    extra=structured_extra(
                        "novel_process",
                        device_id=device_id,
                        behavior_key=key,
                        count=decision.get("count"),
                    ),
                )
    return novel


def _filter_suppressed(alerts: list[SecurityAlert]) -> list[SecurityAlert]:
    kept: list[SecurityAlert] = []
    for alert in alerts:
        key_info = behavior_from_alert(alert)
        if key_info is None:
            kept.append(alert)
            continue
        kind, key, meta = key_info
        decision = observe_behavior(
            device_id=alert.device_id,
            behavior_kind=kind,
            behavior_key=key,
            alert_type=alert.alert_type,
            meta=meta,
        )
        if decision and str(decision.get("action") or "").lower() == "suppress":
            LOG.info(
                "alert suppressed by behavior baseline",
                extra=structured_extra(
                    "alert_suppressed_baseline",
                    alert_type=alert.alert_type,
                    device_id=alert.device_id,
                    behavior_key=key,
                    count=decision.get("count"),
                ),
            )
            continue
        kept.append(alert)
    return kept


def _emit_alerts(alerts: list[SecurityAlert]) -> None:
    if not alerts:
        return

    now = time.time()
    _prune_seen(now)
    fresh = [alert for alert in alerts if _mark_seen(alert.fingerprint(), now)]
    if not fresh:
        return

    api_alerts = []
    for alert in fresh:
        api = alert.to_api()
        remember_alert(api)
        api_alerts.append(api)
        LOG.warning(
            "security alert raised",
            extra=structured_extra(
                "alert_raised",
                alert_type=alert.alert_type,
                device_id=alert.device_id,
                severity=alert.severity,
            ),
        )
    # Optional Postgres ingest still stores high-severity only when enabled.
    if _post_alerts_to_backend():
        high = [a for a in api_alerts if (a.get("severity") or "").strip().lower() == SEVERITY_HIGH]
        if high:
            post_alerts(high)


def _process_event(raw: str) -> None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        LOG.warning("invalid event json", extra=structured_extra("agent_event_invalid", raw=raw[:500]))
        return

    LOG.info(
        "trustedge agent event received",
        extra=structured_extra(
            "agent_event",
            event_id=payload.get("event_id"),
            device_id=payload.get("device_id"),
            event_type=payload.get("type"),
            ts=payload.get("ts"),
        ),
    )

    # Record into chain + run typed rules first so parent lookup sees this event.
    alerts = evaluate_event(payload, _state)
    # Learn process profile identities (and maybe novel_process) on every process_start.
    alerts = list(alerts) + _collect_profile_alerts(payload)
    if not alerts:
        return

    kept = _filter_suppressed(alerts)
    _emit_alerts(kept)


def run() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    api_thread = threading.Thread(target=serve_forever, name="alert-api", daemon=True)
    api_thread.start()

    retries = 0
    consumer: KafkaConsumer | None = None
    while not _shutdown:
        if consumer is None:
            try:
                consumer = _create_consumer()
                retries = 0
                LOG.info("consumer ready", extra=structured_extra("consumer_ready"))
            except NoBrokersAvailable:
                retries += 1
                LOG.warning(
                    "kafka brokers unavailable",
                    extra=structured_extra("kafka_unavailable", retry=retries),
                )
                time.sleep(min(5 * retries, 30))
                continue
            except Exception as exc:
                LOG.exception("consumer init failed: %s", exc)
                return 1

        try:
            for message in consumer:
                if _shutdown:
                    break
                _process_event(message.value)
        except Exception as exc:
            LOG.exception("consumer loop error: %s", exc)
            try:
                consumer.close()
            except Exception:
                pass
            consumer = None

    if consumer is not None:
        consumer.close()
    LOG.info("consumer stopped", extra=structured_extra("consumer_stopped"))
    return 0


if __name__ == "__main__":
    sys.exit(run())
