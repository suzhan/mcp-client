import jsonrpc from './jsonrpc';

export interface Message {
  id: string;
  role: string;
  content: any;
  timestamp: number;
}

export interface Session {
  id: string;
  title: string;
  messages: Message[];
  created_at: number;
  updated_at: number;
  metadata: Record<string, any>;
  llm_provider?: string;
  llm_model?: string;
  mcp_server_id?: string;
  message_count?: number;
}

export interface SessionSummary {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  llm_provider?: string;
  llm_model?: string;
  mcp_server_id?: string;
}

export const sessionApi = {
  /**
   * 获取所有会话的概要信息
   */
  async getAll(): Promise<SessionSummary[]> {
    try {
      const response = await jsonrpc.getAllSessions();
      return response?.sessions || [];
    } catch (error) {
      console.error('获取会话列表失败:', error);
      return [];
    }
  },
  
  /**
   * 获取会话详情
   */
  async getById(sessionId: string): Promise<Session | null> {
    try {
      return await jsonrpc.getSession(sessionId);
    } catch (error) {
      console.error(`获取会话 ${sessionId} 失败:`, error);
      return null;
    }
  },
  
  /**
   * 创建新会话
   */
  async create(title: string = '新会话', llmProvider?: string, llmModel?: string, mcpServerId?: string): Promise<Session> {
    try {
      return await jsonrpc.createSession(title, llmProvider, llmModel, mcpServerId);
    } catch (error) {
      console.error('创建会话失败:', error);
      throw error;
    }
  },
  
  /**
   * 更新会话标题
   */
  async updateTitle(sessionId: string, title: string): Promise<boolean> {
    try {
      const result = await jsonrpc.updateSessionTitle(sessionId, title);
      return result.success;
    } catch (error) {
      console.error(`更新会话 ${sessionId} 标题失败:`, error);
      throw error;
    }
  },
  
  /**
   * 更新会话的LLM信息
   */
  async updateLLM(sessionId: string, provider: string, model: string): Promise<boolean> {
    try {
      const result = await jsonrpc.updateSessionLLM(sessionId, provider, model);
      return result.success;
    } catch (error) {
      console.error(`更新会话 ${sessionId} LLM信息失败:`, error);
      throw error;
    }
  },
  
  /**
   * 更新会话的MCP服务器
   */
  async updateMCPServer(sessionId: string, serverId: string): Promise<boolean> {
    try {
      const result = await jsonrpc.updateSessionMCPServer(sessionId, serverId);
      return result.success;
    } catch (error) {
      console.error(`更新会话 ${sessionId} MCP服务器失败:`, error);
      throw error;
    }
  },
  
  /**
   * 删除会话
   */
  async delete(sessionId: string): Promise<boolean> {
    try {
      const result = await jsonrpc.deleteSession(sessionId);
      return result.success;
    } catch (error) {
      console.error(`删除会话 ${sessionId} 失败:`, error);
      throw error;
    }
  },
  
  /**
   * 添加消息到会话
   */
  async addMessage(sessionId: string, role: string, content: any): Promise<Message> {
    try {
      return await jsonrpc.addMessage(sessionId, role, content);
    } catch (error) {
      console.error(`向会话 ${sessionId} 添加消息失败:`, error);
      throw error;
    }
  },
  
  /**
   * 获取会话消息列表
   */
  async getMessages(sessionId: string): Promise<Message[]> {
    try {
      return await jsonrpc.getMessages(sessionId);
    } catch (error) {
      console.error(`获取会话 ${sessionId} 消息列表失败:`, error);
      return [];
    }
  },
  
  /**
   * 清空会话消息
   */
  async clearMessages(sessionId: string): Promise<boolean> {
    try {
      const result = await jsonrpc.clearMessages(sessionId);
      return result.success;
    } catch (error) {
      console.error(`清空会话 ${sessionId} 消息失败:`, error);
      throw error;
    }
  },
  
  /**
   * 与LLM和MCP工具聊天
   */
  async chatWithTools(
    sessionId: string, 
    userMessage: string,
    providerName: string,
    model: string,
    serverId?: string
  ): Promise<any> {
    try {
      return await jsonrpc.chatWithTools(sessionId, userMessage, providerName, model, serverId);
    } catch (error) {
      console.error(`会话 ${sessionId} 聊天失败:`, error);
      throw error;
    }
  }
}; 