"""Top-level MeshNode unifying transport, discovery, and capability advertisement."""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from mcp_mesh.config import MeshConfig
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import MeshToolDefinition, ToolParameterSchema
from mcp_mesh.discovery.gossip import GossipEngine
from mcp_mesh.discovery.detector import FailureDetector

class MeshNode:
    """Unified P2P Mesh Node that can host tools and participate in the swarm."""

    def __init__(
        self,
        node_id: Optional[str] = None,
        listen_host: str = "127.0.0.1",
        tcp_port: int = 9000,
        udp_port: int = 9001,
        seeds: Optional[List[str]] = None,
        config: Optional[MeshConfig] = None,
    ):
        self.config = config or MeshConfig(
            node_id=node_id or "node_auto",
            host=listen_host,
            tcp_port=tcp_port,
            udp_port=udp_port,
            seeds=seeds or [],
        )
        self.identity = NodeIdentity(self.config.private_key_hex)
        self.node_id = node_id or self.identity.node_id
        self.registry = CapabilityRegistry()
        self.tools: List[MeshToolDefinition] = []
        self._handlers: Dict[str, Callable] = {}

        self.gossip = GossipEngine(
            node_id=self.node_id,
            host=self.config.host,
            tcp_port=self.config.tcp_port,
            udp_port=self.config.udp_port,
            public_key_hex=self.identity.public_key_hex,
            registry=self.registry,
            seeds=self.config.seeds,
            heartbeat_interval=self.config.heartbeat_interval,
        )
        self.detector = FailureDetector(
            self.registry,
            suspect_timeout=self.config.suspect_timeout,
            failure_timeout=self.config.failure_timeout,
        )

    def tool(self, name: str, description: str = "") -> Callable:
        """Decorator to register a function as a mesh tool."""
        def decorator(func: Callable) -> Callable:
            tool_def = MeshToolDefinition(
                name=name,
                description=description or (func.__doc__ or ""),
                input_schema=ToolParameterSchema(),
            )
            self.register_tool(tool_def, func)
            return func
        return decorator

    def register_tool(self, tool_def: MeshToolDefinition, handler: Callable) -> None:
        """Registers a tool definition and handler on this node."""
        self.tools.append(tool_def)
        self._handlers[tool_def.name] = handler

    async def start(self) -> None:
        """Starts discovery and heartbeat daemons."""
        await self.gossip.start()
        await self.detector.start()

    async def stop(self) -> None:
        """Stops discovery and heartbeat daemons."""
        await self.detector.stop()
        await self.gossip.stop()

    def start_and_block(self) -> None:
        """Helper to start the node and run until interrupted."""
        async def _run():
            await self.start()
            try:
                while True:
                    await asyncio.sleep(3600)
            finally:
                await self.stop()

        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            pass
