"""Explain a security alert using the local Ollama container."""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from app.features.dashboard.services.ollama_connectivity import (
    ensure_model_available,
    resolve_ollama_base_url,
)
from app.features.twin.schemas.security_alert import (
    SecurityAlertExplainRequest,
    SecurityAlertExplainResponse,
)
from app.shared.config import settings
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


def _build_prompt(alert: SecurityAlertExplainRequest) -> tuple[str, str]:
    detail_obj: Any = None
    if alert.detail:
        try:
            detail_obj = json.loads(alert.detail)
        except json.JSONDecodeError:
            detail_obj = alert.detail

    payload = {
        "timestamp": alert.timestamp.isoformat(),
        "device_id": alert.device_id,
        "event_id": alert.event_id,
        "event_type": alert.event_type,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "detail": detail_obj,
        "fingerprint": alert.fingerprint,
    }

    system = (
        "You are a security analyst assistant for TrustEdge, an endpoint detection product. "
        "Explain the alert in plain language for an operator. Cover: what happened, why it may "
        "matter, likely benign vs suspicious interpretations, and 2-4 concrete next checks. "
        "Be concise (about 120-220 words). Do not invent host facts that are not in the alert. "
        "Do not output JSON or markdown headings; use short paragraphs and optional bullet lines."
    )
    user = (
        "Explain this TrustEdge security alert for a SOC/operator dashboard:\n\n"
        + json.dumps(payload, indent=2, default=str)
    )
    return system, user


def explain_security_alert(alert: SecurityAlertExplainRequest) -> SecurityAlertExplainResponse:
    base = resolve_ollama_base_url()
    ensure_model_available(base)
    system, user = _build_prompt(alert)
    model = settings.OLLAMA_MODEL.strip()
    url = f"{base}/api/chat"
    body = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": 0.3,
            "num_predict": 500,
            "num_ctx": 4096,
        },
    }
    timeout = httpx.Timeout(
        connect=15.0,
        read=settings.LLM_TIMEOUT_SEC,
        write=30.0,
        pool=15.0,
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Ollama timed out after {int(settings.LLM_TIMEOUT_SEC)}s. "
            "Increase LLM_TIMEOUT_SEC or use a smaller model."
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    content = (data.get("message") or {}).get("content") or ""
    explanation = str(content).strip()
    if not explanation:
        raise RuntimeError("Ollama returned an empty explanation")

    return SecurityAlertExplainResponse(
        explanation=explanation,
        model=model,
        source="ollama",
    )
