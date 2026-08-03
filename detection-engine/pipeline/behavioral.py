"""Behavioral engine: in-memory novelty + baseline suppress."""

from __future__ import annotations

import os
import time
from typing import Any

from log_config import setup_logging, structured_extra
from rules.alerts import SecurityAlert
from rules.behavior_key import behavior_from_alert
from rules.constants import TYPE_PROCESS_START
from rules.engine import with_alert_context
from rules.process_profile import (
    KIND_PROCESS_COMM,
    novel_process_alert,
    profile_keys_from_event,
)
from rules.state import StateStore

from pipeline.baseline_store import BaselineStore
from pipeline.rule_engine import alert_to_hit
from pipeline.types import ENGINE_BEHAVIORAL, ENGINE_RULE, EngineHit

LOG = setup_logging(service=os.getenv("LOG_SERVICE", "detection-engine"), logger_name=__name__)

_PROFILE_DEBOUNCE_SECONDS = 5 * 60
_PROFILE_DEBOUNCE_MAX = 20000


def _env_bool(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in ("0", "false", "no", "off")


class BehavioralEngine:
    def __init__(self, baseline: BaselineStore | None = None) -> None:
        self.baseline = baseline or BaselineStore()
        self._profile_observe_seen: dict[str, float] = {}
        self.enabled = _env_bool("TRUSTEDGE_BEHAVIOR_BASELINE", "1")

    def clear_debounce(self) -> None:
        self._profile_observe_seen.clear()

    def evaluate(
        self,
        event: dict[str, Any],
        rule_hits: list[EngineHit],
        store: StateStore,
    ) -> tuple[list[EngineHit], list[EngineHit]]:
        """Return (behavioral_hits, kept_rule_hits)."""
        if not self.enabled:
            return [], list(rule_hits)

        behavioral_hits = self._collect_novel_hits(event, store)
        kept_rule = self._filter_suppressed(rule_hits)
        return behavioral_hits, kept_rule

    def _prune_debounce(self, now: float) -> None:
        if len(self._profile_observe_seen) < _PROFILE_DEBOUNCE_MAX:
            expired = [
                key
                for key, ts in self._profile_observe_seen.items()
                if now - ts > _PROFILE_DEBOUNCE_SECONDS
            ]
        else:
            expired = list(self._profile_observe_seen.keys())
        for key in expired:
            self._profile_observe_seen.pop(key, None)

    def _debounce_allow(self, device_id: str, kind: str, key: str, now: float) -> bool:
        token = f"{device_id}|{kind}|{key}"
        last = self._profile_observe_seen.get(token)
        if last is not None and now - last < _PROFILE_DEBOUNCE_SECONDS:
            return False
        self._profile_observe_seen[token] = now
        return True

    def _collect_novel_hits(
        self,
        event: dict[str, Any],
        store: StateStore,
    ) -> list[EngineHit]:
        if str(event.get("type") or "").strip() != TYPE_PROCESS_START:
            return []

        device_id = str(event.get("device_id") or "").strip()
        if not device_id:
            return []

        now = time.time()
        self._prune_debounce(now)
        novel: list[EngineHit] = []

        for kind, key, meta in profile_keys_from_event(event, store):
            if not self._debounce_allow(device_id, kind, key, now):
                continue
            decision = self.baseline.observe(device_id, kind, key, now=now)
            if kind != KIND_PROCESS_COMM:
                continue
            if decision.profile_warm and not decision.established:
                alert = novel_process_alert(event, behavior_key=key, meta=meta)
                if alert is None:
                    continue
                chain = store.get_chain(device_id)
                if chain is not None:
                    alert = with_alert_context(chain, alert)
                novel.append(alert_to_hit(alert, engine=ENGINE_BEHAVIORAL))
                LOG.info(
                    "novel process detected",
                    extra=structured_extra(
                        "novel_process",
                        device_id=device_id,
                        behavior_key=key,
                        count=decision.count,
                    ),
                )
        return novel

    def _filter_suppressed(self, rule_hits: list[EngineHit]) -> list[EngineHit]:
        kept: list[EngineHit] = []
        for hit in rule_hits:
            if hit.engine != ENGINE_RULE:
                kept.append(hit)
                continue
            # Reconstruct a minimal alert for behavior_from_alert.
            alert = SecurityAlert(
                timestamp=hit.timestamp,
                device_id=hit.device_id,
                alert_type=hit.alert_type,
                severity=hit.severity,
                message=hit.message,
                event_id=hit.event_id,
                event_type=hit.event_type,
                detail=hit.detail,
            )
            key_info = behavior_from_alert(alert)
            if key_info is None:
                kept.append(hit)
                continue
            kind, key, _meta = key_info
            decision = self.baseline.observe(hit.device_id, kind, key)
            if decision.action == "suppress":
                LOG.info(
                    "alert suppressed by behavior baseline",
                    extra=structured_extra(
                        "alert_suppressed_baseline",
                        alert_type=hit.alert_type,
                        device_id=hit.device_id,
                        behavior_key=key,
                        count=decision.count,
                    ),
                )
                continue
            kept.append(hit)
        return kept
