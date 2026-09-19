# Test Strategy & Quality Assurance Architecture: `mcp-p2p-swarm-mesh`

## 1. Test Engineering Philosophy & Objectives

The testing strategy for `mcp-p2p-swarm-mesh` is rooted in **Test-Driven Development (TDD)** and distributed systems chaos engineering. Because distributed peer-to-peer networks are inherently susceptible to race conditions, partial failures, split-brain scenarios, and packet corruption, every layer is tested under deterministic fault-injection harnesses before deployment.

```
       / \
      /   \        Chaos / Partition Tests (EC-01 .. EC-04, 15s Dropouts)
     /     \       -----------------------------------------------------
    / Integration \   Multi-Node Mesh (Gossip, TLS Channels, MCP Gateway Facade)
   /               \  ----------------------------------------------------------
  /   Unit & Security \  Wire Framing, Ed25519 Cryptography, JWT Claims, Schemas
 /_____________________\ ---------------------------------------------------------------
```

### Core Verification Metrics
* **Branch Coverage**: >= 90% across `crypto`, `protocol`, `discovery`, and `router` modules.
* **Failing Baseline (Red State)**: In Phase 2, all test cases must be implemented against the skeleton/stubbed architecture to verify clean test failure without silent passes.
* **Deterministic Concurrency**: All asynchronous tests must complete without memory leaks, hanging futures, or unhandled task exceptions.

---

## 2. Test Environments & Harness Infrastructure

### 2.1 Async In-Memory Socket Pair (`MockAsyncSocketPair`)
To enable millisecond-speed testing of TLS channels and length-prefixed framing without binding OS-level TCP ports for every unit test, the harness provides an in-memory bi-directional asynchronous pipe:
```python
class MockAsyncSocketPair:
    """Provides paired asyncio.StreamReader and StreamWriter interconnected via queues."""
    def __init__(self):
        self.client_reader = asyncio.StreamReader()
        self.server_reader = asyncio.StreamReader()
        self.client_writer = MockStreamWriter(self.server_reader)
        self.server_writer = MockStreamWriter(self.client_reader)
```

### 2.2 Chaos Network Simulator (`ChaosTransport`)
For integration and resiliency testing, a specialized transport proxy injects synthetic real-world network degradations:
* **Configurable Latency**: Injects random delay `d ~ Normal(mu, sigma)`.
* **Packet Dropping**: Randomly drops UDP gossip datagrams with probability `p_drop`.
* **Byte Corruption**: Flips bits or truncates length headers to verify protocol decoders reject corrupt frames without crashing the daemon.
* **Network Partition**: Simulates two isolated partitions by rejecting all cross-partition network I/O.

### 2.3 Virtual Clock & Time Travel
Testing the 15-second heartbeat failure detector (`NFR-03`) using real clock sleeps would make test runs painfully slow and flaky. The test harness integrates virtual clock manipulation (`unittest.mock.patch("time.time")` and `asyncio.sleep` overrides) to advance simulation time deterministically in sub-second test execution.

---

## 3. Test Layers & Scope

### 3.1 Unit Testing Layer
* **Wire Protocol & Framing (`test_framing.py`)**:
  * Encode and decode valid `RPC_REQUEST`, `RPC_RESPONSE`, and `RPC_STREAM_CHUNK` frames.
  * Verify rejection of invalid magic bytes (`!= 0x53`).
  * Verify boundary enforcement against oversized frames (`> 16MB`).
  * Verify multi-chunk frame reassembly.
* **Cryptographic Identity & Certificates (`test_crypto_identity.py`)**:
  * Ed25519 keypair generation, public key serialization, and node ID hashing.
  * In-memory self-signed X.509 certificate generation with matching Subject Alternative Names.
  * Cryptographic signature creation and verification.
* **Capability Tokens & Replay Defense (`test_tokens.py`)**:
  * Token generation with valid claims (`iss`, `sub`, `exp`, `capabilities`).
  * Rejection of expired tokens (`exp < now`).
  * Rejection of tampered signatures.
  * Nonce replay detection: Verify that submitting the same token `jti` twice within the sliding window raises an `UnauthorizedTokenError`.
  * Scope enforcement: Calling an unlisted tool is rejected.

