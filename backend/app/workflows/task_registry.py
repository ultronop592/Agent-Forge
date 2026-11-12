import asyncio
from typing import Dict, Optional, Any


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task[Any]] = {}

    def register(self, task_id: str, task: asyncio.Task[Any]) -> None:
        self._tasks[task_id] = task

    def unregister(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def get(self, task_id: str) -> Optional[asyncio.Task[Any]]:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False


task_registry = TaskRegistry()

