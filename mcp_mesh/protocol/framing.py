"""Wire framing codec with length prefix and magic byte."""

import asyncio
from typing import Tuple
from mcp_mesh.protocol.messages import MessageType
from mcp_mesh.protocol.errors import ProtocolViolationError

class FrameCodec:
    """Encodes and decodes length-prefixed frames."""
    MAGIC: bytes = b"\x53"  # 'S' for Swarm
    MAX_FRAME_SIZE: int = 16 * 1024 * 1024  # 16 MB

    @classmethod
    def encode_frame(cls, msg_type: MessageType, payload: bytes) -> bytes:
        """Encodes frame: [4-byte big-endian length][1-byte magic 0x53][1-byte type][payload]."""
        remainder = cls.MAGIC + bytes([int(msg_type)]) + payload
        length = len(remainder)
        if length > cls.MAX_FRAME_SIZE:
            raise ProtocolViolationError(f"Frame size {length} exceeds maximum {cls.MAX_FRAME_SIZE}")
        return length.to_bytes(4, "big") + remainder

    @classmethod
    async def read_frame(cls, reader: asyncio.StreamReader) -> Tuple[MessageType, bytes]:
        """Reads and decodes a single frame from the async reader stream."""
        try:
            length_bytes = await reader.readexactly(4)
        except (asyncio.IncompleteReadError, ConnectionResetError) as e:
            raise ProtocolViolationError(f"Incomplete frame length header: {e}")

        length = int.from_bytes(length_bytes, "big")
        if length > cls.MAX_FRAME_SIZE:
            raise ProtocolViolationError(f"Frame length {length} exceeds MAX_FRAME_SIZE")
        if length < 2:
            raise ProtocolViolationError(f"Frame length {length} is too short")

        try:
            body = await reader.readexactly(length)
        except (asyncio.IncompleteReadError, ConnectionResetError) as e:
            raise ProtocolViolationError(f"Incomplete frame body: {e}")

        magic = body[0:1]
        if magic != cls.MAGIC:
            raise ProtocolViolationError(f"Invalid magic byte {magic!r}, expected {cls.MAGIC!r}")

        try:
            msg_type = MessageType(body[1])
        except ValueError:
            raise ProtocolViolationError(f"Unknown message type byte {body[1]}")

        payload = body[2:]
        return msg_type, payload
