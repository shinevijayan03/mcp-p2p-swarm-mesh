"""Registry data models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class PeerStatus(str, Enum):
    ALIVE = "ALIVE"
    SUSPECT = "SUSPECT"
    DEAD = "DEAD"

class ToolParameterSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)

class MeshToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: ToolParameterSchema = Field(default_factory=ToolParameterSchema)
    rate_limit_rpm: Optional[int] = Field(default=60)

class MeshResourceDefinition(BaseModel):
    uri: str
    name: str
    mime_type: Optional[str] = "application/json"
    description: Optional[str] = None

class MeshPromptDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: List[Dict[str, Any]] = Field(default_factory=list)

class PeerNodeRecord(BaseModel):
    node_id: str
    host: str
    tcp_port: int
    udp_port: int
    public_key_hex: str
    status: PeerStatus = PeerStatus.ALIVE
    last_heartbeat: float
    sequence_number: int = 0
    tools: List[MeshToolDefinition] = Field(default_factory=list)
    resources: List[MeshResourceDefinition] = Field(default_factory=list)
    prompts: List[MeshPromptDefinition] = Field(default_factory=list)
    load_average: float = 0.0
