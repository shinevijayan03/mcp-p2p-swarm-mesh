"""Integration tests for TC-FR04-01 & TC-FR04-02: Distributed Task Delegation."""

import asyncio
import pytest
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import PeerNodeRecord, MeshToolDefinition
from mcp_mesh.router.dispatcher import TaskDispatcher

@pytest.mark.asyncio
async def test_successful_task_delegation():
    """Verify task delegation to target peer executes and returns result (TC-FR04-01)."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)

    peer = PeerNodeRecord(
        node_id="worker_alpha",
        host="127.0.0.1",
        tcp_port=9100,
        udp_port=9101,
        public_key_hex="pub_worker",
        last_heartbeat=1000.0,
        tools=[MeshToolDefinition(name="fibonacci", description="compute fib")]
    )
    registry.update_peer(peer)

    result = await dispatcher.delegate_task(
        target_node_id="worker_alpha",
        tool_name="fibonacci",
        arguments={"n": 10},
    )
    assert result is not None
    assert result.get("isError") is False

@pytest.mark.asyncio
async def test_streaming_task_delegation():
    """Verify streaming progress chunks during task delegation (TC-FR04-02)."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)

    chunks = []
    async for chunk in dispatcher.delegate_task_stream("worker_alpha", "stream_proc", {}):
        chunks.append(chunk)

    assert len(chunks) > 0
