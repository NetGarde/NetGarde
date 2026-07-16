from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional


class DeviceCreate(BaseModel):
    external_id: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    source: str = "manual"

    @field_validator("external_id")
    @classmethod
    def normalize_external_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("external_id must not be empty")
        return cleaned

    @field_validator("mac_address")
    @classmethod
    def normalize_mac(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip().lower()


class DeviceUpdate(BaseModel):
    hostname: Optional[str] = None
    mac_address: Optional[str] = None

    @field_validator("mac_address")
    @classmethod
    def normalize_mac(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip().lower()


class DeviceRead(BaseModel):
    id: int
    external_id: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    source: str
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
