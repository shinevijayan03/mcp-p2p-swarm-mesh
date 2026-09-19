"""Integration tests for TC-NFR03-01: 15-Second Heartbeat Decay & Peer Eviction."""

import pytest
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import PeerNodeRecord, PeerStatus
from mcp_mesh.discovery.detector import FailureDetector

def test_peer_dropout_eviction_15s(mock_clock):
    """Verify peer transitions from ALIVE -> SUSPECT -> DEAD (TC-NFR03-01)."""
    registry = CapabilityRegistry()
    detector = FailureDetector(registry, suspect_timeout=10.0, failure_timeout=15.0)

    start_time = 1774088400.0
    peer = PeerNodeRecord(
        node_id="failing_node",
        host="127.0.0.1",
        tcp_port=9100,
        udp_port=9101,
        public_key_hex="pub_fail",
        last_heartbeat=start_time,
        status=PeerStatus.ALIVE,
    )
    registry.update_peer(peer)

    # At t = start + 5s: still ALIVE
    detector.check_peers(start_time + 5.0)
    p = registry.get_peer("failing_node")
    assert p is not None
    assert p.status == PeerStatus.ALIVE

    # At t = start + 11s: transitioned to SUSPECT
    detector.check_peers(start_time + 11.0)
    p = registry.get_peer("failing_node")
    assert p is not None
    assert p.status == PeerStatus.SUSPECT

    # At t = start + 16s: past 15s cutoff -> evict to DEAD or remove
    detector.check_peers(start_time + 16.0)
    p = registry.get_peer("failing_node")
    assert p is None or p.status == PeerStatus.DEAD
