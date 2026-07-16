import hashlib
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.twin.repositories.security_alert_repository import SecurityAlertRepository
from app.features.twin.schemas.security_alert import (
    SecurityAlertCreate,
    SecurityAlertListResponse,
    SecurityAlertResponse,
)
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


def _fingerprint(item: SecurityAlertCreate) -> str:
    """Stable identity for an alert so re-evaluation / replay does not duplicate rows."""
    if item.fingerprint:
        return item.fingerprint
    anchor = item.event_id or item.timestamp.isoformat()
    raw = f"{item.device_id}|{item.alert_type}|{anchor}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class SecurityAlertService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SecurityAlertRepository(db)

    def ingest(self, alerts: list[SecurityAlertCreate]) -> int:
        created = 0
        skipped = 0
        seen_in_batch: set[str] = set()
        for item in alerts:
            fingerprint = _fingerprint(item)
            if fingerprint in seen_in_batch or self.repo.exists_fingerprint(fingerprint):
                skipped += 1
                continue
            try:
                self.repo.create(
                    timestamp=item.timestamp,
                    device_id=item.device_id,
                    event_id=item.event_id,
                    event_type=item.event_type,
                    alert_type=item.alert_type,
                    severity=item.severity,
                    message=item.message,
                    detail=item.detail,
                    fingerprint=fingerprint,
                )
                self.db.commit()
            except IntegrityError:
                # Concurrent ingest inserted the same fingerprint first.
                self.db.rollback()
                skipped += 1
                continue
            seen_in_batch.add(fingerprint)
            created += 1
        if created or skipped:
            logger.warning(
                "Security alerts ingested",
                extra=structured_extra(
                    "security_alerts_ingested", count=created, skipped=skipped
                ),
            )
        return created

    def list_alerts(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        alert_type: Optional[str] = None,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> SecurityAlertListResponse:
        items, total = self.repo.get_recent(
            page=page,
            page_size=page_size,
            alert_type=alert_type,
            device_id=device_id,
            severity=severity,
        )
        return SecurityAlertListResponse(
            items=[SecurityAlertResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size if page_size else 0,
        )
