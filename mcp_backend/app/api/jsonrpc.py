from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
import traceback
import json
from loguru import logger
from pydantic import BaseModel, Field
from fastapi import APIRouter, Response, Request
from app.i18n import get_message

# 创建一个路由器
router = APIRouter()

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0请求对象"""
    jsonrpc: str = Field("2.0", description="JSON-RPC版本")
    id: Optional[Union[str, int]] = Field(None, description="请求ID")
    method: str = Field(..., description="方法名")
    params: Optional[Dict[str, Any]] = Field(None, description="参数")

class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0响应对象"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class JSONRPCError(Exception):
    """JSON-RPC错误类"""
    
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(self.message)

class InvalidRequest(JSONRPCError):
    """Invalid Request 错误类"""
    
    def __init__(self, message: str = None):
        message = message or get_message("errors.invalid_request")
        super().__init__(-32600, message)

class MethodNotFound(JSONRPCError):
    """Method Not Found 错误类"""
    
    def __init__(self, method: str = None):
        message = get_message("errors.not_found") if method is None else f"方法未找到: {method}"
        super().__init__(-32601, message)

class InvalidParams(JSONRPCError):
    """Invalid Params 错误类"""
    
    def __init__(self, message: str = None):
        message = message or get_message("errors.invalid_params")
        super().__init__(-32602, message)

class InternalError(JSONRPCError):
    """Internal Error 错误类"""
    
    def __init__(self, message: str = None):
        message = message or get_message("errors.server_error")
        super().__init__(-32603, message)

class ServerError(JSONRPCError):
    """Server Error 错误类"""
    
    def __init__(self, message: str = None):
        message = message or get_message("errors.server_error")
        super().__init__(-32000, message)

class JSONRPC:
    """JSON-RPC处理类"""
    
    def __init__(self):
        self.methods: Dict[str, Callable[..., Awaitable[Any]]] = {}
    
    def register_method(self, name: str, method: Callable[..., Awaitable[Any]]) -> None:
        """注册一个方法到JSON-RPC处理器"""
        self.methods[name] = method
    
    def method(self, name: str):
        """装饰器，用于注册方法"""
        def decorator(func: Callable[..., Awaitable[Any]]):
            self.register_method(name, func)
            return func
        return decorator
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理JSON-RPC请求"""
        # 检查请求是否为批量请求
        if isinstance(request_data, list):
            return await self._handle_batch_request(request_data)
        
        try:
            # 验证请求
            if not isinstance(request_data, dict):
                raise InvalidRequest("请求必须是一个对象")
            
            # 检查必要字段
            if "jsonrpc" not in request_data:
                raise InvalidRequest("缺少 jsonrpc 字段")
            
            if request_data["jsonrpc"] != "2.0":
                raise InvalidRequest("jsonrpc 字段必须为 2.0")
            
            if "method" not in request_data:
                raise InvalidRequest("缺少 method 字段")
            
            method_name = request_data["method"]
            params = request_data.get("params", {})
            id = request_data.get("id", None)
            
            # 通知没有ID，不需要回复
            if id is None:
                await self._execute_method(method_name, params)
                return None
            
            # 处理方法调用
            result = await self._execute_method(method_name, params)
            
            # 构建响应
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": id
            }
        except JSONRPCError as e:
            # 只对有ID的请求返回错误
            if "id" in request_data:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": e.code,
                        "message": e.message
                    },
                    "id": request_data.get("id", None)
                }
                
                # 如果有额外数据，添加到错误响应中
                if e.data is not None:
                    error_response["error"]["data"] = e.data
                
                return error_response
            else:
                # 通知出错，不返回任何内容
                return None
        except Exception as e:
            # 未捕获的异常
            logger.error(f"处理JSON-RPC请求时发生未捕获的异常: {e}", exc_info=True)
            
            if "id" in request_data:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": get_message("errors.server_error")
                    },
                    "id": request_data.get("id", None)
                }
            else:
                return None
    
    async def _handle_batch_request(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理批量JSON-RPC请求"""
        if not requests:
            raise InvalidRequest("批量请求不能为空")
        
        responses = []
        for request in requests:
            response = await self.handle_request(request)
            if response is not None:  # 只添加非通知的响应
                responses.append(response)
        
        return responses if responses else None
    
    async def _execute_method(self, method_name: str, params: Any) -> Any:
        """执行方法"""
        if method_name not in self.methods:
            raise MethodNotFound(method_name)
        
        method = self.methods[method_name]
        
        # 检查参数类型，适配不同的调用方式
        if isinstance(params, dict):
            try:
                return await method(**params)
            except TypeError as e:
                logger.error(f"参数类型错误: {e}", exc_info=True)
                raise InvalidParams(f"参数类型错误: {str(e)}")
        elif isinstance(params, list):
            try:
                return await method(*params)
            except TypeError as e:
                logger.error(f"参数类型错误: {e}", exc_info=True)
                raise InvalidParams(f"参数类型错误: {str(e)}")
        else:
            try:
                return await method()
            except TypeError as e:
                logger.error(f"参数类型错误: {e}", exc_info=True)
                raise InvalidParams(f"参数类型错误: {str(e)}")

# 创建一个全局JSON-RPC实例
jsonrpc = JSONRPC() 