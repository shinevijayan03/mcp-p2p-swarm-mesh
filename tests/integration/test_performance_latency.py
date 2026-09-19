"""Integration test for TC-NFR04-01: Intra-Mesh RPC Latency Overhead (< 50ms)."""

import time
import pytest
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.registry.models import PeerNodeRecord, MeshToolDefinition

@pytest.mark.asyncio
async def test_intra_mesh_rpc_latency_overhead():
    """Verify intra-mesh dispatch overhead is strictly < 50ms (TC-NFR04-01)."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)

    peer = PeerNodeRecord(
        node_id="perf_node",
        host="127.0.0.1",
        tcp_port=9100,
        udp_port=9101,
        public_key_hex="pub_perf",
        last_heartbeat=time.time(),
        tools=[MeshToolDefinition(name="noop_tool", description="no-op tool")]
    )
    registry.update_peer(peer)

    t0 = time.perf_counter()
    res = await dispatcher.delegate_task("perf_node", "noop_tool", {})
    t1 = time.perf_counter()

    elapsed_ms = (t1 - t0) * 1000.0
    assert elapsed_ms < 50.0, f"Overhead was {elapsed_ms:.2f}ms, expected < 50ms"
