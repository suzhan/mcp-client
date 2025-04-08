import json
import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
from loguru import logger

from app.core.config import settings
from app.api.endpoints import router, startup_event
from app.services.llm_service import llm_service_manager
from app.i18n import get_message, load_language_from_config, get_language
from app.api.i18n import router as i18n_router

# 配置日志
logger.remove()  # 移除默认处理程序
logger.add(sys.stdout, level="INFO")  # 添加标准输出处理程序
logger.add("mcp_client.log", rotation="10 MB", level="INFO", 
          format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"/api/v1/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取项目根目录（mcp_backend的父目录）
project_root = Path(os.getcwd()).parent if os.getcwd().endswith('mcp_backend') else Path(os.getcwd())
docs_path = project_root / "docs"

# 如果docs目录存在，挂载静态文件服务
if docs_path.exists():
    app.mount("/docs", StaticFiles(directory=str(docs_path)), name="docs")

# 自定义HTTP异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = get_message(f"errors.{exc.status_code}", detail=str(exc.detail)) if exc.status_code in [400, 401, 403, 404, 500] else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": message}
    )

# 自定义验证错误处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        field = error.get('loc', [''])[1] if len(error.get('loc', [])) > 1 else ''
        message = get_message("errors.invalid_value", field=field, value=error.get('msg', ''))
        error_details.append(message)
    
    return JSONResponse(
        status_code=400,
        content={"detail": error_details}
    )

# 注册路由
app.include_router(router, prefix="/api/v1")
app.include_router(i18n_router, prefix="/api/v1")

# 应用启动事件
@app.on_event("startup")
async def startup():
    try:
        logger.info("="*50)
        
        # 加载语言配置
        load_language_from_config()
        current_lang = get_language()
        logger.info(get_message("general.starting"))
        logger.info(f"当前语言: {current_lang}")
        
        logger.info(f"当前工作目录: {os.getcwd()}")
        logger.info(f"Python路径: {sys.path}")
        logger.info(f"应用名称: {settings.APP_NAME}")
        
        # 获取项目根目录（mcp_backend的父目录）
        project_root = Path(os.getcwd()).parent if os.getcwd().endswith('mcp_backend') else Path(os.getcwd())
        logger.info(f"项目根目录: {project_root}")
        
        # 检查配置文件
        logger.info("检查配置文件...")
        config_dir = project_root / ".config"
        if not config_dir.exists():
            logger.error(get_message("errors.file_not_found", path=str(config_dir)))
            sys.exit(1)
            
        llm_config = config_dir / "llm.json"
        if not llm_config.exists():
            logger.error(get_message("errors.file_not_found", path=str(llm_config)))
            sys.exit(1)
        logger.info(f"找到LLM配置文件: {llm_config}")
        
        servers_config = config_dir / "servers.json"
        if not servers_config.exists():
            logger.error(get_message("errors.file_not_found", path=str(servers_config)))
            sys.exit(1)
        logger.info(f"找到服务器配置文件: {servers_config}")
        
        # 加载LLM供应商
        logger.info("正在加载LLM供应商...")
        for provider in settings.llm_providers:
            llm_service_manager.add_provider(provider)
            logger.info(f"已加载LLM供应商: {provider.name}")
            logger.info(f"可用模型: {provider.models}")
        
        # 注册JSON-RPC方法
        logger.info("正在注册JSON-RPC方法...")
        await startup_event()
        
        logger.info(get_message("success.started"))
        logger.info("="*50)
    except Exception as e:
        logger.error(f"启动过程中出错: {str(e)}", exc_info=True)
        sys.exit(1)

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown():
    from app.services.mcp_client import client_manager
    
    try:
        logger.info("="*50)
        logger.info(get_message("general.stopping"))
        
        # 断开所有MCP服务器连接
        logger.info("正在断开所有MCP服务器连接...")
        connected_servers = client_manager.list_connected_servers()
        logger.info(f"当前连接的服务器: {connected_servers}")
        await client_manager.disconnect_all()
        
        logger.info(get_message("success.stopped"))
        logger.info("="*50)
    except Exception as e:
        logger.error(f"关闭过程中出错: {str(e)}", exc_info=True)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "description": get_message("general.welcome"),
        "status": "running",
        "language": get_language()
    }

@app.get("/api-docs", response_class=HTMLResponse)
async def get_api_docs():
    """返回JSON-RPC API文档页面"""
    return FileResponse(str(docs_path / "rpc_client.html"))

@app.get("/jsonrpc-docs", response_class=HTMLResponse)
async def get_jsonrpc_docs():
    """返回JSON-RPC API markdown文档"""
    return FileResponse(str(docs_path / "jsonrpc_api.md"))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 