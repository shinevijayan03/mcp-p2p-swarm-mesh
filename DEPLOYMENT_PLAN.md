# Production Deployment & Operations Guide: `mcp-p2p-swarm-mesh`

## 1. Deployment Topology & Cluster Architectures

`mcp-p2p-swarm-mesh` supports two primary operational topologies:
1. **Local Multi-Process Development Cluster**: Ideal for local multi-agent prototyping, Claude Desktop integration, and rapid automated testing.
2. **Multi-Host / Containerized Swarm Mesh**: Production topology where nodes run across separate virtual machines or containers with mutual TLS authentication across physical networks.

```
                  +----------------------------------------------+
                  | Upstream Client (Claude Desktop / Agent)    |
                  +----------------------------------------------+
                                         |
                                         | Stdio (Local) or SSE (Remote)
                                         v
+-----------------------------------------------------------------------------------------+
| HOST / CONTAINER 1: GATEWAY & WEB CONTROL CENTER                                        |
|                                                                                         |
|   +------------------------------------+   +----------------------------------------+   |
|   | Streamlit Web UI (Port 8501)       |   | Gateway MCP Server Node                |   |
|   | - Topology visualization           |   | - Upstream SSE Port: 8000              |   |
|   | - Swarm consensus workbench        |   | - P2P TLS Port: 9000                   |   |
|   | - Live capability browser          |   | - UDP Gossip Port: 9001                |   |
|   +------------------------------------+   +----------------------------------------+   |
+-----------------------------------------------------------------------------------------+
                    |                                     |
               Gossip / TLS                          Gossip / TLS
                    v                                     v
+--------------------------------------+   +--------------------------------------+
| HOST / CONTAINER 2: WORKER NODE A    |   | HOST / CONTAINER 3: WORKER NODE B    |
| - Specialized Tools (e.g., Database) |   | - Specialized Tools (e.g., Analysis) |
| - P2P TLS Port: 9100                 |   | - P2P TLS Port: 9200                 |
| - UDP Gossip Port: 9101              |   | - UDP Gossip Port: 9201              |
+--------------------------------------+   +--------------------------------------+
```

---

## 2. Port & Network Matrix

| Service / Node | Transport | Protocol | Default Port | Exposure | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gateway MCP SSE** | TCP | HTTP/SSE | `8000` | Ingress / Client | Upstream MCP JSON-RPC bridge |
| **Gateway P2P** | TCP | Mutual TLS 1.3 | `9000` | Mesh Internal | Inter-node task delegation & streams |
| **Gateway Gossip** | UDP | Gossip Datagram | `9001` | Mesh Internal | Decentralized peer discovery & heartbeats |
| **Worker Node A P2P** | TCP | Mutual TLS 1.3 | `9100` | Mesh Internal | Worker A execution channel |
| **Worker Node A Gossip**| UDP | Gossip Datagram | `9101` | Mesh Internal | Worker A discovery & heartbeats |
| **Worker Node B P2P** | TCP | Mutual TLS 1.3 | `9200` | Mesh Internal | Worker B execution channel |
| **Worker Node B Gossip**| UDP | Gossip Datagram | `9201` | Mesh Internal | Worker B discovery & heartbeats |
| **Streamlit Control App**| TCP | HTTP/WS | `8501` | Operator / Web | Interactive UI and telemetry dashboard |

---

## 3. Local Cluster Deployment (Python Virtualenv)

### 3.1 Step 1: Virtual Environment Setup
```bash
# Clone and enter directory
cd /path/to/mcp-p2p-swarm-mesh

# Create virtual environment with Python 3.10+
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install package in editable mode with dependencies
pip install -e ".[all]"
```

### 3.2 Step 2: Launching a 3-Node Swarm + Gateway Cluster
You can launch nodes individually or via the provided cluster orchestration script:

#### Terminal 1: Gateway Node
```bash
python -m mcp_mesh.gateway.server \
  --node-id "gw_master_01" \
  --host "127.0.0.1" \
  --tcp-port 9000 \
  --udp-port 9001 \
  --mcp-mode "sse" \
  --mcp-port 8000
```

#### Terminal 2: Worker Node A (Specialized in Data Tools)
```bash
python -m mcp_mesh.node \
  --node-id "worker_data_01" \
  --host "127.0.0.1" \
  --tcp-port 9100 \
  --udp-port 9101 \
  --seeds "127.0.0.1:9001" \
  --tool-module "samples.data_tools"
```

