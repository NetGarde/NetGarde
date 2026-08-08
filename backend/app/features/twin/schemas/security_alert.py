from datetime import datetime
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field


class SecurityAlertCreate(BaseModel):
    timestamp: datetime
    device_id: str = Field(
        min_length=1,
        max_length=64,
        validation_alias=AliasChoices("device_id", "trusttwin_device_id"),
    )
    event_id: Optional[str] = Field(default=None, max_length=64)
    event_type: Optional[str] = Field(default=None, max_length=32)
    alert_type: str = Field(min_length=1, max_length=64)
    severity: str = Field(default="medium", max_length=16)
    message: Optional[str] = None
    detail: Optional[str] = None
    fingerprint: Optional[str] = Field(default=None, max_length=64)


class SecurityAlertResponse(BaseModel):
    id: int
    timestamp: datetime
    device_id: str
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    alert_type: str
    severity: str
    message: Optional[str] = None
    detail: Optional[str] = None
    fingerprint: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SecurityAlertListResponse(BaseModel):
    items: List[SecurityAlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SecurityAlertExplainRequest(BaseModel):
    timestamp: datetime
    device_id: str = Field(min_length=1, max_length=64)
    event_id: Optional[str] = Field(default=None, max_length=64)
    event_type: Optional[str] = Field(default=None, max_length=32)
    alert_type: str = Field(min_length=1, max_length=64)
    severity: str = Field(default="medium", max_length=16)
    message: Optional[str] = None
    detail: Optional[str] = None
    fingerprint: Optional[str] = Field(default=None, max_length=64)


class SecurityAlertExplainResponse(BaseModel):
    explanation: str
    model: str
    source: str = "ollama"
