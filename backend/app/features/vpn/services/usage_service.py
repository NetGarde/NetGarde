from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.features.alerts.repositories.alert_repository import AlertRepository
from app.features.vpn.repositories.device_usage_repository import DeviceUsageRepository
from app.features.vpn.schemas.usage import UsageReportRequest, UsageReportResponse
from app.features.vpn.schemas.usage_history import UsageHistoryResponse
from app.features.vpn.schemas.usage_live import DeviceUsageLiveItem, DeviceUsageLiveResponse
from app.features.vpn.services import usage_redis_store
from app.features.vpn.services.usage_broadcast import broadcast_usage_update
from app.shared.config import settings
from app.shared.logging_context import structured_extra
from app.shared.redis_client import redis_available
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

MIB = 1024 * 1024


class UsageService:
    def __init__(self, db: Session):
        self.db = db
        self.usage_repo = DeviceUsageRepository(db)
        self.alert_repo = AlertRepository(db)

    def report_usage(self, payload: UsageReportRequest) -> UsageReportResponse:
        now = datetime.now(timezone.utc)
        total_delta = payload.delta_rx_bytes + payload.delta_tx_bytes
        rate_mib_per_sec = (total_delta / MIB) / payload.interval_sec

        record_result = None
        if redis_available():
            try:
                record_result = usage_redis_store.record_sample(payload)
            except Exception as exc:
                logger.warning(
                    "Redis usage record failed",
                    extra=structured_extra("usage_redis_write_failed", error=str(exc)),
                )

        if settings.USAGE_PERSIST_SAMPLES:
            self.usage_repo.create_sample(
                device_external_id=payload.device_id.strip(),
                recorded_at=now,
                interval_sec=payload.interval_sec,
                rx_bytes=payload.rx_bytes,
                tx_bytes=payload.tx_bytes,
                delta_rx_bytes=payload.delta_rx_bytes,
                delta_tx_bytes=payload.delta_tx_bytes,
            )

        alert_created = False
        if rate_mib_per_sec >= settings.BANDWIDTH_ALERT_MIB_PER_SEC:
            self.alert_repo.create(
                timestamp=now,
                client_ip="",
                alert_type="bandwidth_spike",
                severity="high",
                domain=None,
                root_domain=None,
                message=(
                    f"Device {payload.device_id}: "
                    f"{rate_mib_per_sec:.1f} MiB/s "
                    f"(down {payload.delta_rx_bytes / MIB:.1f} MiB, "
                    f"up {payload.delta_tx_bytes / MIB:.1f} MiB "
                    f"in {payload.interval_sec:.0f}s)"
                ),
            )
            alert_created = True

        self.db.commit()

        if record_result is not None:
            live = DeviceUsageLiveResponse(
                items=usage_redis_store.enrich_live_items(self.db, record_result.live_items),
                max_age_sec=settings.USAGE_LIVE_MAX_AGE_SEC,
            )
            broadcast_usage_update(aggregate_point=record_result.aggregate_point, live=live)

        if alert_created:
            logger.warning(
                "Bandwidth spike detected",
                extra=structured_extra(
                    "bandwidth_spike",
                    device_id=payload.device_id,
                    rate_mib_per_sec=round(rate_mib_per_sec, 2),
                ),
            )
        return UsageReportResponse(
            stored=True,
            alert_created=alert_created,
            rate_mib_per_sec=round(rate_mib_per_sec, 2),
        )

    def list_live_bandwidth(self, *, max_age_sec: Optional[int] = None) -> DeviceUsageLiveResponse:
        if redis_available():
            try:
                return usage_redis_store.list_live(self.db, max_age_sec=max_age_sec)
            except Exception as exc:
                logger.warning(
                    "Redis usage live read failed",
                    extra=structured_extra("usage_redis_live_read_failed", error=str(exc)),
                )

        age = max_age_sec if max_age_sec is not None else settings.USAGE_LIVE_MAX_AGE_SEC
        age = max(5, min(age, 300))
        since = datetime.now(timezone.utc) - timedelta(seconds=age)
        rows = self.usage_repo.list_latest_with_device_since(since)
        pg_items = []
        for row in rows:
            sample = row.sample
            interval = float(sample.interval_sec) or 1.0
            rx_rate = (sample.delta_rx_bytes / MIB) / interval
            tx_rate = (sample.delta_tx_bytes / MIB) / interval
            pg_items.append(
                DeviceUsageLiveItem(
                    device_id=row.device_id,
                    vpn_device_id=sample.device_external_id,
                    client_ip=row.client_ip,
                    recorded_at=sample.recorded_at,
                    interval_sec=interval,
                    rx_bytes=sample.rx_bytes,
                    tx_bytes=sample.tx_bytes,
                    delta_rx_bytes=sample.delta_rx_bytes,
                    delta_tx_bytes=sample.delta_tx_bytes,
                    rx_mib_per_sec=round(rx_rate, 3),
                    tx_mib_per_sec=round(tx_rate, 3),
                    total_mib_per_sec=round(rx_rate + tx_rate, 3),
                )
            )
        return DeviceUsageLiveResponse(items=pg_items, max_age_sec=age)

    def list_usage_history(self, *, minutes: Optional[int] = None) -> UsageHistoryResponse:
        if redis_available():
            try:
                return usage_redis_store.list_history(minutes=minutes)
            except Exception as exc:
                logger.warning(
                    "Redis usage history read failed",
                    extra=structured_extra("usage_redis_history_read_failed", error=str(exc)),
                )
        return UsageHistoryResponse(points=[], minutes=minutes or settings.USAGE_HISTORY_MINUTES)
