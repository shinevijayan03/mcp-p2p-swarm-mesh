"""JSON-RPC and message models."""

from enum import IntEnum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class MessageType(IntEnum):
    RPC_REQUEST = 0x01
    RPC_RESPONSE = 0x02
    RPC_STREAM_CHUNK = 0x03
    HEARTBEAT = 0x04
    ERROR_FRAME = 0x05

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class StreamChunk(BaseModel):
    id: str
    chunk_index: int
    is_final: bool = False
    payload: Any
