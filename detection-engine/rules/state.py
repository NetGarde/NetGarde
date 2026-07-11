from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceState:
    network_type: str | None = None
    public_ip: str | None = None
    presence: str | None = None


class StateStore:
    def __init__(self) -> None:
        self._devices: dict[str, DeviceState] = {}

    def get(self, device_id: str) -> DeviceState:
        if device_id not in self._devices:
            self._devices[device_id] = DeviceState()
        return self._devices[device_id]
