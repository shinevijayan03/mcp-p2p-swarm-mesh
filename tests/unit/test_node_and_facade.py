"""Additional unit tests covering MeshNode, GatewayMcpFacade methods, and NodeIdentity."""

import asyncio
import json
import pytest
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import MeshToolDefinition, ToolParameterSchema
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine
from mcp_mesh.gateway.mcp_facade import GatewayMcpFacade
from mcp_mesh.node import MeshNode

@pytest.mark.asyncio
async def test_node_identity_serialization_and_verification():
    """Verify NodeIdentity export/import and signature verification."""
    id1 = NodeIdentity()
    priv_hex = id1.private_key_hex
    pub_hex = id1.public_key_hex

    id2 = NodeIdentity(priv_hex)
    assert id2.node_id == id1.node_id
    assert id2.public_key_hex == pub_hex

    data = b"Swarm mesh cryptographic payload"
    sig = id1.sign(data)
    assert id2.verify(data, sig) is True
    assert id2.verify(data, sig, pub_hex) is True
    assert id2.verify(b"tampered", sig) is False

@pytest.mark.asyncio
async def test_mesh_node_tool_registration():
    """Verify MeshNode registers tools with decorators."""
    node = MeshNode(node_id="test_node_dec")

    @node.tool(name="multiply_numbers", description="multiplies two floats")
    def multiply(a: float, b: float) -> float:
        return a * b

    assert any(t.name == "multiply_numbers" for t in node.tools)

    # Test lifecycle start/stop
    await node.start()
    await node.stop()

@pytest.mark.asyncio
async def test_gateway_facade_calls_and_resources():
    """Verify GatewayMcpFacade call_tool, read_resource, and get_prompt."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)
    consensus = SwarmConsensusEngine(registry, dispatcher)
    facade = GatewayMcpFacade(registry, dispatcher, consensus)

    # Register local handler in dispatcher for execution
    dispatcher.register_local_handler("echo_tool", lambda msg: f"Echo: {msg}")

    # Register dummy tool in registry so target node is known
    from mcp_mesh.registry.models import PeerNodeRecord, PeerStatus
    peer = PeerNodeRecord(
        node_id="node_target_1",
        host="127.0.0.1",
        tcp_port=9100,
        udp_port=9101,
        public_key_hex="pub_1",
        last_heartbeat=1000.0,
        tools=[MeshToolDefinition(name="echo_tool", description="echoes")]
    )
    registry.update_peer(peer)

    # Call mesh_delegate_task
    res = await facade.call_tool(
        "mesh_delegate_task",
        {"target_node_id": "node_target_1", "tool_name": "echo_tool", "arguments": {"msg": "hello"}},
    )
    assert res.get("isError") is False

    # Read resource
    resource_data = await facade.read_resource("mesh://capabilities/registry")
    assert "contents" in resource_data
    parsed = json.loads(resource_data["contents"][0]["text"])
    assert parsed.get("mesh_id") == "mcp-p2p-swarm-mesh"

    # List prompts
    prompts = await facade.list_prompts()
    assert any(p["name"] == "swarm_consensus_review" for p in prompts)

    # Get prompt
    prompt_res = await facade.get_prompt(
        "swarm_consensus_review",
        {"topic": "Architecture", "context": "New node proposal", "k_peers": 2, "min_quorum": 2}
    )
    assert "messages" in prompt_res
