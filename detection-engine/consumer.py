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

from api_client import post_alerts
from http_api import serve_forever
from log_config import setup_logging, structured_extra
from recent_alerts import append as remember_alert
from rules.engine import evaluate_event
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


def _post_alerts_to_backend() -> bool:
    return _env("TRUSTEDGE_POST_ALERTS_TO_BACKEND", "0").lower() in ("1", "true", "yes")


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

    alerts = evaluate_event(payload, _state)
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
        high = [a for a in api_alerts if (a.get("severity") or "").strip().lower() == "high"]
        if high:
            post_alerts(high)


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
