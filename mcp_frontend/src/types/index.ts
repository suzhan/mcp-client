// MCP服务器相关类型
export interface MCPServer {
  id: string;
  name: string;
  type: string; // "stdio" | "sse"
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
}

// MCP工具类型
export interface MCPTool {
  name: string;
  description?: string;
  inputSchema: any;
}

// MCP资源类型
export interface MCPResource {
  name: string;
  uri: string;
  mimeType?: string;
}

// MCP资源模板类型
export interface MCPResourceTemplate {
  name: string;
  uriTemplate: string;
}

// MCP提示模板类型
export interface MCPPrompt {
  name: string;
  description?: string;
  arguments?: MCPPromptArgument[];
}

export interface MCPPromptArgument {
  name: string;
  description?: string;
  required?: boolean;
}

// LLM供应商类型
export interface LLMProvider {
  name: string;
  api_key: string;
  base_url?: string;
  models: string[];
}

// 消息类型
export interface Message {
  id: string;
  role: string; // 'user' | 'assistant' | 'system' | 'tool'
  content: any;
  timestamp: number;
}

// 会话类型
export interface Session {
  id: string;
  title: string;
  messages: Message[];
  created_at: number;
  updated_at: number;
  metadata?: Record<string, any>;
}

// 会话摘要类型（用于列表展示）
export interface SessionSummary {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

// 工具调用类型
export interface ToolCall {
  id: string;
  name: string;
  arguments: string | Record<string, any>;
}

// 工具调用结果类型
export interface ToolCallResult {
  tool_call_id: string;
  content: string;
}

// LLM响应类型
export interface LLMResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: LLMChoice[];
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface LLMChoice {
  index: number;
  message: {
    role: string;
    content: string | null;
    tool_calls?: ToolCall[];
  };
  finish_reason: string;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
} 