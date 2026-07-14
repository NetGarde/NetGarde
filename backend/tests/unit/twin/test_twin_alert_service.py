from datetime import datetime, timezone

from app.features.twin.services.twin_alert_service import TwinAlertService
from app.features.twin.schemas.twin_alert import TwinAlertCreate


def test_twin_alert_service_ingest_and_list(db_session):
    service = TwinAlertService(db_session)
    ts = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)
    created = service.ingest(
        [
            TwinAlertCreate(
                timestamp=ts,
                device_id="dev_unit",
                alert_type="network_type_change",
                severity="medium",
                message="wifi -> ethernet",
            ),
            TwinAlertCreate(
                timestamp=ts,
                device_id="dev_unit",
                alert_type="temp_path_execution",
                severity="high",
                message="Process started from /tmp/x",
            ),
        ]
    )
    assert created == 2
    result = service.list_alerts(device_id="dev_unit")
    assert result.total == 2
    high = service.list_alerts(device_id="dev_unit", severity="high")
    assert high.total == 1
    assert high.items[0].alert_type == "temp_path_execution"
    assert high.items[0].device_id == "dev_unit"
