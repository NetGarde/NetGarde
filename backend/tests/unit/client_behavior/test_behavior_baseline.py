from datetime import datetime, timedelta, timezone

from app.features.client_behavior.models.client_behavior_rollup import ClientBehaviorRollup
from app.features.client_behavior.services.behavior_baseline_service import BehaviorBaselineService
from tests.helpers.factories import create_device


def _seed_rollups(db_session, device_id: int, hours: int, queries_per_hour: int = 10):
    now = datetime.now(timezone.utc)
    for i in range(hours):
        window = (now - timedelta(hours=hours - i)).replace(minute=0, second=0, microsecond=0)
        db_session.add(
            ClientBehaviorRollup(
                device_id=device_id,
                window_start=window,
                query_count=queries_per_hour,
                unique_roots=5,
                new_roots=1,
                hour_utc=window.hour,
            )
        )
    db_session.commit()


def test_baseline_not_ready_with_few_rollups(db_session):
    device = create_device(
        db_session,
        external_id="dev-baseline-1",
        mac_address="aa:bb:cc:dd:ee:01",
    )

    _seed_rollups(db_session, device.id, hours=10, queries_per_hour=5)
    ready = BehaviorBaselineService(db_session).recompute_device(device.id)
    assert ready is False


def test_baseline_ready_with_enough_data(db_session):
    device = create_device(
        db_session,
        external_id="dev-baseline-2",
        mac_address="aa:bb:cc:dd:ee:02",
    )

    _seed_rollups(db_session, device.id, hours=80, queries_per_hour=10)
    ready = BehaviorBaselineService(db_session).recompute_device(device.id)
    assert ready is True
