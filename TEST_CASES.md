# Detailed Test Cases: `mcp-p2p-swarm-mesh`

This document defines the formal, granular test case specifications for `mcp-p2p-swarm-mesh`. Every test case maps directly to the system's Functional Requirements (`FR-01` to `FR-05`), Non-Functional Requirements (`NFR-01` to `NFR-04`), and Edge Cases (`EC-01` to `EC-04`).

---

## 1. Functional Requirement Test Cases

### TC-FR01-01: Gateway Initialization & Stdio Transport
* **Requirement**: `FR-01` (Gateway Node Lifecycle)
* **Test File**: `tests/unit/test_gateway_lifecycle.py`
* **Test Method**: `test_gateway_initialization_stdio()`
* **Pre-conditions**: Gateway configuration initialized with valid node identity.
* **Test Steps**:
  1. Instantiate `GatewayMcpServer` with Stdio transport configuration.
  2. Start the gateway server session over a mocked Stdio pipe (`asyncio.StreamReader` / `StreamWriter`).
  3. Send MCP JSON-RPC `initialize` frame (`capabilities`, `protocolVersion: "2024-11-05"`).
  4. Receive response frame and inspect protocol handshake.
* **Expected Result**: Gateway returns HTTP 200 / JSON-RPC success containing server info `{"name": "mcp-p2p-swarm-gateway", "version": "1.0.0"}` and advertises `tools`, `resources`, and `prompts` capabilities.

---

### TC-FR01-02: Gateway SSE Transport & Session Lifecycle
* **Requirement**: `FR-01` (Gateway Node Lifecycle)
* **Test File**: `tests/unit/test_gateway_lifecycle.py`
* **Test Method**: `test_gateway_sse_transport_lifecycle()`
* **Pre-conditions**: Gateway initialized with SSE transport binding to `127.0.0.1:8000`.
* **Test Steps**:
  1. Launch Gateway SSE endpoint using async Starlette test client.
  2. Initiate SSE GET connection to `/sse`.
  3. Verify reception of `endpoint` event containing unique session URL.
  4. Post JSON-RPC `tools/list` request to the session endpoint.
* **Expected Result**: The session endpoint successfully receives the request and yields the tool list over the established SSE event stream.

---

### TC-FR02-01: P2P Gossip Broadcast & Neighbor Discovery
* **Requirement**: `FR-02` (P2P Transport & Node Discovery)
* **Test File**: `tests/integration/test_discovery_gossip.py`
* **Test Method**: `test_p2p_gossip_discovery_three_nodes()`
* **Pre-conditions**: Three independent `MeshNode` instances (Node A, Node B, Node C) configured with random localhost UDP ports.
* **Test Steps**:
  1. Start Node A as seed listener.
  2. Start Node B and Node C with Node A set as bootstrap peer.
  3. Allow 2 gossip heartbeat cycles (6 seconds virtual time).
  4. Query `node_b.peer_table` and `node_c.peer_table`.
* **Expected Result**: Node B discovers Node C (and vice-versa) via gossip exchange through Node A; all three nodes list each other as `ALIVE` with accurate IP, TCP port, and public keys.

---

### TC-FR02-02: Encrypted Bi-Directional Stream Establishment (TLS 1.3)
* **Requirement**: `FR-02` & `NFR-02` (Encrypted Transport)
* **Test File**: `tests/integration/test_transport_tls.py`
* **Test Method**: `test_bidirectional_tls_stream()`
* **Pre-conditions**: Two nodes configured with in-memory self-signed Ed25519 X.509 certificates.
* **Test Steps**:
  1. Start Node A TLS server listener.
  2. Initiate outbound `P2PChannel` connection from Node B to Node A.
  3. Validate TLS cipher suite negotiation.
  4. Transmit ping/pong frame over the encrypted channel.
* **Expected Result**: Mutual TLS handshake succeeds with cipher suite `TLS_AES_256_GCM_SHA384`; frames transmit and decrypt with zero data corruption.

---

### TC-FR03-01: Capability Advertising & Registry Aggregation
* **Requirement**: `FR-03` (Dynamic Capability Registry)
* **Test File**: `tests/integration/test_capability_registry.py`
* **Test Method**: `test_registry_capability_aggregation()`
* **Pre-conditions**: Gateway Node active; Peer Node A advertises `query_database`, Peer Node B advertises `generate_code`.
* **Test Steps**:
  1. Deliver gossip heartbeat from Peer Node A containing `query_database` tool metadata.
  2. Deliver gossip heartbeat from Peer Node B containing `generate_code` tool metadata.
  3. Inspect Gateway's `CapabilityRegistry.catalog`.
* **Expected Result**: Registry contains both tools mapped to their respective owner node IDs, input schemas, and network endpoints.

---

