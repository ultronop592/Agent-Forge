import asyncio
from typing import Dict, Optional


class GateRegistry:
    def __init__(self) -> None:
        self._gates: Dict[str, asyncio.Event] = {}

    def open(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._gates[task_id] = event
        return event

    def signal(self, task_id: str) -> None:
        event = self._gates.get(task_id)
        if event is not None:
            event.set()

    def close(self, task_id: str) -> None:
        self._gates.pop(task_id, None)

    def get(self, task_id: str) -> Optional[asyncio.Event]:
        return self._gates.get(task_id)


gate_registry = GateRegistry()
