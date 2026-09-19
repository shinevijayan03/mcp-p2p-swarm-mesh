"""JWT Capability token authority with EdDSA signatures and replay prevention."""

import time
import uuid
from typing import Any, Dict, List, Optional, Set
import jwt
from pydantic import BaseModel, Field
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.protocol.errors import UnauthorizedTokenError, ReplayAttackDetectedError

class CapabilityConstraint(BaseModel):
    max_execution_time_ms: int = 15000
    read_only: bool = True
    allowed_arguments: Optional[List[str]] = None

class CapabilityGrant(BaseModel):
    action: str = "execute_tool"
    resource: str
    constraints: CapabilityConstraint = Field(default_factory=CapabilityConstraint)

class CapabilityTokenClaims(BaseModel):
    iss: str
    sub: str
    aud: str = "mcp-p2p-swarm-mesh"
    jti: str
    iat: int
    nbf: int
    exp: int
    capabilities: List[CapabilityGrant] = Field(default_factory=list)

class TokenAuthority:
    """Issues and validates EdDSA signed capability JWT tokens."""

    def __init__(self, identity: NodeIdentity):
        self._identity = identity
        self._seen_nonces: Set[str] = set()

    def issue_token(
        self,
        target_node_id: str,
        tool_name: str,
        ttl_seconds: int = 60,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> str:
        now = int(time.time())
        nonce = str(uuid.uuid4())
        cap_constraint = CapabilityConstraint(**(constraints or {}))
        grant = CapabilityGrant(action="execute_tool", resource=tool_name, constraints=cap_constraint)

        claims_dict = {
            "iss": self._identity.node_id,
            "sub": target_node_id,
            "aud": "mcp-p2p-swarm-mesh",
            "jti": nonce,
            "iat": now,
            "nbf": now,
            "exp": now + ttl_seconds,
            "capabilities": [grant.model_dump()],
        }

        token = jwt.encode(claims_dict, self._identity._private_key, algorithm="EdDSA")
        return token

    def verify_token(self, token_jwt: str, expected_tool: str) -> CapabilityTokenClaims:
        try:
            # We allow verifying against local identity or general mesh audience
            decoded = jwt.decode(
                token_jwt,
                self._identity._public_key,
                algorithms=["EdDSA"],
                audience="mcp-p2p-swarm-mesh",
            )
        except jwt.ExpiredSignatureError:
            raise UnauthorizedTokenError("Token has expired")
        except Exception as e:
            raise UnauthorizedTokenError(f"Invalid token signature: {e}")

        jti = decoded.get("jti")
        if not jti or jti in self._seen_nonces:
            raise ReplayAttackDetectedError(f"Duplicate or missing nonce '{jti}'")
        self._seen_nonces.add(jti)

        claims = CapabilityTokenClaims(**decoded)

        # Enforce tool scope
        has_tool = any(cap.resource == expected_tool for cap in claims.capabilities)
        if not has_tool:
            raise UnauthorizedTokenError(f"Token scope does not permit '{expected_tool}'")

        return claims
