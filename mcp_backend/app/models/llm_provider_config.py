from typing import Dict, List, Optional
from pydantic import BaseModel, validator

class LLMProviderConfig(BaseModel):
    """LLM 供应商配置模型"""
    name: str
    type: str  # OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen 等
    apiKey: str
    apiBase: Optional[str] = None
    models: List[str] = []
    
    @validator('type')
    def validate_type(cls, v):
        valid_types = ["OpenAI", "Anthropic", "OpenRouter", "DeepSeek", "Qwen", "其他"]
        if v not in valid_types:
            raise ValueError(f"不支持的供应商类型: {v}，支持的类型为 {', '.join(valid_types)}")
        return v
    
    def get_default_api_base(self) -> str:
        """根据供应商类型获取默认的 API 基础URL"""
        defaults = {
            "OpenAI": "https://api.openai.com/v1",
            "Anthropic": "https://api.anthropic.com",
            "OpenRouter": "https://openrouter.ai/api/v1",
            "DeepSeek": "https://api.deepseek.com/v1",
            "Qwen": "https://dashscope.aliyuncs.com/api/v1"
        }
        return defaults.get(self.type, "") 