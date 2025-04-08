"""
Chinese (Simplified) language strings for the MCP client backend
"""

MESSAGES = {
    # General messages
    "general": {
        "welcome": "欢迎使用MCP客户端",
        "starting": "正在启动MCP客户端...",
        "stopping": "正在停止MCP客户端...",
        "version": "版本",
    },
    
    # Error messages
    "errors": {
        "general": "发生错误",
        "not_found": "资源未找到",
        "invalid_request": "无效请求",
        "invalid_params": "无效参数",
        "server_error": "服务器错误",
        "connection_error": "连接错误",
        "timeout": "请求超时",
        "auth_failed": "认证失败",
        "permission_denied": "权限被拒绝",
        "config_error": "配置错误",
        "file_not_found": "文件未找到: {path}",
        "invalid_config": "无效的配置: {detail}",
        "missing_required": "缺少必填字段: {field}",
        "invalid_value": "字段 {field} 的值无效: {value}",
        "server_connection_failed": "连接服务器失败: {server}",
        "provider_connection_failed": "连接供应商失败: {provider}",
        "tool_execution_failed": "工具执行失败: {reason}",
        "unsupported_operation": "不支持的操作: {operation}",
        "invalid_token": "无效的令牌",
        "token_expired": "令牌已过期",
    },
    
    # Success messages
    "success": {
        "started": "MCP客户端启动成功",
        "stopped": "MCP客户端停止成功",
        "connected": "已成功连接到 {server}",
        "disconnected": "已成功从 {server} 断开连接",
        "saved": "{item} 保存成功",
        "deleted": "{item} 删除成功",
        "updated": "{item} 更新成功",
        "created": "{item} 创建成功",
        "tool_executed": "工具执行成功",
        "config_loaded": "配置加载成功",
    },
    
    # Server-related messages
    "server": {
        "connecting": "正在连接到服务器: {server}",
        "disconnecting": "正在从服务器断开连接: {server}",
        "testing_connection": "正在测试与服务器的连接: {server}",
        "discovery": "正在发现服务器功能",
        "tools_found": "发现 {count} 个工具",
        "resources_found": "发现 {count} 个资源",
        "prompts_found": "发现 {count} 个提示",
        "no_tools": "没有可用的工具",
        "no_resources": "没有可用的资源",
        "no_prompts": "没有可用的提示",
        "invalid_server_type": "无效的服务器类型: {type}",
        "invalid_server_config": "无效的服务器配置",
    },
    
    # LLM Provider messages
    "provider": {
        "connecting": "正在连接到供应商: {provider}",
        "disconnecting": "正在从供应商断开连接: {provider}",
        "testing_connection": "正在测试与供应商的连接: {provider}",
        "models_found": "发现 {count} 个模型",
        "no_models": "没有可用的模型",
        "invalid_provider_type": "无效的供应商类型: {type}",
        "invalid_provider_config": "无效的供应商配置",
        "model_not_found": "模型未找到: {model}",
    },
    
    # Session related messages
    "session": {
        "creating": "正在创建新会话",
        "loading": "正在加载会话: {session_id}",
        "saving": "正在保存会话: {session_id}",
        "deleting": "正在删除会话: {session_id}",
        "not_found": "会话未找到: {session_id}",
        "invalid_session": "无效的会话数据",
    },
    
    # Tool execution messages
    "tools": {
        "executing": "正在执行工具: {tool}",
        "with_args": "参数: {args}",
        "execution_result": "工具执行结果",
        "no_result": "工具执行未返回结果",
        "invalid_tool": "无效的工具: {tool}",
        "tool_not_found": "工具未找到: {tool}",
        "invalid_args": "工具 {tool} 的参数无效",
    },
} 