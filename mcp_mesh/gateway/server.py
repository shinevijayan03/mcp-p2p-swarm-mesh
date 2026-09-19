"""Gateway Server supporting Stdio and SSE transports."""

import asyncio
from typing import Optional
from mcp_mesh.config import MeshConfig
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine
from mcp_mesh.discovery.detector import FailureDetector
from mcp_mesh.discovery.gossip import GossipEngine
from mcp_mesh.gateway.mcp_facade import GatewayMcpFacade

class GatewayServer:
    """Runnable Gateway MCP Server bridging clients over Stdio or SSE to the mesh."""

    def __init__(self, config: Optional[MeshConfig] = None):
        self.config = config or MeshConfig()
        self.identity = NodeIdentity(self.config.private_key_hex)
        self.registry = CapabilityRegistry()
        self.token_authority = TokenAuthority(self.identity)
        self.dispatcher = TaskDispatcher(self.registry, self.token_authority)
        self.consensus = SwarmConsensusEngine(self.registry, self.dispatcher)
        self.failure_detector = FailureDetector(
            self.registry,
            suspect_timeout=self.config.suspect_timeout,
            failure_timeout=self.config.failure_timeout,
        )
        self.gossip = GossipEngine(
            node_id=self.config.node_id or self.identity.node_id,
            host=self.config.host,
            tcp_port=self.config.tcp_port,
            udp_port=self.config.udp_port,
            public_key_hex=self.identity.public_key_hex,
            registry=self.registry,
            seeds=self.config.seeds,
            heartbeat_interval=self.config.heartbeat_interval,
        )
        self.facade = GatewayMcpFacade(self.registry, self.dispatcher, self.consensus)

    async def run_stdio(self) -> None:
        """Runs the gateway in Stdio mode."""
        await self.gossip.start()
        await self.failure_detector.start()
        try:
            # Keep running until cancelled
            while True:
                await asyncio.sleep(3600)
        finally:
            await self.failure_detector.stop()
            await self.gossip.stop()

    async def run_sse(self, port: int = 8000) -> None:
        """Runs the gateway in SSE mode."""
        await self.gossip.start()
        await self.failure_detector.start()
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await self.failure_detector.stop()
            await self.gossip.stop()
