from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import uuid

class MCPServerConfig(BaseModel):
    """MCP 服务器配置模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # "stdio" 或 "sse"
    command: Optional[str] = None  # 对于 stdio 类型的服务器
    args: Optional[List[str]] = None  # 对于 stdio 类型的服务器
    url: Optional[str] = None  # 对于 sse 类型的服务器
    env: Optional[Dict[str, str]] = None  # 环境变量

    @validator('type')
    def validate_type(cls, v):
        if v not in ["stdio", "sse"]:
            raise ValueError(f"不支持的服务器类型: {v}，支持的类型为 stdio 和 sse")
        return v

    @validator('command')
    def validate_command(cls, v, values):
        if values.get('type') == 'stdio' and not v:
            raise ValueError("stdio 类型的服务器必须指定 command")
        return v

    @validator('url')
    def validate_url(cls, v, values):
        if values.get('type') == 'sse' and not v:
            raise ValueError("sse 类型的服务器必须指定 url")
        return v

    def to_parameters(self) -> Dict[str, Any]:
        """将配置转换为连接参数"""
        if self.type == "stdio":
            return {
                "command": self.command,
                "args": self.args or [],
                "env": self.env
            }
        elif self.type == "sse":
            return {
                "url": self.url,
                "env": self.env
            }
        return {}

    class Config:
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        } 