### 3.2 Integration Testing Layer
* **Decentralized Node Discovery (`test_discovery_gossip.py`)**:
  * Spin up 3 mock mesh nodes on ephemeral localhost UDP ports.
  * Verify all nodes populate their local peer tables within 2 gossip cycles.
  * Verify capability catalog aggregation across all nodes.
* **P2P Multiplexed Channel (`test_p2p_channel.py`)**:
  * Open encrypted TLS channel between two nodes.
  * Concurrently dispatch 50 interleaved requests across the same socket.
  * Verify all responses map accurately to their respective caller `Future` by `id`.
* **Gateway MCP Facade (`test_gateway_mcp.py`)**:
  * Initialize Gateway with Stdio and SSE transports.
  * Query `tools/list` and verify dynamic inclusion of `mesh_delegate_task`.
  * Query resource `mesh://capabilities/registry` and verify JSON payload matches active peers.
  * Trigger prompt `swarm_consensus_review` and verify structured review output.

---

## 4. Edge Cases & Resiliency Testing (`EC-01` .. `EC-04`)

### 4.1 Split-Brain & Partition Healing (`EC-01`)
* **Scenario**: Cluster of 5 nodes partitioned into `{A, B}` and `{C, D, E}`.
* **Verification**:
  * Partition `{A, B}` detects absence of `{C, D, E}` after 15.0s and evicts their tools.
  * Partition `{C, D, E}` continues normal operation.
  * Re-link partitions: Verify gossip anti-entropy restores the full 5-node unified capability registry within 6.0s without duplicate entries.

### 4.2 Malformed JSON-RPC Payloads (`EC-02`)
* **Scenario**: A malicious or buggy peer sends truncated JSON strings, invalid UTF-8, missing `jsonrpc: "2.0"` fields, or corrupted method signatures.
* **Verification**:
  * The `FrameCodec` and `P2PChannel` catch `json.JSONDecodeError` and `ValidationError`.
  * Send low-level `ERROR_FRAME` (Type `0x05`) back to the offending peer.
  * The Gateway and other peer sessions remain completely unaffected.

### 4.3 Concurrent Tool Execution Congestion (`EC-03`)
* **Scenario**: 100 concurrent task delegation requests flooded against a single worker node with concurrency limit set to 10.
* **Verification**:
  * The `RateLimiter` accepts 10 tasks in active execution and queues the next 50.
  * Subsequent requests exceeding queue depth receive `-32004 Peer Node Congested`.
  * No memory exhaustion or unhandled socket closure occurs.

### 4.4 Orphaned Streams & Client Abort (`EC-04`)
* **Scenario**: Client initiates a long-running streaming tool delegation (`mesh_delegate_task`), then abruptly closes the Stdio/SSE connection mid-stream.
* **Verification**:
  * The Gateway catches `ConnectionResetError` / `CancelledError`.
  * Immediately propagates cancellation downstream to the target peer node.
  * Worker releases local execution thread and clears socket buffers.

---

## 5. Security & Penetration Testing Strategy

```
+-------------------+---------------------------------------------+---------------------+
| Attack Vector     | Simulated Action                            | Expected Outcome    |
+-------------------+---------------------------------------------+---------------------+
| Unauthorized Tool | Client requests Tool X with token for Tool Y| 403 Forbidden       |
| Token Tampering   | Modify JWT payload signature bit            | Cryptographic Rejection |
| Expired Token     | Submit token with exp = now - 10s           | ExpiredTokenError   |
| Replay Attack     | Re-send identical JWT token with seen jti   | DuplicateNonceError |
| Cross-Target Misuse| Token issued for Node B sent to Node C     | InvalidAudienceError|
| Identity Spoofing | Peer claims Node ID without matching Ed25519| Handshake Aborted   |
+-------------------+---------------------------------------------+---------------------+
```

---

## 6. Performance Benchmarking Strategy (`NFR-04`)

* **Benchmark Harness**: Automated benchmark script spawning 2 local peer nodes and measuring round-trip latency over 1,000 sequential and concurrent tool delegations.
* **Target Metric**: Intra-mesh routing overhead (time spent in Gateway dispatch + serialization + framing + network parsing) must be **< 50ms** beyond the raw execution time of the underlying tool.
* **Reporting**: Automated latency histograms (p50, p95, p99) generated during the test run.
