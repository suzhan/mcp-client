import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Tuple
import traceback
import time
import httpx

# 正确导入stdio_client和相关函数
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    logging.info("Successfully imported stdio_client from mcp.client.stdio")
except ImportError:
    logging.error("Failed to import stdio_client from mcp.client.stdio")
    # 提供空函数以避免运行时错误
    def stdio_client(*args, **kwargs):
        raise ImportError("stdio_client could not be imported")

# 尝试导入sse相关模块
try:
    # 检查是否有sse相关模块
    from mcp.client.sse import sse_client
    logging.info("Successfully imported sse_client from mcp.client.sse")
except ImportError:
    logging.error("Failed to import sse_client from mcp.client.sse")
    # 提供空函数以避免运行时错误
    def sse_client(*args, **kwargs):
        raise ImportError("sse_client could not be imported")

# 尝试导入ErrorCodes，如果不可用则创建一个本地替代类
try:
    from mcp.types import ErrorCodes
    logging.info("Successfully imported ErrorCodes from mcp.types")
except ImportError:
    try:
        from mcp.client.errors import ErrorCodes
        logging.info("Successfully imported ErrorCodes from mcp.client.errors")
    except ImportError:
        logging.warning("ErrorCodes not found in mcp modules, creating local alternative")
        # 创建一个本地替代类
        class ErrorCodes:
            """本地替代ErrorCodes类"""
            SERVER_ERROR = "ServerError"
            REQUEST_FAILED = "RequestFailed"
            INVALID_REQUEST = "InvalidRequest"
            METHOD_NOT_FOUND = "MethodNotFound"

from app.core.config import settings
from app.models.mcp_server_config import MCPServerConfig
from app.services.llm_service import provider_manager

logger = logging.getLogger(__name__)

