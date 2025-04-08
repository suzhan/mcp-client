import asyncio
import json
import logging
import uuid
import traceback
import re
from typing import Dict, List, Optional, Any, Tuple

import httpx
from loguru import logger

from app.models.llm_provider_config import LLMProviderConfig

class LLMService:
    """LLM服务类，负责与不同LLM供应商的API交互"""
    
    def __init__(self, provider_config: LLMProviderConfig):
        self.config = provider_config
        self.name = provider_config.name
        self.api_key = provider_config.apiKey
        self.base_url = provider_config.apiBase
        self.models = provider_config.models
    
    async def get_completion(self, 
                             messages: List[Dict[str, Any]], 
                             model: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: Optional[int] = None,
                             tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """从LLM获取回复"""
        try:
            # 默认使用配置中的第一个模型
            model_to_use = model if model else self.models[0]
            
            # 验证消息格式
            if not isinstance(messages, list):
                raise ValueError("消息必须是列表格式")
            
            for msg in messages:
                if not isinstance(msg, dict):
                    raise ValueError("每条消息必须是字典格式")
                if "role" not in msg:
                    raise ValueError("每条消息必须包含role字段")
                if "content" not in msg and "tool_calls" not in msg:
                    raise ValueError("每条消息必须包含content或tool_calls字段")
            
            # 根据不同的供应商进行适配
            if self.name.lower() == "openai":
                return await self._openai_completion(messages, model_to_use, temperature, max_tokens, tools)
            elif self.name.lower() == "openrouter":
                return await self._openrouter_completion(messages, model_to_use, temperature, max_tokens, tools)
            elif self.name.lower() == "deepseek":
                return await self._deepseek_completion(messages, model_to_use, temperature, max_tokens, tools)
            elif self.name.lower() == "qwen":
                return await self._qwen_completion(messages, model_to_use, temperature, max_tokens, tools)
            else:
                logger.error(f"不支持的LLM供应商: {self.name}")
                return {"error": f"不支持的LLM供应商: {self.name}"}
                
        except Exception as e:
            error_msg = f"LLM调用失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}
    
    async def get_available_models(self) -> Dict[str, Any]:
        """获取供应商可用的模型列表"""
        try:
            # 根据不同的供应商进行适配
            if self.name.lower() == "openai":
                return await self._openai_models()
            elif self.name.lower() == "openrouter":
                return await self._openrouter_models()
            elif self.name.lower() == "deepseek":
                return await self._deepseek_models()
            elif self.name.lower() == "qwen":
                return await self._qwen_models()
            else:
                logger.error(f"不支持的LLM供应商: {self.name}")
                return {"error": f"不支持的LLM供应商: {self.name}", "models": []}
        except Exception as e:
            error_msg = f"获取模型列表失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg, "models": []}
    
    async def _openai_completion(self, 
                                messages: List[Dict[str, Any]], 
                                model: str,
                                temperature: float,
                                max_tokens: Optional[int],
                                tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """OpenAI API调用"""
        url = f"{self.base_url or 'https://api.openai.com'}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"OpenAI API调用失败: {response.status_code} - {response.text}")
                    return {"error": f"API call failed: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"OpenAI API调用异常: {str(e)}")
            return {"error": f"API call exception: {str(e)}"}
    
    async def _openrouter_completion(self, 
                                    messages: List[Dict[str, Any]], 
                                    model: str,
                                    temperature: float,
                                    max_tokens: Optional[int],
                                    tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """OpenRouter API调用"""
        url = f"{self.base_url or 'https://openrouter.ai'}/api/v1/chat/completions"
        
        # 记录请求参数
        logger.info(f"OpenRouter请求参数: model={model}, temperature={temperature}")
        logger.debug(f"原始消息内容: {json.dumps(messages, ensure_ascii=False)}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://mcp-client.app",
            "X-Title": "MCP Client"
        }
        
        # 确保消息格式正确 - 严格按照OpenRouter要求格式化
        formatted_messages = []
        for msg in messages:
            # 跳过非字典消息
            if not isinstance(msg, dict):
                logger.warning(f"跳过非字典消息: {msg}")
                continue
                
            # OpenRouter只支持以下角色
            valid_roles = ["user", "assistant", "system", "tool"]
            role = msg.get("role", "user")
            if role not in valid_roles:
                logger.warning(f"无效角色 '{role}'，跳过此消息")
                continue
                
            # 处理content字段，确保是字符串或有效的内容数组
            content = msg.get("content", "")
            
            # 检查内容是否是嵌套的消息格式
            if isinstance(content, dict) and "role" in content and "content" in content:
                # 这是嵌套的消息格式，直接提取内部的content
                logger.info(f"检测到嵌套消息格式，提取内部content: {content}")
                content = content.get("content", "")
            elif content is None and role == "assistant" and "tool_calls" in msg:
                # 助手消息中如果有tool_calls，content可以为null
                pass
            elif isinstance(content, dict):
                # 将字典内容转为字符串，优先使用text字段
                content = content.get("text", str(content))
            elif isinstance(content, list):
                # 处理内容数组
                content = " ".join([
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                ])
            
            # 基本消息结构
            formatted_msg = {
                "role": role,
                "content": content
            }
            
            # 特殊处理tool消息
            if role == "tool":
                if "tool_call_id" not in msg:
                    logger.warning(f"工具消息缺少tool_call_id字段，跳过: {msg}")
                    continue
                formatted_msg["tool_call_id"] = msg["tool_call_id"]
            
            # 处理助手的工具调用
            if role == "assistant" and "tool_calls" in msg:
                tool_calls = []
                for tc in msg.get("tool_calls", []):
                    if not isinstance(tc, dict):
                        continue
                    
                    call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                    
                    args = tc.get("arguments", {})
                    if isinstance(args, dict):
                        args = json.dumps(args)
                    
                    tool_call = {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": args
                        }
                    }
                    tool_calls.append(tool_call)
                
                if tool_calls:
                    formatted_msg["tool_calls"] = tool_calls
            
            formatted_messages.append(formatted_msg)
        
        logger.debug(f"发送到OpenRouter的格式化消息: {json.dumps(formatted_messages, ensure_ascii=False)}")
        
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": False
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            logger.info(f"发送工具定义到OpenRouter: {len(tools)}个工具")
            payload["tools"] = tools
            # 让LLM自行决定是否使用工具，不强制特定工具的使用
            payload["tool_choice"] = "auto"
        
        try:
            logger.info("发送请求到OpenRouter...")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("OpenRouter请求成功")
                    logger.debug(f"OpenRouter响应: {json.dumps(result, ensure_ascii=False)}")
                    return result
                else:
                    error_msg = f"OpenRouter API调用失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"error": error_msg}
        except Exception as e:
            error_msg = f"OpenRouter API调用异常: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def _deepseek_completion(self, 
                                  messages: List[Dict[str, Any]], 
                                  model: str,
                                  temperature: float,
                                  max_tokens: Optional[int],
                                  tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """DeepSeek API调用"""
        url = f"{self.base_url or 'https://api.deepseek.com'}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"DeepSeek API调用失败: {response.status_code} - {response.text}")
                    return {"error": f"API call failed: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {str(e)}")
            return {"error": f"API call exception: {str(e)}"}
    
    async def _qwen_completion(self, 
                              messages: List[Dict[str, Any]], 
                              model: str,
                              temperature: float,
                              max_tokens: Optional[int],
                              tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Qwen API调用"""
        url = f"{self.base_url or 'https://dashscope.aliyuncs.com'}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Qwen API调用失败: {response.status_code} - {response.text}")
                    return {"error": f"API call failed: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"Qwen API调用异常: {str(e)}")
            return {"error": f"API call exception: {str(e)}"}

    # ------- 模型获取方法 -------
    
    async def _openai_models(self) -> Dict[str, Any]:
        """获取OpenAI可用模型列表"""
        url = f"{self.base_url or 'https://api.openai.com'}/v1/models"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    # 提取模型名称列表
                    models = [model["id"] for model in result["data"]]
                    # 只保留可用于聊天的模型
                    chat_models = [m for m in models if any(prefix in m for prefix in ["gpt-", "text-davinci"])]
                    return {"models": chat_models}
                else:
                    logger.error(f"获取OpenAI模型列表失败: {response.status_code} - {response.text}")
                    return {"error": f"API调用失败: {response.status_code} - {response.text}", "models": []}
        except Exception as e:
            logger.error(f"获取OpenAI模型列表异常: {str(e)}")
            return {"error": f"API调用异常: {str(e)}", "models": []}
    
    async def _openrouter_models(self) -> Dict[str, Any]:
        """获取OpenRouter可用模型列表"""
        url = f"{self.base_url or 'https://openrouter.ai'}/api/v1/models"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://mcp-client.app",
            "X-Title": "MCP Client"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    # 模型信息更丰富，返回完整的数据
                    models = [
                        {
                            "id": model["id"],
                            "name": model.get("name", model["id"]),
                            "context_length": model.get("context_length"),
                            "pricing": model.get("pricing", {})
                        }
                        for model in result["data"]
                    ]
                    # 只提取ID用于模型列表
                    model_ids = [model["id"] for model in result["data"]]
                    return {"models": model_ids, "model_details": models}
                else:
                    logger.error(f"获取OpenRouter模型列表失败: {response.status_code} - {response.text}")
                    return {"error": f"API调用失败: {response.status_code} - {response.text}", "models": []}
        except Exception as e:
            logger.error(f"获取OpenRouter模型列表异常: {str(e)}")
            return {"error": f"API调用异常: {str(e)}", "models": []}
    
    async def _deepseek_models(self) -> Dict[str, Any]:
        """获取DeepSeek可用模型列表"""
        # DeepSeek API可能不提供模型列表端点，返回固定列表
        models = [
            "deepseek-chat", 
            "deepseek-coder", 
            "deepseek-chat-v3-0324",
            "deepseek-coder-v2-0531"
        ]
        return {"models": models}
    
    async def _qwen_models(self) -> Dict[str, Any]:
        """获取Qwen可用模型列表"""
        # 阿里云Qwen API可能不提供模型列表端点，返回固定列表
        models = [
            "qwen-turbo", 
            "qwen-plus", 
            "qwen-max", 
            "qwen-max-longcontext"
        ]
        return {"models": models}

class LLMServiceManager:
    """LLM服务管理器，管理多个供应商的服务实例"""
    
    def __init__(self):
        self.providers: Dict[str, LLMService] = {}
    
    def add_provider(self, provider_config: LLMProviderConfig) -> None:
        """添加供应商服务"""
        self.providers[provider_config.name] = LLMService(provider_config)
    
    def get_provider(self, name: str) -> Optional[LLMService]:
        """获取特定供应商的服务实例"""
        return self.providers.get(name)
    
    def remove_provider(self, name: str) -> None:
        """移除供应商服务"""
        if name in self.providers:
            del self.providers[name]
    
    async def get_provider_models(self, name: str) -> Dict[str, Any]:
        """获取特定供应商的模型列表"""
        provider = self.get_provider(name)
        if not provider:
            return {"error": f"供应商未找到: {name}", "models": []}
        
        return await provider.get_available_models()
        
    async def chat_with_tools(self,
                            provider_name: str,
                            model: str,
                            messages: List[Dict[str, Any]],
                            tools: Optional[List[Dict[str, Any]]] = None,
                            temperature: float = 0.7,
                            max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """使用指定的LLM供应商进行对话，可选择性地使用工具"""
        service = self.get_provider(provider_name)
        if not service:
            logger.error(f"LLM供应商不存在: {provider_name}")
            return {"error": f"Provider not found: {provider_name}"}
            
        try:
            logger.info(f"使用供应商 {provider_name} 进行对话")
            logger.info(f"模型: {model}")
            if tools:
                logger.info(f"使用 {len(tools)} 个工具")
                
            response = await service.get_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools
            )
            
            if "error" in response:
                logger.error(f"LLM对话失败: {response['error']}")
                return response
                
            # 处理响应
            logger.info(f"收到LLM响应: {json.dumps(response, ensure_ascii=False)[:200]}...")
            
            if "choices" in response and response["choices"]:
                choice = response["choices"][0]
                message = choice.get("message", {})
                
                # 检查工具调用
                if "tool_calls" in message and message["tool_calls"]:
                    # 正式的工具调用格式
                    tool_calls = message["tool_calls"]
                    logger.info(f"检测到官方格式工具调用: {len(tool_calls)}个")
                    logger.debug(f"工具调用详情: {json.dumps(tool_calls, ensure_ascii=False)}")
                    
                    return {
                        "tool_calls": [
                            {
                                "name": call["function"]["name"],
                                "arguments": json.loads(call["function"]["arguments"])
                            }
                            for call in tool_calls
                        ]
                    }
                else:
                    # 获取内容
                    content = message.get("content", "")
                    logger.info(f"LLM返回普通文本内容: {content[:100]}...")
                    
                    # 解析 DeepSeek 工具调用格式 (< | tool_calls_begin | > ... < | tool_calls_end | >)
                    if content and "< | tool_calls_begin | >" in content:
                        logger.info("检测到 DeepSeek 特定格式的工具调用")
                        try:
                            # 提取工具名称和参数
                            tool_name = None
                            tool_args = {}
                            
                            # 使用正则表达式提取工具名称
                            tool_name_match = re.search(r"< \| function< \| tool_sep \| >(\w+)", content)
                            if tool_name_match:
                                tool_name = tool_name_match.group(1)
                                logger.info(f"提取到工具名称: {tool_name}")
                                
                                # 找到工具参数的JSON部分
                                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(0)
                                    try:
                                        tool_args = json.loads(json_str)
                                        logger.info(f"提取到工具参数: {json.dumps(tool_args, ensure_ascii=False)[:200]}...")
                                        
                                        # 生成工具调用ID
                                        tool_call_id = f"call_{uuid.uuid4().hex[:20]}"
                                        
                                        # 返回标准格式的工具调用
                                        return {
                                            "tool_calls": [
                                                {
                                                    "id": tool_call_id,
                                                    "name": tool_name,
                                                    "arguments": tool_args
                                                }
                                            ]
                                        }
                                    except json.JSONDecodeError as je:
                                        logger.warning(f"DeepSeek工具参数JSON解析失败: {je}, 原始内容: {json_str[:200]}")
                                else:
                                    logger.warning("在DeepSeek工具调用中未找到JSON参数")
                            else:
                                logger.warning("在DeepSeek工具调用中未找到工具名称")
                                
                        except Exception as e:
                            logger.error(f"解析DeepSeek工具调用格式失败: {str(e)}", exc_info=True)
                            logger.debug(f"原始内容: {content}")
                    
                    # 尝试解析内容是否为JSON工具调用格式
                    try:
                        # 检查是否是JSON格式
                        if content.strip() and content.strip().startswith('{') and content.strip().endswith('}'):
                            try:
                                parsed_content = json.loads(content)
                                logger.info(f"成功解析为JSON: {json.dumps(parsed_content, ensure_ascii=False)[:200]}...")
                                
                                # 检查是否是工具调用格式
                                if ("tool" in parsed_content and "arguments" in parsed_content and 
                                    isinstance(parsed_content["arguments"], dict)):
                                    
                                    logger.info(f"检测到JSON格式工具调用: {parsed_content['tool']}")
                                    logger.debug(f"工具参数: {json.dumps(parsed_content['arguments'], ensure_ascii=False)}")
                                    
                                    # 是工具调用，返回标准格式
                                    # 生成唯一的工具调用ID
                                    tool_call_id = f"call_{uuid.uuid4().hex[:20]}"
                                    
                                    return {
                                        "tool_calls": [
                                            {
                                                "id": tool_call_id,
                                                "name": parsed_content["tool"],
                                                "arguments": parsed_content["arguments"]
                                            }
                                        ]
                                    }
                                
                                # 检查其他可能的工具调用格式
                                elif "function_call" in parsed_content or "tool_calls" in parsed_content:
                                    # 兼容OpenAI格式
                                    logger.info("检测到OpenAI格式工具调用")
                                    tool_calls = []
                                    
                                    # 处理function_call格式
                                    if "function_call" in parsed_content:
                                        try:
                                            fc = parsed_content["function_call"]
                                            tool_call_id = fc.get("id", f"call_{uuid.uuid4().hex[:20]}")
                                            name = fc.get("name")
                                            # 参数可能是字符串或对象
                                            args = fc.get("arguments", "{}")
                                            if isinstance(args, str):
                                                try:
                                                    args = json.loads(args)
                                                except json.JSONDecodeError as e:
                                                    logger.warning(f"解析function_call参数失败: {e}, 原始参数: {args}")
                                                    args = {"raw_input": args}
                                            
                                            if name:  # 只有当name存在时才添加
                                                tool_calls.append({
                                                    "id": tool_call_id,
                                                    "name": name,
                                                    "arguments": args
                                                })
                                        except Exception as e:
                                            logger.warning(f"解析function_call失败: {e}, 源数据: {parsed_content['function_call']}")
                                    
                                    # 处理tool_calls格式
                                    elif "tool_calls" in parsed_content:
                                        for tc in parsed_content["tool_calls"]:
                                            try:
                                                if "function" in tc and "name" in tc["function"]:
                                                    tool_call_id = tc.get("id", f"call_{uuid.uuid4().hex[:20]}")
                                                    name = tc["function"]["name"]
                                                    # 参数可能是字符串或对象
                                                    args = tc["function"].get("arguments", "{}")
                                                    if isinstance(args, str):
                                                        try:
                                                            args = json.loads(args)
                                                        except json.JSONDecodeError as e:
                                                            logger.warning(f"解析tool_call参数失败: {e}, 原始参数: {args}")
                                                            args = {"raw_input": args}
                                                    
                                                    tool_calls.append({
                                                        "id": tool_call_id,
                                                        "name": name,
                                                        "arguments": args
                                                    })
                                                elif "name" in tc:  # 简化的工具调用格式
                                                    tool_call_id = tc.get("id", f"call_{uuid.uuid4().hex[:20]}")
                                                    name = tc["name"]
                                                    args = tc.get("arguments", {})
                                                    if isinstance(args, str):
                                                        try:
                                                            args = json.loads(args)
                                                        except json.JSONDecodeError as e:
                                                            logger.warning(f"解析简化tool_call参数失败: {e}, 原始参数: {args}")
                                                            args = {"raw_input": args}
                                                    
                                                    tool_calls.append({
                                                        "id": tool_call_id,
                                                        "name": name,
                                                        "arguments": args
                                                    })
                                            except Exception as e:
                                                logger.warning(f"解析tool_call项失败: {e}, 源数据: {json.dumps(tc, ensure_ascii=False)}")
                                
                                if tool_calls:
                                    logger.info(f"成功解析了 {len(tool_calls)} 个工具调用")
                                    return {"tool_calls": tool_calls}
                            except json.JSONDecodeError as je:
                                logger.warning(f"JSON解析失败: {je}, 原始内容: {content[:200]}")
                    except Exception as e:
                        # 解析失败或不是工具调用格式，当作普通消息处理
                        logger.warning(f"内容不是有效的工具调用JSON或解析过程中出错: {e}")
                    
                    # 如果上面的解析失败，则作为普通消息处理
                    logger.info("返回普通消息响应")
                    
                    # 确保内容不为None并且是字符串
                    if content is None:
                        content = ""
                    elif not isinstance(content, str):
                        try:
                            content = str(content)
                            logger.warning(f"内容不是字符串，已转换: {content[:100]}...")
                        except Exception as e:
                            logger.error(f"转换内容为字符串失败: {e}")
                            content = "错误: LLM返回了非字符串内容，无法显示"
                    
                    return {"content": content}
            else:
                logger.error(f"LLM响应格式错误: {json.dumps(response, ensure_ascii=False)[:200]}...")
                return {"error": "LLM响应格式错误", "raw_response": response}
                
        except Exception as e:
            logger.error(f"chat_with_tools失败: {str(e)}", exc_info=True)
            return {"error": f"对话失败: {str(e)}"}

    def get_service(self, provider_name: str):
        """
        获取指定供应商的LLM服务
        
        Args:
            provider_name: 供应商名称
            
        Returns:
            LLMService 实例或 None
        """
        return self.get_provider(provider_name)

    def list_services(self):
        """
        获取所有可用的LLM服务列表
        
        Returns:
            List[LLMService]: 服务列表
        """
        return list(self.providers.keys())

# 创建全局LLM服务管理器实例
llm_service_manager = LLMServiceManager()

class ProviderManager:
    """LLM供应商管理器，处理带工具的聊天功能"""
    
    def __init__(self, llm_service_manager: LLMServiceManager):
        self.llm_service_manager = llm_service_manager
    
    async def chat_with_tools(self,
                         provider_name: str,
                         model: str,
                         messages: List[Dict[str, Any]],
                         tools: Optional[List[Dict[str, Any]]] = None
                     ) -> Dict[str, Any]:
        """使用工具进行对话
        
        Args:
            provider_name: LLM供应商名称
            model: 模型名称
            messages: 对话历史消息
            tools: 可用的工具列表
            
        Returns:
            Dict[str, Any]: LLM响应，包含消息内容或工具调用
        """
        try:
            # 获取LLM服务
            service = self.llm_service_manager.get_provider(provider_name)
            if not service:
                logger.error(f"未找到LLM供应商: {provider_name}")
                return {"error": f"未找到LLM供应商: {provider_name}"}
                
            # 准备工具描述
            tools_desc = ""
            if tools:
                for tool in tools:
                    tool_desc = f"\n- {tool['name']}: {tool.get('description', '无描述')}"
                    if "parameters" in tool:
                        params = tool["parameters"].get("properties", {})
                        required = tool["parameters"].get("required", [])
                        tool_desc += "\n  参数:"
                        for param_name, param_info in params.items():
                            is_required = param_name in required
                            tool_desc += f"\n    - {param_name}: {param_info.get('description', '无描述')}"
                            if is_required:
                                tool_desc += " (必需)"
                    tools_desc += tool_desc
                
            # 准备系统消息
            system_content = (
                "你是一个能够使用外部工具的助手，可以使用以下工具：\n"
                f"{tools_desc}\n\n"
                "使用工具时必须严格遵循以下规则：\n"
                "1. 只能使用上面列出的工具，不要使用未定义的工具\n"
                "2. 工具名称必须精确匹配，不要修改或简化工具名称\n"
                "3. 当需要使用工具时，请生成完全符合JSON格式的工具调用，不要有任何额外文本\n"
                "4. JSON格式必须包含 'tool' 和 'arguments' 两个字段\n"
                "5. 'tool' 字段是工具名称，'arguments' 字段是包含参数的对象\n"
                "6. 不要使用代码块或引号包裹JSON，直接输出原始JSON\n"
                "7. 不要自己猜测或伪造工具执行结果\n"
                "8. 确保参数完全符合工具要求，参数名必须精确匹配\n"
                "9. 当调用查询类工具时，生成合适的查询语句，确保语法正确\n"
                "10. mysql 有4个工具 list_databases,list_tables,describe_table,execute_query 提问mysql时，请使用这些工具,严禁使用其它工具 \n"
                "11. influxdb 有4个工具 write_data,query_data,create_bucket,create_org 提问influxdb时，请使用这些工具 严禁使用其它工具  \n"
                "12. brave-search 有4个工具 brave_web_search,brave_local_search 提问brave-search时，请使用这些工具 严禁使用其它工具 \n"
                "13. filesystem 有11 个工具，分别是read_file,read_multiple_files,write_file,edit_file,create_directory,list_directory,directory_tree,move_file,search_files,get_file_info,list_allowed_directories ,对本地文件系统进行操作，请使用这些工具，严禁使用其它工具\n"
                "14. iot-checker 有2个工具 query_equip_data,run_Flux_to_query 提问iot-checker, 与 iot 有关的信息时，需要参数 tenantCode 是客户/租户编码，equipmentName 是设备名称，startTime 是指时间范围，请使用这些工具 严禁使用其它工具 \n"
                "15. baidu-map 有8个工具 都是map_ 开头 ,提问与地图有关的信息时，如一个地点的天气，位置，距离测量，地理规划等请使用这些工具 严禁使用其它工具 \n"
               
                "工具调用格式示例：\n"
                "{\n"
                '  "tool": "工具名称",\n'
                '  "arguments": {\n'
                '    "参数1": "值1",\n'
                '    "参数2": "值2"\n'
                '  }\n'
                "}\n\n"
                "特别地，如果是有关InfluxDB 查询工具，一定要使用以下的格式：\n"
                "{\n"
                '  "tool": "query-data",\n'
                '  "arguments": {\n'
                '    "org": "neuron",\n'
                '    "query": "from(bucket: \\"system\\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \\"cpu\\")" \n'
                '  }\n'
                "}\n\n"
                "InfluxDB查询使用Flux语言而不是SQL。以下是一些常用的Flux查询示例：\n"
                "- 列出所有buckets: buckets()\n"
                "- 查询指定bucket: from(bucket: \"mybucket\") |> range(start: -1h)\n"
                "- 筛选数据: from(bucket: \"mybucket\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"cpu\")\n"
                "注意不要使用SQL语法（如SELECT, SHOW DATABASES等），这些在Flux中不适用。\n\n"
                "如果用户请求不需要使用工具或没有可用工具，请直接用自然语言回答。\n"
                "如果用户请求需要使用工具但没有合适的工具可用，请告知用户该功能暂不支持。\n"
                "map_geocode 输入参数是 address 地址信息\n"
                "map_reverse_geocode 输入要参数 location 经纬度\n"
                "map_search_places 输入要参数 query 关键词 location  圆形中心点、radius 半径、region 城市\n"
                "map_place_details 输入要参数 uid\n"
                "map_distance_matrix 输入要参数  origins 起点列表、destinations 终点列表、mode 出行方式，如 driving）\n"
                "map_directions 输入要参数 origin（起点）、destination（终点）、mode（出行方式，如 transit）\n"
                "map_weather 输入要参数 district_id 行政区编码 或 location  经纬度\n"
                "地址信息之类查询需要组合查询，如查询一个地点的天气，需要先查询地点的经纬度，然后使用map_weather工具查询天气信息。\n"
             )
            
            if tools:
                logger.info(f"可用工具数量: {len(tools)}")
                for tool in tools:
                    logger.info(f"工具: {tool['name']}")
            
            # 格式化消息
            formatted_messages = [
                {"role": "system", "content": system_content}
            ]
            
            # 添加历史消息
            for msg in messages:
                if not isinstance(msg, dict):
                    logger.warning(f"跳过非字典消息: {msg}")
                    continue
                    
                # 获取基本消息属性
                role = msg.get("role", "user")
                content = msg.get("content")
                
                # 如果content是字典，需要特殊处理
                if isinstance(content, dict):
                    # 如果是工具调用
                    if "tool_call" in content:
                        tool_call = content["tool_call"]
                        formatted_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": str(uuid.uuid4()),
                                "type": "function",
                                "function": {
                                    "name": tool_call["name"],
                                    "arguments": json.dumps(tool_call["arguments"])
                                }
                            }]
                        })
                    # 如果是工具结果
                    elif "name" in content and "result" in content:
                        formatted_messages.append({
                            "role": "tool",
                            "content": str(content["result"]),
                            "tool_call_id": str(uuid.uuid4())
                        })
                    # 其他情况，转换为字符串
                    else:
                        formatted_messages.append({
                            "role": role,
                            "content": json.dumps(content)
                        })
                else:
                    # 普通消息
                    formatted_messages.append({
                        "role": role,
                        "content": str(content) if content is not None else ""
                    })
            
            logger.info(f"发送到LLM的消息数量: {len(formatted_messages)}")
            logger.debug(f"格式化后的消息: {json.dumps(formatted_messages, ensure_ascii=False)}")
            
            # 调用LLM服务
            return await self.llm_service_manager.chat_with_tools(
                provider_name=provider_name,
                model=model,
                messages=formatted_messages,
                tools=tools
            )
            
        except Exception as e:
            logger.error(f"chat_with_tools失败: {str(e)}", exc_info=True)
            return {"error": f"对话失败: {str(e)}"}
            
    def get_service(self, provider_name: str):
        """
        获取指定供应商的LLM服务
        
        Args:
            provider_name: 供应商名称
            
        Returns:
            LLMService 实例或 None
        """
        return self.llm_service_manager.get_provider(provider_name)

    def list_services(self):
        """
        获取所有可用的LLM服务列表
        
        Returns:
            List[LLMService]: 服务列表
        """
        return list(self.llm_service_manager.providers.keys())

# 导出全局provider_manager实例
provider_manager = ProviderManager(llm_service_manager) 