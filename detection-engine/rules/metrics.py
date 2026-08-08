"""Lightweight in-process counters for detection evaluation hot path."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class EvalSnapshot:
    events: int
    rules_selected: int
    rules_gated: int
    rules_run: int
    alerts: int
    total_eval_ns: int
    hits_rule: int = 0
    hits_behavioral: int = 0
    hits_threat_intel: int = 0
    hits_ai_activity: int = 0
    scored_events: int = 0

    @property
    def avg_eval_ms(self) -> float:
        if self.events <= 0:
            return 0.0
        return (self.total_eval_ns / self.events) / 1_000_000.0


class EvalMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events = 0
        self.rules_selected = 0
        self.rules_gated = 0
        self.rules_run = 0
        self.alerts = 0
        self.total_eval_ns = 0
        self.hits_rule = 0
        self.hits_behavioral = 0
        self.hits_threat_intel = 0
        self.hits_ai_activity = 0
        self.scored_events = 0

    def record_event(
        self,
        *,
        selected: int,
        gated: int,
        ran: int,
        alerts: int,
        elapsed_ns: int,
    ) -> None:
        with self._lock:
            self.events += 1
            self.rules_selected += selected
            self.rules_gated += gated
            self.rules_run += ran
            self.alerts += alerts
            self.total_eval_ns += max(0, elapsed_ns)

    def record_pipeline(
        self,
        *,
        hits_rule: int,
        hits_behavioral: int,
        hits_threat_intel: int,
        hits_ai_activity: int = 0,
    ) -> None:
        with self._lock:
            self.hits_rule += max(0, hits_rule)
            self.hits_behavioral += max(0, hits_behavioral)
            self.hits_threat_intel += max(0, hits_threat_intel)
            self.hits_ai_activity += max(0, hits_ai_activity)

    def record_scored(self) -> None:
        with self._lock:
            self.scored_events += 1

    def snapshot(self) -> EvalSnapshot:
        with self._lock:
            return EvalSnapshot(
                events=self.events,
                rules_selected=self.rules_selected,
                rules_gated=self.rules_gated,
                rules_run=self.rules_run,
                alerts=self.alerts,
                total_eval_ns=self.total_eval_ns,
                hits_rule=self.hits_rule,
                hits_behavioral=self.hits_behavioral,
                hits_threat_intel=self.hits_threat_intel,
                hits_ai_activity=self.hits_ai_activity,
                scored_events=self.scored_events,
            )

    def reset(self) -> None:
        with self._lock:
            self.events = 0
            self.rules_selected = 0
            self.rules_gated = 0
            self.rules_run = 0
            self.alerts = 0
            self.total_eval_ns = 0
            self.hits_rule = 0
            self.hits_behavioral = 0
            self.hits_threat_intel = 0
            self.hits_ai_activity = 0
            self.scored_events = 0


METRICS = EvalMetrics()


class Timer:
    __slots__ = ("_start",)

    def __init__(self) -> None:
        self._start = time.perf_counter_ns()

    def elapsed_ns(self) -> int:
        return time.perf_counter_ns() - self._start
