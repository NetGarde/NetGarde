"""Orchestrate Rule → Behavioral → ThreatIntel → score fusion."""

from __future__ import annotations

from typing import Any

from rules.alerts import SecurityAlert
from rules.metrics import METRICS
from rules.state import StateStore

from pipeline.baseline_store import BaselineStore
from pipeline.behavioral import BehavioralEngine
from pipeline import rule_engine
from pipeline import threat_intel
from pipeline.score import finding_to_alert, fuse


class Pipeline:
    def __init__(
        self,
        store: StateStore | None = None,
        baseline: BaselineStore | None = None,
        behavioral: BehavioralEngine | None = None,
    ) -> None:
        self.store = store or StateStore()
        self.baseline = baseline or BaselineStore()
        self.behavioral = behavioral or BehavioralEngine(self.baseline)

    def process_event(self, event: dict[str, Any]) -> SecurityAlert | None:
        rule_hits = rule_engine.evaluate(event, self.store)
        beh_hits, kept_rule = self.behavioral.evaluate(event, rule_hits, self.store)

        device_id = str(event.get("device_id") or "").strip()
        chain = self.store.get_chain(device_id) if device_id else None
        ti_hits = threat_intel.evaluate(event, chain)

        METRICS.record_pipeline(
            hits_rule=len(kept_rule),
            hits_behavioral=len(beh_hits),
            hits_threat_intel=len(ti_hits),
        )

        finding = fuse(kept_rule + beh_hits + ti_hits)
        if finding is None:
            return None
        METRICS.record_scored()
        return finding_to_alert(finding)


def process_event(
    event: dict[str, Any],
    *,
    store: StateStore,
    baseline: BaselineStore | None = None,
    behavioral: BehavioralEngine | None = None,
) -> SecurityAlert | None:
    """One-shot helper used by tests; production uses Pipeline instance."""
    pipe = Pipeline(store=store, baseline=baseline, behavioral=behavioral)
    return pipe.process_event(event)
