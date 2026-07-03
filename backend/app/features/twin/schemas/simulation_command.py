from typing import Literal, Optional

from pydantic import BaseModel, Field


class SimulationCommandRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    active_ports: list[int] = Field(default_factory=list)
    active_apps: list[str] = Field(default_factory=list)


class SimulationCommandResponse(BaseModel):
    action: Literal[
        "block_port",
        "unblock_port",
        "block_tunnel",
        "unblock_tunnel",
        "block_gateway",
        "unblock_gateway",
        "clear_simulation",
        "enable_what_if",
        "noop",
        "unknown",
    ]
    port: Optional[int] = Field(default=None, ge=0, le=65535)
    app_slug: Optional[str] = None
    message: str
    source: Literal["rules", "ollama"]
