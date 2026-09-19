"""Custom exception hierarchy for mcp_mesh."""

class MeshError(Exception):
    """Base exception for all mesh errors."""
    code: int = -32000

class NodeUnreachableError(MeshError):
    """Raised when target peer is DEAD or unreachable."""
    code: int = -32001

class ExecutionTimeoutError(MeshError):
    """Raised when delegation execution times out."""
    code: int = -32002

class UnauthorizedTokenError(MeshError):
    """Raised when capability token is invalid or unauthorized."""
    code: int = -32003

class ReplayAttackDetectedError(UnauthorizedTokenError):
    """Raised when a duplicated token nonce (jti) is encountered."""
    code: int = -32003

class NodeCongestedError(MeshError):
    """Raised when node capacity or rate limit is saturated."""
    code: int = -32004

class ProtocolViolationError(MeshError):
    """Raised when invalid magic byte or malformed wire frame is received."""
    code: int = -32005

class ConsensusQuorumFailedError(MeshError):
    """Raised when swarm consensus review fails to achieve min quorum."""
    code: int = -32006
