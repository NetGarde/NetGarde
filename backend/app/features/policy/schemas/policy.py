from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
