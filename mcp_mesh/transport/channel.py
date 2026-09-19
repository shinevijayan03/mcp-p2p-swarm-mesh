"""Asynchronous multiplexed P2P channel over bidirectional streams."""

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Dict, Optional
from mcp_mesh.protocol.framing import FrameCodec
from mcp_mesh.protocol.messages import MessageType, JsonRpcRequest, JsonRpcResponse, StreamChunk
from mcp_mesh.protocol.errors import ExecutionTimeoutError, ProtocolViolationError

class P2PChannel:
    """Bi-directional, multiplexed channel over an async stream reader and writer."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._active_queues: Dict[str, asyncio.Queue] = {}
        self._closed = False
        self._read_task = asyncio.create_task(self._demux_loop())

    async def _demux_loop(self) -> None:
        """Continuously reads frames from the socket and demultiplexes by request ID."""
        try:
            while not self._closed:
                try:
                    msg_type, payload = await FrameCodec.read_frame(self._reader)
                except (ProtocolViolationError, asyncio.IncompleteReadError, ConnectionResetError):
                    break

                try:
                    data = json.loads(payload.decode("utf-8"))
                except Exception:
                    continue

                req_id = data.get("id")
                if not req_id:
                    continue

                if msg_type == MessageType.RPC_RESPONSE:
                    fut = self._pending_requests.pop(req_id, None)
                    if fut and not fut.done():
                        response = JsonRpcResponse(**data)
                        fut.set_result(response)

                elif msg_type == MessageType.RPC_STREAM_CHUNK:
                    q = self._active_queues.get(req_id)
                    if q:
                        chunk = StreamChunk(**data)
                        await q.put(chunk)
                        if chunk.is_final:
                            self._active_queues.pop(req_id, None)
        except asyncio.CancelledError:
            pass
        finally:
            self._abort_pending("Channel closed")

    def _abort_pending(self, reason: str) -> None:
        for fut in list(self._pending_requests.values()):
            if not fut.done():
                fut.set_exception(ConnectionResetError(reason))
        self._pending_requests.clear()

        for q in list(self._active_queues.values()):
            q.put_nowait(None)
        self._active_queues.clear()

    async def send_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout_seconds: float = 15.0,
    ) -> JsonRpcResponse:
        """Dispatches a single JSON-RPC request and awaits the matching response."""
        if self._closed:
            raise ConnectionResetError("Cannot send request on closed channel")

        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending_requests[req_id] = fut

        req = JsonRpcRequest(id=req_id, method=method, params=params)
        payload = json.dumps(req.model_dump()).encode("utf-8")
        frame = FrameCodec.encode_frame(MessageType.RPC_REQUEST, payload)

        self._writer.write(frame)
        await self._writer.drain()

        try:
            return await asyncio.wait_for(fut, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise ExecutionTimeoutError(f"Request {req_id} timed out after {timeout_seconds}s")

    async def stream_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout_seconds: float = 30.0,
    ) -> AsyncIterator[StreamChunk]:
        """Dispatches a request and yields streaming chunks as they arrive."""
        if self._closed:
            raise ConnectionResetError("Cannot stream request on closed channel")

        req_id = str(uuid.uuid4())
        q: asyncio.Queue = asyncio.Queue()
        self._active_queues[req_id] = q

        req = JsonRpcRequest(id=req_id, method=method, params=params)
        payload = json.dumps(req.model_dump()).encode("utf-8")
        frame = FrameCodec.encode_frame(MessageType.RPC_REQUEST, payload)

        self._writer.write(frame)
        await self._writer.drain()

        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                self._active_queues.pop(req_id, None)
                raise ExecutionTimeoutError(f"Streaming request {req_id} timed out")

            if chunk is None:
                break
            yield chunk
            if chunk.is_final:
                break

    async def close(self) -> None:
        """Gracefully closes channel and cancels background tasks."""
        if self._closed:
            return
        self._closed = True
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        self._abort_pending("Channel closed")
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except Exception:
            pass
