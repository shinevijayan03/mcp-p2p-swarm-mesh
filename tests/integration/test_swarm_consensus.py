"""Integration tests for TC-FR05-01 & TC-FR05-02: Swarm Consensus Orchestration."""

import asyncio
import pytest
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine
from mcp_mesh.protocol.errors import ConsensusQuorumFailedError

@pytest.mark.asyncio
async def test_swarm_consensus_review_success():
    """Verify swarm consensus review fans out to peers and aggregates verdict (TC-FR05-01)."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)
    consensus = SwarmConsensusEngine(registry, dispatcher)

    review = await consensus.orchestrate_review(
        topic="Security Audit",
        context="Reviewing cryptographic key rotation PR",
        k_peers=3,
        min_quorum=2,
    )
    assert review.quorum_met is True
    assert review.consensus_status == "CONSENSUS_REACHED"

@pytest.mark.asyncio
async def test_swarm_consensus_quorum_failure():
    """Verify swarm consensus handles quorum failure when peers are unavailable (TC-FR05-02)."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)
    consensus = SwarmConsensusEngine(registry, dispatcher)

    with pytest.raises(ConsensusQuorumFailedError):
        await consensus.orchestrate_review(
            topic="High Security Policy",
            context="Impossible Quorum Test",
            k_peers=5,
            min_quorum=4,
            timeout_seconds=0.1,
        )
