from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from rules.chain import ChainEvent, DeviceChain


@dataclass
class DeviceState:
    network_type: str | None = None
    public_ip: str | None = None
    presence: str | None = None


class StateStore:
    def __init__(
        self,
        *,
        max_chain_events: int = 100,
        chain_window_minutes: int = 30,
    ) -> None:
        self._devices: dict[str, DeviceState] = {}
        self._chains: dict[str, DeviceChain] = {}
        self._max_chain_events = max_chain_events
        self._chain_window = timedelta(minutes=chain_window_minutes)

    def get(self, device_id: str) -> DeviceState:
        if device_id not in self._devices:
            self._devices[device_id] = DeviceState()
        return self._devices[device_id]

    def get_chain(self, device_id: str) -> DeviceChain:
        if device_id not in self._chains:
            self._chains[device_id] = DeviceChain(device_id=device_id)
        return self._chains[device_id]

    def record_event(self, event: dict[str, Any]) -> DeviceChain | None:
        chain_event = ChainEvent.from_kafka(event)
        if chain_event is None:
            return None

        device_id = str(event.get("device_id", "")).strip()
        if not device_id:
            return None

        chain = self.get_chain(device_id)
        chain.append(
            chain_event,
            max_events=self._max_chain_events,
            window=self._chain_window,
        )

        state = self.get(device_id)
        if chain_event.event_type == "action_summary":
            presence = str(chain_event.payload.get("presence") or "").strip()
            if presence:
                state.presence = presence
        elif chain_event.event_type == "network_summary":
            network_type = str(chain_event.payload.get("network_type") or "").strip()
            public_ip = str(chain_event.payload.get("public_ip") or "").strip()
            if network_type:
                state.network_type = network_type
            if public_ip:
                state.public_ip = public_ip

        return chain
