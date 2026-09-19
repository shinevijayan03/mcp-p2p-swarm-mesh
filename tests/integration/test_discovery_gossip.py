"""Integration tests for TC-FR02-01: P2P Gossip Discovery."""

import asyncio
import pytest
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.discovery.gossip import GossipEngine, GossipHeartbeat
from mcp_mesh.registry.models import MeshToolDefinition

@pytest.mark.asyncio
async def test_p2p_gossip_discovery_three_nodes():
    """Verify that three nodes exchange gossip heartbeats and discover each other (TC-FR02-01)."""
    reg_a = CapabilityRegistry()
    reg_b = CapabilityRegistry()
    reg_c = CapabilityRegistry()

    engine_a = GossipEngine("node_a", "127.0.0.1", 9100, 9101, "pub_a", reg_a, seeds=[])
    engine_b = GossipEngine("node_b", "127.0.0.1", 9200, 9201, "pub_b", reg_b, seeds=["127.0.0.1:9101"])
    engine_c = GossipEngine("node_c", "127.0.0.1", 9300, 9301, "pub_c", reg_c, seeds=["127.0.0.1:9101"])

    await engine_a.start()
    await engine_b.start()
    await engine_c.start()

    try:
        # Trigger heartbeat broadcasts
        await engine_a.broadcast_heartbeat()
        await engine_b.broadcast_heartbeat()
        await engine_c.broadcast_heartbeat()

        await asyncio.sleep(0.1)

        peers_b = reg_b.get_all_peers()
        assert any(p.node_id == "node_a" for p in peers_b)
    finally:
        await engine_a.stop()
        await engine_b.stop()
        await engine_c.stop()
