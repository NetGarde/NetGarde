from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentUpsertRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=128)
    hostname: Optional[str] = Field(default=None, max_length=255)
    os: Optional[str] = Field(default=None, max_length=64)
    os_version: Optional[str] = Field(default=None, max_length=128)
    arch: Optional[str] = Field(default=None, max_length=64)
    agent_version: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)


class AgentRead(BaseModel):
    id: int
    agent_id: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    arch: Optional[str] = None
    agent_version: Optional[str] = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: List[AgentRead] = Field(default_factory=list)
    total: int = 0