#### Terminal 3: Worker Node B (Specialized in Compute/AI Tools)
```bash
python -m mcp_mesh.node \
  --node-id "worker_compute_02" \
  --host "127.0.0.1" \
  --tcp-port 9200 \
  --udp-port 9201 \
  --seeds "127.0.0.1:9001" \
  --tool-module "samples.compute_tools"
```

#### Terminal 4: Streamlit Control Dashboard
```bash
streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

---

## 4. Containerized Multi-Node Deployment (Docker & Compose)

### 4.1 Production Dockerfile
```dockerfile
# Multi-stage lightweight Python 3.12 image
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies (build-essential for cryptography if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY mcp_mesh/ mcp_mesh/
COPY app.py ./

RUN pip install --upgrade pip && \
    pip install .

EXPOSE 8000 8501 9000 9001

ENTRYPOINT ["python", "-m"]
CMD ["mcp_mesh.gateway.server"]
```

### 4.2 Docker Compose Configuration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  gateway:
    build: .
    command: ["mcp_mesh.gateway.server", "--node-id", "gw_prod_01", "--host", "0.0.0.0", "--tcp-port", "9000", "--udp-port", "9001", "--mcp-mode", "sse", "--mcp-port", "8000"]
    ports:
      - "8000:8000"   # Upstream MCP SSE
      - "9000:9000"   # P2P TLS
      - "9001:9001/udp" # Gossip UDP
    networks:
      mesh_net:
        ipv4_address: 172.28.0.10

  worker-alpha:
    build: .
    command: ["mcp_mesh.node", "--node-id", "worker_alpha", "--host", "0.0.0.0", "--tcp-port", "9100", "--udp-port", "9101", "--seeds", "172.28.0.10:9001"]
    depends_on:
      - gateway
    networks:
      mesh_net:
        ipv4_address: 172.28.0.20

  worker-beta:
    build: .
    command: ["mcp_mesh.node", "--node-id", "worker_beta", "--host", "0.0.0.0", "--tcp-port", "9200", "--udp-port", "9201", "--seeds", "172.28.0.10:9001"]
    depends_on:
      - gateway
    networks:
      mesh_net:
        ipv4_address: 172.28.0.30

  dashboard:
    build: .
    command: ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
    ports:
      - "8501:8501"
    environment:
      - GATEWAY_API_URL=http://172.28.0.10:8000
    depends_on:
      - gateway
    networks:
      mesh_net:
        ipv4_address: 172.28.0.50

networks:
  mesh_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

---

## 5. Security & Key Lifecycle Management

1. **Ed25519 Identity Keys**:
   * Nodes can generate ephemeral keys at startup or load persistent keys from environment variables (`MCP_MESH_PRIVATE_KEY_HEX`) or a secure secret vault (e.g., HashiCorp Vault, AWS Secrets Manager).
   * File permissions on disk-backed keys MUST be restricted to `0600` (read/write only by the executing process owner).
2. **Mutual TLS Certificates**:
   * Ephemeral self-signed certificates are bound strictly to the node's Ed25519 identity. Certificates expire every 72 hours and auto-renew asynchronously in-memory.
3. **Replay Cache Memory Limits**:
   * The sliding-window nonce cache uses an in-memory TTL structure capped at 100,000 recent nonces (~4MB RAM) with an automatic 60-second eviction horizon.

---

## 6. Telemetry & Monitoring Architecture

### 6.1 Structured Logging
All nodes produce structured JSON logs to `stdout` conforming to standard observability schemas:
```json
{
  "timestamp": "2026-09-19T07:30:00.124Z",
  "level": "INFO",
  "logger": "mcp_mesh.router.dispatcher",
  "node_id": "gw_master_01",
  "event": "task_delegated",
  "target_node": "worker_alpha",
  "tool": "execute_sql_query",
  "duration_ms": 14.8,
  "status": "success"
}
```

### 6.2 Health Checks & Metric Signals
* **`/healthz` (HTTP)**: Returns `200 OK` if the Gateway event loop is responsive and active peer count `>= 1`.
* **Telemetry Metrics Exposed**:
  * `mcp_mesh_active_peers`: Count of current `ALIVE` nodes in the capability catalog.
  * `mcp_mesh_delegation_duration_ms`: Histogram of intra-mesh execution latency (p50, p95, p99).
  * `mcp_mesh_congested_rejections_total`: Counter tracking rate-limit drops (`-32004`).
  * `mcp_mesh_heartbeat_decay_evictions_total`: Counter tracking peer dropouts after 15-second cutoff.
