from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.features.alerts.models.alert import Alert


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        timestamp: datetime,
        client_ip: str,
        alert_type: str,
        severity: str,
        domain: Optional[str] = None,
        root_domain: Optional[str] = None,
        message: Optional[str] = None,
        device_id: Optional[int] = None,
    ) -> Alert:
        alert = Alert(
            timestamp=timestamp,
            client_ip=client_ip,
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            domain=domain,
            root_domain=root_domain,
            message=message,
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
        client_ip: Optional[str] = None,
        days: int = 90,
    ) -> tuple[List[Alert], int]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = self.db.query(Alert).filter(Alert.timestamp >= cutoff)
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)
        if client_ip:
            query = query.filter(Alert.client_ip == client_ip)
        total = query.count()
        offset = (page - 1) * page_size
        items = (
            query.order_by(desc(Alert.timestamp))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return items, total

    def delete_older_than(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        count = self.db.query(Alert).filter(Alert.timestamp < cutoff).delete()
        self.db.commit()
        return count
