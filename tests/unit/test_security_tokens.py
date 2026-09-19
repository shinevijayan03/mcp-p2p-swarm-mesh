"""Unit tests for TC-NFR02-01 and TC-NFR02-02: Cryptographic tokens and replay prevention."""

import time
import pytest
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority, CapabilityTokenClaims
from mcp_mesh.protocol.errors import UnauthorizedTokenError, ReplayAttackDetectedError

def test_token_issue_and_verify():
    """Verify that a validly signed token is successfully verified."""
    issuer_id = NodeIdentity()
    authority = TokenAuthority(issuer_id)

    token = authority.issue_token(
        target_node_id="target_peer_01",
        tool_name="execute_sql",
        ttl_seconds=60,
    )

    claims = authority.verify_token(token, expected_tool="execute_sql")
    assert claims.sub == "target_peer_01"
    assert claims.iss == issuer_id.node_id
    assert any(cap.resource == "execute_sql" for cap in claims.capabilities)

def test_token_scope_enforcement():
    """Verify that attempting to execute an ungranted tool raises UnauthorizedTokenError (TC-NFR02-01)."""
    issuer_id = NodeIdentity()
    authority = TokenAuthority(issuer_id)

    token = authority.issue_token(
        target_node_id="target_peer_01",
        tool_name="read_logs",
        ttl_seconds=60,
    )

    with pytest.raises(UnauthorizedTokenError):
        authority.verify_token(token, expected_tool="delete_logs")

def test_token_nonce_replay_prevention():
    """Verify that replaying a token with identical nonce is rejected (TC-NFR02-02)."""
    issuer_id = NodeIdentity()
    authority = TokenAuthority(issuer_id)

    token = authority.issue_token(
        target_node_id="target_peer_01",
        tool_name="read_logs",
        ttl_seconds=60,
    )

    # First verification succeeds
    authority.verify_token(token, expected_tool="read_logs")

    # Second verification with same jti must fail
    with pytest.raises(ReplayAttackDetectedError):
        authority.verify_token(token, expected_tool="read_logs")
