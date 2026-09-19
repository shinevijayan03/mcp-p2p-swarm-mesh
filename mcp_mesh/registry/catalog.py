"""Reactive, thread-safe capability registry catalog."""

from typing import Any, Dict, List, Optional
from mcp_mesh.registry.models import PeerNodeRecord, PeerStatus

class CapabilityRegistry:
    """Catalog storing active peers and advertising capabilities."""

    def __init__(self):
        self._peers: Dict[str, PeerNodeRecord] = {}

    def update_peer(self, peer: PeerNodeRecord) -> None:
        """Adds or updates a peer in the catalog."""
        self._peers[peer.node_id] = peer

    def evict_peer(self, node_id: str) -> None:
        """Evicts a peer from the registry catalog."""
        self._peers.pop(node_id, None)

    def get_peer(self, node_id: str) -> Optional[PeerNodeRecord]:
        """Retrieves a peer record by node_id."""
        return self._peers.get(node_id)

    def get_all_peers(self) -> List[PeerNodeRecord]:
        """Returns all registered peers."""
        return list(self._peers.values())

    def find_peers_for_tool(self, tool_name: str) -> List[PeerNodeRecord]:
        """Returns list of ALIVE peers offering the specified tool."""
        results = []
        for peer in self._peers.values():
            if peer.status == PeerStatus.ALIVE:
                for tool in peer.tools:
                    if tool.name == tool_name:
                        results.append(peer)
                        break
        return results

    def get_manifest(self) -> Dict[str, Any]:
        """Generates the unified mesh capabilities manifest exposed via mesh://."""
        active_nodes = [p for p in self._peers.values() if p.status == PeerStatus.ALIVE]
        return {
            "mesh_id": "mcp-p2p-swarm-mesh",
            "active_nodes_count": len(active_nodes),
            "total_nodes_count": len(self._peers),
            "nodes": [
                {
                    "node_id": p.node_id,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "endpoint": f"{p.host}:{p.tcp_port}",
                    "tools": [t.model_dump() for t in p.tools],
                    "resources": [r.model_dump() for r in p.resources],
                    "prompts": [pr.model_dump() for pr in p.prompts],
                    "load_average": p.load_average,
                }
                for p in self._peers.values()
            ],
        }
