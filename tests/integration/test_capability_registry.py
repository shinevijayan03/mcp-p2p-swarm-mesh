"""Integration tests for TC-FR03-01 & TC-FR03-02: Capability Registry and Resource Reading."""

import pytest
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import PeerNodeRecord, MeshToolDefinition, ToolParameterSchema

def test_registry_capability_aggregation():
    """Verify registry aggregates tools and maps them to owner nodes (TC-FR03-01)."""
    registry = CapabilityRegistry()

    peer_a = PeerNodeRecord(
        node_id="node_a",
        host="127.0.0.1",
        tcp_port=9100,
        udp_port=9101,
        public_key_hex="pub_a",
        last_heartbeat=1000.0,
        tools=[
            MeshToolDefinition(
                name="query_db",
                description="Query DB",
                input_schema=ToolParameterSchema(properties={"query": {"type": "string"}})
            )
        ]
    )
    registry.update_peer(peer_a)

    found = registry.find_peers_for_tool("query_db")
    assert len(found) == 1
    assert found[0].node_id == "node_a"

def test_mesh_capabilities_resource_manifest():
    """Verify mesh capabilities resource manifest generation (TC-FR03-02)."""
    registry = CapabilityRegistry()
    manifest = registry.get_manifest()
    assert "nodes" in manifest
    assert "active_nodes_count" in manifest
