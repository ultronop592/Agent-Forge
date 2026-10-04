import asyncio
import logging
from typing import Dict, Set, Optional, Any

logger = logging.getLogger("agentforge.stream")


class TokenStreamManager:
    """
    In-memory pub/sub manager for streaming token-by-token chunks from agents
    to active Server-Sent Event (SSE) clients in real time.
    """
    def __init__(self):
        # Maps task_id -> set of subscriber asyncio.Queue instances
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe an SSE client to live token stream events for a task."""
        async with self._lock:
            q: asyncio.Queue = asyncio.Queue(maxsize=2000)
            if task_id not in self._subscribers:
                self._subscribers[task_id] = set()
            self._subscribers[task_id].add(q)
            logger.debug(f"[Stream] Client subscribed to task '{task_id}' (active subs: {len(self._subscribers[task_id])})")
            return q

    async def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        """Unsubscribe an SSE client queue and clean up memory."""
        async with self._lock:
            if task_id in self._subscribers:
                self._subscribers[task_id].discard(q)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]
                logger.debug(f"[Stream] Client unsubscribed from task '{task_id}'")

    async def publish_token(
        self,
        task_id: str,
        agent_name: str,
        chunk: str,
        subtask_id: Optional[str] = None
    ) -> None:
        """
        Publish a generated token chunk to all active SSE subscribers for this task.
        Non-blocking and safe against full queues.
        """
        if not task_id or not chunk:
            return

        async with self._lock:
            subs = list(self._subscribers.get(task_id, []))

        if not subs:
            return

        payload = {
            "event": "token",
            "data": {
                "task_id": task_id,
                "subtask_id": subtask_id,
                "agent_name": agent_name,
                "chunk": chunk,
            },
            "task_id": task_id,
            "subtask_id": subtask_id,
            "agent_name": agent_name,
            "chunk": chunk,
        }

        for q in subs:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # If subscriber is slow, discard oldest item to make space
                try:
                    q.get_nowait()
                    q.put_nowait(payload)
                except Exception:
                    pass

    def publish_token_sync(
        self,
        task_id: str,
        agent_name: str,
        chunk: str,
        subtask_id: Optional[str] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Thread-safe synchronous publishing helper for executor threads."""
        try:
            target_loop = loop or asyncio.get_event_loop()
            if target_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.publish_token(task_id, agent_name, chunk, subtask_id),
                    target_loop
                )
        except Exception as e:
            logger.debug(f"Failed to publish token sync: {e}")


# Global singleton instance
token_stream_manager = TokenStreamManager()
