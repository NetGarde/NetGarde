from datetime import datetime, timezone
from unittest.mock import patch

from app.features.twin.schemas.security_alert import SecurityAlertExplainRequest
from app.features.twin.services.alert_explain_service import (
    _build_prompt,
    explain_security_alert,
)


def test_build_prompt_includes_alert_fields():
    alert = SecurityAlertExplainRequest(
        timestamp=datetime(2026, 7, 17, 0, 0, tzinfo=timezone.utc),
        device_id="dev_x",
        event_type="registry_persistence",
        alert_type="registry_persistence",
        severity="high",
        message="Persistence artifact installed/changed: com.example",
        detail='{"path":"/Users/test/Library/LaunchAgents/com.example.plist"}',
    )
    system, user = _build_prompt(alert)
    assert "security analyst" in system.lower()
    assert "registry_persistence" in user
    assert "com.example.plist" in user


def test_explain_security_alert_calls_ollama():
    alert = SecurityAlertExplainRequest(
        timestamp=datetime(2026, 7, 17, 0, 0, tzinfo=timezone.utc),
        device_id="dev_x",
        alert_type="temp_path_execution",
        severity="high",
        message="Process started from suspicious path",
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "This looks like temp-path execution."}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            assert url.endswith("/api/chat")
            assert json["model"] == "llama3.2:3b"
            return FakeResponse()

    with (
        patch(
            "app.features.twin.services.alert_explain_service.resolve_ollama_base_url",
            return_value="http://ollama:11434",
        ),
        patch("app.features.twin.services.alert_explain_service.ensure_model_available"),
        patch("app.features.twin.services.alert_explain_service.settings") as mock_settings,
        patch("httpx.Client", FakeClient),
    ):
        mock_settings.OLLAMA_MODEL = "llama3.2:3b"
        mock_settings.LLM_TIMEOUT_SEC = 60.0
        result = explain_security_alert(alert)

    assert result.source == "ollama"
    assert result.model == "llama3.2:3b"
    assert "temp-path execution" in result.explanation