class Server:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name: str = name
        self.config: Dict[str, Any] = config
        self.session: Optional[ClientSession] = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()
        self._tools_cache: List[Dict[str, Any]] = []
        self._resources_cache: List[Dict[str, Any]] = []
        self._task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the server connection using MCP SDK."""
        try:
            logger.info(f"正在初始化MCP服务器: {self.name}")
            
            # 获取连接类型
            connection_type = self.config.get("type", "stdio")
            logger.info(f"连接类型: {connection_type}")
            
            if connection_type == "stdio":
                # 创建 stdio 服务器参数
                server_params = StdioServerParameters(
                    command=self.config["command"],
                    args=self.config.get("args", []),
                    env=self.config.get("env", {})
                )
                logger.info(f"服务器参数: command={server_params.command}, args={server_params.args}")
                
                # 在新的任务中创建stdio客户端
                self._task = asyncio.create_task(self._initialize_stdio_session(server_params))
                await self._task
            elif connection_type == "sse":
                # 检查必要参数
                if "url" not in self.config:
                    raise ValueError("SSE 连接需要指定 url 参数")
                    
                # 在新的任务中创建 SSE 客户端
                server_url = self.config["url"]
                logger.info(f"SSE 服务器URL: {server_url}")
                
                self._task = asyncio.create_task(self._initialize_sse_session(server_url))
                await self._task
            else:
                raise ValueError(f"不支持的连接类型: {connection_type}")
            
            # 缓存工具列表
            await self._cache_tools()
            
            # 缓存资源列表
            await self._cache_resources()
            
        except Exception as e:
            logger.error(f"初始化服务器失败: {self.name}, 错误: {str(e)}", exc_info=True)
            await self.cleanup()
            raise

    async def _initialize_stdio_session(self, server_params: StdioServerParameters) -> None:
        """Initialize the session in a separate task."""
        # 创建stdio客户端
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        logger.info("已创建stdio客户端")

        # 创建会话
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        logger.info("已创建ClientSession")

        # 初始化会话
        await self.session.initialize()
        logger.info("已初始化ClientSession")

    async def _initialize_sse_session(self, server_url: str) -> None:
        """通过 SSE 连接初始化会话。"""
        try:
            # 对 URL 进行验证/格式化
            if not server_url.startswith("http://") and not server_url.startswith("https://"):
                server_url = f"http://{server_url}"
            
            # 添加超时查询参数，防止连接被无限期阻塞
            if "?" not in server_url:
                server_url = f"{server_url}?timeout=10000"
            else:
                server_url = f"{server_url}&timeout=10000"
            
            logger.info(f"连接到 SSE 服务器: {server_url}")
            
            # 使用 MCP SDK 的 sse_client 函数获取通信管道
            # sse_client 与 stdio_client 一样返回 (read, write) 元组
            try:
                # 设置较短的超时时间，避免长时间阻塞
                sse_transport = await asyncio.wait_for(
                    self.exit_stack.enter_async_context(sse_client(server_url)),
                    timeout=30.0
                )
                logger.info("已创建 SSE 通信管道")
            except asyncio.TimeoutError:
                error_msg = f"连接 SSE 服务器超时 (30秒): {server_url}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            except (ConnectionRefusedError, ConnectionError) as ce:
                error_msg = f"连接 SSE 服务器失败: {server_url}, 错误: {str(ce)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            except Exception as e:
                error_msg = f"创建 SSE 连接时发生未知错误: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg)
            
            # 从元组中解析出读写通道
            try:
                read, write = sse_transport
            except (ValueError, TypeError) as e:
                error_msg = f"解析 SSE 通信管道失败: {str(e)}, 类型: {type(sse_transport)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # 创建会话
            try:
                self.session = await asyncio.wait_for(
                    self.exit_stack.enter_async_context(ClientSession(read, write)),
                    timeout=10.0
                )
                logger.info("已创建 SSE ClientSession")
            except asyncio.TimeoutError:
                error_msg = f"创建 SSE ClientSession 超时 (10秒)"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            except Exception as e:
                error_msg = f"创建 SSE ClientSession 失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg)
            
            # 初始化会话
            try:
                await asyncio.wait_for(
                    self.session.initialize(),
                    timeout=15.0
                )
                logger.info("已初始化 SSE 客户端会话")
            except asyncio.TimeoutError:
                error_msg = f"初始化 SSE ClientSession 超时 (15秒)"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            except Exception as e:
                error_msg = f"初始化 SSE ClientSession 失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg)
        except Exception as e:
            if not isinstance(e, RuntimeError):
                logger.error(f"初始化 SSE 会话失败: {str(e)}", exc_info=True)
            raise

    async def _cache_tools(self) -> None:
        """Cache the tools list from the server."""
        if not self.session:
            raise RuntimeError(f"服务器未初始化: {self.name}")
        
        try:
            logger.info(f"正在获取服务器工具列表: {self.name}")
            tools_response = await self.session.list_tools()
            self._tools_cache = []
            
            for item in tools_response:
                if isinstance(item, tuple) and item[0] == "tools":
                    for tool in item[1]:
                        tool_info = {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema
                        }
                        self._tools_cache.append(tool_info)
                        logger.info(f"找到工具: {tool.name}")
            
            logger.info(f"已缓存 {len(self._tools_cache)} 个工具")
            
        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}", exc_info=True)
            raise

    async def _cache_resources(self) -> None:
        """Cache the resources list from the server."""
        if not self.session:
            raise RuntimeError(f"服务器未初始化: {self.name}")
        
        try:
            logger.info(f"正在获取服务器资源列表: {self.name}")
            self._resources_cache = []
            
            try:
                resources_response = await self.session.list_resources()
                
                # 处理资源列表格式
                if hasattr(resources_response, 'resources'):
                    # 新版SDK格式
                    for resource in resources_response.resources:
                        resource_info = {
                            "name": getattr(resource, 'name', 'Unknown'),
                            "uri": getattr(resource, 'uri', ''),
                            "mimeType": getattr(resource, 'mimeType', '')
                        }
                        self._resources_cache.append(resource_info)
                        logger.info(f"找到资源: {resource_info['name']} ({resource_info['uri']})")
                elif isinstance(resources_response, tuple) and len(resources_response) > 0:
                    # 兼容旧版格式
                    for item in resources_response:
                        if isinstance(item, tuple) and item[0] == "resources":
                            for resource in item[1]:
                                resource_info = {
                                    "name": getattr(resource, 'name', 'Unknown'),
                                    "uri": getattr(resource, 'uri', ''),
                                    "mimeType": getattr(resource, 'mimeType', '')
                                }
                                self._resources_cache.append(resource_info)
                                logger.info(f"找到资源: {resource_info['name']} ({resource_info['uri']})")
            except Exception as e:
                # 捕获方法不存在的错误，直接返回空列表
                if "Method not found" in str(e):
                    logger.warning(f"服务器 {self.name} 不支持 resources/list 方法，返回空资源列表")
                else:
                    logger.error(f"获取资源列表失败: {str(e)}")
                    # 记录堆栈跟踪但不抛出异常
                    logger.debug(traceback.format_exc())
                
                # 返回空列表
                self._resources_cache = []
            
            logger.info(f"已缓存 {len(self._resources_cache)} 个资源")
            
        except Exception as e:
            logger.error(f"处理资源列表失败: {str(e)}")
            logger.debug(traceback.format_exc())
            # 不抛出异常，返回空列表
            self._resources_cache = []

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get the cached tools list."""
        if not self._tools_cache:
            await self._cache_tools()
        return self._tools_cache

    async def list_resources(self) -> List[Dict[str, Any]]:
        """Get the cached resources list."""
        if not self._resources_cache:
            try:
                await self._cache_resources()
            except Exception as e:
                logger.error(f"刷新资源缓存失败: {str(e)}")
                # 出错时返回空列表
                return []
        return self._resources_cache

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """获取服务器提供的prompt列表
        
        Returns:
            List[Dict[str, Any]]: prompt列表，每个prompt包含name和description字段
            
        Raises:
            RuntimeError: 服务器未初始化
        """
        try:
            if not self.session:
                error_msg = f"服务器 {self.name} 未初始化或连接已断开"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            logger.info(f"[MCP] 获取服务器 {self.name} 的prompt列表")
            
            # 使用MCP SDK获取prompt列表
            try:
                prompts_response = await self.session.list_prompts()
                
                # 处理响应格式
                result = []
                if hasattr(prompts_response, 'prompts'):
                    # 标准SDK格式
                    for prompt in prompts_response.prompts:
                        prompt_info = {
                            "name": getattr(prompt, 'name', 'Unknown'),
                            "description": getattr(prompt, 'description', '')
                        }
                        result.append(prompt_info)
                        logger.info(f"找到prompt: {prompt_info['name']}")
                elif isinstance(prompts_response, dict) and "prompts" in prompts_response:
                    # 字典格式
                    for prompt in prompts_response["prompts"]:
                        prompt_info = {
                            "name": prompt.get('name', 'Unknown'),
                            "description": prompt.get('description', '')
                        }
                        result.append(prompt_info)
                        logger.info(f"找到prompt: {prompt_info['name']}")
                
                logger.info(f"共找到 {len(result)} 个prompt")
                return result
                
            except Exception as e:
                # 捕获方法不存在的错误，直接返回空列表
                if "Method not found" in str(e):
                    logger.warning(f"服务器 {self.name} 不支持 prompts/list 方法，返回空prompt列表")
                else:
                    logger.error(f"获取prompt列表失败: {str(e)}")
                    logger.debug(traceback.format_exc())
                
                # 返回空列表
                return []
                
        except Exception as e:
            logger.error(f"获取prompt列表失败: {str(e)}")
            logger.debug(traceback.format_exc())
            # 不抛出异常，返回空列表
            return []

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行MCP工具，严格遵循MCP Python SDK
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            Any: 工具执行结果
            
        Raises:
            RuntimeError: 工具执行失败或服务器未初始化
            ValueError: 工具不存在
        """
        start_time = time.time()
        try:
            if not self.session:
                error_msg = f"服务器 {self.name} 未初始化或连接已断开"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            logger.info(f"[MCP] 执行工具: {tool_name}")
            logger.info(f"[MCP] 参数: {json.dumps(arguments, ensure_ascii=False)}")
            
            # 检查工具是否存在
            tools = await self.list_tools()
            tool = next((t for t in tools if t["name"] == tool_name), None)
            
            if not tool:
                error_msg = f"工具未找到: {tool_name}"
                logger.error(f"[MCP] {error_msg}")
                raise ValueError(error_msg)
                
            logger.info(f"[MCP] 工具描述: {tool.get('description', '无描述')}")
            
            # 使用MCP SDK执行工具调用
            try:
                # 严格按照MCP规范调用工具
                result = await self.session.call_tool(tool_name, arguments)
                
                # 计算执行时间
                end_time = time.time()
                execution_time = end_time - start_time
                
                # 记录执行结果
                logger.info(f"[MCP] 工具执行成功: {tool_name}")
                logger.info(f"[MCP] 执行时间: {execution_time:.2f}秒")
                
                # 处理特殊的CallToolResult对象
                if hasattr(result, '__dict__'):
                    logger.info(f"[MCP] 检测到特殊对象类型: {type(result).__name__}")
                    
                    # 如果是TextContent对象
                    if hasattr(result, 'content') and isinstance(result.content, list):
                        content_list = []
                        for item in result.content:
                            if hasattr(item, 'text') and item.text:
                                content_list.append(item.text)
                        
                        if content_list:
                            result = "\n".join(content_list)
                            logger.info(f"[MCP] 提取文本内容: {result[:200]}...")
                    
                    # 通用处理：转换为字典
                    elif hasattr(result, '__dict__'):
                        result = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                        logger.info(f"[MCP] 转换对象为字典: {json.dumps(result, ensure_ascii=False)[:200]}...")
                
                # 确保结果可序列化为JSON以便日志记录
                try:
                    if result is not None:
                        result_excerpt = json.dumps(result, ensure_ascii=False)[:500]
                        logger.info(f"[MCP] 结果预览: {result_excerpt}...")
                except (TypeError, json.JSONDecodeError) as json_err:
                    logger.warning(f"[MCP] 结果无法序列化为JSON，转换为字符串: {str(result)[:200]}...")
                    # 如果结果不可序列化，强制转换为字符串
                    result = str(result)
                
                return result
                
            except Exception as e:
                error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                logger.error(f"[MCP] {error_msg}", exc_info=True)
                
                # 处理MCP特定的错误码
                if hasattr(e, 'code'):
                    if e.code == ErrorCodes.SERVER_ERROR:
                        logger.error(f"[MCP] 服务器错误: {getattr(e, 'message', '未知错误')}")
                    elif e.code == ErrorCodes.REQUEST_FAILED:
                        logger.error("[MCP] 请求失败，可能是服务器无响应")
                    elif e.code == ErrorCodes.INVALID_REQUEST:
                        logger.error("[MCP] 无效请求格式")
                    elif e.code == ErrorCodes.METHOD_NOT_FOUND:
                        logger.error("[MCP] 请求的方法不存在")
                
                raise RuntimeError(error_msg)
                
        except Exception as e:
            if isinstance(e, (RuntimeError, ValueError)):
                raise
            
            error_msg = f"工具执行失败: {str(e)}"
            logger.error(f"[MCP] {error_msg}", exc_info=True)
            raise RuntimeError(error_msg)

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                logger.info(f"正在清理服务器资源: {self.name}")
                if self._task and not self._task.done():
                    self._task.cancel()
                    try:
                        await self._task
                    except asyncio.CancelledError:
                        logger.info(f"已取消任务: {self.name}")
                    except Exception as e:
                        logger.warning(f"取消任务时发生错误: {self.name}, {str(e)}")
                
                # 清理会话
                self.session = None
                
                try:
                    # 安全地关闭 exit stack
                    await self.exit_stack.aclose()
                    logger.info(f"已关闭资源管理器: {self.name}")
                except RuntimeError as e:
                    if "Attempted to exit cancel scope in a different task" in str(e):
                        logger.warning(f"跨任务关闭资源的错误，已安全处理: {self.name}")
                        # 创建新的 exit stack 以避免后续使用出错
                        self.exit_stack = AsyncExitStack()
                    else:
                        logger.error(f"关闭资源管理器出错: {self.name}, {str(e)}")
                except Exception as e:
                    logger.error(f"关闭资源管理器时发生未知错误: {self.name}, {str(e)}")
                
                # 清理缓存
                self._tools_cache = []
                self._resources_cache = []
                logger.info(f"服务器资源已清理: {self.name}")
            except Exception as e:
                logger.error(f"清理服务器资源失败: {self.name}, 错误: {str(e)}", exc_info=True)

class MCPClientManager:
    """Manages multiple MCP server connections."""
    
    def __init__(self):
        self._servers: Dict[str, Server] = {}
        
    async def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """Add and initialize a new server."""
        if name in self._servers:
            await self._servers[name].cleanup()
            
        server = Server(name, config)
        await server.initialize()
        self._servers[name] = server
        
    async def get_server(self, name: str) -> Optional[Server]:
        """Get a server by name."""
        return self._servers.get(name)
        
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List tools for a specific server."""
        server = self._servers.get(server_name)
        if not server:
            raise ValueError(f"服务器不存在: {server_name}")
        return await server.list_tools()
        
    async def get_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tools for a specific server with error handling."""
        try:
            return await self.list_tools(server_name)
        except Exception as e:
            logger.error(f"获取服务器工具列表失败: {server_name}, 错误: {str(e)}")
            return []
            
    async def list_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """List resources for a specific server."""
        server = self._servers.get(server_name)
        if not server:
            raise ValueError(f"服务器不存在: {server_name}")
        return await server.list_resources()
        
    async def get_server_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """Get resources for a specific server with error handling."""
        try:
            return await self.list_resources(server_name)
        except Exception as e:
            logger.error(f"获取服务器资源列表失败: {server_name}, 错误: {str(e)}")
            return []
            
    async def list_prompts(self, server_name: str) -> List[Dict[str, Any]]:
        """List prompts for a specific server."""
        server = self._servers.get(server_name)
        if not server:
            raise ValueError(f"服务器不存在: {server_name}")
        return await server.list_prompts()
        
    async def get_server_prompts(self, server_name: str) -> List[Dict[str, Any]]:
        """Get prompts for a specific server with error handling."""
        try:
            return await self.list_prompts(server_name)
        except Exception as e:
            logger.error(f"获取服务器prompt列表失败: {server_name}, 错误: {str(e)}")
            return []
            
    async def read_resource(self, server_name: str, resource_uri: str) -> Tuple[str, str]:
        """Read a resource from a specific server.
        
        Args:
            server_name: 服务器名称
            resource_uri: 资源URI
            
        Returns:
            Tuple[str, str]: 内容和MIME类型
            
        Raises:
            ValueError: 服务器不存在
            RuntimeError: 资源读取失败
        """
        server = self._servers.get(server_name)
        if not server:
            error_msg = f"服务器不存在: {server_name}"
            logger.error(f"[MCP] {error_msg}")
            raise ValueError(error_msg)
            
        # 检查服务器连接状态
        if not server.session:
            logger.warning(f"[MCP] 服务器 {server_name} 未连接，尝试重新初始化...")
            try:
                await server.initialize()
            except Exception as e:
                error_msg = f"重新初始化服务器 {server_name} 失败: {str(e)}"
                logger.error(f"[MCP] {error_msg}")
                raise RuntimeError(error_msg)
        
        try:
            # 读取资源
            logger.info(f"[MCP] 从服务器 {server_name} 读取资源: {resource_uri}")
            result = await server.session.read_resource(resource_uri)
            
            # 处理结果
            if hasattr(result, 'contents') and result.contents:
                content_item = result.contents[0]
                if hasattr(content_item, 'text') and content_item.text:
                    mime_type = getattr(content_item, 'mimeType', 'text/plain')
                    return content_item.text, mime_type
                elif hasattr(content_item, 'blob') and content_item.blob:
                    mime_type = getattr(content_item, 'mimeType', 'application/octet-stream')
                    return content_item.blob, mime_type
            
            # 默认返回空内容
            return "", "text/plain"
            
        except Exception as e:
            error_msg = f"从服务器 {server_name} 读取资源 {resource_uri} 失败: {str(e)}"
            logger.error(f"[MCP] {error_msg}")
            
            # 尝试重新初始化并重试一次
            if "未初始化" in str(e) or "连接已断开" in str(e):
                logger.info(f"[MCP] 尝试重新连接服务器 {server_name} 并重试...")
                try:
                    await server.cleanup()
                    await server.initialize()
                    logger.info(f"[MCP] 服务器 {server_name} 重新连接成功，重试读取资源")
                    result = await server.session.read_resource(resource_uri)
                    
                    # 处理结果
                    if hasattr(result, 'contents') and result.contents:
                        content_item = result.contents[0]
                        if hasattr(content_item, 'text') and content_item.text:
                            mime_type = getattr(content_item, 'mimeType', 'text/plain')
                            return content_item.text, mime_type
                        elif hasattr(content_item, 'blob') and content_item.blob:
                            mime_type = getattr(content_item, 'mimeType', 'application/octet-stream')
                            return content_item.blob, mime_type
                    
                    # 默认返回空内容
                    return "", "text/plain"
                except Exception as retry_error:
                    retry_error_msg = f"重试读取资源失败: {str(retry_error)}"
                    logger.error(f"[MCP] {retry_error_msg}")
                    raise RuntimeError(retry_error_msg)
            else:
                raise RuntimeError(error_msg)
            
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """使用MCP SDK在指定服务器上执行工具
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            Any: 工具执行结果
            
        Raises:
            ValueError: 服务器不存在
            RuntimeError: 工具执行失败
        """
        server = self._servers.get(server_name)
        if not server:
            error_msg = f"服务器不存在: {server_name}"
            logger.error(f"[MCP] {error_msg}")
            raise ValueError(error_msg)
            
        # 检查服务器连接状态
        if not server.session:
            logger.warning(f"[MCP] 服务器 {server_name} 未连接，尝试重新初始化...")
            try:
                await server.initialize()
            except Exception as e:
                error_msg = f"重新初始化服务器 {server_name} 失败: {str(e)}"
                logger.error(f"[MCP] {error_msg}")
                raise RuntimeError(error_msg)
        
        logger.info(f"[MCP] 在服务器 {server_name} 上执行工具 {tool_name}")
        
        try:
            # 执行工具调用
            result = await server.execute_tool(tool_name, arguments)
            return result
            
        except Exception as e:
            error_msg = f"在服务器 {server_name} 上执行工具 {tool_name} 失败: {str(e)}"
            logger.error(f"[MCP] {error_msg}")
            
            # 尝试重新初始化并重试一次
            if "未初始化" in str(e) or "连接已断开" in str(e):
                logger.info(f"[MCP] 尝试重新连接服务器 {server_name} 并重试...")
                try:
                    await server.cleanup()
                    await server.initialize()
                    logger.info(f"[MCP] 服务器 {server_name} 重新连接成功，重试工具 {tool_name}")
                    return await server.execute_tool(tool_name, arguments)
                except Exception as retry_error:
                    retry_error_msg = f"重试执行工具失败: {str(retry_error)}"
                    logger.error(f"[MCP] {retry_error_msg}")
                    raise RuntimeError(retry_error_msg)
            else:
                raise RuntimeError(error_msg)

    def list_servers(self) -> List[str]:
        """List all server names."""
        return list(self._servers.keys())
        
    def list_connected_servers(self) -> List[str]:
        """List all connected server names."""
        return [name for name, server in self._servers.items() if server.session is not None]
        
    def is_server_connected(self, server_name: str) -> bool:
        """Check if a server is connected."""
        server = self._servers.get(server_name)
        return server is not None and server.session is not None
        
    async def connect_to_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        """连接到服务器。
        
        Args:
            server_name: 服务器名称
            config: 服务器配置，包含连接类型和相关参数
            
        Returns:
            bool: 连接是否成功
        """
        try:
            # 验证配置中的必要参数
            if "type" not in config:
                config["type"] = "stdio"  # 默认连接类型为 stdio
            
            connection_type = config["type"]
            logger.info(f"尝试连接服务器 {server_name}，连接类型: {connection_type}")
            
            # 验证不同连接类型所需的参数
            if connection_type == "stdio":
                if "command" not in config:
                    raise ValueError("stdio 连接类型必须指定 command 参数")
            elif connection_type == "sse":
                if "url" not in config:
                    raise ValueError("sse 连接类型必须指定 url 参数")
                
                # 对于 SSE 连接，先测试连接是否可用
                success, message = await self.test_sse_connection(config["url"])
                if not success:
                    logger.error(f"SSE 服务器连接测试失败: {message}")
                    return False
            else:
                raise ValueError(f"不支持的连接类型: {connection_type}")
            
            # 如果服务器已存在，先断开连接
            if server_name in self._servers:
                logger.info(f"服务器 {server_name} 已存在，先断开连接")
                await self.disconnect_from_server(server_name)
            
            # 建立新连接
            await self.add_server(server_name, config)
            logger.info(f"服务器 {server_name} 连接成功")
            return True
        except Exception as e:
            logger.error(f"连接服务器失败: {server_name}, 错误: {e}", exc_info=True)
            return False
            
    async def disconnect_from_server(self, server_name: str) -> bool:
        """Disconnect from a server."""
        server = self._servers.get(server_name)
        if server:
            await server.cleanup()
            del self._servers[server_name]
            return True
        return False
        
    async def disconnect_all(self) -> None:
        """Disconnect all servers."""
        for server in self._servers.values():
            await server.cleanup()
        self._servers.clear()

    async def test_sse_connection(self, url: str) -> Tuple[bool, str]:
        """测试 SSE 服务器连接是否可用
        
        对于 SSE 连接，简单返回 True 因为实际连接将在初始化过程中建立
        真正的连接检查将在 _initialize_sse_session 中完成
        
        Args:
            url: SSE 服务器 URL
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        # 确保 URL 格式正确
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        
        logger.info(f"准备连接 SSE 服务器: {url}")
        return True, "准备连接"

