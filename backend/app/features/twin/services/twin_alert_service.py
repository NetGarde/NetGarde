from typing import Optional

from sqlalchemy.orm import Session

from app.features.twin.repositories.twin_alert_repository import TwinAlertRepository
from app.features.twin.schemas.twin_alert import (
    TwinAlertCreate,
    TwinAlertListResponse,
    TwinAlertResponse,
)
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class TwinAlertService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TwinAlertRepository(db)

    def ingest(self, alerts: list[TwinAlertCreate]) -> int:
        created = 0
        for item in alerts:
            self.repo.create(
                timestamp=item.timestamp,
                device_id=item.device_id,
                event_id=item.event_id,
                event_type=item.event_type,
                alert_type=item.alert_type,
                severity=item.severity,
                message=item.message,
                detail=item.detail,
            )
            created += 1
        if created:
            self.db.commit()
            logger.warning(
                "Security alerts ingested",
                extra=structured_extra("twin_alerts_ingested", count=created),
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
    ) -> TwinAlertListResponse:
        items, total = self.repo.get_recent(
            page=page,
            page_size=page_size,
            alert_type=alert_type,
            device_id=device_id,
            severity=severity,
        )
        return TwinAlertListResponse(
            items=[TwinAlertResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size if page_size else 0,
        )
