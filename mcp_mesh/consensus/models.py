"""Consensus data models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class PeerEvaluation(BaseModel):
    peer_id: str
    score: float
    verdict: str  # "APPROVE", "REJECT", "ABSTAIN"
    justification: str
    confidence: float = 1.0

class ConsensusReviewResult(BaseModel):
    topic: str
    quorum_met: bool
    consensus_status: str  # "CONSENSUS_REACHED", "QUORUM_FAILED", "REJECTED"
    mean_score: float
    variance: float
    participating_peers: int
    evaluations: List[PeerEvaluation]
    synthesis_summary: str
