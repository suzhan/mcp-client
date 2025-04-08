import os
import json
from typing import List, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from loguru import logger

# 导入配置模型
from app.models.mcp_server_config import MCPServerConfig
from app.models.llm_provider_config import LLMProviderConfig

# 获取根目录
ROOT_DIR = Path(__file__).parent.parent.parent.parent

class Settings(BaseSettings):
    """应用配置"""
    APP_NAME: str = "MCP Client"
    PROJECT_NAME: str = "MCP Client"  # 兼容性别名
    API_V1_STR: str = "/api/v1"  # API前缀
    DEBUG: bool = True
    
    # 会话设置
    SESSION_TIMEOUT_SECONDS: int = 300  # 会话超时时间（5分钟）
    
    # 配置文件路径
    CONFIG_DIR: Path = ROOT_DIR / ".config"
    SERVERS_CONFIG_PATH: Path = CONFIG_DIR / "servers.json"
    LLM_CONFIG_PATH: Path = CONFIG_DIR / "llm.json"
    
    # 动态加载的配置
    mcp_servers: List[MCPServerConfig] = []
    llm_providers: List[LLMProviderConfig] = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 确保配置目录存在
        self.CONFIG_DIR.mkdir(exist_ok=True)
        
        # 加载配置
        self.load_mcp_servers()
        self.load_llm_providers()
    
    def load_mcp_servers(self) -> List[MCPServerConfig]:
        """加载MCP服务器配置"""
        self.mcp_servers = []  # 重置配置
        try:
            if self.SERVERS_CONFIG_PATH.exists():
                with open(self.SERVERS_CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    loaded_servers = []
                    
                    # 处理可能的不同格式
                    if isinstance(data, dict) and "mcpServers" in data:
                        # 格式为 {mcpServers: {id1: {配置1}, id2: {配置2}, ...}}
                        for server_id, server_config in data["mcpServers"].items():
                            try:
                                # 添加必要的字段
                                config: Dict[str, Any] = {
                                    "id": server_id,
                                    "name": server_id,  # 用ID作为默认名称
                                    "type": "stdio",    # 默认为stdio类型
                                    **server_config
                                }
                                loaded_servers.append(MCPServerConfig(**config))
                                logger.info(f"已加载MCP服务器配置: {server_id}")
                            except Exception as e:
                                logger.error(f"解析服务器配置 {server_id} 失败: {e}")
                    elif isinstance(data, list):
                        # 格式为 [{配置1}, {配置2}, ...]
                        for item in data:
                            try:
                                if "name" not in item:
                                    item["name"] = item.get("id", "未命名服务器")
                                if "type" not in item:
                                    item["type"] = "stdio"
                                loaded_servers.append(MCPServerConfig(**item))
                            except Exception as e:
                                logger.error(f"解析服务器配置失败: {e}")
                    else:
                        # 未知格式
                        logger.warning(f"未知的服务器配置格式: {data}")
                    
                    self.mcp_servers = loaded_servers
                    logger.info(f"已加载 {len(self.mcp_servers)} 个MCP服务器配置")
                return self.mcp_servers
            else:
                logger.warning(f"MCP服务器配置文件不存在: {self.SERVERS_CONFIG_PATH}")
                return []
        except Exception as e:
            logger.error(f"加载MCP服务器配置时出错: {e}")
            return []
    
    def load_llm_providers(self) -> List[LLMProviderConfig]:
        """加载LLM供应商配置"""
        self.llm_providers = []  # 重置配置
        try:
            if self.LLM_CONFIG_PATH.exists():
                with open(self.LLM_CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    
                    # 处理不同的配置格式
                    if isinstance(data, dict) and ("provider" in data or "api_key" in data):
                        # 单个供应商配置: {provider: "名称", api_key: "密钥", ...}
                        provider_type = data.get("provider", "其他")
                        # 修复OpenRouter大小写问题
                        if provider_type.lower() == "openrouter":
                            provider_type = "OpenRouter"
                        
                        try:
                            provider = {
                                "name": data.get("provider", "default"),
                                "type": provider_type,
                                "apiKey": data.get("api_key", ""),
                                "models": data.get("models", []) if isinstance(data.get("models", []), list) else [data.get("model", "")] if data.get("model") else []
                            }
                            if "api_base" in data:
                                provider["apiBase"] = data["api_base"]
                                
                            self.llm_providers = [LLMProviderConfig(**provider)]
                            logger.info(f"已加载单个LLM供应商配置: {provider['name']}")
                        except Exception as e:
                            logger.error(f"解析LLM供应商配置失败: {e}")
                    elif isinstance(data, list):
                        # 多个供应商配置: [{配置1}, {配置2}, ...]
                        loaded_providers = []
                        for item in data:
                            try:
                                # 修复OpenRouter大小写问题
                                if "type" in item and item["type"].lower() == "openrouter":
                                    item["type"] = "OpenRouter"
                                loaded_providers.append(LLMProviderConfig(**item))
                            except Exception as e:
                                logger.error(f"解析LLM供应商配置失败: {e}")
                        self.llm_providers = loaded_providers
                    else:
                        # 未知格式
                        logger.warning(f"未知的LLM供应商配置格式: {data}")
                    
                    logger.info(f"已加载 {len(self.llm_providers)} 个LLM供应商配置")
                return self.llm_providers
            else:
                logger.warning(f"LLM供应商配置文件不存在: {self.LLM_CONFIG_PATH}")
                return []
        except Exception as e:
            logger.error(f"加载LLM供应商配置时出错: {e}")
            return []

# 创建全局设置实例
settings = Settings() 