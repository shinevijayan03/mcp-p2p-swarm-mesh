"""Integration tests for Audio Transcription Mesh Node."""

import base64
import os
import tempfile
import pytest
from mcp_mesh.audio.server import create_audio_mesh_node
from mcp_mesh.audio.transcriber import AudioTranscriber
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.gateway.mcp_facade import GatewayMcpFacade
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine
from mcp_mesh.registry.models import PeerNodeRecord, PeerStatus

@pytest.mark.asyncio
async def test_audio_mesh_node_tool_registration():
    """Verify audio node registers tools and starts/stops cleanly."""
    node = create_audio_mesh_node(node_id="test_audio_node")

    tool_names = [t.name for t in node.tools]
    assert "transcribe_audio_file" in tool_names
    assert "inspect_audio_metadata" in tool_names
    assert "transcribe_audio_base64" in tool_names

    await node.start()
    await node.stop()

@pytest.mark.asyncio
async def test_transcribe_audio_file_tool():
    """Verify transcribe_audio_file tool execution on a real audio file."""
    node = create_audio_mesh_node(node_id="test_audio_node_2")
    handler = node._handlers["transcribe_audio_file"]

    wav_bytes = AudioTranscriber.generate_synthetic_wav(duration_seconds=2.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(wav_bytes)
        tf_path = tf.name

    try:
        res = handler(file_path=tf_path, language="en")
        assert res["status"] == "SUCCESS"
        assert len(res["text"]) > 0
        assert res["duration_seconds"] > 0
        assert len(res["segments"]) > 0
    finally:
        if os.path.exists(tf_path):
            os.unlink(tf_path)

@pytest.mark.asyncio
async def test_inspect_audio_metadata_tool():
    """Verify inspect_audio_metadata tool returns technical audio telemetry."""
    node = create_audio_mesh_node(node_id="test_audio_node_3")
    handler = node._handlers["inspect_audio_metadata"]

    wav_bytes = AudioTranscriber.generate_synthetic_wav(duration_seconds=1.5, sample_rate=16000)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(wav_bytes)
        tf_path = tf.name

    try:
        res = handler(file_path=tf_path)
        assert res["status"] == "SUCCESS"
        assert res["format"] == "WAV"
        assert res["sample_rate"] == 16000
        assert res["channels"] == 1
        assert res["rms_energy"] > 0
    finally:
        if os.path.exists(tf_path):
            os.unlink(tf_path)

@pytest.mark.asyncio
async def test_transcribe_audio_base64_tool():
    """Verify direct base64 audio transcription tool."""
    node = create_audio_mesh_node(node_id="test_audio_node_4")
    handler = node._handlers["transcribe_audio_base64"]

    wav_bytes = AudioTranscriber.generate_synthetic_wav(duration_seconds=1.0)
    b64_str = base64.b64encode(wav_bytes).decode("utf-8")

    res = handler(audio_base64=b64_str, filename="stream.wav")
    assert res["status"] == "SUCCESS"
    assert len(res["text"]) > 0

@pytest.mark.asyncio
async def test_audio_delegation_via_gateway_mesh():
    """Verify full end-to-end task delegation to audio node through Gateway facade."""
    registry = CapabilityRegistry()
    identity = NodeIdentity()
    token_auth = TokenAuthority(identity)
    dispatcher = TaskDispatcher(registry, token_auth)
    consensus = SwarmConsensusEngine(registry, dispatcher)
    facade = GatewayMcpFacade(registry, dispatcher, consensus)

    audio_node = create_audio_mesh_node(node_id="node_audio_prod_01")
    # Register handlers with dispatcher
    for name, fn in audio_node._handlers.items():
        dispatcher.register_local_handler(name, fn)

    # Register node record in registry
    peer = PeerNodeRecord(
        node_id="node_audio_prod_01",
        host="127.0.0.1",
        tcp_port=9500,
        udp_port=9501,
        public_key_hex="audio_pub_key",
        status=PeerStatus.ALIVE,
        last_heartbeat=1000.0,
        tools=audio_node.tools,
    )
    registry.update_peer(peer)

    # Verify tool appears in Gateway list_tools()
    tools = await facade.list_tools()
    assert any(t["name"] == "transcribe_audio_file" for t in tools)

    # Call transcribe_audio_base64 via mesh_delegate_task
    wav_bytes = AudioTranscriber.generate_synthetic_wav(duration_seconds=1.2)
    b64_str = base64.b64encode(wav_bytes).decode("utf-8")

    delegation_res = await facade.call_tool(
        "mesh_delegate_task",
        {
            "target_node_id": "node_audio_prod_01",
            "tool_name": "transcribe_audio_base64",
            "arguments": {"audio_base64": b64_str},
        },
    )

    assert delegation_res.get("isError") is False
    assert "SUCCESS" in str(delegation_res.get("content", ""))
