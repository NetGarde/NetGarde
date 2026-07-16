from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DevicePolicyAssignmentRead(BaseModel):
    device_id: int
    policy_profile_id: Optional[int] = None
    policy_profile_slug: Optional[str] = None
    policy_profile_name: Optional[str] = None
    in_quarantine: bool = False
    quarantine_expires_at: Optional[datetime] = None


class AssignPolicyProfileRequest(BaseModel):
    policy_profile_slug: str


class PolicyProfileRead(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None
    behavior_sensitivity: str
    quarantine_on_abnormal: bool
    quarantine_hours: int
    is_builtin: bool
    model_config = ConfigDict(from_attributes=True)


class QuarantineStartRequest(BaseModel):
    hours: int = Field(default=4, ge=1, le=168)


class QuarantineActionResponse(BaseModel):
    device_id: int
    in_quarantine: bool
    quarantine_expires_at: Optional[datetime] = None
    message: str
