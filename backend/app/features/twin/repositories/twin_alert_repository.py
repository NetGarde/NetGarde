from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.features.twin.models.twin_alert import TwinAlert


class TwinAlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        timestamp: datetime,
        device_id: str,
        alert_type: str,
        severity: str,
        event_id: Optional[str] = None,
        event_type: Optional[str] = None,
        message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> TwinAlert:
        alert = TwinAlert(
            timestamp=timestamp,
            device_id=device_id,
            event_id=event_id,
            event_type=event_type,
            alert_type=alert_type,
            severity=severity,
            message=message,
            detail=detail,
        )
        self.db.add(alert)
        self.db.flush()
        return alert

    def get_recent(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        alert_type: Optional[str] = None,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        days: int = 90,
    ) -> tuple[List[TwinAlert], int]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = self.db.query(TwinAlert).filter(TwinAlert.timestamp >= cutoff)
        if alert_type:
            query = query.filter(TwinAlert.alert_type == alert_type)
        if device_id:
            query = query.filter(TwinAlert.device_id == device_id)
        if severity:
            query = query.filter(TwinAlert.severity == severity)
        total = query.count()
        offset = (page - 1) * page_size
        items = (
            query.order_by(desc(TwinAlert.timestamp))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return items, total
