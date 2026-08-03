from typing import List

from pydantic import BaseModel, Field


class DeviceBaselineItem(BaseModel):
    behavior_kind: str
    behavior_key: str
    count: int
    first_seen_at: str
    last_seen_at: str
    established: bool = False


class DeviceBaselineResponse(BaseModel):
    device_id: str
    profile_warm: bool = False
    total: int = 0
    items: List[DeviceBaselineItem] = Field(default_factory=list)
    suppress_count: int = 20
    suppress_age_hours: int = 72
    profile_min_keys: int = 30
