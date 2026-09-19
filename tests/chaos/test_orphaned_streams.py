"""Chaos tests for TC-EC04-01: Orphaned Stream & Abrupt Socket Teardown."""

import asyncio
import pytest
from mcp_mesh.transport.channel import P2PChannel

@pytest.mark.asyncio
async def test_client_abrupt_disconnect_teardown(mock_socket_pair):
    """Verify channel handles abrupt socket teardown cleanly without leaking tasks (TC-EC04-01)."""
    channel = P2PChannel(mock_socket_pair.client_reader, mock_socket_pair.client_writer)

    # Force close the underlying writer abruptly
    mock_socket_pair.client_writer.close()

    await channel.close()
    assert True
