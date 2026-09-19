"""Gateway MCP Facade implementation mapping MCP frames to internal mesh operations."""

import json
from typing import Any, Dict, List, Optional
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.router.dispatcher import TaskDispatcher
from mcp_mesh.consensus.orchestrator import SwarmConsensusEngine

class GatewayMcpFacade:
    """Standard MCP server facade exposing mesh tools, resources, and prompts."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        dispatcher: TaskDispatcher,
        consensus: SwarmConsensusEngine,
    ):
        self.registry = registry
        self.dispatcher = dispatcher
        self.consensus = consensus

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Lists standard mesh delegation tool plus any aggregated peer tools."""
        tools: List[Dict[str, Any]] = [
            {
                "name": "mesh_delegate_task",
                "description": "Delegates execution of an arbitrary tool to a target peer in the mesh.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target_node_id": {"type": "string", "description": "Target peer node ID or 'auto'"},
                        "tool_name": {"type": "string", "description": "Name of the target tool"},
                        "arguments": {"type": "object", "description": "JSON arguments for the tool"},
                        "timeout_seconds": {"type": "number", "default": 15.0},
                    },
                    "required": ["target_node_id", "tool_name"],
                },
            }
        ]

        # Aggregate tools from active peers
        manifest = self.registry.get_manifest()
        for node in manifest.get("nodes", []):
            for tool in node.get("tools", []):
                tools.append({
                    "name": tool.get("name"),
                    "description": f"[Node: {node.get('node_id')}] {tool.get('description', '')}",
                    "inputSchema": tool.get("input_schema", {"type": "object"}),
                })

        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool execution through the mesh task dispatcher."""
        if name == "mesh_delegate_task":
            target = arguments.get("target_node_id", "auto")
            tool_name = arguments.get("tool_name", "")
            tool_args = arguments.get("arguments", {})
            timeout = float(arguments.get("timeout_seconds", 15.0))
            return await self.dispatcher.delegate_task(target, tool_name, tool_args, timeout)

        # Automatic capability routing if called by tool name directly
        return await self.dispatcher.delegate_task("auto", name, arguments)

    async def list_resources(self) -> List[Dict[str, Any]]:
        """Lists resources including dynamic capabilities registry."""
        return [
            {
                "uri": "mesh://capabilities/registry",
                "name": "Mesh Capabilities Registry",
                "mimeType": "application/json",
                "description": "Real-time registry of active nodes, tools, resources, and topology health.",
            }
        ]

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Reads contents of a mesh resource."""
        if uri == "mesh://capabilities/registry":
            manifest = self.registry.get_manifest()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(manifest, indent=2),
                    }
                ]
            }
        raise ValueError(f"Resource '{uri}' not found")

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """Lists swarm consensus prompt templates."""
        return [
            {
                "name": "swarm_consensus_review",
                "description": "Distributes review task across multiple peer nodes and aggregates evaluations.",
                "arguments": [
                    {"name": "topic", "description": "Subject of review", "required": True},
                    {"name": "context", "description": "Context or content to evaluate", "required": True},
                    {"name": "k_peers", "description": "Number of peers to query", "required": False},
                    {"name": "min_quorum", "description": "Minimum agreeing evaluations required", "required": False},
                ],
            }
        ]

    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes swarm consensus prompt and formats synthesis as a prompt message."""
        if name == "swarm_consensus_review":
            topic = arguments.get("topic", "")
            context = arguments.get("context", "")
            k_peers = int(arguments.get("k_peers", 3))
            min_quorum = int(arguments.get("min_quorum", 2))
            res = await self.consensus.orchestrate_review(topic, context, k_peers, min_quorum)
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": {
                            "type": "text",
                            "text": f"Consensus Status: {res.consensus_status}\nMean Score: {res.mean_score}\n\nSummary:\n{res.synthesis_summary}",
                        },
                    }
                ]
            }
        raise ValueError(f"Prompt '{name}' not found")
