"""Chaos tests for TC-EC02-01: Malformed JSON-RPC Payloads."""

import asyncio
import pytest
from mcp_mesh.protocol.framing import FrameCodec
from mcp_mesh.protocol.messages import MessageType
from mcp_mesh.protocol.errors import ProtocolViolationError

@pytest.mark.asyncio
async def test_malformed_wire_frames():
    """Verify daemon rejects corrupted frames without unhandled exceptions (TC-EC02-01)."""
    # 1. Truncated frame
    reader = asyncio.StreamReader()
    reader.feed_data(b"\x00\x00\x00\x10\x53\x01truncated")  # 16 bytes declared, only 9 provided
    reader.feed_eof()

    with pytest.raises(ProtocolViolationError):
        await FrameCodec.read_frame(reader)

    # 2. Corrupt magic byte
    reader2 = asyncio.StreamReader()
    reader2.feed_data(b"\x00\x00\x00\x04\x99\x01ok")
    with pytest.raises(ProtocolViolationError):
        await FrameCodec.read_frame(reader2)
