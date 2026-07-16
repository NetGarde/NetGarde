from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

OverviewSource = Literal["template", "llm"]


class NetworkOverviewStats(BaseModel):
    reporting_clients: int = Field(ge=0)
    live_total_mib_per_sec: float = Field(ge=0)
    peak_mib_per_sec: float = Field(ge=0)
    alerts_total: int = Field(ge=0)


class NetworkOverviewRead(BaseModel):
    generated_at: datetime
    period_minutes: int = Field(ge=1, le=24 * 60)
    bullets: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    stats: NetworkOverviewStats
    source: OverviewSource = "template"
    llm_model: Optional[str] = None
    review_mode: str = "template"
    llm_error: Optional[str] = None
