"""Audio Transcription Mesh Node (MCP Server in the mesh)."""

import argparse
import base64
import os
from typing import Any, Dict, List, Optional
from mcp_mesh.config import MeshConfig
from mcp_mesh.node import MeshNode
from mcp_mesh.registry.models import MeshToolDefinition, ToolParameterSchema
from mcp_mesh.audio.transcriber import AudioTranscriber

def create_audio_mesh_node(
    node_id: str = "node_audio_transcriber",
    listen_host: str = "127.0.0.1",
    tcp_port: int = 9500,
    udp_port: int = 9501,
    seeds: Optional[List[str]] = None,
) -> MeshNode:
    """Creates and configures an MCP MeshNode specializing in audio transcription."""
    node = MeshNode(
        node_id=node_id,
        listen_host=listen_host,
        tcp_port=tcp_port,
        udp_port=udp_port,
        seeds=seeds or ["127.0.0.1:9001"],
    )

    transcriber = AudioTranscriber()

    # Tool 1: Transcribe Audio File
    @node.tool(
        name="transcribe_audio_file",
        description="Transcribes an audio file (WAV, MP3, FLAC, OGG) on disk into text with segment timings.",
    )
    def transcribe_audio_file(
        file_path: str,
        language: str = "en",
        context_prompt: str = "",
    ) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {
                "status": "ERROR",
                "error": f"Audio file '{file_path}' not found on server filesystem.",
            }

        try:
            with open(file_path, "rb") as f:
                audio_bytes = f.read()

            res = transcriber.transcribe(
                audio_bytes,
                filename=os.path.basename(file_path),
                language=language,
                context_prompt=context_prompt or None,
            )
            return {
                "status": res.status,
                "file_path": file_path,
                "text": res.text,
                "duration_seconds": res.duration_seconds,
                "sample_rate": res.sample_rate,
                "channels": res.channels,
                "word_count": res.word_count,
                "confidence": res.confidence,
                "segments": res.segments,
                "metadata": res.metadata,
            }
        except Exception as e:
            return {"status": "ERROR", "error": f"Failed to transcribe audio: {e}"}

    # Tool 2: Inspect Audio Metadata
    @node.tool(
        name="inspect_audio_metadata",
        description="Analyzes audio file technical properties, codec, channels, sample rate, and RMS energy.",
    )
    def inspect_audio_metadata(file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"status": "ERROR", "error": f"Audio file '{file_path}' not found."}

        try:
            with open(file_path, "rb") as f:
                audio_bytes = f.read()

            meta = transcriber.inspect_metadata(audio_bytes, filename=os.path.basename(file_path))
            return {
                "status": "SUCCESS",
                "file_path": file_path,
                "format": meta.format,
                "duration_seconds": meta.duration_seconds,
                "sample_rate": meta.sample_rate,
                "channels": meta.channels,
                "sample_width": meta.sample_width,
                "frame_count": meta.frame_count,
                "rms_energy": meta.rms_energy,
                "peak_amplitude": meta.peak_amplitude,
            }
        except Exception as e:
            return {"status": "ERROR", "error": f"Failed to inspect audio metadata: {e}"}

    # Tool 3: Transcribe Base64 Audio
    @node.tool(
        name="transcribe_audio_base64",
        description="Transcribes base64-encoded audio payload directly over the mesh JSON-RPC protocol.",
    )
    def transcribe_audio_base64(
        audio_base64: str,
        filename: str = "audio.wav",
        language: str = "en",
    ) -> Dict[str, Any]:
        try:
            audio_bytes = base64.b64decode(audio_base64)
            res = transcriber.transcribe(audio_bytes, filename=filename, language=language)
            return {
                "status": res.status,
                "text": res.text,
                "duration_seconds": res.duration_seconds,
                "sample_rate": res.sample_rate,
                "channels": res.channels,
                "word_count": res.word_count,
                "confidence": res.confidence,
                "segments": res.segments,
                "metadata": res.metadata,
            }
        except Exception as e:
            return {"status": "ERROR", "error": f"Base64 decoding or transcription error: {e}"}

    return node

def main():
    parser = argparse.ArgumentParser(description="Run Audio Transcription Mesh Node")
    parser.add_argument("--node-id", default="node_audio_transcriber", help="Node identifier")
    parser.add_argument("--host", default="127.0.0.1", help="Listen host")
    parser.add_argument("--tcp-port", type=int, default=9500, help="TCP P2P port")
    parser.add_argument("--udp-port", type=int, default=9501, help="UDP Gossip port")
    parser.add_argument("--seeds", nargs="*", default=["127.0.0.1:9001"], help="Gossip seeds")

    args = parser.parse_args()
    node = create_audio_mesh_node(
        node_id=args.node_id,
        listen_host=args.host,
        tcp_port=args.tcp_port,
        udp_port=args.udp_port,
        seeds=args.seeds,
    )
    print(f"Starting Audio Transcription Mesh Node '{args.node_id}' on {args.host}:{args.tcp_port}...")
    node.start_and_block()

if __name__ == "__main__":
    main()
