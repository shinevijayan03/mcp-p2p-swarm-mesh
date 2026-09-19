"""Configuration models for mcp_mesh."""

from typing import List, Optional
from pydantic import BaseModel, Field

class MeshConfig(BaseModel):
    node_id: str = Field(default="node_default")
    host: str = Field(default="127.0.0.1")
    tcp_port: int = Field(default=9000)
    udp_port: int = Field(default=9001)
    seeds: List[str] = Field(default_factory=list)
    heartbeat_interval: float = Field(default=3.0)
    failure_timeout: float = Field(default=15.0)
    suspect_timeout: float = Field(default=10.0)
    mcp_mode: str = Field(default="stdio")
    mcp_port: int = Field(default=8000)
    private_key_hex: Optional[str] = None
