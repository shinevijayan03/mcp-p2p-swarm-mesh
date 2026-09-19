# Usage Guide & API Reference: `mcp-p2p-swarm-mesh`

## 1. Upstream MCP Client Integrations

The Gateway Node exposes a fully compliant Model Context Protocol (MCP) interface, enabling instant plug-and-play integration with Claude Desktop, Cursor, and any MCP-compatible autonomous agent framework.

---

### 1.1 Claude Desktop Integration

Claude Desktop communicates with MCP servers via standard I/O (stdio) or Server-Sent Events (SSE). 

#### Mode A: Stdio Bridge (Recommended for Single-Host Workstations)
Edit your Claude Desktop configuration file:
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "swarm-mesh": {
      "command": "python",
      "args": [
        "-m",
        "mcp_mesh.gateway.server",
        "--mcp-mode",
        "stdio",
        "--seeds",
        "127.0.0.1:9001"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

#### Mode B: SSE Remote Bridge (Recommended for Multi-Host Clusters)
If the Gateway is running on an internal server or Docker container (e.g. `http://192.168.1.50:8000/sse`):

```json
{
  "mcpServers": {
    "swarm-mesh-remote": {
      "url": "http://192.168.1.50:8000/sse"
    }
  }
}
```

---

### 1.2 Programmatic Python Client Integration (`mcp` SDK)

To interact with the swarm mesh from an autonomous Python script or LangChain / AutoGen / CrewAI agent:

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_mesh.gateway.server", "--mcp-mode", "stdio"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize session
            await session.initialize()

            # 2. Query available mesh tools
            tools = await session.list_tools()
            print("Discovered Mesh Tools:", [t.name for t in tools.tools])

            # 3. Read dynamic mesh capabilities registry
            registry_res = await session.read_resource("mesh://capabilities/registry")
            print("Active Mesh Registry:\n", registry_res.contents[0].text)

            # 4. Delegate a task to a target peer
            result = await session.call_tool(
                "mesh_delegate_task",
                arguments={
                    "target_node_id": "worker_node_alpha",
                    "tool_name": "execute_code",
                    "arguments": {"code": "print('Hello from Swarm!')"}
                }
            )
            print("Execution Result:", result.content)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2. API & Tool Reference

### 2.1 Tool: `mesh_delegate_task`
Delegates execution of an arbitrary tool to a specific target peer or capability provider in the swarm mesh.

* **Parameters**:
  * `target_node_id` (`string`, required): The 16-character hexadecimal ID of the destination peer node (or `"auto"` for automatic load-balanced routing).
  * `tool_name` (`string`, required): Name of the tool to execute on the peer.
  * `arguments` (`object`, required): JSON object containing parameters expected by the target tool.
  * `timeout_seconds` (`number`, optional, default: `15.0`): Maximum time allowed for execution before aborting.
* **Return Format**:
  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "Execution completed successfully: Result output..."
      }
    ],
    "isError": false,
    "metadata": {
      "executing_node": "worker_node_alpha",
      "duration_ms": 23.4,
      "authenticated_via": "Ed25519-JWT"
    }
  }
  ```
* **Common Error Codes**:
  * `-32001 (Node Unreachable)`: Target node is `DEAD` or not found in capability catalog.
  * `-32002 (Execution Timeout)`: Tool call exceeded `timeout_seconds`.
  * `-32003 (Unauthorized)`: Capability token expired or does not grant access to the specified tool.
  * `-32004 (Node Congested)`: Target node is currently processing at capacity; retry with backoff.

---

### 2.2 Resource: `mesh://capabilities/registry`
Dynamic JSON-formatted resource detailing active nodes, available tools, resources, and overall mesh health.