### TC-FR03-02: Dynamic Resource Expose `mesh://capabilities/registry`
* **Requirement**: `FR-03` (Dynamic Capability Registry)
* **Test File**: `tests/integration/test_capability_registry.py`
* **Test Method**: `test_mesh_capabilities_resource_read()`
* **Pre-conditions**: Gateway connected to active mesh with 2 registered peers.
* **Test Steps**:
  1. Send MCP `resources/read` request to Gateway with URI `mesh://capabilities/registry`.
  2. Parse the returned JSON text content.
* **Expected Result**: Content is valid JSON-RPC resource with mime type `application/json`, containing an active nodes list, aggregated tools inventory, and current mesh topology status.

---

### TC-FR04-01: Distributed Task Delegation via `mesh_delegate_task`
* **Requirement**: `FR-04` (Distributed Task Delegation)
* **Test File**: `tests/integration/test_task_delegation.py`
* **Test Method**: `test_successful_task_delegation()`
* **Pre-conditions**: Gateway Node connected to Worker Node A providing tool `calculate_fibonacci`.
* **Test Steps**:
  1. Issue MCP `tools/call` request to Gateway:
     ```json
     {
       "name": "mesh_delegate_task",
       "arguments": {
         "target_node_id": "node_worker_a",
         "tool_name": "calculate_fibonacci",
         "arguments": {"n": 10}
       }
     }
     ```
  2. Gateway signs JWT capability token and dispatches internal `mesh/execute` frame over TLS.
  3. Worker Node A verifies token, executes tool, and returns result `55`.
* **Expected Result**: Gateway forwards the execution output to caller as a successful MCP tool response.

---

### TC-FR04-02: Task Delegation Stream Chunking & Async Progress
* **Requirement**: `FR-04` (Streaming Responses)
* **Test File**: `tests/integration/test_task_delegation.py`
* **Test Method**: `test_streaming_task_delegation()`
* **Pre-conditions**: Worker Node provides long-running tool `stream_data_processing`.
* **Test Steps**:
  1. Dispatch `mesh_delegate_task` with streaming enabled.
  2. Worker sends 3 `RPC_STREAM_CHUNK` (Type `0x03`) frames followed by final `RPC_RESPONSE` (Type `0x02`).
  3. Inspect Gateway chunk queue and client notifications.
* **Expected Result**: All 3 progress chunks are received sequentially by the Gateway without frame tearing, followed by the final completion payload.

---

### TC-FR05-01: Swarm Consensus Review Orchestration
* **Requirement**: `FR-05` (Swarm Consensus Prompts)
* **Test File**: `tests/integration/test_swarm_consensus.py`
* **Test Method**: `test_swarm_consensus_review_success()`
* **Pre-conditions**: 3 peer nodes active in mesh with consensus evaluation handler enabled.
* **Test Steps**:
  1. Issue MCP `prompts/get` or tool execution for `swarm_consensus_review` with:
     * `topic`: "Approve Security Patch #402"
     * `context`: "Diff adding rate limiting to socket layer"
     * `k_peers`: 3
  2. Swarm orchestrator fans out evaluation requests to all 3 peers.
  3. Peers return scores `[0.90, 0.85, 0.95]`.
* **Expected Result**: Consensus engine synthesizes results into a unified consensus report with mean score `0.90`, unanimous approval verdict, and compiled peer justifications.

---

### TC-FR05-02: Consensus Quorum Failure Handling
* **Requirement**: `FR-05` (Consensus Fault Resilience)
* **Test File**: `tests/integration/test_swarm_consensus.py`
* **Test Method**: `test_swarm_consensus_quorum_failure()`
* **Pre-conditions**: 3 peers requested, but 2 peers fail to respond within timeout window.
* **Test Steps**:
  1. Trigger `swarm_consensus_review` with `k_peers=3, min_quorum=2, timeout_seconds=2.0`.
  2. Mock timeouts on 2 of the 3 peers.
* **Expected Result**: Orchestrator raises `ConsensusQuorumFailedError` and reports partial evaluation results with an explicit quorum failure advisory.

---

## 2. Non-Functional Requirement Test Cases

### TC-NFR01-01: Python 3.10+ Strict Typing & Compatibility
* **Requirement**: `NFR-01` (Tech Stack Constraint)
* **Test File**: `tests/unit/test_compatibility.py`
* **Test Method**: `test_python_typing_and_syntax()`
* **Test Steps**: Run `mypy --strict mcp_mesh` and inspect type annotations.
* **Expected Result**: 0 type errors; full compliance with modern Python typing (`list[str]`, `dict[str, Any]`, `X | Y`).

---

### TC-NFR02-01: Capability Token Authorization & Scope Enforcement
* **Requirement**: `NFR-02` (Security & Encryption)
* **Test File**: `tests/unit/test_security_tokens.py`
* **Test Method**: `test_token_scope_enforcement()`
* **Test Steps**:
  1. Generate JWT token scoped strictly for tool `read_logs`.
  2. Worker receives delegation request attempting to execute `delete_logs` using that token.
* **Expected Result**: Worker rejects execution with error `-32003 Unauthorized: Token scope does not permit 'delete_logs'`.

