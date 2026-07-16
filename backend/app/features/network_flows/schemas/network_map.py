from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class NetworkMapNode(BaseModel):
    id: str
    type: Literal["device", "app", "domain", "flow"]
    label: str
    app_slug: Optional[str] = None
    client_ip: Optional[str] = None
    device_id: Optional[int] = None
    blocked: Optional[bool] = None
    fresh: Optional[bool] = None


class NetworkMapEdge(BaseModel):
    source: str
    target: str
    kind: Literal["foreground", "dns", "dns_direct", "flow_session", "dns_to_flow"]
    query_count: int = 1
    blocked_count: int = 0


class NetworkMapResponse(BaseModel):
    generated_at: datetime
    minutes: int
    nodes: List[NetworkMapNode]
    edges: List[NetworkMapEdge]
