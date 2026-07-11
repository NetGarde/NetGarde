from rules.engine import evaluate_event
from rules.state import StateStore


def _network_event(device_id: str, network_type: str, public_ip: str, ts: str = "2026-07-11T12:00:00Z"):
    return {
        "event_id": "evt_1",
        "device_id": device_id,
        "type": "network_summary",
        "ts": ts,
        "payload": {"network_type": network_type, "public_ip": public_ip},
    }


def _action_event(device_id: str, presence: str):
    return {
        "device_id": device_id,
        "type": "action_summary",
        "ts": "2026-07-11T12:00:00Z",
        "payload": {"presence": presence},
    }


def test_network_type_change_alert():
    store = StateStore()
    device = "dev_test"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(_network_event(device, "ethernet", "1.1.1.1", "2026-07-11T12:01:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "network_type_change" in types


def test_new_public_ip_alert():
    store = StateStore()
    device = "dev_test"
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(_network_event(device, "wifi", "2.2.2.2", "2026-07-11T12:01:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "new_public_ip" in types


def test_network_change_while_active():
    store = StateStore()
    device = "dev_test"
    evaluate_event(_action_event(device, "active"), store)
    evaluate_event(_network_event(device, "wifi", "1.1.1.1"), store)
    alerts = evaluate_event(_network_event(device, "ethernet", "1.1.1.1", "2026-07-11T12:02:00Z"), store)
    types = {a.alert_type for a in alerts}
    assert "network_change_while_active" in types


def test_first_network_event_no_alerts():
    store = StateStore()
    alerts = evaluate_event(_network_event("dev_new", "wifi", "1.1.1.1"), store)
    assert alerts == []
