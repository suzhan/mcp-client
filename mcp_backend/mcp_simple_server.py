#!/usr/bin/env python3
"""
简单的MCP服务器，支持基本的MCP方法
特别提供resources/list和prompts/list的支持，即使没有资源或提示也返回空列表
"""

import asyncio
import logging
import sys
from mcp import types
from mcp.server import FastMCP
from mcp.server.stdio import stdio_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

logger = logging.getLogger("mcp_simple_server")

# 创建MCP服务器实例
server = FastMCP({
    "name": "Simple MCP Server",
    "version": "1.0.0"
})

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

async def main():
    """主函数"""
    logger.info("启动MCP简单服务器...")
    
    try:
        # 使用stdio_server作为传输层
        async with stdio_server() as (read_stream, write_stream):
            # 连接服务器到传输层
            await server.connect_reader_writer(read_stream, write_stream)
            logger.info("服务器已连接到传输层")
            
            # 保持服务器运行
            while True:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器出错: {e}", exc_info=True)
    finally:
        # 确保关闭服务器
        try:
            await server.close()
            logger.info("服务器已关闭")
        except Exception as close_error:
            logger.error(f"关闭服务器时出错: {close_error}")

if __name__ == "__main__":
    asyncio.run(main()) 