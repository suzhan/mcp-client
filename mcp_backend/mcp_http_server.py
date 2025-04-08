#!/usr/bin/env python3
"""
HTTP版的MCP服务器，支持基本的MCP方法和SSE连接
特别提供resources/list和prompts/list的支持，即使没有资源或提示也返回空列表
"""

import asyncio
import logging
import sys
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from mcp import types
from mcp.server import FastMCP
from mcp.server.sse import SSEServerTransport

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

logger = logging.getLogger("mcp_http_server")

# 创建FastAPI应用
app = FastAPI(title="MCP HTTP Server")

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建MCP服务器实例
server = FastMCP({
    "name": "MCP HTTP Server",
    "version": "1.0.0"
})

# 保存活跃连接
active_connections = {}

# 工具列表，空的或添加你想要提供的工具
@server.tool(
    'echo',
    {'message': str},  # 简单的参数定义
    description='Echo back the input message'
)
async def echo(message: str):
    """简单的回显工具"""
    logger.info(f"执行echo工具，参数: {message}")
    return {
        "content": [{"type": "text", "text": f"Echo: {message}"}]
    }

# 实现一个文件创建工具，这在聊天应用中会很有用
@server.tool(
    'write_file',
    {
        'path': str,  # 文件路径
        'content': str  # 文件内容
    },
    description='创建或写入文件'
)
async def write_file(path: str, content: str):
    """创建或写入文件工具"""
    logger.info(f"执行write_file工具，路径: {path}")
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {
            "content": [{"type": "text", "text": f"成功写入文件: {path}"}]
        }
    except Exception as e:
        logger.error(f"写入文件失败: {e}")
        return {
            "content": [{"type": "text", "text": f"写入文件失败: {str(e)}"}],
            "isError": True
        }

# 添加一个目录列表工具
@server.tool(
    'list_allowed_directories',
    {},  # 无参数
    description='列出允许访问的目录'
)
async def list_allowed_directories():
    """列出允许访问的目录"""
    logger.info("执行list_allowed_directories工具")
    # 这里可以写入实际的目录列表
    allowed_dirs = ["/Users/suzhan/Downloads"]
    return {
        "content": [{"type": "text", "text": f"Allowed directories:\n{allowed_dirs}"}]
    }

# 资源列表，实现空的resource list，防止Method not found错误
@server.request_handler(types.ListResourcesRequest)
async def list_resources(request):
    """返回空的资源列表，而不是Method not found错误"""
    logger.info("处理resources/list请求")
    return {
        "resources": [],
        "resourceTemplates": []
    }

# 提示列表，实现空的prompt list，防止Method not found错误
@server.request_handler(types.ListPromptsRequest)
async def list_prompts(request):
    """返回空的提示列表，而不是Method not found错误"""
    logger.info("处理prompts/list请求")
    return {
        "prompts": []
    }

# SSE端点
@app.get("/sse")
async def sse_endpoint(request: Request, response: Response):
    """处理SSE连接"""
    client_id = str(id(request))
    logger.info(f"收到SSE连接请求: {client_id}")
    
    # 设置SSE响应头
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    
    # 创建SSE传输
    transport = SSEServerTransport("/messages", response)
    
    try:
        # 保存连接
        active_connections[client_id] = transport
        
        # 连接服务器到传输层
        await server.connect(transport)
        logger.info(f"客户端 {client_id} 已连接")
        
        # 等待连接关闭
        await request.is_disconnected()
        logger.info(f"客户端 {client_id} 已断开连接")
    except Exception as e:
        logger.error(f"SSE连接出错: {e}", exc_info=True)
    finally:
        # 清理连接
        if client_id in active_connections:
            del active_connections[client_id]
        logger.info(f"已清理客户端 {client_id} 的连接")
    
    return response

# 消息端点
@app.post("/messages")
async def messages_endpoint(request: Request):
    """处理客户端发送的消息"""
    client_id = request.headers.get("X-Client-ID", str(id(request)))
    
    if client_id not in active_connections:
        logger.warning(f"客户端 {client_id} 的连接不存在")
        return {"error": "Connection not found"}
    
    transport = active_connections[client_id]
    
    try:
        # 获取请求体
        body = await request.json()
        logger.info(f"收到客户端 {client_id} 的消息: {body}")
        
        # 处理消息
        await transport.handle_post_message(request, Response())
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"处理客户端 {client_id} 的消息时出错: {e}", exc_info=True)
        return {"error": str(e)}

# 主页
@app.get("/")
async def home():
    """主页，返回服务器信息"""
    return {
        "name": "MCP HTTP Server", 
        "version": "1.0.0",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages"
        }
    }

# 健康检查
@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "connections": len(active_connections)}

if __name__ == "__main__":
    logger.info("启动MCP HTTP服务器...")
    # 运行FastAPI应用
    uvicorn.run(app, host="0.0.0.0", port=8765) 