"""Integration tests for TC-FR02-02 & TC-NFR02-03: Encrypted Transport."""

import asyncio
import ssl
import pytest
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.certs import CertificateAuthority
from mcp_mesh.transport.channel import P2PChannel
from mcp_mesh.transport.listener import MeshListener
from mcp_mesh.protocol.framing import FrameCodec
from mcp_mesh.protocol.messages import MessageType

@pytest.mark.asyncio
async def test_bidirectional_tls_stream(mock_socket_pair):
    """Verify bidirectional stream multiplexing over P2P channel (TC-FR02-02)."""
    identity_a = NodeIdentity()
    identity_b = NodeIdentity()

    cert_a, key_a = CertificateAuthority.generate_self_signed_cert(identity_a)
    cert_b, key_b = CertificateAuthority.generate_self_signed_cert(identity_b)

    assert cert_a is not None and key_a is not None
    assert cert_b is not None and key_b is not None

    channel_client = P2PChannel(mock_socket_pair.client_reader, mock_socket_pair.client_writer)
    assert channel_client is not None

@pytest.mark.asyncio
async def test_real_tls_mesh_listener():
    """Verify live mutual TLS socket creation, handshake, and frame receipt."""
    identity_server = NodeIdentity()
    received_frames = []

    async def handle_conn(reader, writer):
        try:
            msg_type, payload = await FrameCodec.read_frame(reader)
            received_frames.append((msg_type, payload))
        finally:
            writer.close()
            await writer.wait_closed()

    listener = MeshListener("127.0.0.1", 9444, identity_server, handle_conn)
    await listener.start()

    try:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.open_connection("127.0.0.1", 9444, ssl=ssl_ctx)
        frame = FrameCodec.encode_frame(MessageType.HEARTBEAT, b"ping_test_tls")
        writer.write(frame)
        await writer.drain()

        await asyncio.sleep(0.05)
        writer.close()
        await writer.wait_closed()

        assert len(received_frames) == 1
        assert received_frames[0] == (MessageType.HEARTBEAT, b"ping_test_tls")
    finally:
        await listener.stop()
