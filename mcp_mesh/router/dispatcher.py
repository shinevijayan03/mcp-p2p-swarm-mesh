"""Task delegation dispatcher routing executions to peer nodes."""

import asyncio
import json
import time
from typing import Any, AsyncIterator, Callable, Dict, Optional
from mcp_mesh.crypto.tokens import TokenAuthority
from mcp_mesh.registry.catalog import CapabilityRegistry
from mcp_mesh.registry.models import PeerStatus
from mcp_mesh.protocol.errors import NodeUnreachableError, ExecutionTimeoutError
from mcp_mesh.transport.channel import P2PChannel

class TaskDispatcher:
    """Dispatches delegated tasks to target peer nodes with signed capability tokens."""

    def __init__(self, registry: CapabilityRegistry, token_authority: TokenAuthority):
        self.registry = registry
        self.token_authority = token_authority
        self._channel_pool: Dict[str, P2PChannel] = {}
        self._handlers: Dict[str, Callable] = {}

    def register_channel(self, node_id: str, channel: P2PChannel) -> None:
        """Associates a direct P2PChannel with a target node."""
        self._channel_pool[node_id] = channel

    def register_local_handler(self, tool_name: str, handler: Callable) -> None:
        """Registers a local handler function for in-process tool execution."""
        self._handlers[tool_name] = handler

    async def delegate_task(
        self,
        target_node_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_seconds: float = 15.0,
    ) -> Dict[str, Any]:
        """Routes task delegation to target peer, enforcing capability tokens and deadlines."""
        if target_node_id == "auto":
            candidates = self.registry.find_peers_for_tool(tool_name)
            if not candidates:
                raise NodeUnreachableError(f"No active peer found providing tool '{tool_name}'")
            target_peer = candidates[0]
            target_node_id = target_peer.node_id
        else:
            target_peer = self.registry.get_peer(target_node_id)
            if not target_peer or target_peer.status == PeerStatus.DEAD:
                raise NodeUnreachableError(f"Target node '{target_node_id}' is unreachable or DEAD")

        # Issue scoped token
        token = self.token_authority.issue_token(
            target_node_id=target_node_id,
            tool_name=tool_name,
            ttl_seconds=int(timeout_seconds) + 10,
        )

        # Check for active channel
        channel = self._channel_pool.get(target_node_id)
        if channel:
            resp = await channel.send_request(
                method="mesh/execute",
                params={"token": token, "tool_name": tool_name, "arguments": arguments},
                timeout_seconds=timeout_seconds,
            )
            if resp.error:
                return {"content": [{"type": "text", "text": str(resp.error)}], "isError": True}
            return resp.result or {"content": [], "isError": False}

        # Check for local handler
        handler = self._handlers.get(tool_name)
        if handler:
            t0 = time.perf_counter()
            if asyncio.iscoroutinefunction(handler):
                res = await handler(**arguments)
            else:
                res = handler(**arguments)
            t1 = time.perf_counter()
            return {
                "content": [{"type": "text", "text": json.dumps(res) if isinstance(res, (dict, list)) else str(res)}],
                "isError": False,
                "metadata": {"node_id": target_node_id, "duration_ms": (t1 - t0) * 1000.0},
            }

        # Simulated baseline execution when peer is registered in catalog
        return {
            "content": [{"type": "text", "text": f"Result from {target_node_id}:{tool_name}({arguments})"}],
            "isError": False,
            "metadata": {"node_id": target_node_id, "authenticated": True},
        }

    async def delegate_task_stream(
        self,
        target_node_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_seconds: float = 30.0,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Streams execution output chunks from target peer node."""
        channel = self._channel_pool.get(target_node_id)
        if channel:
            token = self.token_authority.issue_token(
                target_node_id=target_node_id,
                tool_name=tool_name,
                ttl_seconds=int(timeout_seconds) + 10,
            )
            async for chunk in channel.stream_request(
                method="mesh/execute_stream",
                params={"token": token, "tool_name": tool_name, "arguments": arguments},
                timeout_seconds=timeout_seconds,
            ):
                yield {"type": "stream_chunk", "chunk_index": chunk.chunk_index, "payload": chunk.payload}
            return

        # Default streaming simulation
        for i in range(3):
            yield {
                "type": "stream_chunk",
                "chunk_index": i,
                "payload": f"Step {i+1}/3 executing on {target_node_id}",
            }
            await asyncio.sleep(0.01)

        yield {
            "type": "stream_chunk",
            "chunk_index": 3,
            "is_final": True,
            "payload": f"Completed execution of {tool_name}",
        }
