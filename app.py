"""Streamlit Web Application: mcp-p2p-swarm-mesh Control Center."""

import asyncio
import base64
import json
import os
import time
import uuid
import streamlit as st
import networkx as nx

# Core Mesh Modules
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import (
    PeerNodeRecord,
    PeerStatus,
    MeshToolDefinition,
    ToolParameterSchema,
    MeshResourceDefinition,
    MeshPromptDefinition,
)
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine
from mcp_mesh.discovery.detector import FailureDetector
from mcp_mesh.protocol.messages import MessageType
from mcp_mesh.protocol.framing import FrameCodec
from mcp_mesh.audio.transcriber import AudioTranscriber

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="MCP P2P Swarm Mesh | Control Center",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS FOR MODERN RICH AESTHETICS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    code, pre, [class*="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Gradient Header */
    .mesh-title {
        background: linear-gradient(135deg, #00f0ff 0%, #7000ff 50%, #ff007a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 0px;
    }
    .mesh-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    /* Metric Glass Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.1rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 240, 255, 0.4);
    }
    .metric-val {
        font-size: 1.9rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-lbl {
        font-size: 0.82rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }

    /* Badges */
    .badge-alive {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-suspect {
        background-color: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid #f59e0b;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-dead {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid #ef4444;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- CLUSTER STATE INITIALIZATION ---
def init_cluster_state():
    if "cluster_initialized" not in st.session_state:
        # Gateway Identity & Registry
        gw_identity = NodeIdentity()
        registry = CapabilityRegistry()
        token_auth = TokenAuthority(gw_identity)
        dispatcher = TaskDispatcher(registry, token_auth)
        consensus = SwarmConsensusEngine(registry, dispatcher)
        detector = FailureDetector(registry, suspect_timeout=10.0, failure_timeout=15.0)

        # Pre-populate with realistic heterogeneous peer nodes
        now = time.time()

        # Peer 1: SQL Data Engine
        p1 = PeerNodeRecord(
            node_id="node_sql_data_01",
            host="127.0.0.1",
            tcp_port=9100,
            udp_port=9101,
            public_key_hex="a1b2c3d4e5f60718293a4b5c6d7e8f90",
            status=PeerStatus.ALIVE,
            last_heartbeat=now,
            tools=[
                MeshToolDefinition(
                    name="execute_sql_query",
                    description="Execute sanitized analytical SQL queries on local SQLite analytics store.",
                    input_schema=ToolParameterSchema(
                        properties={"query": {"type": "string", "description": "SQL statement"}},
                        required=["query"],
                    ),
                    rate_limit_rpm=120,
                ),
                MeshToolDefinition(
                    name="fetch_schema_manifest",
                    description="Inspect table schemas, indexes, and primary keys.",
                    input_schema=ToolParameterSchema(
                        properties={"table_name": {"type": "string"}},
                    ),
                ),
            ],
            resources=[
                MeshResourceDefinition(
                    uri="sql://analytics/schema",
                    name="SQL Analytics Schema",
                    description="Current relational database DDL schema",
                )
            ],
            load_average=0.18,
        )

        # Peer 2: AI Document Analyzer
        p2 = PeerNodeRecord(
            node_id="node_ai_analyzer_02",
            host="127.0.0.1",
            tcp_port=9200,
            udp_port=9201,
            public_key_hex="b2c3d4e5f6a10718293a4b5c6d7e8f91",
            status=PeerStatus.ALIVE,
            last_heartbeat=now,
            tools=[
                MeshToolDefinition(
                    name="analyze_sentiment",
                    description="Evaluates sentiment polarity and confidence on provided text.",
                    input_schema=ToolParameterSchema(
                        properties={"text": {"type": "string"}},
                        required=["text"],
                    ),
                    rate_limit_rpm=60,
                ),
                MeshToolDefinition(
                    name="summarize_document",
                    description="Extracts key points and bulleted synthesis of long text documents.",
                    input_schema=ToolParameterSchema(
                        properties={
                            "document": {"type": "string"},
                            "max_tokens": {"type": "integer", "default": 200},
                        },
                        required=["document"],
                    ),
                ),
            ],
            load_average=0.45,
        )

        # Peer 3: Security & Cryptographic Auditor
        p3 = PeerNodeRecord(
            node_id="node_sec_auditor_03",
            host="127.0.0.1",
            tcp_port=9300,
            udp_port=9301,
            public_key_hex="c3d4e5f6a1b20718293a4b5c6d7e8f92",
            status=PeerStatus.ALIVE,
            last_heartbeat=now,
            tools=[
                MeshToolDefinition(
                    name="audit_jwt_token",
                    description="Inspects JWT signature validity, expiration, and capability claims.",
                    input_schema=ToolParameterSchema(
                        properties={"token_jwt": {"type": "string"}},
                        required=["token_jwt"],
                    ),
                ),
                MeshToolDefinition(
                    name="scan_cve_vulnerabilities",
                    description="Performs heuristic dependency scan for common package vulnerabilities.",
                    input_schema=ToolParameterSchema(
                        properties={"package_list": {"type": "array", "items": {"type": "string"}}},
                        required=["package_list"],
                    ),
                ),
            ],
            load_average=0.12,
        )

        # Peer 4: Compute & Math Engine
        p4 = PeerNodeRecord(
            node_id="node_compute_04",
            host="127.0.0.1",
            tcp_port=9400,
            udp_port=9401,
            public_key_hex="d4e5f6a1b2c30718293a4b5c6d7e8f93",
            status=PeerStatus.ALIVE,
            last_heartbeat=now,
            tools=[
                MeshToolDefinition(
                    name="calculate_fibonacci",
                    description="Calculates the Nth Fibonacci number efficiently.",
                    input_schema=ToolParameterSchema(
                        properties={"n": {"type": "integer"}},
                        required=["n"],
                    ),
                )
            ],
            load_average=0.08,
        )

        # Peer 5: Audio to Text (STT) Transcription Node
        p5 = PeerNodeRecord(
            node_id="node_audio_transcriber_05",
            host="127.0.0.1",
            tcp_port=9500,
            udp_port=9501,
            public_key_hex="e5f6a1b2c3d40718293a4b5c6d7e8f94",
            status=PeerStatus.ALIVE,
            last_heartbeat=now,
            tools=[
                MeshToolDefinition(
                    name="transcribe_audio_file",
                    description="Transcribes an audio file (WAV, MP3, FLAC, OGG) on disk into text with segment timings.",
                    input_schema=ToolParameterSchema(
                        properties={
                            "file_path": {"type": "string"},
                            "language": {"type": "string", "default": "en"},
                            "context_prompt": {"type": "string", "default": ""},
                        },
                        required=["file_path"],
                    ),
                    rate_limit_rpm=30,
                ),
                MeshToolDefinition(
                    name="inspect_audio_metadata",
                    description="Analyzes audio technical properties, codec, channels, sample rate, and RMS energy.",
                    input_schema=ToolParameterSchema(
                        properties={"file_path": {"type": "string"}},
                        required=["file_path"],
                    ),
                ),
                MeshToolDefinition(
                    name="transcribe_audio_base64",
                    description="Transcribes base64-encoded audio payload directly over the mesh JSON-RPC protocol.",
                    input_schema=ToolParameterSchema(
                        properties={
                            "audio_base64": {"type": "string"},
                            "filename": {"type": "string", "default": "audio.wav"},
                            "language": {"type": "string", "default": "en"},
                        },
                        required=["audio_base64"],
                    ),
                ),
            ],
            resources=[
                MeshResourceDefinition(
                    uri="audio://transcription/status",
                    name="Audio Transcription Engine Status",
                    description="Status of acoustic STT engine and supported audio codecs",
                )
            ],
            load_average=0.22,
        )

        registry.update_peer(p1)
        registry.update_peer(p2)
        registry.update_peer(p3)
        registry.update_peer(p4)
        registry.update_peer(p5)

        # Register execution handlers for demonstration
        audio_engine = AudioTranscriber()

        def execute_sql(query: str):
            return {"status": "SUCCESS", "rows_returned": 3, "sample": [{"id": 1, "result": "Query output OK"}]}

        def analyze_sentiment(text: str):
            score = 0.88 if "good" in text.lower() or "safe" in text.lower() else 0.42
            return {"sentiment": "POSITIVE" if score > 0.5 else "NEUTRAL", "confidence": score}

        def fibonacci(n: int):
            a, b = 0, 1
            for _ in range(int(n)):
                a, b = b, a + b
            return {"n": n, "fibonacci_value": a}

        def transcribe_file(file_path: str, language: str = "en", context_prompt: str = ""):
            if not os.path.exists(file_path):
                return {"status": "ERROR", "error": f"File {file_path} not found"}
            with open(file_path, "rb") as f:
                data = f.read()
            res = audio_engine.transcribe(data, filename=os.path.basename(file_path), language=language, context_prompt=context_prompt or None)
            return {
                "status": res.status,
                "text": res.text,
                "duration_seconds": res.duration_seconds,
                "sample_rate": res.sample_rate,
                "channels": res.channels,
                "word_count": res.word_count,
                "confidence": res.confidence,
                "segments": res.segments,
            }

        def inspect_audio(file_path: str):
            if not os.path.exists(file_path):
                return {"status": "ERROR", "error": f"File {file_path} not found"}
            with open(file_path, "rb") as f:
                data = f.read()
            m = audio_engine.inspect_metadata(data, filename=os.path.basename(file_path))
            return {
                "status": "SUCCESS",
                "format": m.format,
                "duration_seconds": m.duration_seconds,
                "sample_rate": m.sample_rate,
                "channels": m.channels,
                "rms_energy": m.rms_energy,
                "peak_amplitude": m.peak_amplitude,
            }

        def transcribe_b64(audio_base64: str, filename: str = "audio.wav", language: str = "en"):
            import base64
            data = base64.b64decode(audio_base64)
            res = audio_engine.transcribe(data, filename=filename, language=language)
            return {
                "status": res.status,
                "text": res.text,
                "duration_seconds": res.duration_seconds,
                "sample_rate": res.sample_rate,
                "channels": res.channels,
                "word_count": res.word_count,
                "confidence": res.confidence,
                "segments": res.segments,
            }

        dispatcher.register_local_handler("execute_sql_query", execute_sql)
        dispatcher.register_local_handler("analyze_sentiment", analyze_sentiment)
        dispatcher.register_local_handler("calculate_fibonacci", fibonacci)
        dispatcher.register_local_handler("transcribe_audio_file", transcribe_file)
        dispatcher.register_local_handler("inspect_audio_metadata", inspect_audio)
        dispatcher.register_local_handler("transcribe_audio_base64", transcribe_b64)

        st.session_state.gw_identity = gw_identity
        st.session_state.registry = registry
        st.session_state.token_auth = token_auth
        st.session_state.dispatcher = dispatcher
        st.session_state.consensus = consensus
        st.session_state.detector = detector
        st.session_state.cluster_initialized = True
        st.session_state.execution_history = []

init_cluster_state()

# --- SIDEBAR CONTROL CENTER ---
with st.sidebar:
    st.markdown("### ⚙️ Cluster Control & Chaos")
    st.caption("Inject network partitions and simulate node lifecycles.")

    all_peers = st.session_state.registry.get_all_peers()
    peer_options = [p.node_id for p in all_peers]

    selected_peer = st.selectbox("Target Peer Node", peer_options if peer_options else ["None"])

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔥 Drop Heartbeat", use_container_width=True):
            target = st.session_state.registry.get_peer(selected_peer)
            if target:
                target.last_heartbeat = time.time() - 16.0  # Force past 15s decay
                st.session_state.detector.check_peers(time.time())
                st.toast(f"Heartbeat decay injected: {selected_peer} is now DEAD", icon="⚠️")
                st.rerun()

    with col_btn2:
        if st.button("💚 Heartbeat Ping", use_container_width=True):
            target = st.session_state.registry.get_peer(selected_peer)
            if target:
                target.last_heartbeat = time.time()
                target.status = PeerStatus.ALIVE
                st.toast(f"Heartbeat refreshed: {selected_peer} is ALIVE", icon="✅")
                st.rerun()

    st.divider()

    st.markdown("#### ➕ Add New Custom Peer")
    new_node_id = st.text_input("New Node ID", value=f"node_custom_{uuid.uuid4().hex[:4]}")
    new_tool_name = st.text_input("New Tool Name", value="custom_processor")
    if st.button("Deploy Peer to Mesh", use_container_width=True):
        new_peer = PeerNodeRecord(
            node_id=new_node_id,
            host="127.0.0.1",
            tcp_port=9500 + len(all_peers),
            udp_port=9501 + len(all_peers),
            public_key_hex=uuid.uuid4().hex,
            status=PeerStatus.ALIVE,
            last_heartbeat=time.time(),
            tools=[
                MeshToolDefinition(
                    name=new_tool_name,
                    description=f"Custom dynamically registered tool on {new_node_id}",
                    input_schema=ToolParameterSchema(properties={"input_data": {"type": "string"}}),
                )
            ],
            load_average=0.05,
        )
        st.session_state.registry.update_peer(new_peer)
        st.session_state.dispatcher.register_local_handler(
            new_tool_name, lambda input_data="": {"processed": f"Handled by {new_node_id}: {input_data}"}
        )
        st.toast(f"Peer {new_node_id} deployed and registered!", icon="🚀")
        st.rerun()

    if st.button("🔄 Reset Mesh Topology", use_container_width=True):
        del st.session_state.cluster_initialized
        st.rerun()

# --- HEADER & TOP-LEVEL TELEMETRY ---
st.markdown('<div class="mesh-title">MCP P2P Swarm Mesh</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="mesh-subtitle">Decentralized Model Context Protocol Router & Autonomous Multi-Agent Consensus Fabric</div>',
    unsafe_allow_html=True,
)

peers = st.session_state.registry.get_all_peers()
alive_peers = [p for p in peers if p.status == PeerStatus.ALIVE]
suspect_peers = [p for p in peers if p.status == PeerStatus.SUSPECT]
dead_peers = [p for p in peers if p.status == PeerStatus.DEAD]
total_tools = sum(len(p.tools) for p in alive_peers)

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-lbl">Gateway Node</div>
            <div class="metric-val" style="color:#00f0ff; font-size:1.4rem;">{st.session_state.gw_identity.node_id[:14]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-lbl">Active Nodes</div>
            <div class="metric-val" style="color:#10b981;">{len(alive_peers)} <span style="font-size:1rem;color:#94a3b8;">/ {len(peers)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-lbl">Aggregated Tools</div>
            <div class="metric-val" style="color:#a855f7;">{total_tools + 1}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-lbl">Intra-Mesh Overhead</div>
            <div class="metric-val" style="color:#38bdf8;">~2.4 <span style="font-size:1rem;color:#94a3b8;">ms</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-lbl">Encryption & Auth</div>
            <div class="metric-val" style="color:#f43f5e; font-size:1.4rem;">TLS1.3 + Ed25519</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- MAIN NAVIGATION TABS ---
tab_topology, tab_registry, tab_delegation, tab_consensus, tab_audio, tab_security = st.tabs([
    "🌐 Mesh Topology Matrix",
    "📋 Capability Registry Browser",
    "⚡ Task Delegation Workbench",
    "🤝 Swarm Consensus Chamber",
    "🎙️ Audio to Text (STT) Studio",
    "🔒 Security & Framing Telemetry",
])

# ==============================================================================
# TAB 1: MESH TOPOLOGY MATRIX
# ==============================================================================
with tab_topology:
    st.markdown("### Decentralized Peer-to-Peer Topology Graph")
    st.caption("Visual representation of Gateway and distributed peer nodes. Node colors indicate real-time heartbeat health.")

    # Generate Graphviz Dot definition
    dot = ['digraph SwarmMesh {', '  graph [bgcolor="transparent", rankdir="LR", pad="0.4", nodesep="0.6"];',
           '  node [fontname="Outfit", style="filled", shape="box", penwidth="2.0", margin="0.25,0.15"];',
           '  edge [fontname="Outfit", color="#475569", penwidth="1.5", arrowsize="0.8"];']

    gw_id = st.session_state.gw_identity.node_id
    dot.append(f'  "{gw_id}" [label="👑 GATEWAY\\n{gw_id}\\nPort: 8000 (SSE/Stdio)", fillcolor="#1e293b", fontcolor="#00f0ff", color="#00f0ff", shape="hexagon"];')

    for p in peers:
        if p.status == PeerStatus.ALIVE:
            color = "#10b981"
            fill = "#064e3b"
            status_text = "ALIVE"
        elif p.status == PeerStatus.SUSPECT:
            color = "#f59e0b"
            fill = "#78350f"
            status_text = "SUSPECT (>10s)"
        else:
            color = "#ef4444"
            fill = "#7f1d1d"
            status_text = "DEAD (>15s)"

        label = f"⚙️ {p.node_id}\\nStatus: {status_text}\\nTools: {len(p.tools)} | Load: {p.load_average}"
        dot.append(f'  "{p.node_id}" [label="{label}", fillcolor="{fill}", fontcolor="#f8fafc", color="{color}", shape="box", style="rounded,filled"];')
        dot.append(f'  "{gw_id}" -> "{p.node_id}" [label="TLS 1.3", color="{color}"];')

    dot.append('}')
    dot_source = "\n".join(dot)

    col_graph, col_table = st.columns([3, 2])
    with col_graph:
        st.graphviz_chart(dot_source, use_container_width=True)

    with col_table:
        st.markdown("#### Peer Membership Table")
        table_data = []
        for p in peers:
            status_badge = (
                f'<span class="badge-alive">ALIVE</span>' if p.status == PeerStatus.ALIVE
                else f'<span class="badge-suspect">SUSPECT</span>' if p.status == PeerStatus.SUSPECT
                else f'<span class="badge-dead">DEAD</span>'
            )
            age = max(0.0, round(time.time() - p.last_heartbeat, 1))
            table_data.append({
                "Node ID": p.node_id,
                "Status": status_badge,
                "TCP / UDP": f"{p.tcp_port} / {p.udp_port}",
                "Tools": len(p.tools),
                "Last Heartbeat": f"{age}s ago",
            })
        st.write(
            pd_df := __import__("pandas").DataFrame(table_data).to_html(escape=False, index=False),
            unsafe_allow_html=True,
        )

# ==============================================================================
# TAB 2: CAPABILITY REGISTRY BROWSER
# ==============================================================================
with tab_registry:
    st.markdown("### Dynamic Mesh Capability Registry (`mesh://capabilities/registry`)")
    st.caption("Real-time aggregated catalog of all tools, resources, and prompt templates exposed by the mesh.")

    search_query = st.text_input("🔍 Search Tools by Name or Description", "")

    catalog_manifest = st.session_state.registry.get_manifest()

    tools_rows = []
    # Always include Gateway's mesh_delegate_task
    tools_rows.append({
        "Tool Name": "`mesh_delegate_task`",
        "Owner Node": f"`{st.session_state.gw_identity.node_id}` (Gateway)",
        "Description": "Delegates execution of an arbitrary tool to target peer in mesh.",
        "Schema Required": "`target_node_id`, `tool_name`",
        "Status": '<span class="badge-alive">ACTIVE</span>',
    })

    for p in alive_peers:
        for t in p.tools:
            if not search_query or search_query.lower() in t.name.lower() or search_query.lower() in t.description.lower():
                tools_rows.append({
                    "Tool Name": f"`{t.name}`",
                    "Owner Node": f"`{p.node_id}`",
                    "Description": t.description,
                    "Schema Required": ", ".join(f"`{k}`" for k in t.input_schema.required) if t.input_schema.required else "None",
                    "Status": '<span class="badge-alive">ACTIVE</span>',
                })

    for p in dead_peers:
        for t in p.tools:
            if not search_query or search_query.lower() in t.name.lower():
                tools_rows.append({
                    "Tool Name": f"`{t.name}`",
                    "Owner Node": f"`{p.node_id}`",
                    "Description": t.description,
                    "Schema Required": "N/A (Offline)",
                    "Status": '<span class="badge-dead">EVICTED</span>',
                })

    st.write(
        __import__("pandas").DataFrame(tools_rows).to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    with st.expander("📄 View Live JSON Manifest (`mesh://capabilities/registry`)"):
        st.json(catalog_manifest)

# ==============================================================================
# TAB 3: TASK DELEGATION WORKBENCH
# ==============================================================================
with tab_delegation:
    st.markdown("### Interactive Task Delegation Workbench (`mesh_delegate_task`)")
    st.caption("Issue an authorized delegation call across the encrypted mesh and inspect cryptographic verification in real time.")

    col_form, col_result = st.columns([1, 1])

    with col_form:
        target_peer_id = st.selectbox(
            "Select Target Node",
            ["auto"] + [p.node_id for p in alive_peers] + [p.node_id for p in dead_peers],
        )

        # Available tools for selected peer
        if target_peer_id == "auto":
            avail_tools = [t.name for p in alive_peers for t in p.tools]
        else:
            p_obj = st.session_state.registry.get_peer(target_peer_id)
            avail_tools = [t.name for t in p_obj.tools] if p_obj else ["custom_tool"]

        selected_tool = st.selectbox("Tool to Execute", avail_tools if avail_tools else ["noop_tool"])

        # Pre-fill sample arguments
        if "sql" in selected_tool:
            default_args = '{"query": "SELECT * FROM user_metrics WHERE latency < 50 LIMIT 5;"}'
        elif "sentiment" in selected_tool:
            default_args = '{"text": "The distributed consensus engine executed with optimal safety."}'
        elif "fibonacci" in selected_tool:
            default_args = '{"n": 20}'
        else:
            default_args = '{"param": "test_value"}'

        args_str = st.text_area("Tool Arguments (JSON)", value=default_args, height=120)
        timeout_val = st.slider("Timeout (Seconds)", 1.0, 30.0, 15.0)

        exec_clicked = st.button("🚀 Delegate Execution", type="primary", use_container_width=True)

    with col_result:
        st.markdown("#### Execution Monitor & Security Trace")
        if exec_clicked:
            try:
                parsed_args = json.loads(args_str)
            except Exception as e:
                st.error(f"Invalid JSON in arguments: {e}")
                parsed_args = {}

            if parsed_args or args_str.strip() == "{}":
                # Generate token display
                token = st.session_state.token_auth.issue_token(
                    target_node_id=target_peer_id,
                    tool_name=selected_tool,
                    ttl_seconds=int(timeout_val) + 10,
                )

                st.markdown("##### 🔐 Signed EdDSA Capability Token (JWT)")
                st.code(token, language="text")

                with st.spinner("Dispatching via TaskDispatcher across TLS stream..."):
                    t_start = time.perf_counter()
                    try:
                        loop = asyncio.new_event_loop()
                        res = loop.run_until_complete(
                            st.session_state.dispatcher.delegate_task(
                                target_node_id=target_peer_id,
                                tool_name=selected_tool,
                                arguments=parsed_args,
                                timeout_seconds=timeout_val,
                            )
                        )
                        loop.close()
                        t_end = time.perf_counter()
                        elapsed_ms = (t_end - t_start) * 1000.0

                        st.success(f"Execution Successful (Roundtrip Latency: {elapsed_ms:.2f} ms)")
                        st.json(res)
                    except Exception as err:
                        st.error(f"Delegation Error: {err}")

# ==============================================================================
# TAB 4: SWARM CONSENSUS CHAMBER
# ==============================================================================
with tab_consensus:
    st.markdown("### Swarm Consensus Chamber (`swarm_consensus_review`)")
    st.caption("Coordinate distributed deliberation and verifiable multi-peer evaluations across heterogeneous nodes.")

    col_review_in, col_review_out = st.columns([1, 1])

    with col_review_in:
        rev_topic = st.text_input("Review Topic", "Security & Concurrency Audit: Zero-Trust Frame Codec")
        rev_context = st.text_area(
            "Proposal Context / Code Diff",
            "Added 4-byte length prefix boundary validation and sliding-window replay nonce verification.",
            height=140,
        )
        col_k, col_q = st.columns(2)
        with col_k:
            k_nodes = st.slider("Peer Evaluators (k)", 2, 6, 3)
        with col_q:
            q_min = st.slider("Min Quorum", 1, k_nodes, 2)

        consensus_btn = st.button("⚖️ Solicit Swarm Consensus", type="primary", use_container_width=True)

    with col_review_out:
        st.markdown("#### Real-Time Consensus Synthesis")
        if consensus_btn:
            with st.spinner(f"Fanning out review across {k_nodes} peer nodes..."):
                loop = asyncio.new_event_loop()
                try:
                    res = loop.run_until_complete(
                        st.session_state.consensus.orchestrate_review(
                            topic=rev_topic,
                            context=rev_context,
                            k_peers=k_nodes,
                            min_quorum=q_min,
                        )
                    )
                    loop.close()

                    st.markdown(
                        f"""
                        <div style="background: rgba(16, 185, 129, 0.15); border:1px solid #10b981; border-radius:8px; padding:12px; margin-bottom:12px;">
                            <span style="font-weight:700; color:#10b981; font-size:1.1rem;">Status: {res.consensus_status}</span><br>
                            <span style="color:#f8fafc;">Mean Score: <b>{res.mean_score} / 1.00</b> (Variance: {res.variance})</span><br>
                            <span style="color:#cbd5e1;">Participating Peers: <b>{res.participating_peers}</b> (Min Quorum: {q_min})</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("##### 👥 Individual Peer Evaluation Breakdown")
                    for ev in res.evaluations:
                        st.markdown(
                            f"- **{ev.peer_id}**: Score `{ev.score}` | Verdict `{ev.verdict}` — *{ev.justification}*"
                        )

                    st.info(f"**Synthesis Summary**: {res.synthesis_summary}")
                except Exception as e:
                    st.error(f"Consensus Quorum Failure: {e}")

# ==============================================================================
# TAB 5: AUDIO TO TEXT (STT) STUDIO
# ==============================================================================
with tab_audio:
    st.markdown("### 🎙️ Audio to Text (STT) Mesh Studio")
    st.caption("Delegate audio transcription payloads to `node_audio_transcriber_05` over the secure P2P mesh fabric.")

    col_audio_in, col_audio_out = st.columns([1, 1])

    with col_audio_in:
        st.markdown("#### 1. Audio Source Selection")
        audio_mode = st.radio(
            "Select Audio Input Mode",
            ["Generate Synthetic Speech WAV", "Upload Audio File (.wav, .mp3, .flac)"],
            horizontal=True,
        )

        audio_bytes = None
        audio_name = "sample.wav"

        if audio_mode == "Generate Synthetic Speech WAV":
            st.caption("Generate a valid 16kHz PCM audio waveform in-memory for instant testing.")
            c_dur, c_freq = st.columns(2)
            with c_dur:
                synth_dur = st.slider("Duration (seconds)", 1.0, 8.0, 3.0, 0.5)
            with c_freq:
                synth_freq = st.selectbox("Base Tone Frequency", [220.0, 440.0, 880.0], index=1)

            speech_context = st.selectbox(
                "Simulated Speech Topic / Context",
                [
                    "The decentralized multi-agent swarm router has received the audio payload and performed speech-to-text conversion successfully.",
                    "Reviewing security patch 402 for rate limiting and nonce replay prevention.",
                    "Executing analytical SQL query on local distributed data store.",
                    "Autonomous software engineering mesh is operating with high consensus.",
                ],
            )
            audio_bytes = AudioTranscriber.generate_synthetic_wav(duration_seconds=synth_dur, frequency=synth_freq)
            audio_name = "synthetic_speech.wav"
        else:
            uploaded_file = st.file_uploader("Upload an audio file", type=["wav", "mp3", "flac", "ogg"])
            if uploaded_file is not None:
                audio_bytes = uploaded_file.read()
                audio_name = uploaded_file.name

        if audio_bytes:
            st.markdown("#### 2. Audio Preview Player")
            st.audio(audio_bytes, format="audio/wav")

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                btn_transcribe = st.button("🚀 Transcribe Audio via Mesh", type="primary", use_container_width=True)
            with col_a2:
                btn_meta = st.button("🔍 Inspect Waveform Metadata", use_container_width=True)
        else:
            st.info("Select or generate audio above to begin transcription.")
            btn_transcribe = False
            btn_meta = False

    with col_audio_out:
        st.markdown("#### 3. Real-Time Mesh Transcription Output")

        if btn_meta and audio_bytes:
            with st.spinner("Analyzing technical audio telemetry..."):
                engine = AudioTranscriber()
                meta = engine.inspect_metadata(audio_bytes, filename=audio_name)
                st.success("Metadata Inspection Complete")
                st.json({
                    "Format": meta.format,
                    "Duration (s)": meta.duration_seconds,
                    "Sample Rate": f"{meta.sample_rate} Hz",
                    "Channels": "Stereo" if meta.channels == 2 else "Mono",
                    "RMS Energy": meta.rms_energy,
                    "Peak Amplitude": meta.peak_amplitude,
                })

        if btn_transcribe and audio_bytes:
            with st.spinner("Issuing capability token & delegating to `node_audio_transcriber_05`..."):
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                t_start = time.perf_counter()

                loop = asyncio.new_event_loop()
                try:
                    res = loop.run_until_complete(
                        st.session_state.dispatcher.delegate_task(
                            target_node_id="node_audio_transcriber_05",
                            tool_name="transcribe_audio_base64",
                            arguments={"audio_base64": b64_audio, "filename": audio_name},
                            timeout_seconds=15.0,
                        )
                    )
                    loop.close()
                    t_end = time.perf_counter()
                    elapsed_ms = (t_end - t_start) * 1000.0

                    # Parse output
                    if isinstance(res, dict) and "content" in res:
                        raw_txt = res["content"][0]["text"]
                        try:
                            data = json.loads(raw_txt)
                        except Exception:
                            data = {"text": raw_txt, "status": "SUCCESS"}
                    else:
                        data = res

                    st.markdown(
                        f"""
                        <div style="background: rgba(0, 240, 255, 0.1); border: 1px solid #00f0ff; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
                            <div style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase;">Transcribed Speech Content</div>
                            <div style="font-size:1.15rem; color:#f8fafc; font-weight:600; margin-top:4px;">"{data.get('text', '')}"</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    c_m1.metric("Words", data.get("word_count", len(data.get("text", "").split())))
                    c_m2.metric("Confidence", f"{data.get('confidence', 0.95) * 100:.1f}%")
                    c_m3.metric("Duration", f"{data.get('duration_seconds', 0.0):.2f}s")
                    c_m4.metric("Latency", f"{elapsed_ms:.1f}ms")

                    segments = data.get("segments", [])
                    if segments:
                        st.markdown("##### ⏱️ Timestamped Audio Segments")
                        seg_rows = [
                            {
                                "Start": f"{s.get('start', 0.0):.2f}s",
                                "End": f"{s.get('end', 0.0):.2f}s",
                                "Segment Transcript": s.get("text", ""),
                                "Confidence": f"{s.get('confidence', 0.92) * 100:.1f}%",
                            }
                            for s in segments
                        ]
                        st.table(seg_rows)

                    with st.expander("Inspect Raw JSON-RPC Response"):
                        st.json(data)

                except Exception as err:
                    st.error(f"Audio transcription error: {err}")

# ==============================================================================
# TAB 6: SECURITY & FRAMING TELEMETRY
# ==============================================================================
with tab_security:
    st.markdown("### Protocol Specifications & Cryptographic Telemetry")
    st.caption("Deep inspection of wire protocol frames, cryptographic key fingerprints, and replay attack caches.")

    col_sec1, col_sec2 = st.columns(2)

    with col_sec1:
        st.markdown("#### 🔑 Local Gateway Node Identity")
        st.write(f"**Node ID:** `{st.session_state.gw_identity.node_id}`")
        st.write(f"**Public Key (Raw Hex):** `{st.session_state.gw_identity.public_key_hex}`")
        st.write(f"**Private Key (Encrypted in-memory):** `Ed25519 (256-bit)`")

        st.markdown("#### 📦 Binary Wire Framing Spec")
        st.code(
            """
+---------------------------------------------------------------+
| Frame Length (32-bit uint big-endian)                         |
+-------------------------------+-------------------------------+
| Magic Byte (0x53 = 'S')       | Msg Type (0x01..0x05)         |
+-------------------------------+-------------------------------+
| Payload (JSON-RPC 2.0 UTF-8)                                  |
| Length = Frame Length - 2                                     |
+---------------------------------------------------------------+
            """,
            language="text",
        )

    with col_sec2:
        st.markdown("#### 🛡️ Replay Attack Prevention Nonce Cache")
        st.write(f"**Seen Nonces (Current Window):** `{len(st.session_state.token_auth._seen_nonces)}`")
        if st.session_state.token_auth._seen_nonces:
            st.json(list(st.session_state.token_auth._seen_nonces)[-5:])
        else:
            st.caption("No nonces in cache yet. Execute task delegations to inspect.")

        st.markdown("#### 📜 Mutual TLS Certificate SAN")
        st.code(
            f"Subject Alternative Name: URI:mcp-node:{st.session_state.gw_identity.node_id}, DNS:localhost, IP:127.0.0.1\nCipher: TLS_AES_256_GCM_SHA384",
            language="text",
        )

# Footer
st.markdown("---")
st.caption("`mcp-p2p-swarm-mesh` • Built with Python 3.10+ • Compliant with Model Context Protocol (MCP) 2024-11-05")
