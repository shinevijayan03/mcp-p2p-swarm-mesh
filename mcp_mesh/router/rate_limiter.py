"""Concurrency rate limiter with bounded queuing and congestion shedding."""

import asyncio
from typing import List
from mcp_mesh.protocol.errors import NodeCongestedError

class ConcurrencyRateLimiter:
    """Limits concurrent executions and rejects requests when queue capacity is reached."""

    def __init__(self, max_concurrency: int = 10, max_queue_depth: int = 50):
        self.max_concurrency = max_concurrency
        self.max_queue_depth = max_queue_depth
        self._active = 0
        self._waiting: List[asyncio.Future] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquires execution slot or queues; raises NodeCongestedError if queue is full."""
        async with self._lock:
            if self._active < self.max_concurrency:
                self._active += 1
                return

            if len(self._waiting) >= self.max_queue_depth:
                raise NodeCongestedError(
                    f"Peer congested: active={self._active}/{self.max_concurrency}, queue={len(self._waiting)}/{self.max_queue_depth}"
                )

            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            self._waiting.append(fut)

        # Await slot outside lock
        await fut

    def release(self) -> None:
        """Releases an active execution slot and unblocks the next queued request."""
        if self._waiting:
            next_fut = self._waiting.pop(0)
            if not next_fut.done():
                next_fut.set_result(True)
        else:
            if self._active > 0:
                self._active -= 1