---

### TC-NFR02-02: Nonce Replay Prevention
* **Requirement**: `NFR-02` (Security & Encryption)
* **Test File**: `tests/unit/test_security_tokens.py`
* **Test Method**: `test_token_nonce_replay_rejection()`
* **Test Steps**:
  1. Generate valid token with unique `jti="nonce_12345"`.
  2. Execute valid tool call.
  3. Re-submit identical token with identical `jti` in a second request.
* **Expected Result**: Second request is rejected with `ReplayAttackDetectedError: Duplicate nonce 'nonce_12345'`.

---

### TC-NFR03-01: 15-Second Heartbeat Decay & Peer Eviction
* **Requirement**: `NFR-03` (Reliability & Fault Tolerance)
* **Test File**: `tests/integration/test_fault_tolerance.py`
* **Test Method**: `test_peer_dropout_eviction_15s()`
* **Pre-conditions**: Node A and Node B actively peering.
* **Test Steps**:
  1. Abruptly kill Node B process / stop sending gossip heartbeats.
  2. Advance virtual clock by 10.0 seconds: Verify Node B status transitions to `SUSPECT`.
  3. Advance virtual clock past 15.0 seconds.
* **Expected Result**: Failure detector marks Node B as `DEAD`; all tools belonging to Node B are purged from `CapabilityRegistry`; Gateway and active client sessions remain stable and unaffected.

---

### TC-NFR04-01: Intra-Mesh RPC Latency Overhead (< 50ms)
* **Requirement**: `NFR-04` (Performance)
* **Test File**: `tests/integration/test_performance_latency.py`
* **Test Method**: `test_intra_mesh_rpc_latency_overhead()`
* **Pre-conditions**: 2 nodes connected over localhost TLS.
* **Test Steps**:
  1. Benchmark raw execution time of an in-memory no-op tool `t_raw`.
  2. Benchmark total round-trip delegation time `t_mesh` through Gateway and P2P channel across 100 iterations.
  3. Compute overhead: `overhead = t_mesh - t_raw`.
* **Expected Result**: Mean overhead is strictly `< 50ms` (typically < 10ms on localhost).

---

## 3. Edge Case Test Cases (`EC-01` to `EC-04`)

### TC-EC01-01: Split-Brain Partition & State Reconciliation
* **Requirement**: `EC-01` (Split-Brain Scenarios)
* **Test File**: `tests/chaos/test_split_brain.py`
* **Test Method**: `test_split_brain_partition_and_heal()`
* **Test Steps**:
  1. Initialize 4 nodes: A, B, C, D.
  2. Simulate network partition isolating `{A, B}` from `{C, D}`.
  3. Advance clock 16s; verify `{A, B}` drop `{C, D}` capabilities and vice-versa.
  4. Restore network connectivity between partitions.
  5. Run anti-entropy sync cycle.
* **Expected Result**: State reconciles without conflicting capability versions; all 4 nodes re-establish full mesh visibility.

---

### TC-EC02-01: Malformed JSON-RPC Payloads & Protocol Recovery
* **Requirement**: `EC-02` (Malformed JSON-RPC Payloads)
* **Test File**: `tests/chaos/test_malformed_frames.py`
* **Test Method**: `test_malformed_wire_frames()`
* **Test Steps**:
  1. Send frame with corrupted magic byte `0xFF`.
  2. Send frame with valid magic byte but broken JSON string (`{"jsonrpc": "2.0", incomplete...`).
  3. Send frame missing required `id` parameter.
* **Expected Result**: Daemon rejects malformed frames with low-level protocol error without dropping the physical socket or crashing the event loop; subsequent valid frames execute cleanly.

---

### TC-EC03-01: Concurrent Tool Execution Congestion & Throttle
* **Requirement**: `EC-03` (Concurrent Tool Execution Congestion)
* **Test File**: `tests/chaos/test_congestion_control.py`
* **Test Method**: `test_concurrent_congestion_throttling()`
* **Test Steps**:
  1. Configure worker node with concurrency limit `10` and queue depth `20`.
  2. Launch 50 simultaneous delegation requests via `asyncio.gather`.
* **Expected Result**: The first 10 execute immediately; next 20 are queued and executed as capacity frees; remaining 20 fail fast with `-32004 Node Congested`; no memory leak or hanging coroutines.

---

### TC-EC04-01: Orphaned Stream & Abrupt Socket Disconnect Teardown
* **Requirement**: `EC-04` (Orphaned Streams)
* **Test File**: `tests/chaos/test_orphaned_streams.py`
* **Test Method**: `test_client_abrupt_disconnect_teardown()`
* **Test Steps**:
  1. Client initiates long-running streaming tool.
  2. Mid-stream, forcefully close client socket transport without sending close frame.
* **Expected Result**: Gateway catches connection reset, cancels worker delegation future, tears down reader/writer buffers, and frees all allocated socket descriptors.
