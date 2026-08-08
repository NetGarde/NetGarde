"""Schemas for AI Activity sessions proxied from detection-engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AiSessionCounters(BaseModel):
    tool_executions: int = 0
    files_read: int = 0
    files_modified: int = 0
    network_connections: int = 0
    process_count: int = 0


class AiSessionSummary(BaseModel):
    session_id: str
    device_id: str
    app_name: str
    root_process_id: str
    root_pid: int = 0
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str = "active"
    counters: AiSessionCounters = Field(default_factory=AiSessionCounters)
    external_domains: List[str] = Field(default_factory=list)
    secrets_accessed: List[str] = Field(default_factory=list)
    git_repos: List[str] = Field(default_factory=list)
    docker_activity: List[str] = Field(default_factory=list)
    k8s_activity: List[str] = Field(default_factory=list)
    cloud_activity: List[str] = Field(default_factory=list)
    risk_score: int = 0
    risk_factors: List[str] = Field(default_factory=list)
    finding_count: int = 0
    process_count: int = 0


class AiSessionListResponse(BaseModel):
    device_id: str
    total: int = 0
    items: List[AiSessionSummary] = Field(default_factory=list)


class AiSessionDetailResponse(AiSessionSummary):
    processes: Dict[str, Any] = Field(default_factory=dict)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    spawn_tree: Dict[str, Any] = Field(default_factory=dict)
    activity_chain: List[Dict[str, Any]] = Field(default_factory=list)


class AiSessionGraphResponse(BaseModel):
    session_id: str
    device_id: str
    app_name: str
    graph: Dict[str, Any] = Field(default_factory=dict)


class AiSessionTimelineResponse(BaseModel):
    session_id: str
    device_id: str
    total: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)


class AiSessionChainResponse(BaseModel):
    session_id: str
    device_id: str
    app_name: str
    total: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)


class AiProcessLookupResponse(BaseModel):
    process_id: str
    session_id: str
    device_id: str
    app_name: str
    role: str = "unknown"
