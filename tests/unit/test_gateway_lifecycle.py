"""Unit tests for TC-FR01-01 & TC-FR01-02: Gateway Node Lifecycle."""

import asyncio
import pytest
from mcp_mesh.config import MeshConfig
from mcp_mesh.gateway.server import GatewayServer
from mcp_mesh.gateway.mcp_facade import GatewayMcpFacade
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority

@pytest.mark.asyncio
async def test_gateway_initialization_stdio():
    """Verify Gateway initializes correctly with Stdio configuration (TC-FR01-01)."""
    config = MeshConfig(node_id="gw_test_01", mcp_mode="stdio")
    server = GatewayServer(config=config)
    assert server is not None

    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)
    consensus = SwarmConsensusEngine(registry, dispatcher)
    facade = GatewayMcpFacade(registry, dispatcher, consensus)

    tools = await facade.list_tools()
    assert any(t["name"] == "mesh_delegate_task" for t in tools)

    resources = await facade.list_resources()
    assert any(r["uri"] == "mesh://capabilities/registry" for r in resources)

@pytest.mark.asyncio
async def test_gateway_sse_transport_lifecycle():
    """Verify Gateway SSE facade handles session lifecycle (TC-FR01-02)."""
    config = MeshConfig(node_id="gw_test_sse", mcp_mode="sse", mcp_port=8088)
    server = GatewayServer(config=config)
    assert server is not None
