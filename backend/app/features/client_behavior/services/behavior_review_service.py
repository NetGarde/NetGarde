from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from sqlalchemy.orm import Session

from app.features.client_behavior.repositories.behavior_profile_repository import BehaviorProfileRepository
from app.features.client_behavior.repositories.behavior_rollup_repository import BehaviorRollupRepository
from app.features.client_behavior.repositories.client_blocked_domain_repository import ClientBlockedDomainRepository
from app.features.client_behavior.schemas.behavior import BehaviorReviewRead
from app.features.client_behavior.services import behavior_review_cache
from app.features.client_behavior.services.behavior_review_templates import (
    build_device_review_template,
    explain_alert_message,
)
from app.features.devices.repositories.device_repository import DeviceRepository
from app.features.alerts.models.alert import Alert
from app.features.policy.repositories.policy_repository import PolicyRepository
from app.features.policy.sensitivity import alert_threshold_for_sensitivity
from app.shared.config import settings
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

ReviewSource = Literal["template", "llm"]


class BehaviorReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.device_repo = DeviceRepository(db)
        self.profile_repo = BehaviorProfileRepository(db)
        self.rollup_repo = BehaviorRollupRepository(db)
        self.block_repo = ClientBlockedDomainRepository(db)
        self.policy_repo = PolicyRepository(db)

    def get_device_review(self, device_id: int, *, refresh: bool = False) -> BehaviorReviewRead:
        device = self.device_repo.get_by_id(device_id)
        if not device:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        if not refresh:
            cached = behavior_review_cache.get_cached_review(device_id)
            if cached is not None:
                return cached

        now = datetime.now(timezone.utc)
        snapshot = self._build_snapshot(device_id, device)
        summary, source, llm_model, llm_error = self._resolve_summary(snapshot)

        review = BehaviorReviewRead(
            device_id=device_id,
            generated_at=now,
            summary=summary,
            source=source,
            review_mode=settings.BEHAVIOR_REVIEW_MODE.strip().lower() or "template",
            llm_model=llm_model,
            llm_error=llm_error,
        )
        mode = review.review_mode
        if source == "llm" or mode == "template":
            behavior_review_cache.set_cached_review(review, device_id)
        return review

    def explain_alert_for_parent(
        self, *, message: Optional[str], domain: Optional[str] = None
    ) -> str:
        return explain_alert_message(message, domain=domain)

    def _build_snapshot(self, device_id: int, device) -> dict[str, Any]:
        profile = self.profile_repo.get_or_create(device_id)
        baseline = self.profile_repo.parse_baseline(profile)
        window_min = max(1, settings.BEHAVIOR_SCORE_WINDOW_MINUTES)
        since = datetime.now(timezone.utc) - timedelta(minutes=window_min)
        query_count, _, new_roots = self.rollup_repo.sum_recent_window(device_id, since)

        policy_profile = self._policy_profile_for_device(device)
        alert_threshold = alert_threshold_for_sensitivity(
            policy_profile.behavior_sensitivity if policy_profile else "medium"
        )

        recent_rows = (
            self.db.query(Alert)
            .filter(
                Alert.device_id == device_id,
                Alert.alert_type == "behavior_anomaly",
            )
            .order_by(Alert.timestamp.desc())
            .limit(5)
            .all()
        )
        recent_alerts = [
            {
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "severity": a.severity,
                "domain": a.domain,
                "message": a.message,
            }
            for a in recent_rows
        ]

        blocks = self.block_repo.list_active_for_device(device_id)
        lease = getattr(device, "ip_lease", None)
        lease_ip = lease.ip if lease is not None else None
        label = device.hostname or lease_ip or f"Device {device_id}"

        return {
            "device_id": device_id,
            "device_label": label,
            "profile_ready": bool(profile.profile_ready),
            "last_score": profile.last_score,
            "last_scored_at": profile.last_scored_at.isoformat() if profile.last_scored_at else None,
            "baseline": baseline,
            "alert_threshold": alert_threshold,
            "window": {
                "minutes": window_min,
                "query_count": query_count,
                "new_roots": new_roots,
            },
            "recent_alerts": recent_alerts,
            "active_block_count": len(blocks),
        }

    def _policy_profile_for_device(self, device):
        if device.policy_profile_id:
            profile = self.policy_repo.get_profile_by_id(device.policy_profile_id)
            if profile:
                return profile
        return self.policy_repo.get_default_profile()

    def _resolve_summary(
        self, snapshot: dict[str, Any]
    ) -> tuple[str, ReviewSource, Optional[str], Optional[str]]:
        mode = settings.BEHAVIOR_REVIEW_MODE.strip().lower()
        if mode == "template":
            return build_device_review_template(snapshot), "template", None, None

        llm_model: Optional[str] = None
        llm_error: Optional[str] = None
        try:
            if mode == "openai":
                from app.features.client_behavior.services.behavior_review_llm import (
                    summarize_behavior_review_openai,
                )

                llm_model = settings.OPENAI_MODEL
                return summarize_behavior_review_openai(snapshot), "llm", llm_model, None
            if mode == "ollama":
                from app.features.client_behavior.services.behavior_review_llm import (
                    summarize_behavior_review_ollama,
                )

                llm_model = settings.OLLAMA_MODEL
                return summarize_behavior_review_ollama(snapshot), "llm", llm_model, None
            llm_error = f"Unknown BEHAVIOR_REVIEW_MODE={mode}"
            logger.warning(
                "Unknown behavior review mode",
                extra=structured_extra("behavior_review_unknown_mode", mode=mode),
            )
        except Exception as exc:
            llm_error = str(exc)
            logger.warning(
                "LLM behavior review failed, using template fallback",
                extra=structured_extra("behavior_review_llm_failed", error=str(exc)),
            )

        return build_device_review_template(snapshot), "template", None, llm_error
