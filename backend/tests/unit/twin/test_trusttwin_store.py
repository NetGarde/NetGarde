import json
from datetime import datetime, timezone
from unittest.mock import patch

import fakeredis
import pytest

from app.features.twin.services import trusttwin_store


@pytest.fixture
def fake_redis():
    client = fakeredis.FakeRedis(decode_responses=True)
    with patch("app.features.twin.services.trusttwin_store.get_redis", return_value=client):
        with patch("app.features.twin.services.trusttwin_store.redis_available", return_value=True):
            yield client


def test_list_latest_parses_device_documents(fake_redis):
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    doc = {
        "device_id": "dev_abc",
        "last_seen_at": now.isoformat().replace("+00:00", "Z"),
        "client_details": {"hostname": "elad-mbp", "os": "darwin", "status": "online"},
        "network_summary": {"public_ip": "1.2.3.4", "established_count": 12},
        "action_summary": {
            "presence": "active",
            "focus": [
                {
                    "app_name": "Code",
                    "bundle_id": "com.microsoft.VSCode",
                    "duration_sec": 40,
                }
            ],
        },
    }
    fake_redis.sadd(trusttwin_store.DEVICES_KEY, "dev_abc")
    fake_redis.set(
        trusttwin_store.LATEST_KEY_FMT.format(device_id="dev_abc"),
        json.dumps(doc),
    )

    items = trusttwin_store.list_latest()
    assert len(items) == 1
    rec = items[0]
    assert rec.device_id == "dev_abc"
    assert rec.client_details["hostname"] == "elad-mbp"
    assert rec.network_summary["public_ip"] == "1.2.3.4"
    assert rec.action_summary["presence"] == "active"
    assert rec.last_seen_at == now


def test_app_slug_from_focus():
    assert (
        trusttwin_store.app_slug_from_focus({"bundle_id": "com.microsoft.VSCode"})
        == "com-microsoft-vscode"
    )
    assert trusttwin_store.app_slug_from_focus({"app_name": "Visual Studio Code"}) == (
        "visual-studio-code"
    )


def test_twin_device_node_id():
    assert trusttwin_store.twin_device_node_id("dev_x") == "device:twin:dev_x"
