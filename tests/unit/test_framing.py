"""Unit tests for wire framing codec."""

import asyncio
import pytest
from mcp_mesh.protocol.framing import FrameCodec
from mcp_mesh.protocol.messages import MessageType
from mcp_mesh.protocol.errors import ProtocolViolationError

@pytest.mark.asyncio
async def test_encode_and_read_valid_frame():
    """Verify encoding and reading of a standard RPC_REQUEST frame."""
    payload = b'{"jsonrpc": "2.0", "id": "1", "method": "ping"}'
    encoded = FrameCodec.encode_frame(MessageType.RPC_REQUEST, payload)

    reader = asyncio.StreamReader()
    reader.feed_data(encoded)

    msg_type, read_payload = await FrameCodec.read_frame(reader)
    assert msg_type == MessageType.RPC_REQUEST
    assert read_payload == payload

@pytest.mark.asyncio
async def test_reject_invalid_magic_byte():
    """Verify that a frame with an invalid magic byte raises ProtocolViolationError."""
    # Build a frame with invalid magic byte 0xFF
    length = 10
    corrupt_frame = length.to_bytes(4, "big") + b"\xff\x01" + b"12345678"

    reader = asyncio.StreamReader()
    reader.feed_data(corrupt_frame)

    with pytest.raises(ProtocolViolationError):
        await FrameCodec.read_frame(reader)

@pytest.mark.asyncio
async def test_reject_oversized_frame():
    """Verify that frames exceeding MAX_FRAME_SIZE are rejected."""
    oversized = (FrameCodec.MAX_FRAME_SIZE + 100).to_bytes(4, "big") + b"\x53\x01"

    reader = asyncio.StreamReader()
    reader.feed_data(oversized)

    with pytest.raises(ProtocolViolationError):
        await FrameCodec.read_frame(reader)