# 创建全局客户端管理器实例
client_manager = MCPClientManager()

async def main():
    try:
        # 配置服务器参数
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"],
            env=None
        )
        
        logger.info(f"尝试连接MCP服务器: {server_params.command}")
        
        # 使用上下文管理器确保资源正确释放
        try:
            async with stdio_client(server_params) as (read, write):
                try:
                    async with ClientSession(read, write) as session:
                        try:
                            # 初始化会话
                            await session.initialize()
                            logger.info("会话初始化成功")
                            
                            # 获取工具列表
                            try:
                                tools_response = await session.list_tools()
                                logger.info(f"可用工具: {[tool.name for tool in tools_response.tools]}")
                            except Exception as e:
                                logger.error(f"获取工具列表失败: {e}")
                                if hasattr(e, 'code') and e.code == ErrorCodes.SERVER_ERROR:
                                    logger.error(f"服务器错误: {e.message}")
                                raise
                                
                        except Exception as e:
                            logger.error(f"会话操作失败: {e}")
                            if hasattr(e, 'code'):
                                if e.code == ErrorCodes.REQUEST_FAILED:
                                    logger.error("请求失败，可能是服务器无响应")
                                elif e.code == ErrorCodes.INVALID_REQUEST:
                                    logger.error("无效请求格式")
                                elif e.code == ErrorCodes.METHOD_NOT_FOUND:
                                    logger.error("请求的方法不存在")
                            raise
                            
                except Exception as e:
                    logger.error(f"ClientSession创建失败: {e}")
                    raise
                    
        except Exception as e:
            logger.error(f"连接到服务器失败: {e}")
            if "找不到文件" in str(e) or "No such file or directory" in str(e):
                logger.error(f"服务器程序 '{server_params.command}' 不存在或路径错误")
            elif "Permission denied" in str(e):
                logger.error(f"没有执行服务器程序的权限")
            raise
            
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
    except Exception as e:
        logger.critical(f"发生未处理的异常: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("程序执行完毕")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"主程序异常: {e}")
        sys.exit(1) 