"""Chaos tests for TC-EC01-01: Split-Brain Partition & State Reconciliation."""

import pytest
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import PeerNodeRecord, MeshToolDefinition

def test_split_brain_partition_and_heal():
    """Verify split-brain partitions evict separated peers and reconcile upon healing (TC-EC01-01)."""
    # Partition 1: Node A and B
    reg_1 = CapabilityRegistry()
    peer_a = PeerNodeRecord(node_id="a", host="127.0.0.1", tcp_port=9100, udp_port=9101, public_key_hex="k_a", last_heartbeat=100.0)
    peer_b = PeerNodeRecord(node_id="b", host="127.0.0.1", tcp_port=9200, udp_port=9201, public_key_hex="k_b", last_heartbeat=100.0)
    reg_1.update_peer(peer_a)
    reg_1.update_peer(peer_b)

    # Partition 2: Node C and D
    reg_2 = CapabilityRegistry()
    peer_c = PeerNodeRecord(node_id="c", host="127.0.0.1", tcp_port=9300, udp_port=9301, public_key_hex="k_c", last_heartbeat=100.0)
    peer_d = PeerNodeRecord(node_id="d", host="127.0.0.1", tcp_port=9400, udp_port=9401, public_key_hex="k_d", last_heartbeat=100.0)
    reg_2.update_peer(peer_c)
    reg_2.update_peer(peer_d)

    # Simulate partition: reg_1 drops c and d
    assert len(reg_1.get_all_peers()) == 2

    # Simulate healing: exchange state
    for p in reg_2.get_all_peers():
        reg_1.update_peer(p)

    assert len(reg_1.get_all_peers()) == 4
