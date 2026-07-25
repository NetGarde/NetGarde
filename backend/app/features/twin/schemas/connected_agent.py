from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConnectedAgentRead(BaseModel):
    device_id: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    arch: Optional[str] = None
    agent_version: Optional[str] = None
    status: Optional[str] = None
    public_ip: Optional[str] = None
    network_type: Optional[str] = None
    listening_count: Optional[int] = None
    established_count: Optional[int] = None
    presence: Optional[str] = None
    idle_sec: Optional[int] = None
    app_switches: Optional[int] = None
    last_seen_at: Optional[datetime] = None
    connected: bool = False
    client_details: dict[str, Any] = Field(default_factory=dict)
    network_summary: dict[str, Any] = Field(default_factory=dict)
    action_summary: dict[str, Any] = Field(default_factory=dict)


class ConnectedAgentListResponse(BaseModel):
    items: list[ConnectedAgentRead] = Field(default_factory=list)
    total: int = 0
    connected_within_sec: int = 300


class AgentEventRead(BaseModel):
    event_id: str = ""
    device_id: str = ""
    type: str = ""
    ts: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentEventListResponse(BaseModel):
    items: list[AgentEventRead] = Field(default_factory=list)
    total: int = 0
    device_id: str

