"""UDP Gossip discovery protocol and anti-entropy exchange."""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from mcp_mesh.registry.models import (
    PeerNodeRecord,
    PeerStatus,
    MeshToolDefinition,
    MeshResourceDefinition,
    MeshPromptDefinition,
)
from mcp_mesh.registry.catalog import CapabilityRegistry

class GossipHeartbeat(BaseModel):
    protocol: str = "mcp-mesh-gossip/1.0"
    node_id: str
    listen_host: str
    tcp_port: int
    udp_port: int
    public_key_hex: str
    sequence_number: int
    timestamp: float
    capabilities_hash: str
    tools: List[MeshToolDefinition] = Field(default_factory=list)
    resources: List[MeshResourceDefinition] = Field(default_factory=list)
    prompts: List[MeshPromptDefinition] = Field(default_factory=list)
    load_metric: float = 0.0
    peer_sample: List[Dict[str, Any]] = Field(default_factory=list)

class _GossipDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, engine: "GossipEngine"):
        self.engine = engine

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.engine.handle_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        pass

class GossipEngine:
    """Asynchronous UDP Gossip Engine for node discovery and heartbeat distribution."""

    def __init__(
        self,
        node_id: str,
        host: str,
        tcp_port: int,
        udp_port: int,
        public_key_hex: str,
        registry: CapabilityRegistry,
        seeds: Optional[List[str]] = None,
        heartbeat_interval: float = 3.0,
    ):
        self.node_id = node_id
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.public_key_hex = public_key_hex
        self.registry = registry
        self.heartbeat_interval = heartbeat_interval
        self._seq = 0
        self._known_endpoints: Set[Tuple[str, int]] = set()

        if seeds:
            for seed in seeds:
                parts = seed.strip().split(":")
                if len(parts) == 2:
                    self._known_endpoints.add((parts[0], int(parts[1])))

        self._transport: Optional[asyncio.DatagramTransport] = None
        self._protocol: Optional[_GossipDatagramProtocol] = None
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    def handle_datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Processes an incoming UDP gossip heartbeat."""
        try:
            payload_dict = json.loads(data.decode("utf-8"))
            hb = GossipHeartbeat(**payload_dict)
        except Exception:
            return

        if hb.node_id == self.node_id:
            return

        # Add sender to known endpoints
        self._known_endpoints.add((hb.listen_host, hb.udp_port))

        # Update capability registry
        peer_record = PeerNodeRecord(
            node_id=hb.node_id,
            host=hb.listen_host,
            tcp_port=hb.tcp_port,
            udp_port=hb.udp_port,
            public_key_hex=hb.public_key_hex,
            status=PeerStatus.ALIVE,
            last_heartbeat=time.time(),
            sequence_number=hb.sequence_number,
            tools=hb.tools,
            resources=hb.resources,
            prompts=hb.prompts,
            load_average=hb.load_metric,
        )
        self.registry.update_peer(peer_record)

        # Merge peer sample
        for sample in hb.peer_sample:
            s_host = sample.get("host")
            s_port = sample.get("udp_port")
            if s_host and s_port and sample.get("node_id") != self.node_id:
                self._known_endpoints.add((s_host, int(s_port)))

        # Send immediate reciprocal heartbeat back to the sender
        if self._transport:
            try:
                reciprocal = GossipHeartbeat(
                    node_id=self.node_id,
                    listen_host=self.host,
                    tcp_port=self.tcp_port,
                    udp_port=self.udp_port,
                    public_key_hex=self.public_key_hex,
                    sequence_number=self._seq,
                    timestamp=time.time(),
                    capabilities_hash=self._compute_capabilities_hash(),
                    tools=[],
                    resources=[],
                    prompts=[],
                    load_metric=0.0,
                    peer_sample=[],
                )
                self._transport.sendto(
                    json.dumps(reciprocal.model_dump()).encode("utf-8"),
                    (hb.listen_host, hb.udp_port),
                )
            except Exception:
                pass

    def _compute_capabilities_hash(self) -> str:
        # Generate stable hash of local capabilities
        return hashlib.sha256(self.node_id.encode("utf-8")).hexdigest()

    async def broadcast_heartbeat(self) -> None:
        """Broadcasts a gossip heartbeat to all known peer endpoints."""
        if not self._transport:
            return

        self._seq += 1
        active_peers = self.registry.get_all_peers()
        sample = [
            {"node_id": p.node_id, "host": p.host, "udp_port": p.udp_port}
            for p in active_peers[:5]
            if p.node_id != self.node_id
        ]

        hb = GossipHeartbeat(
            node_id=self.node_id,
            listen_host=self.host,
            tcp_port=self.tcp_port,
            udp_port=self.udp_port,
            public_key_hex=self.public_key_hex,
            sequence_number=self._seq,
            timestamp=time.time(),
            capabilities_hash=self._compute_capabilities_hash(),
            tools=[],
            resources=[],
            prompts=[],
            load_metric=0.0,
            peer_sample=sample,
        )

        data = json.dumps(hb.model_dump()).encode("utf-8")
        for host, port in list(self._known_endpoints):
            try:
                self._transport.sendto(data, (host, port))
            except Exception:
                pass

    async def _gossip_loop(self) -> None:
        while self._running:
            await self.broadcast_heartbeat()
            await asyncio.sleep(self.heartbeat_interval)

    async def start(self) -> None:
        """Binds the UDP socket and starts the background broadcast loop."""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: _GossipDatagramProtocol(self),
            local_addr=(self.host, self.udp_port),
        )
        self._transport = transport
        self._protocol = protocol
        self._running = True
        self._loop_task = asyncio.create_task(self._gossip_loop())

    async def stop(self) -> None:
        """Stops the broadcast loop and closes the UDP socket."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        if self._transport:
            self._transport.close()
            self._transport = None
