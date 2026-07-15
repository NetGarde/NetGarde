from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class DnsAlertResponse(BaseModel):
    id: int
    timestamp: datetime
    client_ip: str
    device_id: Optional[int] = None
    alert_type: str
    severity: str
    domain: Optional[str] = None
    root_domain: Optional[str] = None
    message: Optional[str] = None
    parent_summary: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DnsAlertListResponse(BaseModel):
    items: List[DnsAlertResponse]
    total: int
    page: int
    page_size: int
    pages: int