* **URI**: `mesh://capabilities/registry`
* **MIME Type**: `application/json`
* **Sample Content**:
  ```json
  {
    "mesh_id": "swarm_mesh_prod",
    "updated_at": "2026-09-19T07:35:00Z",
    "active_nodes_count": 3,
    "nodes": [
      {
        "node_id": "gw_master_01",
        "role": "GATEWAY",
        "status": "ALIVE",
        "endpoint": "127.0.0.1:9000",
        "latency_ms": 0.0
      },
      {
        "node_id": "worker_alpha",
        "role": "PEER",
        "status": "ALIVE",
        "endpoint": "127.0.0.1:9100",
        "latency_ms": 1.2,
        "tools": [
          {
            "name": "execute_sql_query",
            "description": "Run analytical SQL queries",
            "parameters": {
              "type": "object",
              "properties": {"query": {"type": "string"}},
              "required": ["query"]
            }
          }
        ]
      }
    ]
  }
  ```

---

### 2.3 Prompt: `swarm_consensus_review`
Dispatches a peer evaluation prompt across multiple nodes in parallel to reach verified consensus on high-stakes tasks (e.g. code safety, architectural reviews, risk scores).

* **Prompt Arguments**:
  * `topic` (`string`, required): Short summary of the review subject.
  * `context` (`string`, required): Detailed context, code diff, or proposal text.
  * `k_peers` (`integer`, optional, default: `3`): Number of peer nodes to solicit for review.
  * `min_quorum` (`integer`, optional, default: `2`): Minimum number of agreeing evaluations required.
* **Return Format**:
  Structured review document containing:
  1. Consolidated consensus score `[0.00 - 1.00]`.
  2. Final status: `CONSENSUS_REACHED` or `QUORUM_FAILED`.
  3. Individual peer breakdowns with justifications.
  4. Outlier analysis and dissenting opinions.

---

## 3. Creating Custom Worker Nodes with Custom Tools

Creating a new specialized worker node to expand the mesh capability is straightforward. You can register custom tools using Python decorators:

```python
# my_worker_tools.py
from mcp_mesh.node import MeshNode

node = MeshNode(
    node_id="worker_finance_01",
    listen_host="127.0.0.1",
    tcp_port=9300,
    udp_port=9301,
    seeds=["127.0.0.1:9001"]  # Point to Gateway or existing peer
)

@node.tool(
    name="calculate_compound_interest",
    description="Calculates compound interest given principal, rate, and time."
)
async def calculate_compound_interest(principal: float, rate: float, years: int) -> dict:
    total = principal * ((1 + rate / 100) ** years)
    return {
        "principal": principal,
        "rate": rate,
        "years": years,
        "final_amount": round(total, 2)
    }

if __name__ == "__main__":
    node.start_and_block()
```

When started:
1. `node` binds its TCP TLS port (`9300`) and UDP gossip port (`9301`).
2. Transmits discovery heartbeat to the seed node.
3. Automatically advertises `calculate_compound_interest`.
4. The Gateway immediately incorporates `calculate_compound_interest` into `mesh://capabilities/registry`.
5. Upstream clients (Claude Desktop) can now invoke it seamlessly!

---

## 4. Interactive Streamlit Web Application (`app.py`)

Launch the operator control dashboard:
```bash
streamlit run app.py
```

### Dashboard Features
1. **Mesh Topology Graph**:
   * Interactive network visualization powered by NetworkX and SVG/HTML canvas.
   * Visualizes Gateway (primary node) and connected peers with color-coded health indicators (`ALIVE` = Green, `SUSPECT` = Amber, `DEAD` = Red).
2. **Dynamic Capability Browser**:
   * Live filtering and search across all tools, resources, and prompts registered in the mesh.
   * Inspect JSON parameter schemas and rate-limit policies in real time.
3. **Task Delegation Execution Runner**:
   * Direct execution form: select target node, select tool, supply JSON arguments.
   * Real-time execution monitor with streaming response chunks, latency timer, and raw JSON-RPC inspection.
4. **Swarm Consensus Chamber**:
   * Form to launch consensus reviews with customizable quorum thresholds.
   * Live evaluation timeline displaying concurrent peer scoring, variance graphs, and synthesized consensus reports.
