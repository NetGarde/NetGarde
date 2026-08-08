import json
from unittest.mock import patch

import fakeredis
import pytest

from app.features.twin.services import trusttwin_store
from app.features.twin.services.connected_agent_service import ConnectedAgentService


@pytest.fixture
def fake_redis():
    client = fakeredis.FakeRedis(decode_responses=True)
    with patch("app.features.twin.services.trusttwin_store.get_redis", return_value=client):
        with patch("app.features.twin.services.trusttwin_store.redis_available", return_value=True):
            yield client


def test_list_ai_software_sorted_from_twin(fake_redis):
    doc = {
        "device_id": "dev_ai",
        "known_ai_apps": {
            "cursor:/applications/cursor.app": {
                "id": "cursor:/applications/cursor.app",
                "product_id": "cursor",
                "product_name": "Cursor",
                "vendor": "Cursor",
                "category": "code_editor",
                "confidence": "VERIFIED",
                "installed": True,
                "running": True,
                "path": "/Applications/Cursor.app",
                "version": "1.2.3",
                "bundle_id": "com.todesktop.230313mzl4w4u92",
                "signature_valid": True,
            },
            "claude:/applications/claude.app": {
                "id": "claude:/applications/claude.app",
                "product_id": "claude",
                "product_name": "Claude",
                "vendor": "Anthropic",
                "category": "chat_client",
                "confidence": "VERIFIED",
                "installed": True,
                "running": False,
                "path": "/Applications/Claude.app",
                "version": "0.9.0",
            },
            "cursor:cursor": {
                "id": "cursor:cursor",
                "product_id": "cursor",
                "product_name": "Cursor",
                "vendor": "Cursor",
                "category": "code_editor",
                "confidence": "LOW",
                "installed": False,
                "running": True,
                "path": "Cursor",
            },
        },
    }
    fake_redis.set(
        trusttwin_store.LATEST_KEY_FMT.format(device_id="dev_ai"),
        json.dumps(doc),
    )

    result = ConnectedAgentService().list_ai_software("dev_ai")
    assert result.device_id == "dev_ai"
    assert result.total == 2
    assert [item.product_name for item in result.items] == ["Claude", "Cursor"]
    assert result.items[1].running is True
    assert result.items[1].version == "1.2.3"
    assert all(item.installed for item in result.items)


def test_list_ai_software_includes_evidence(fake_redis):
    doc = {
        "device_id": "dev_ai",
        "known_ai_apps": {
            "cursor:/applications/cursor.app": {
                "id": "cursor:/applications/cursor.app",
                "product_id": "cursor",
                "product_name": "Cursor",
                "installed": True,
                "running": True,
                "confidence": "LOW",
                "confidence_reason": "LOW. Recognized mainly by name/path or bundle ID; code-signing evidence is missing; matched: app name; missing: code signing ID.",
                "matched_evidence": ["candidate_name", "bundle_id"],
                "failed_evidence": ["signing_identifier", "signature_valid"],
            },
        },
    }
    fake_redis.set(
        trusttwin_store.LATEST_KEY_FMT.format(device_id="dev_ai"),
        json.dumps(doc),
    )
    result = ConnectedAgentService().list_ai_software("dev_ai")
    assert result.items[0].matched_evidence == ["candidate_name", "bundle_id"]
    assert result.items[0].failed_evidence == ["signing_identifier", "signature_valid"]
    assert "code-signing" in result.items[0].confidence_reason


def test_list_ai_software_empty_when_missing(fake_redis):
    result = ConnectedAgentService().list_ai_software("missing")
    assert result.device_id == "missing"
    assert result.total == 0
    assert result.items == []
