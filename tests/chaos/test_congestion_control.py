"""Chaos tests for TC-EC03-01: Concurrent Tool Execution Congestion."""

import asyncio
import pytest
from mcp_mesh.router.rate_limiter import ConcurrencyRateLimiter
from mcp_mesh.protocol.errors import NodeCongestedError

@pytest.mark.asyncio
async def test_concurrent_congestion_throttling():
    """Verify rate limiter enforces max concurrency and queue limits under load (TC-EC03-01)."""
    limiter = ConcurrencyRateLimiter(max_concurrency=2, max_queue_depth=3)

    acquired = []

    async def worker(idx: int):
        try:
            await limiter.acquire()
            acquired.append(idx)
            await asyncio.sleep(0.05)
        finally:
            limiter.release()

    tasks = [asyncio.create_task(worker(i)) for i in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Some must succeed, and when queue is exceeded, NodeCongestedError is raised
    errors = [r for r in results if isinstance(r, NodeCongestedError)]
    assert len(acquired) > 0
    assert len(errors) > 0
