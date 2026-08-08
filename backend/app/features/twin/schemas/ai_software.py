"""Schemas for known AI software inventory from Redis twin."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AiSoftwareItem(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    product_id: str = ""
    product_name: str = ""
    vendor: str = ""
    category: str = ""
    confidence: str = ""
    confidence_reason: str = ""
    installed: bool = False
    running: bool = False
    path: str = ""
    version: str = ""
    bundle_id: str = ""
    executable: str = ""
    signing_id: str = ""
    team_id: str = ""
    signature_valid: Optional[bool] = None
    matched_evidence: List[str] = Field(default_factory=list)
    failed_evidence: List[str] = Field(default_factory=list)
    # CLI agent fields (empty for GUI .app inventory).
    invocation_path: str = ""
    resolved_path: str = ""
    package_manager: str = ""
    package_identifier: str = ""
    entry_point: str = ""
    interpreter: str = ""
    # Local model runtime fields (empty/false for apps and CLI agents).
    serving: bool = False
    exposure: str = ""
    listeners: List[dict] = Field(default_factory=list)
    models_available: int = 0
    model_format: str = ""
    runtime_version: str = ""
    local_clients: List[dict] = Field(default_factory=list)


class AiSoftwareListResponse(BaseModel):
    device_id: str
    total: int = 0
    items: List[AiSoftwareItem] = Field(default_factory=list)
