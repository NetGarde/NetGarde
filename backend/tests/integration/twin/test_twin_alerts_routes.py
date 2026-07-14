from datetime import datetime, timezone


def test_ingest_and_list_twin_alerts(api_client, db_session):
    ts = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    ingest = api_client.post(
        "/twin/alerts/ingest",
        json=[
            {
                "timestamp": ts,
                "device_id": "dev_alert_test",
                "event_id": "evt_1",
                "event_type": "network_summary",
                "alert_type": "network_type_change",
                "severity": "medium",
                "message": "Network type changed from wifi to ethernet",
            }
        ],
    )
    assert ingest.status_code == 200
    assert ingest.json()["created"] == 1

    listed = api_client.get("/twin/alerts?device_id=dev_alert_test")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 1
    assert body["items"][0]["alert_type"] == "network_type_change"
    assert body["items"][0]["device_id"] == "dev_alert_test"


def test_ingest_accepts_legacy_trusttwin_device_id(api_client, db_session):
    ts = datetime(2026, 7, 11, 12, 30, 0, tzinfo=timezone.utc).isoformat()
    ingest = api_client.post(
        "/twin/alerts/ingest",
        json=[
            {
                "timestamp": ts,
                "trusttwin_device_id": "dev_legacy_alias",
                "alert_type": "temp_path_execution",
                "severity": "high",
                "message": "legacy field alias",
            }
        ],
    )
    assert ingest.status_code == 200
    assert ingest.json()["created"] == 1

    listed = api_client.get("/twin/alerts?device_id=dev_legacy_alias")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["device_id"] == "dev_legacy_alias"


def test_list_twin_alerts_filter_type(api_client, db_session):
    ts = datetime(2026, 7, 11, 13, 0, 0, tzinfo=timezone.utc).isoformat()
    api_client.post(
        "/twin/alerts/ingest",
        json=[
            {
                "timestamp": ts,
                "device_id": "dev_filter",
                "alert_type": "new_public_ip",
                "severity": "high",
                "message": "IP changed",
            }
        ],
    )
    response = api_client.get("/twin/alerts?alert_type=new_public_ip&device_id=dev_filter")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["alert_type"] == "new_public_ip" for item in items)
