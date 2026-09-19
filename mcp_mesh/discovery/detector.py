"""Heartbeat decay failure detector."""

import asyncio
import time
from typing import Optional
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import PeerStatus

class FailureDetector:
    """Monitors peer heartbeats and updates status based on decay timeouts."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        suspect_timeout: float = 10.0,
        failure_timeout: float = 15.0,
    ):
        self._registry = registry
        self._suspect_timeout = suspect_timeout
        self._failure_timeout = failure_timeout
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def check_peers(self, current_time: float) -> None:
        """Evaluates last_heartbeat timestamps against the given current_time."""
        for peer in self._registry.get_all_peers():
            elapsed = current_time - peer.last_heartbeat
            if elapsed > self._failure_timeout:
                peer.status = PeerStatus.DEAD
            elif elapsed > self._suspect_timeout:
                peer.status = PeerStatus.SUSPECT
            else:
                peer.status = PeerStatus.ALIVE

    async def _monitor_loop(self) -> None:
        while self._running:
            self.check_peers(time.time())
            await asyncio.sleep(1.0)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
