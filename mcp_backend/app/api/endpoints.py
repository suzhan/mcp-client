import json
import sys
import time
import traceback
import os
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from fastapi import APIRouter, HTTPException, Body, Depends, Request
from loguru import logger

from app.api.jsonrpc import jsonrpc, JSONRPCError, InvalidParams, router as jsonrpc_router
from app.services.mcp_client import client_manager
from app.services.llm_service import llm_service_manager, ProviderManager
from app.services.session_service import session_manager, Message, SESSION_DIR
from app.core.config import settings
from app.models.mcp_server_config import MCPServerConfig
from app.models.llm_provider_config import LLMProviderConfig
from app.api.i18n import router as i18n_router

router = APIRouter()

# 创建ProviderManager实例
provider_manager = ProviderManager(llm_service_manager)

# 添加JSON-RPC路由
router.include_router(jsonrpc_router)

# 添加i18n路由
router.include_router(i18n_router)

# JSON-RPC接口
@router.post("/jsonrpc")
async def handle_jsonrpc(request_data: Dict[str, Any] = Body(...)):
    """处理JSON-RPC请求"""
    response = await jsonrpc.handle_request(request_data)
    return response

# 注册JSON-RPC方法
async def register_jsonrpc_methods():
    """注册所有JSON-RPC方法"""
    
    # ---- 服务器管理方法 ----
    
    # 获取所有MCP服务器配置
    async def get_mcp_servers():
        return [server.dict() for server in settings.mcp_servers]
    jsonrpc.register_method("mcp.get_servers", get_mcp_servers)
    
    # 创建MCP服务器配置
    async def create_mcp_server(**server_data):
        try:
            # 生成唯一ID（如果未提供）
            if "id" not in server_data:
                import uuid
                server_data["id"] = str(uuid.uuid4())
            
            server_id = server_data["id"]
            
            # 创建新的服务器配置
            new_server = MCPServerConfig(**server_data)
            
            # 读取现有配置文件
            servers_data = {}
            if settings.SERVERS_CONFIG_PATH.exists():
                with open(settings.SERVERS_CONFIG_PATH, "r") as f:
                    try:
                        data = json.load(f)
                        # 检查是否已有 mcpServers 结构
                        if isinstance(data, dict) and "mcpServers" in data:
                            servers_data = data
                        else:
                            # 如果文件存在但格式不对，创建正确格式
                            servers_data = {"mcpServers": {}}
                    except json.JSONDecodeError:
                        # 文件存在但不是有效的 JSON
                        servers_data = {"mcpServers": {}}
            else:
                # 文件不存在，创建新的结构
                servers_data = {"mcpServers": {}}
            
            # 确保 mcpServers 键存在
            if "mcpServers" not in servers_data:
                servers_data["mcpServers"] = {}
            
            # 添加新服务器
            server_config = new_server.dict(exclude={"id"})  # 排除ID，因为ID作为key
            servers_data["mcpServers"][server_id] = server_config
            
            # 保存到配置文件
            with open(settings.SERVERS_CONFIG_PATH, "w") as f:
                json.dump(servers_data, f, indent=2)
            
            # 重新加载配置
            settings.load_mcp_servers()
            
            # 返回完整配置（包含ID）
            return {**server_config, "id": server_id}
        except Exception as e:
            logger.error(f"创建MCP服务器失败: {e}")
            raise JSONRPCError(500, f"创建MCP服务器失败: {str(e)}")
    jsonrpc.register_method("mcp.create_server", create_mcp_server)
    
    # 更新MCP服务器配置
    async def update_mcp_server(**params):
        try:
            # 验证必须参数
            if "server_id" not in params:
                raise JSONRPCError(400, "缺少必要参数: server_id")
            
            server_id = params.pop("server_id")
            server_data = params  # 剩余的所有参数都作为服务器数据
            
            # 读取现有配置
            existing_servers = settings.mcp_servers
            
            # 查找服务器
            server = next((s for s in existing_servers if s.id == server_id), None)
            if not server:
                raise JSONRPCError(404, f"服务器未找到: {server_id}")
            
            # 读取现有配置文件
            servers_data = {}
            if settings.SERVERS_CONFIG_PATH.exists():
                with open(settings.SERVERS_CONFIG_PATH, "r") as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict) and "mcpServers" in data:
                            servers_data = data
                        else:
                            # 如果文件存在但格式不对，创建以当前配置为基础的新格式
                            servers_data = {"mcpServers": {}}
                            for s in existing_servers:
                                servers_data["mcpServers"][s.id] = s.dict(exclude={"id"})
                    except json.JSONDecodeError:
                        # 文件存在但不是有效的 JSON，创建新的格式
                        servers_data = {"mcpServers": {}}
                        for s in existing_servers:
                            servers_data["mcpServers"][s.id] = s.dict(exclude={"id"})
            else:
                # 文件不存在，创建新的结构（基于现有加载的配置）
                servers_data = {"mcpServers": {}}
                for s in existing_servers:
                    servers_data["mcpServers"][s.id] = s.dict(exclude={"id"})
            
            # 确保 mcpServers 键存在
            if "mcpServers" not in servers_data:
                servers_data["mcpServers"] = {}
            
            # 更新服务器数据
            if server_id in servers_data["mcpServers"]:
                # 保留未更新字段的原始值
                updated_config = {**servers_data["mcpServers"][server_id]}
                # 应用更新
                for key, value in server_data.items():
                    if key != "id":  # 忽略 ID 更新
                        updated_config[key] = value
                
                # 验证更新后的数据
                MCPServerConfig(id=server_id, **updated_config)  # 仅验证
                
                # 保存更新后的配置
                servers_data["mcpServers"][server_id] = updated_config
            else:
                # 如果在文件中找不到服务器ID，创建一个新条目
                updated_config = server.dict(exclude={"id"})
                # 应用更新
                for key, value in server_data.items():
                    if key != "id":
                        updated_config[key] = value
                    
                # 验证更新后的数据
                MCPServerConfig(id=server_id, **updated_config)
                
                # 保存更新后的配置
                servers_data["mcpServers"][server_id] = updated_config
            
            # 保存到配置文件
            with open(settings.SERVERS_CONFIG_PATH, "w") as f:
                json.dump(servers_data, f, indent=2)
            
            # 重新加载配置
            settings.load_mcp_servers()
            
            # 返回完整配置（包含ID）
            return {**updated_config, "id": server_id}
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"更新MCP服务器失败: {e}")
            raise JSONRPCError(500, f"更新MCP服务器失败: {str(e)}")
    jsonrpc.register_method("mcp.update_server", update_mcp_server)
    
    # 删除MCP服务器配置
    async def delete_mcp_server(**params):
        try:
            # 验证必须参数
            if "server_id" not in params:
                raise JSONRPCError(400, "缺少必要参数: server_id")
            
            server_id = params["server_id"]
            
            # 先断开连接（如果已连接）
            if client_manager.is_server_connected(server_id):
                await client_manager.disconnect_from_server(server_id)
            
            # 读取现有配置
            existing_servers = settings.mcp_servers
            
            # 查找服务器
            server = next((s for s in existing_servers if s.id == server_id), None)
            if not server:
                raise JSONRPCError(404, f"服务器未找到: {server_id}")
            
            # 读取现有配置文件
            servers_data = {}
            if settings.SERVERS_CONFIG_PATH.exists():
                with open(settings.SERVERS_CONFIG_PATH, "r") as f:
                    try:
                        servers_data = json.load(f)
                    except json.JSONDecodeError:
                        # 文件存在但不是有效的 JSON
                        servers_data = {"mcpServers": {}}
            else:
                # 文件不存在，无需删除
                return {"success": False, "message": "配置文件不存在"}
            
            # 确保 mcpServers 键存在
            if "mcpServers" not in servers_data:
                return {"success": False, "message": "配置文件格式不正确"}
            
            # 删除服务器
            if server_id in servers_data["mcpServers"]:
                del servers_data["mcpServers"][server_id]
                
                # 保存到配置文件
                with open(settings.SERVERS_CONFIG_PATH, "w") as f:
                    json.dump(servers_data, f, indent=2)
                
                # 重新加载配置
                settings.load_mcp_servers()
                
                return {"success": True}
            else:
                return {"success": False, "message": "服务器在配置文件中未找到"}
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"删除MCP服务器失败: {e}")
            raise JSONRPCError(500, f"删除MCP服务器失败: {str(e)}")
    jsonrpc.register_method("mcp.delete_server", delete_mcp_server)
    
    # 测试MCP服务器连接
    async def test_server_connection(**params):
        try:
            # 验证必须参数
            if "server_id" not in params:
                raise JSONRPCError(400, "缺少必要参数: server_id")
            
            server_id = params["server_id"]
            
            server_config = next((s for s in settings.mcp_servers if s.id == server_id), None)
            if not server_config:
                return {"success": False, "message": "服务器配置未找到"}
            
            # 测试连接
            if not client_manager.list_connected_servers():
                # 如果服务器未连接，先连接
                success = await client_manager.connect_to_server(server_id, server_config.dict())
                if not success:
                    return {"success": False, "message": "服务器连接失败"}
            
            # 获取工具列表以验证连接
            tools = await client_manager.get_server_tools(server_id)
            if tools:
                return {
                    "success": True, 
                    "message": "连接成功", 
                    "details": {
                        "tools_count": len(tools),
                        "tools": tools
                    }
                }
            else:
                await client_manager.disconnect_from_server(server_id)
                return {"success": False, "message": "服务器未提供任何工具"}
            
        except Exception as e:
            logger.error(f"测试MCP服务器连接时出错: {e}")
            return {"success": False, "message": f"连接错误: {str(e)}"}
    jsonrpc.register_method("mcp.test_server_connection", test_server_connection)
    
    # 连接到MCP服务器
    async def connect_to_server(**params):
        try:
            # 验证必须参数
            if "server_id" not in params:
                raise JSONRPCError(400, "缺少必要参数: server_id")
            
            server_id = params["server_id"]
            
            server_config = next((s for s in settings.mcp_servers if s.id == server_id), None)
            if not server_config:
                logger.error(f"服务器配置未找到: {server_id}")
                return {"success": False, "message": f"服务器配置未找到: {server_id}"}
            
            logger.info(f"正在连接到MCP服务器: {server_id} ({server_config.name})")
            
            # 对于 SSE 连接，使用异步任务并立即返回，避免阻塞前端
            if server_config.type == "sse":
                # 检查服务器是否已经在连接中
                if getattr(connect_to_server, f"connecting_{server_id}", False):
                    return {"success": True, "message": "连接中", "status": "connecting"}
                
                # 标记服务器正在连接
                setattr(connect_to_server, f"connecting_{server_id}", True)
                
                # 创建异步任务处理连接
                async def connect_task():
                    try:
                        success = await client_manager.connect_to_server(server_id, server_config.dict())
                        if success:
                            logger.info(f"MCP服务器连接成功: {server_id}")
                        else:
                            logger.error(f"MCP服务器连接失败: {server_id}")
                    finally:
                        # 清除连接中状态
                        setattr(connect_to_server, f"connecting_{server_id}", False)
                
                # 启动连接任务
                asyncio.create_task(connect_task())
                
                # 立即返回连接中状态
                return {"success": True, "message": "正在连接中", "status": "connecting"}
            
            # 对于非 SSE 连接，使用原有的同步连接方式
            success = await client_manager.connect_to_server(server_id, server_config.dict())
            
            if success:
                logger.info(f"MCP服务器连接成功: {server_id}")
                # 尝试获取工具列表以验证连接正常
                try:
                    tools = await client_manager.get_server_tools(server_id)
                    logger.info(f"获取到服务器工具: {len(tools)}个")
                except Exception as e:
                    logger.warning(f"获取工具列表失败，但连接成功: {e}")
                return {"success": True, "message": "连接成功"}
            else:
                logger.error(f"MCP服务器连接失败: {server_id}")
                return {"success": False, "message": "连接失败，请检查服务器配置和网络连接"}
        except Exception as e:
            logger.error(f"连接MCP服务器时出错: {e}")
            return {"success": False, "message": f"连接错误: {str(e)}"}
    jsonrpc.register_method("mcp.connect_server", connect_to_server)
    
    # 断开与MCP服务器的连接
    async def disconnect_from_server(**params):
        try:
            # 验证必须参数
            if "server_id" not in params:
                raise JSONRPCError(400, "缺少必要参数: server_id")
            
            server_id = params["server_id"]
            
            success = await client_manager.disconnect_from_server(server_id)
            return {"success": success}
        except Exception as e:
            logger.error(f"断开MCP服务器连接时出错: {e}")
            return {"success": False, "message": f"断开连接错误: {str(e)}"}
    jsonrpc.register_method("mcp.disconnect_server", disconnect_from_server)
    
    # 获取所有已连接的MCP服务器
    async def get_connected_servers():
        connected_servers = client_manager.list_connected_servers()
        return {"servers": connected_servers}
    jsonrpc.register_method("mcp.get_connected_servers", get_connected_servers)
    
    # 获取所有MCP服务器状态及工具信息
    async def get_mcp_servers_with_tools():
        """获取所有MCP服务器的状态、工具和资源信息"""
        try:
            # 从配置中获取所有服务器
            all_servers = settings.mcp_servers
            
            # 准备结果
            result = {"servers": []}
            
            # 处理每个服务器
            for server_config in all_servers:
                server_id = server_config.id
                server_info = {
                    "id": server_id,
                    "name": server_config.name,
                    "status": "offline",
                    "error_message": None,
                    "tools": [],
                    "resources": [],  # 新增资源列表
                    "tools_count": 0,  # 工具数量
                    "resources_count": 0,  # 资源数量
                    "prompts_count": 0,  # Prompt数量
                    "prompts_list": []  # Prompt列表
                }
                
                # 检查是否正在连接中（对于SSE连接）
                if server_config.type == "sse" and getattr(connect_to_server, f"connecting_{server_id}", False):
                    server_info["status"] = "connecting"
                    result["servers"].append(server_info)
                    continue
                
                # 检查是否已连接
                if client_manager.is_server_connected(server_id):
                    server_info["status"] = "online"
                    
                    # 获取工具列表
                    try:
                        tools = await client_manager.get_server_tools(server_id)
                        server_info["tools"] = tools
                        server_info["tools_count"] = len(tools)
                    except Exception as e:
                        logger.error(f"获取服务器 {server_id} 工具列表失败: {e}")
                        
                    # 获取资源列表
                    try:
                        resources = await client_manager.get_server_resources(server_id)
                        server_info["resources"] = resources
                        server_info["resources_count"] = len(resources)
                        logger.info(f"服务器 {server_id} 资源数量: {len(resources)}")
                    except Exception as e:
                        logger.error(f"获取服务器 {server_id} 资源列表失败: {e}")
                        server_info["resources"] = []
                        server_info["resources_count"] = 0
                    
                    # 获取Prompts列表
                    try:
                        prompts_response = await client_manager.get_server_prompts(server_id)
                        server_info["prompts_count"] = len(prompts_response)
                        # 添加prompt名称列表
                        server_info["prompts_list"] = prompts_response
                    except Exception as e:
                        logger.error(f"获取服务器 {server_id} Prompts列表失败: {e}")
                else:
                    # 尝试连接服务器（仅对非SSE连接尝试）
                    if server_config.type != "sse":
                        try:
                            logger.info(f"尝试连接服务器: {server_id}")
                            connected = await client_manager.connect_to_server(server_id, server_config.dict())
                            if connected:
                                server_info["status"] = "online"
                                
                                # 获取工具列表
                                try:
                                    tools = await client_manager.get_server_tools(server_id)
                                    server_info["tools"] = tools
                                    server_info["tools_count"] = len(tools)
                                except Exception as e:
                                    logger.error(f"获取服务器 {server_id} 工具列表失败: {e}")
                                    
                                # 获取资源列表
                                try:
                                    resources = await client_manager.get_server_resources(server_id)
                                    server_info["resources"] = resources
                                    server_info["resources_count"] = len(resources)
                                except Exception as e:
                                    logger.error(f"获取服务器 {server_id} 资源列表失败: {e}")
                        except Exception as e:
                            logger.error(f"连接服务器 {server_id} 失败: {e}")
                
                result["servers"].append(server_info)
            
            return result
        except Exception as e:
            logger.error(f"获取MCP服务器状态和工具信息失败: {e}")
            raise JSONRPCError(500, f"获取MCP服务器状态和工具信息失败: {str(e)}")
    jsonrpc.register_method("mcp.get_servers_with_tools", get_mcp_servers_with_tools)
    
    # 获取所有MCP服务器状态
    async def get_servers_status():
        """获取所有MCP服务器的状态信息"""
        try:
            # 从配置中获取所有服务器
            all_servers = settings.mcp_servers
            
            # 准备结果
            result = []
            
            # 处理每个服务器
            for server_config in all_servers:
                server_id = server_config.id
                server_name = server_config.name
                server_type = server_config.type if hasattr(server_config, 'type') else "default"
                
                # 状态信息
                status_info = {
                    "id": server_id,
                    "name": server_name,
                    "type": server_type,
                    "status": "offline",
                    "tools_count": 0,
                    "resources_count": 0,
                    "prompts_count": 0,
                    "tools_list": [],  # 工具列表
                    "resources_list": [],  # 资源列表
                    "prompts_list": [],  # Prompt列表
                    "operations": []  # 可用操作
                }
                
                # 检查是否已连接
                if client_manager.is_server_connected(server_id):
                    status_info["status"] = "online"
                    
                    # 获取工具列表
                    try:
                        tools = await client_manager.get_server_tools(server_id)
                        status_info["tools_count"] = len(tools)
                        # 添加工具名称列表
                        status_info["tools_list"] = [
                            {"name": tool.get("name", "未知"), "description": tool.get("description", "")}
                            for tool in tools
                        ]
                    except Exception as e:
                        logger.error(f"获取服务器 {server_id} 工具列表失败: {e}")
                        
                    # 获取资源列表
                    try:
                        resources = await client_manager.get_server_resources(server_id)
                        status_info["resources_count"] = len(resources)
                        # 添加资源名称列表
                        status_info["resources_list"] = [
                            {"name": resource.get("name", "未知"), "uri": resource.get("uri", "")}
                            for resource in resources
                        ]
                    except Exception as e:
                        logger.error(f"获取服务器 {server_id} 资源列表失败: {e}")
                    
                    # 获取Prompts列表
                    try:
                        prompts_response = await client_manager.get_server_prompts(server_id)
                        status_info["prompts_count"] = len(prompts_response)
                        # 添加prompt名称列表
                        status_info["prompts_list"] = prompts_response
                    except Exception as e:
                        logger.error(f"获取服务器 {server_id} Prompts列表失败: {e}")
                else:
                    # 尝试连接服务器
                    try:
                        logger.info(f"尝试连接服务器: {server_id}")
                        connected = await client_manager.connect_to_server(server_id, server_config.dict())
                        if connected:
                            status_info["status"] = "online"
                            
                            # 获取工具列表
                            try:
                                tools = await client_manager.get_server_tools(server_id)
                                status_info["tools_count"] = len(tools)
                                # 添加工具名称列表
                                status_info["tools_list"] = [
                                    {"name": tool.get("name", "未知"), "description": tool.get("description", "")}
                                    for tool in tools
                                ]
                            except Exception as e:
                                logger.error(f"获取服务器 {server_id} 工具列表失败: {e}")
                                
                            # 获取资源列表
                            try:
                                resources = await client_manager.get_server_resources(server_id)
                                status_info["resources_count"] = len(resources)
                                # 添加资源名称列表
                                status_info["resources_list"] = [
                                    {"name": resource.get("name", "未知"), "uri": resource.get("uri", "")}
                                    for resource in resources
                                ]
                            except Exception as e:
                                logger.error(f"获取服务器 {server_id} 资源列表失败: {e}")
                    except Exception as e:
                        logger.error(f"连接服务器 {server_id} 失败: {e}")
                
                # 添加可用操作
                status_info["operations"] = [
                    {"name": "view", "label": "查看"},
                    {"name": "disconnect", "label": "断开连接"}
                ]
                
                result.append(status_info)
            
            return {"servers": result}
        except Exception as e:
            logger.error(f"获取MCP服务器状态信息失败: {e}")
            raise JSONRPCError(500, f"获取MCP服务器状态信息失败: {str(e)}")
    jsonrpc.register_method("mcp.get_servers_status", get_servers_status)
    
    # ---- 工具相关方法 ----
    
    # 获取服务器提供的工具列表
    async def list_tools(server_id: str):
        tools = await client_manager.list_tools(server_id)
        logger.info(f"获取到服务器{server_id}的工具列表: {tools}")
        return tools
    jsonrpc.register_method("mcp.list_tools", list_tools)
    
    # 调用工具
    async def call_tool(server_id: str, tool_name: str, arguments: Dict[str, Any]):
        result = await client_manager.call_tool(server_id, tool_name, arguments)
        return result
    jsonrpc.register_method("mcp.call_tool", call_tool)
    
    # ---- 资源相关方法 ----
    
    # 获取服务器提供的资源列表
    async def list_resources(server_id: str):
        resources = await client_manager.list_resources(server_id)
        return resources
    jsonrpc.register_method("mcp.list_resources", list_resources)
    
    # 读取资源
    async def read_resource(server_id: str, resource_uri: str):
        content, mime_type = await client_manager.read_resource(server_id, resource_uri)
        return {"content": content, "mimeType": mime_type}
    jsonrpc.register_method("mcp.read_resource", read_resource)
    
    # ---- 提示模板相关方法 ----
    
    # 获取服务器提供的提示模板列表
    async def list_prompts(server_id: str):
        prompts = await client_manager.list_prompts(server_id)
        return {"prompts": prompts}
    jsonrpc.register_method("mcp.list_prompts", list_prompts)
    
    # 获取提示模板
    async def get_prompt(server_id: str, prompt_name: str, arguments: Dict[str, Any]):
        result = await client_manager.get_prompt(server_id, prompt_name, arguments)
        return result
    jsonrpc.register_method("mcp.get_prompt", get_prompt)
    
    # ---- LLM供应商相关方法 ----
    
    # 获取所有LLM供应商配置
    async def get_llm_providers():
        return [provider.dict() for provider in settings.llm_providers]
    jsonrpc.register_method("llm.get_providers", get_llm_providers)
    
    # 创建LLM供应商
    async def create_llm_provider(provider_data: Dict[str, Any]):
        try:
            # 检查同名供应商
            existing_providers = settings.llm_providers
            if any(p.name == provider_data["name"] for p in existing_providers):
                raise JSONRPCError(400, f"供应商名称已存在: {provider_data['name']}")
            
            # 创建新的供应商配置
            new_provider = LLMProviderConfig(**provider_data)
            
            # 添加新供应商
            providers_data = [provider.dict() for provider in existing_providers]
            providers_data.append(new_provider.dict())
            
            # 保存到配置文件
            with open(settings.LLM_CONFIG_PATH, "w") as f:
                json.dump(providers_data, f, indent=2)
            
            # 添加到LLM服务管理器
            llm_service_manager.add_provider(new_provider)
            
            return new_provider.dict()
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"创建LLM供应商失败: {e}")
            raise JSONRPCError(500, f"创建LLM供应商失败: {str(e)}")
    jsonrpc.register_method("llm.create_provider", create_llm_provider)
    
    # 获取LLM供应商可用的模型列表
    async def get_provider_models(provider_name: str):
        try:
            # 获取LLM服务
            service = llm_service_manager.get_provider(provider_name)
            if not service:
                # 尝试从配置加载服务
                provider_config = next((p for p in settings.llm_providers if p.name == provider_name), None)
                if not provider_config:
                    raise JSONRPCError(404, f"LLM供应商未找到: {provider_name}")
                
                llm_service_manager.add_provider(provider_config)
            
            # 获取模型列表
            result = await llm_service_manager.get_provider_models(provider_name)
            
            if "error" in result and not result.get("models"):
                logger.error(f"获取供应商模型列表失败: {result['error']}")
                raise JSONRPCError(500, result["error"])
                
            return result
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"获取供应商模型列表失败: {e}")
            raise JSONRPCError(500, f"获取供应商模型列表失败: {str(e)}")
    jsonrpc.register_method("llm.get_provider_models", get_provider_models)
    
    # 更新LLM供应商
    async def update_llm_provider(provider_name: str, provider_data: Dict[str, Any]):
        try:
            # 读取现有配置
            existing_providers = settings.llm_providers
            
            # 查找供应商
            provider_index = next((i for i, p in enumerate(existing_providers) if p.name == provider_name), None)
            if provider_index is None:
                raise JSONRPCError(404, f"供应商未找到: {provider_name}")
            
            # 更新供应商数据
            providers_data = [provider.dict() for provider in existing_providers]
            
            # 保留原来的名称，不允许修改名称
            provider_data["name"] = provider_name
            providers_data[provider_index].update(provider_data)
            
            # 验证更新后的数据
            updated_provider = LLMProviderConfig(**providers_data[provider_index])
            providers_data[provider_index] = updated_provider.dict()
            
            # 保存到配置文件
            with open(settings.LLM_CONFIG_PATH, "w") as f:
                json.dump(providers_data, f, indent=2)
            
            # 更新LLM服务管理器
            llm_service_manager.remove_provider(provider_name)
            llm_service_manager.add_provider(updated_provider)
            
            return updated_provider.dict()
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"更新LLM供应商失败: {e}")
            raise JSONRPCError(500, f"更新LLM供应商失败: {str(e)}")
    jsonrpc.register_method("llm.update_provider", update_llm_provider)
    
    # 删除LLM供应商
    async def delete_llm_provider(provider_name: str):
        try:
            # 读取现有配置
            existing_providers = settings.llm_providers
            
            # 查找供应商
            provider_index = next((i for i, p in enumerate(existing_providers) if p.name == provider_name), None)
            if provider_index is None:
                raise JSONRPCError(404, f"供应商未找到: {provider_name}")
            
            # 删除供应商
            providers_data = [provider.dict() for provider in existing_providers]
            del providers_data[provider_index]
            
            # 保存到配置文件
            with open(settings.LLM_CONFIG_PATH, "w") as f:
                json.dump(providers_data, f, indent=2)
            
            # 从LLM服务管理器中移除
            llm_service_manager.remove_provider(provider_name)
            
            return {"success": True}
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"删除LLM供应商失败: {e}")
            raise JSONRPCError(500, f"删除LLM供应商失败: {str(e)}")
    jsonrpc.register_method("llm.delete_provider", delete_llm_provider)
    
    # 测试LLM供应商连接
    async def test_llm_provider_connection(provider_name: str):
        try:
            # 获取LLM服务
            service = llm_service_manager.get_provider(provider_name)
            if not service:
                # 尝试从配置加载服务
                provider_config = next((p for p in settings.llm_providers if p.name == provider_name), None)
                if not provider_config:
                    raise JSONRPCError(404, f"LLM供应商未找到: {provider_name}")
                
                llm_service_manager.add_provider(provider_config)
                service = llm_service_manager.get_provider(provider_name)
            
            # 发送测试消息
            test_message = [{"role": "user", "content": "Hello"}]
            result = await service.get_completion(test_message)
            
            return {"success": True, "message": "连接测试成功"}
        except Exception as e:
            logger.error(f"测试LLM供应商连接失败: {e}")
            return {"success": False, "message": str(e)}
    jsonrpc.register_method("llm.test_provider_connection", test_llm_provider_connection)
    
    # 发送消息到LLM
    async def send_to_llm(provider_name: str, messages: List[Dict[str, Any]], model: Optional[str] = None):
        service = llm_service_manager.get_provider(provider_name)
        if not service:
            # 尝试从配置加载服务
            provider_config = next((p for p in settings.llm_providers if p.name == provider_name), None)
            if not provider_config:
                raise JSONRPCError(404, f"LLM供应商未找到: {provider_name}")
            
            llm_service_manager.add_provider(provider_config)
            service = llm_service_manager.get_provider(provider_name)
        
        result = await service.get_completion(messages, model)
        return result
    jsonrpc.register_method("llm.send_message", send_to_llm)
    
    # 使用LLM生成文本
    async def generate_text(
        session_id: Optional[str] = None,
        prompt: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
        provider_name: str = "",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None
    ):
        try:
            logger.info(f"生成文本请求: provider={provider_name}, model={model}, prompt={prompt[:50]}...")
            
            # 参数验证
            if not provider_name:
                raise InvalidParams("provider_name不能为空")
            
            # 获取LLM服务
            service = llm_service_manager.get_provider(provider_name)
            if not service:
                # 尝试从配置加载服务
                provider_config = next((p for p in settings.llm_providers if p.name == provider_name), None)
                if not provider_config:
                    raise JSONRPCError(404, f"LLM供应商未找到: {provider_name}")
                
                llm_service_manager.add_provider(provider_config)
                service = llm_service_manager.get_provider(provider_name)
            
            # 构造消息列表
            llm_messages = []
            
            # 添加系统消息
            llm_messages.append({
                "role": "system", 
                "content": "你是一个有帮助的AI助手。请按照指示生成内容，简洁、直接地回答，不要添加额外的解释。"
            })
            
            # 如果有消息历史，添加到消息列表
            if messages and isinstance(messages, list):
                # 只取最近的几条消息作为上下文，避免token过多
                recent_messages = messages[-10:]
                # 使用标准格式转换消息
                for msg in recent_messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        llm_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # 添加当前提示
            llm_messages.append({
                "role": "user",
                "content": prompt
            })
            
            logger.info(f"发送到LLM的消息数量: {len(llm_messages)}")
            
            # 调用LLM服务
            response = await service.get_completion(
                messages=llm_messages,
                model=model,
                temperature=0.7,
                max_tokens=max_tokens
            )
            
            if "error" in response:
                logger.error(f"生成文本失败: {response['error']}")
                return {"error": response["error"]}
            
            # 提取生成的文本
            generated_text = ""
            
            # 处理不同格式的响应
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                
                if "message" in choice and "content" in choice["message"]:
                    generated_text = choice["message"]["content"]
                elif "text" in choice:
                    generated_text = choice["text"]
            
            logger.info(f"生成文本成功: {generated_text[:50]}...")
            
            # 如果为会话添加消息记录
            if session_id:
                try:
                    # 添加系统消息，记录生成的文本
                    await session_manager.add_message(
                        session_id=session_id,
                        role="system",
                        content=f"自动生成的标题: {generated_text}"
                    )
                except Exception as e:
                    logger.warning(f"将生成的文本添加到会话失败: {str(e)}")
            
            return {"text": generated_text}
            
        except Exception as e:
            logger.error(f"生成文本失败: {str(e)}", exc_info=True)
            return {"error": f"生成文本失败: {str(e)}"}
    
    jsonrpc.register_method("llm.generateText", generate_text)
    
    # ---- 会话管理相关方法 ----
    
    # 获取所有会话
    async def get_all_sessions():
        try:
            sessions = await session_manager.get_sessions()
            return {"sessions": sessions}
        except Exception as e:
            logger.error(f"获取所有会话时出错: {e}")
            raise JSONRPCError(500, f"获取会话失败: {str(e)}")

    @jsonrpc.method("sessions.createSession")
    async def create_session(**params):
        try:
            title = params.get("title", "新会话")
            mcp_server_id = params.get("mcp_server_id", None)
            llm_provider = params.get("llm_provider", None)
            llm_model = params.get("llm_model", None)
            
            logger.info(f"创建会话请求参数: title={title}, provider={llm_provider}, model={llm_model}, server={mcp_server_id}")
            
            # 确保SESSION_DIR目录存在
            if not os.path.exists(SESSION_DIR):
                logger.info(f"创建会话目录: {SESSION_DIR}")
                os.makedirs(SESSION_DIR, exist_ok=True)
            
            # 创建会话
            new_session = await session_manager.create_session(
                title=title,
                mcp_server_id=mcp_server_id,
                llm_provider=llm_provider,
                llm_model=llm_model
            )
            
            logger.info(f"会话创建成功: {new_session['id']}")
            
            # 检查会话结构是否完整
            if 'id' not in new_session or 'title' not in new_session:
                logger.error(f"创建的会话结构不完整: {new_session}")
                raise JSONRPCError(500, "创建会话失败: 会话结构不完整")
            
            # 确保返回的格式始终为 {"session": session_object}
            return {"session": new_session}
        except Exception as e:
            logger.error(f"创建会话时出错: {e}")
            raise JSONRPCError(500, f"创建会话失败: {str(e)}")

    @jsonrpc.method("sessions.getSession")
    async def get_session(id=None):
        if not id:
            raise InvalidParams("需要会话ID")
        
        try:
            session = await session_manager.get_session(id)
            return {"session": session}
        except Exception as e:
            if "找不到会话" in str(e):
                raise JSONRPCError(404, f"找不到会话: {id}")
            logger.error(f"获取会话 {id} 时出错: {e}")
            raise JSONRPCError(500, f"获取会话失败: {str(e)}")

    @jsonrpc.method("sessions.listSessions")
    async def list_sessions():
        return await get_all_sessions()
    
    # 兼容前端旧的API
    @jsonrpc.method("sessions.getAll")
    async def get_all_sessions_compat():
        return await get_all_sessions()

    @jsonrpc.method("sessions.updateSession")
    async def update_session(id=None, **params):
        if not id:
            raise InvalidParams("需要会话ID")
        
        valid_fields = ["name", "mcp_server_id", "llm_provider", "llm_model"]
        update_data = {}
        
        # 检查并添加有效字段
        for field in valid_fields:
            if field in params:
                update_data[field] = params[field]
        
        if not update_data:
            raise InvalidParams("未提供有效的更新字段")
        
        try:
            # 将name映射为title（如果存在）
            if "name" in update_data:
                update_data["title"] = update_data.pop("name")
            
            # 更新会话
            updated_session = await session_manager.update_session(id, **update_data)
            return {"session": updated_session}
        except Exception as e:
            if "找不到会话" in str(e):
                raise JSONRPCError(404, f"找不到会话: {id}")
            logger.error(f"更新会话 {id} 时出错: {e}")
            raise JSONRPCError(500, f"更新会话失败: {str(e)}")

    @jsonrpc.method("sessions.deleteSession")
    async def delete_session(id=None):
        if not id:
            raise InvalidParams("需要会话ID")
        
        try:
            result = await session_manager.delete_session(id)
            return {"success": result}
        except Exception as e:
            if "找不到会话" in str(e):
                raise JSONRPCError(404, f"找不到会话: {id}")
            logger.error(f"删除会话 {id} 时出错: {e}")
            raise JSONRPCError(500, f"删除会话失败: {str(e)}")

    @jsonrpc.method("sessions.getMessages")
    async def get_messages(session_id=None):
        if not session_id:
            raise InvalidParams("需要会话ID")
        
        try:
            # 检查会话是否存在
            current_session = await session_manager.get_session(session_id)
            if not current_session:
                raise JSONRPCError(404, f"找不到会话: {session_id}")
            
            # 更新会话活动时间
            await session_manager.update_session_activity(session_id)
            
            # 获取消息
            messages = await session_manager.get_messages(session_id)
            return {"messages": messages}
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"获取消息时出错: {e}")
            raise JSONRPCError(500, f"获取消息失败: {str(e)}")

    @jsonrpc.method("sessions.addMessage")
    async def add_message(session_id=None, role=None, content=None):
        if not session_id:
            raise InvalidParams("需要会话ID")
        if not role:
            raise InvalidParams("需要消息角色")
        if role not in ["user", "assistant", "system", "tool"]:
            raise InvalidParams("无效的消息角色")
        if content is None:
            raise InvalidParams("需要消息内容")
        
        try:
            # 检查会话是否存在
            current_session = await session_manager.get_session(session_id)
            if not current_session:
                raise JSONRPCError(404, f"找不到会话: {session_id}")
            
            # 更新会话活动时间
            await session_manager.update_session_activity(session_id)
            
            # 添加消息
            message = await session_manager.add_message(
                session_id=session_id,
                role=role,
                content=content
            )
            
            return {"message": message}
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"添加消息时出错: {e}")
            raise JSONRPCError(500, f"添加消息失败: {str(e)}")

    @jsonrpc.method("sessions.clearMessages")
    async def clear_messages(session_id=None):
        if not session_id:
            raise InvalidParams("需要会话ID")
        
        try:
            # 检查会话是否存在
            current_session = await session_manager.get_session(session_id)
            if not current_session:
                raise JSONRPCError(404, f"找不到会话: {session_id}")
            
            # 更新会话活动时间
            await session_manager.update_session_activity(session_id)
            
            # 清空消息
            result = await session_manager.clear_messages(session_id)
            return {"success": result}
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"清空消息时出错: {e}")
            raise JSONRPCError(500, f"清空消息失败: {str(e)}")

    @jsonrpc.method("chat.chat_with_tools")
    async def chat_with_tools(
        session_id: str,
        user_message: str,
        provider_name: str,
        model: str,
        server_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用工具进行对话
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            provider_name: LLM供应商名称
            model: 模型名称
            server_id: MCP服务器ID（可选）
            
        Returns:
            Dict[str, Any]: 对话响应
        """
        start_time = time.time()
        logger.info(f"开始对话: session_id={session_id}, provider={provider_name}, model={model}")
        try:
            # 参数验证
            if not session_id:
                raise InvalidParams("session_id不能为空")
            if not user_message:
                raise InvalidParams("user_message不能为空")
            if not provider_name:
                raise InvalidParams("provider_name不能为空")
            if not model:
                raise InvalidParams("model不能为空")
            
            # 获取或创建会话
            session_result = await get_active_session(session_id)
            session, new_session_created, error_message = session_result
            
            if not session:
                error_msg = error_message or f"会话不存在: {session_id}"
                logger.error(error_msg)
                raise InvalidParams(error_msg)
            
            # 添加用户消息到会话
            await session_manager.add_message(
                session_id=session_id,
                role="user",
                content=user_message
            )
            
            # 获取会话消息
            messages = await session_manager.get_messages(session_id)
            logger.info(f"当前消息数: {len(messages)}")
            
            # 获取MCP工具
            mcp_tools = []
            if server_id:
                try:
                    # 确保服务器已连接
                    if not client_manager.is_server_connected(server_id):
                        server_config = next((s for s in settings.mcp_servers if s.id == server_id), None)
                        if not server_config:
                            raise InvalidParams(f"找不到服务器配置: {server_id}")
                        logger.info(f"连接到MCP服务器: {server_id}")
                        connected = await client_manager.connect_to_server(server_id, server_config.dict())
                        if not connected:
                            raise RuntimeError(f"无法连接到服务器: {server_id}")
                    
                    # 获取工具列表
                    server_tools = await client_manager.get_server_tools(server_id)
                    
                    # 格式化为LLM可用的工具格式
                    for tool in server_tools:
                        tool_name = tool.get("name")
                        description = tool.get("description", "无描述")
                        
                        # 格式化输入模式
                        input_schema = tool.get("input_schema", {})
                        parameters = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                        
                        if "properties" in input_schema:
                            for param_name, param_info in input_schema["properties"].items():
                                parameters["properties"][param_name] = {
                                    "type": param_info.get("type", "string"),
                                    "description": param_info.get("description", "无描述")
                                }
                        
                        if "required" in input_schema:
                            parameters["required"] = input_schema["required"]
                        
                        mcp_tools.append({
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": description,
                                "parameters": parameters
                            }
                        })
                    
                    logger.info(f"获取到 {len(mcp_tools)} 个MCP工具")
                except Exception as e:
                    logger.error(f"获取MCP工具失败: {str(e)}", exc_info=True)
                    raise RuntimeError(f"获取MCP工具失败: {str(e)}")
            
            # 使用LLM进行对话
            try:
                if mcp_tools:
                    logger.info(f"使用MCP工具进行对话: {len(mcp_tools)}个工具")
                    response = await provider_manager.chat_with_tools(
                        provider_name=provider_name,
                        model=model,
                        messages=messages,
                        tools=mcp_tools
                    )
                else:
                    logger.info("直接使用LLM进行聊天 (无MCP工具)")
                    response = await provider_manager.chat_with_tools(
                        provider_name=provider_name,
                        model=model,
                        messages=messages
                    )
                    
                if "error" in response:
                    error_msg = response["error"]
                    # 检查是否是缺少name字段的错误
                    if "'name'" in error_msg:
                        error_msg = "大模型响应格式错误：工具调用缺少必要字段。请重试或联系管理员。"
                    # 检查是否是其他常见错误并提供友好的错误消息
                    elif "rate limit" in error_msg.lower():
                        error_msg = "请求频率超限：服务商限制了请求频率，请稍后再试。"
                    elif "unauthorized" in error_msg.lower() or "auth" in error_msg.lower():
                        error_msg = "授权验证失败：API密钥可能无效或已过期，请检查配置。"
                    elif "timeout" in error_msg.lower():
                        error_msg = "请求超时：服务响应时间过长，请稍后再试。"
                        
                    logger.error(f"LLM调用失败: {error_msg}")
                    raise RuntimeError(error_msg)
                    
                # 处理工具调用
                if "tool_calls" in response:
                    tool_calls = response["tool_calls"]
                    logger.info(f"处理 {len(tool_calls)} 个工具调用")
                    
                    results = []
                    for tool_call in tool_calls:
                        try:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["arguments"]
                            
                            # 验证工具和参数
                            logger.info(f"验证MCP工具: {tool_name}")
                            
                            # 查找工具所属的服务器
                            tool_servers = []
                            for srv in settings.mcp_servers:
                                if client_manager.is_server_connected(srv.id):
                                    try:
                                        srv_tools = await client_manager.get_server_tools(srv.id)
                                        if any(t["name"] == tool_name for t in srv_tools):
                                            tool_servers.append(srv.id)
                                    except Exception as srv_err:
                                        logger.warning(f"无法从服务器 {srv.id} 获取工具: {str(srv_err)}")
                            
                            # 如果找到多个服务器有相同工具，优先使用指定的服务器
                            target_server_id = server_id
                            if not target_server_id and tool_servers:
                                target_server_id = tool_servers[0]
                                logger.info(f"自动选择服务器: {target_server_id} 用于工具 {tool_name}")
                            
                            if not target_server_id:
                                # 尝试连接所有配置的服务器
                                logger.info("尝试连接所有配置的服务器以查找工具...")
                                for srv in settings.mcp_servers:
                                    if not client_manager.is_server_connected(srv.id):
                                        try:
                                            connected = await client_manager.connect_to_server(srv.id, srv.dict())
                                            if connected:
                                                srv_tools = await client_manager.get_server_tools(srv.id)
                                                if any(t["name"] == tool_name for t in srv_tools):
                                                    target_server_id = srv.id
                                                    logger.info(f"新连接的服务器 {srv.id} 包含工具 {tool_name}")
                                                    break
                                        except Exception as conn_err:
                                            logger.warning(f"连接服务器 {srv.id} 失败: {str(conn_err)}")
                            
                            if not target_server_id:
                                # 工具不存在，记录错误并继续处理
                                error_msg = f"找不到包含工具 {tool_name} 的服务器"
                                logger.error(f"[工具调用错误] {error_msg}")
                                
                                # 记录错误结果
                                await session_manager.add_message(
                                    session_id=session_id,
                                    role="tool",
                                    content={
                                        "name": tool_name,
                                        "result": f"错误: {error_msg}"
                                    }
                                )
                                
                                results.append({
                                    "tool": tool_name,
                                    "success": False,
                                    "error": error_msg
                                })
                                
                                # 跳过当前工具的其余处理
                                continue
                            
                            logger.info(f"执行MCP工具: {tool_name} 在服务器 {target_server_id}")
                            logger.info(f"参数: {json.dumps(tool_args, ensure_ascii=False)}")
                            
                            # 记录工具调用
                            await session_manager.add_message(
                                session_id=session_id,
                                role="assistant",
                                content={
                                    "tool_call": {
                                        "name": tool_name,
                                        "arguments": tool_args
                                    }
                                }
                            )
                            
                            # 执行工具调用
                            try:
                                tool_result = await client_manager.execute_tool(
                                    target_server_id,
                                    tool_name,
                                    tool_args
                                )
                                
                                logger.info(f"工具 {tool_name} 执行成功!")
                                
                                # 预处理工具结果，确保可以序列化
                                try:
                                    # 尝试JSON序列化，检查是否可以序列化
                                    json.dumps(tool_result)
                                    result_preview = json.dumps(tool_result, ensure_ascii=False)[:300]
                                    logger.info(f"结果预览: {result_preview}...")
                                except (TypeError, json.JSONDecodeError) as e:
                                    logger.warning(f"工具结果无法序列化为JSON: {str(e)}")
                                    # 如果不能序列化，转换为字符串
                                    tool_result = str(tool_result)
                                    logger.info(f"转换为字符串结果: {tool_result[:300]}...")
                                
                                # 记录工具结果
                                await session_manager.add_message(
                                    session_id=session_id,
                                    role="tool",
                                    content={
                                        "name": tool_name,
                                        "result": tool_result
                                    }
                                )
                                
                                results.append({
                                    "tool": tool_name,
                                    "success": True,
                                    "result": tool_result
                                })
                            except Exception as exec_error:
                                error_msg = f"工具执行失败: {str(exec_error)}"
                                logger.error(error_msg, exc_info=True)
                                
                                # 记录错误结果
                                await session_manager.add_message(
                                    session_id=session_id,
                                    role="tool",
                                    content={
                                        "name": tool_name,
                                        "result": f"错误: {error_msg}"
                                    }
                                )
                                
                                results.append({
                                    "tool": tool_name,
                                    "success": False,
                                    "error": error_msg
                                })
                            
                        except Exception as e:
                            error_msg = f"工具调用处理失败: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            
                            # 记录错误结果
                            await session_manager.add_message(
                                session_id=session_id,
                                role="tool",
                                content={
                                    "name": tool_call["name"],
                                    "result": f"错误: {error_msg}"
                                }
                            )
                            
                            results.append({
                                "tool": tool_call["name"],
                                "success": False,
                                "error": error_msg
                            })
                    
                    # 获取更新后的消息列表并总结工具执行结果
                    updated_messages = await session_manager.get_messages(session_id)
                    
                    logger.info("总结工具执行结果...")
                    summary = await provider_manager.chat_with_tools(
                        provider_name=provider_name,
                        model=model,
                        messages=updated_messages
                    )
                    
                    if "error" in summary:
                        logger.error(f"总结工具结果失败: {summary['error']}")
                        raise RuntimeError(summary["error"])
                        
                    # 添加总结消息
                    final_content = summary.get("content", "")
                    logger.info(f"工具执行总结: {final_content[:200]}...")
                    
                    await session_manager.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=final_content
                    )
                    
                    # 计算总耗时
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"对话完成，总耗时: {duration:.2f}秒")
                    
                    # 直接返回工具结果和总结
                    response_data = {
                        "content": final_content,
                        "tool_results": results,
                        "duration": duration,
                        "raw_data": None
                    }
                    
                    # 如果所有工具都失败，在总结之前添加错误信息
                    all_failed = all(not result.get("success", False) for result in results)
                    if all_failed:
                        error_summaries = []
                        for result in results:
                            if "error" in result:
                                tool_name = result.get("tool", "未知工具")
                                error_summaries.append(f"- {tool_name}: {result['error']}")
                        
                        if error_summaries:
                            error_prefix = f"工具调用失败:\n{chr(10).join(error_summaries)}\n\n"
                            # 只在content内容为空时添加错误信息
                            if not final_content.strip():
                                response_data["content"] = error_prefix + "请尝试其他命令或询问其他问题。"
                    
                    # 如果只有一个工具调用且成功执行，添加原始数据
                    if len(results) == 1 and results[0].get("success", False):
                        response_data["raw_data"] = results[0]["result"]
                        logger.info("添加原始工具结果到响应")
                    
                    return response_data
                    
                else:
                    # 普通消息响应
                    content = response.get("content", "")
                    logger.info(f"LLM响应: {content[:200]}...")
                    
                    await session_manager.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=content
                    )
                    
                    # 计算总耗时
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"对话完成，总耗时: {duration:.2f}秒")
                    
                    return {
                        "content": content,
                        "duration": duration
                    }
                
            except Exception as e:
                logger.error(f"对话处理失败: {str(e)}", exc_info=True)
                raise RuntimeError(f"对话失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"chat_with_tools失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"对话失败: {str(e)}")

    # 添加chat.with_tools作为chat.chat_with_tools的别名
    jsonrpc.register_method("chat.with_tools", chat_with_tools)
    
    # 新增：获取或创建活跃会话的辅助方法
    async def get_active_session(session_id=None, create_if_not_found=True, provider_name=None, model=None):
        """
        获取活跃会话，如果会话不存在或已过期，则创建新会话
        
        参数:
            session_id (str, 可选): 会话ID
            create_if_not_found (bool): 如果会话不存在，是否创建新会话
            provider_name (str, 可选): LLM供应商名称，创建新会话时使用
            model (str, 可选): LLM模型名称，创建新会话时使用
            
        返回:
            tuple: (会话数据, 是否新创建, 错误信息)
        """
        session = None
        new_session_created = False
        error_message = None
        
        # 如果提供了会话ID，尝试获取现有会话
        if session_id:
            try:
                session = await session_manager.get_session(session_id)
                if session:
                    # 检查会话是否超时
                    await session_manager._check_session_timeout(session)
                    if session.get('timed_out'):
                        logger.warning(f"会话已超时: {session_id}")
                        session = None
                        error_message = "会话已超时"
                else:
                    logger.warning(f"找不到会话: {session_id}")
                    error_message = "找不到会话"
            except Exception as e:
                logger.error(f"获取会话失败: {e}")
                error_message = f"获取会话失败: {str(e)}"
                session = None
        else:
            error_message = "未提供会话ID"
        
        # 如果需要且允许，创建新会话
        if not session and create_if_not_found:
            try:
                logger.info("正在创建新会话...")
                session = await session_manager.create_session(
                    title="新会话",
                    llm_provider=provider_name,
                    llm_model=model
                )
                new_session_created = True
                error_message = None  # 清除错误，因为我们成功创建了新会话
                logger.info(f"已创建新会话: {session['id']}")
            except Exception as e:
                logger.error(f"创建新会话失败: {e}")
                error_message = f"创建新会话失败: {str(e)}"
        
        return session, new_session_created, error_message

    @jsonrpc.method("sessions.getActiveSession")
    async def get_active_session_endpoint(session_id=None, create_if_not_found=True, provider_name=None, model=None):
        """获取活跃会话，如果不存在则创建新会话"""
        session, new_session_created, error_message = await get_active_session(
            session_id, create_if_not_found, provider_name, model
        )
        
        if session:
            return {
                "session": session,
                "new_session_created": new_session_created,
                "error": error_message
            }
        else:
            if error_message:
                raise JSONRPCError(404, error_message)
            else:
                raise JSONRPCError(500, "未知错误：无法获取或创建会话")

    @jsonrpc.method("mcp.direct_tool_call")
    async def direct_tool_call(server_id: str = None, tool_name: str = None, arguments: Dict[str, Any] = None):
        """直接调用MCP工具
        
        Args:
            server_id: MCP服务器ID
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            Dict: 工具执行结果
        """
        try:
            # 验证参数
            if not server_id:
                raise InvalidParams("server_id不能为空")
                
            if not tool_name:
                raise InvalidParams("tool_name不能为空")
                
            if arguments is None:
                arguments = {}
                
            # 记录调用信息
            logger.info(f"直接调用MCP工具: server_id={server_id}, tool={tool_name}")
            logger.info(f"参数: {json.dumps(arguments, ensure_ascii=False)}")
            
            # 确保服务器已连接
            if not client_manager.is_server_connected(server_id):
                logger.info(f"服务器 {server_id} 未连接，尝试连接...")
                server_config = next((s for s in settings.mcp_servers if s.id == server_id), None)
                if not server_config:
                    logger.error(f"找不到服务器配置: {server_id}")
                    raise InvalidParams(f"找不到服务器配置: {server_id}")
                
                connected = await client_manager.connect_to_server(server_id, server_config.dict())
                if not connected:
                    logger.error(f"无法连接到服务器: {server_id}")
                    raise RuntimeError(f"无法连接到服务器: {server_id}")
                    
                logger.info(f"已成功连接到服务器: {server_id}")
            
            # 获取工具列表
            tools = await client_manager.get_server_tools(server_id)
            tool = next((t for t in tools if t["name"] == tool_name), None)
            
            if not tool:
                logger.error(f"工具 {tool_name} 不存在于服务器 {server_id}")
                raise InvalidParams(f"工具 {tool_name} 不存在")
                
            logger.info(f"找到工具: {tool_name}")
            logger.info(f"描述: {tool.get('description', '无描述')}")
            
            # 执行工具调用
            try:
                start_time = time.time()
                result = await client_manager.execute_tool(server_id, tool_name, arguments)
                end_time = time.time()
                
                # 记录执行结果
                logger.info(f"工具 {tool_name} 执行成功")
                logger.info(f"执行时间: {end_time - start_time:.2f}秒")
                logger.info(f"结果: {json.dumps(result, ensure_ascii=False)[:1000]}...")
                
                return {
                    "success": True,
                    "result": result,
                    "execution_time": end_time - start_time
                }
                
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行失败: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"直接调用MCP工具失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"工具调用失败: {str(e)}")

    @jsonrpc.method("mcp.list_tools")
    async def list_mcp_tools(server_id: str):
        """
        获取MCP服务器提供的工具列表
        
        参数:
            server_id: 服务器ID
            
        返回:
            List[Dict]: 工具列表
        """
        try:
            # 检查服务器是否已连接
            if not client_manager.is_server_connected(server_id):
                # 尝试连接服务器
                server_config = next((s for s in settings.mcp_servers if s.id == server_id), None)
                if not server_config:
                    raise JSONRPCError(404, f"找不到服务器配置: {server_id}")
                
                logger.info(f"列出工具: 连接MCP服务器 {server_id}")
                success = await client_manager.connect_to_server(server_id, server_config.dict())
                if not success:
                    raise JSONRPCError(500, f"连接服务器失败: {server_id}")
            
            # 获取工具列表
            tools = await client_manager.get_server_tools(server_id)
            
            # 过滤None工具并进行额外验证
            if tools is None:
                logger.warning(f"服务器 {server_id} 返回的工具列表为None")
                return []
                
            valid_tools = []
            for i, tool in enumerate(tools):
                if tool is None:
                    logger.warning(f"服务器 {server_id} 返回的工具列表中第{i+1}项为None，已跳过")
                    continue
                
                # 确保工具包含name属性
                if not isinstance(tool, dict) or "name" not in tool:
                    logger.warning(f"服务器 {server_id} 返回的第{i+1}个工具缺少name属性或非字典类型: {tool}")
                    continue
                    
                valid_tools.append(tool)
            
            # 记录工具信息
            logger.info(f"服务器 {server_id} 提供了 {len(valid_tools)} 个有效工具")
            for i, tool in enumerate(valid_tools):
                if tool and isinstance(tool, dict) and "name" in tool:
                    desc = tool.get("description", "")[:50] if tool.get("description") else ""
                    logger.info(f"工具 {i+1}: {tool['name']} - {desc}...")
                else:
                    logger.warning(f"工具 {i+1}: 格式无效 - {str(tool)[:50]}...")
            
            return valid_tools
            
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"获取MCP工具列表时出错: {e}")
            raise JSONRPCError(500, f"获取MCP工具列表失败: {str(e)}")

    # 确保chat_with_tools方法可用
    # 注册chat.with_tools别名
    try:
        from app.api.endpoints import chat_with_tools
        jsonrpc.register_method("chat.with_tools", chat_with_tools)
        logger.info("成功注册 chat.with_tools 别名")
    except Exception as e:
        logger.error(f"注册 chat.with_tools 别名失败: {e}")

    # 获取SSE服务器连接状态
    async def get_sse_connection_status(**params):
        """获取SSE服务器的连接状态
        
        如果服务器正在连接中，返回connecting状态
        如果服务器已经连接，返回connected状态
        如果服务器未连接，返回disconnected状态
        """
        try:
            # 验证必须参数
            if "server_id" not in params:
                raise JSONRPCError(400, "缺少必要参数: server_id")
            
            server_id = params["server_id"]
            
            # 获取服务器配置
            server_config = next((s for s in settings.mcp_servers if s.id == server_id), None)
            if not server_config:
                return {"status": "unknown", "message": f"服务器配置未找到: {server_id}"}
            
            # 只处理SSE类型的服务器
            if server_config.type != "sse":
                return {"status": "not_sse", "message": "不是SSE类型的服务器"}
            
            # 检查是否正在连接中
            if getattr(connect_to_server, f"connecting_{server_id}", False):
                return {"status": "connecting", "message": "服务器正在连接中"}
            
            # 检查是否已连接
            if client_manager.is_server_connected(server_id):
                # 尝试获取工具列表以验证连接正常
                try:
                    tools = await client_manager.get_server_tools(server_id)
                    return {
                        "status": "connected", 
                        "message": "服务器已连接", 
                        "tools_count": len(tools)
                    }
                except Exception as e:
                    logger.warning(f"获取工具列表失败: {e}")
                    return {"status": "connected", "message": "服务器已连接但无法获取工具"}
            
            # 未连接状态
            return {"status": "disconnected", "message": "服务器未连接"}
        except Exception as e:
            logger.error(f"获取SSE连接状态时出错: {e}")
            return {"status": "error", "message": f"获取状态错误: {str(e)}"}
    jsonrpc.register_method("mcp.get_sse_connection_status", get_sse_connection_status)

# 在应用启动时注册方法
async def startup_event():
    """服务启动事件，注册所有JSON-RPC方法"""
    await register_jsonrpc_methods()
    
    # 自动连接配置的MCP服务器
    for server in settings.mcp_servers:
        try:
            logger.info(f"自动连接到MCP服务器: {server.name}")
            await client_manager.connect_to_server(server.id, server.dict())
        except Exception as e:
            logger.error(f"无法自动连接到MCP服务器 {server.name}: {e}")
            
    # 注意：不要在这里注册chat.with_tools别名，因为函数可能尚未定义
    # 而是在register_jsonrpc_methods函数的末尾注册别名 