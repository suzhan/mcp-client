"""
English (US) language strings for the MCP client backend
"""

MESSAGES = {
    # General messages
    "general": {
        "welcome": "Welcome to MCP Client",
        "starting": "Starting MCP Client...",
        "stopping": "Stopping MCP Client...",
        "version": "Version",
    },
    
    # Error messages
    "errors": {
        "general": "An error occurred",
        "not_found": "Resource not found",
        "invalid_request": "Invalid request",
        "invalid_params": "Invalid parameters",
        "server_error": "Server error",
        "connection_error": "Connection error",
        "timeout": "Request timed out",
        "auth_failed": "Authentication failed",
        "permission_denied": "Permission denied",
        "config_error": "Configuration error",
        "file_not_found": "File not found: {path}",
        "invalid_config": "Invalid configuration: {detail}",
        "missing_required": "Missing required field: {field}",
        "invalid_value": "Invalid value for {field}: {value}",
        "server_connection_failed": "Failed to connect to server: {server}",
        "provider_connection_failed": "Failed to connect to provider: {provider}",
        "tool_execution_failed": "Tool execution failed: {reason}",
        "unsupported_operation": "Unsupported operation: {operation}",
        "invalid_token": "Invalid token",
        "token_expired": "Token expired",
    },
    
    # Success messages
    "success": {
        "started": "MCP Client started successfully",
        "stopped": "MCP Client stopped successfully",
        "connected": "Connected to {server} successfully",
        "disconnected": "Disconnected from {server} successfully",
        "saved": "{item} saved successfully",
        "deleted": "{item} deleted successfully",
        "updated": "{item} updated successfully",
        "created": "{item} created successfully",
        "tool_executed": "Tool executed successfully",
        "config_loaded": "Configuration loaded successfully",
    },
    
    # Server-related messages
    "server": {
        "connecting": "Connecting to server: {server}",
        "disconnecting": "Disconnecting from server: {server}",
        "testing_connection": "Testing connection to server: {server}",
        "discovery": "Discovering server capabilities",
        "tools_found": "Found {count} tools",
        "resources_found": "Found {count} resources",
        "prompts_found": "Found {count} prompts",
        "no_tools": "No tools available",
        "no_resources": "No resources available",
        "no_prompts": "No prompts available",
        "invalid_server_type": "Invalid server type: {type}",
        "invalid_server_config": "Invalid server configuration",
    },
    
    # LLM Provider messages
    "provider": {
        "connecting": "Connecting to provider: {provider}",
        "disconnecting": "Disconnecting from provider: {provider}",
        "testing_connection": "Testing connection to provider: {provider}",
        "models_found": "Found {count} models",
        "no_models": "No models available",
        "invalid_provider_type": "Invalid provider type: {type}",
        "invalid_provider_config": "Invalid provider configuration",
        "model_not_found": "Model not found: {model}",
    },
    
    # Session related messages
    "session": {
        "creating": "Creating new session",
        "loading": "Loading session: {session_id}",
        "saving": "Saving session: {session_id}",
        "deleting": "Deleting session: {session_id}",
        "not_found": "Session not found: {session_id}",
        "invalid_session": "Invalid session data",
    },
    
    # Tool execution messages
    "tools": {
        "executing": "Executing tool: {tool}",
        "with_args": "with arguments: {args}",
        "execution_result": "Tool execution result",
        "no_result": "Tool execution returned no result",
        "invalid_tool": "Invalid tool: {tool}",
        "tool_not_found": "Tool not found: {tool}",
        "invalid_args": "Invalid arguments for tool: {tool}",
    },
} 