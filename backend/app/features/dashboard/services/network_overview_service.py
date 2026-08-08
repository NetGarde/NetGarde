from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.features.dashboard.schemas.network_overview import NetworkOverviewRead, NetworkOverviewStats
from app.features.dashboard.services import network_overview_cache
from app.features.dashboard.services.overview_templates import build_network_overview_bullets
from app.features.twin.models.security_alert import SecurityAlert
from app.features.twin.services import trusttwin_store
from app.shared.config import settings
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

OverviewSource = Literal["template", "llm"]


class NetworkOverviewService:
    def __init__(self, db: Session):
        self.db = db

    def build_overview(self, *, period_minutes: int = 60, refresh: bool = False) -> NetworkOverviewRead:
        period = max(5, min(period_minutes, 24 * 60))

        if not refresh:
            cached = network_overview_cache.get_cached_overview(period)
            if cached is not None:
                return cached

        now = datetime.now(timezone.utc)
        snapshot = self._build_snapshot(period=period, now=now)
        bullets, summary, source, llm_model, llm_error = self._resolve_review(snapshot)

        stats = NetworkOverviewStats(
            reporting_clients=int(snapshot["live"]["reporting"]),
            live_total_mib_per_sec=0.0,
            peak_mib_per_sec=0.0,
            alerts_total=int(snapshot["alerts"]["total"]),
        )

        overview = NetworkOverviewRead(
            generated_at=now,
            period_minutes=period,
            bullets=bullets,
            summary=summary,
            stats=stats,
            source=source,
            llm_model=llm_model,
            review_mode=settings.NETWORK_REVIEW_MODE.strip().lower() or "template",
            llm_error=llm_error,
        )
        mode = overview.review_mode
        if source == "llm" or mode == "template":
            network_overview_cache.set_cached_overview(overview, period)
        return overview

    def _build_snapshot(self, *, period: int, now: datetime) -> dict[str, Any]:
        cutoff = now - timedelta(minutes=period)
        reporting = 0
        for row in trusttwin_store.list_latest():
            if row.last_seen_at and row.last_seen_at >= cutoff:
                reporting += 1

        alert_rows = (
            self.db.query(SecurityAlert.alert_type, func.count(SecurityAlert.id))
            .filter(SecurityAlert.timestamp >= cutoff)
            .group_by(SecurityAlert.alert_type)
            .all()
        )
        alerts_by_type = {alert_type: int(count) for alert_type, count in alert_rows}
        alerts_total = sum(alerts_by_type.values())

        return {
            "period_minutes": period,
            "live": {"reporting": reporting, "total_mib_per_sec": 0.0},
            "history": {"peak_mib_per_sec": 0.0},
            "alerts": {"total": alerts_total, "by_type": alerts_by_type},
        }

    def _resolve_review(
        self, snapshot: dict[str, Any]
    ) -> tuple[list[str], Optional[str], OverviewSource, Optional[str], Optional[str]]:
        mode = settings.NETWORK_REVIEW_MODE.strip().lower()
        if mode == "template":
            return build_network_overview_bullets(snapshot), None, "template", None, None

        llm_model: Optional[str] = None
        llm_error: Optional[str] = None
        try:
            if mode == "openai":
                from app.features.dashboard.services import openai_llm_client

                llm_model = settings.OPENAI_MODEL
                summary = openai_llm_client.summarize_network_review(snapshot)
                return [], summary, "llm", llm_model, None
            if mode == "ollama":
                from app.features.dashboard.services import ollama_llm_client

                llm_model = settings.OLLAMA_MODEL
                summary = ollama_llm_client.summarize_network_review(snapshot)
                return [], summary, "llm", llm_model, None
            logger.warning(
                "Unknown network review mode",
                extra=structured_extra("network_review_unknown_mode", mode=mode),
            )
            llm_error = f"Unknown NETWORK_REVIEW_MODE={mode}"
        except Exception as exc:
            llm_error = str(exc)
            logger.warning(
                "LLM network review failed, using template fallback",
                extra=structured_extra("network_review_llm_failed", error=str(exc)),
            )

        return build_network_overview_bullets(snapshot), None, "template", None, llm_error
