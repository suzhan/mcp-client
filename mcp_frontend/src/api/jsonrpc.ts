import axios from 'axios';

interface JSONRPCRequest {
  jsonrpc: string;
  method: string;
  params?: any;
  id: number | string;
}

interface JSONRPCResponse {
  jsonrpc: string;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
  id: number | string | null;
}

export class JSONRPCClient {
  private axios: any;
  private requestId = 1;

  constructor(endpoint: string = '/api/v1/jsonrpc') {
    this.axios = axios.create({
      baseURL: '',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 30000
    });
    this.endpoint = endpoint;
  }

  private endpoint: string;

  public async request<T = any>(method: string, params?: any): Promise<T> {
    // 对参数进行深拷贝以去除循环引用
    const safeParams = params ? JSON.parse(JSON.stringify(params)) : undefined;
    
    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      method,
      params: safeParams,
      id: this.requestId++
    };

    try {
      const response = await this.axios.post(this.endpoint, request);

      if (response.data.error) {
        throw new Error(`JSONRPC Error [${response.data.error.code}]: ${response.data.error.message}`);
      }

      return response.data.result as T;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(`Network Error: ${error.message}`);
      }
      throw error;
    }
  }

  // 兼容旧的调用方式
  public call<T = any>(method: string, params?: any): Promise<T> {
    return this.request<T>(method, params);
  }

  // MCP服务器相关方法
  public async getMcpServers() {
    return this.request('mcp.get_servers');
  }

  public async testServerConnection(serverId: string) {
    return this.request('mcp.test_server_connection', { server_id: serverId });
  }

  public async connectToServer(serverId: string) {
    return this.request('mcp.connect_server', { server_id: serverId });
  }

  public async disconnectFromServer(serverId: string) {
    return this.request('mcp.disconnect_server', { server_id: serverId });
  }

  public async getConnectedServers() {
    return this.request('mcp.get_connected_servers');
  }

  public async listTools(serverId: string) {
    return this.request('mcp.list_tools', { server_id: serverId });
  }

  public async callTool(serverId: string, toolName: string, arguments_: any) {
    return this.request('mcp.call_tool', { 
      server_id: serverId, 
      tool_name: toolName, 
      arguments: arguments_ 
    });
  }

  public async listResources(serverId: string) {
    return this.request('mcp.list_resources', { server_id: serverId });
  }

  public async readResource(serverId: string, resourceUri: string) {
    return this.request('mcp.read_resource', { 
      server_id: serverId, 
      resource_uri: resourceUri 
    });
  }

  public async listPrompts(serverId: string) {
    return this.request('mcp.list_prompts', { server_id: serverId });
  }

  public async getPrompt(serverId: string, promptName: string, arguments_: any) {
    return this.request('mcp.get_prompt', { 
      server_id: serverId, 
      prompt_name: promptName, 
      arguments: arguments_ 
    });
  }

  // LLM供应商相关方法
  public async getLlmProviders() {
    return this.request('llm.get_providers');
  }

  // 获取LLM供应商支持的模型列表
  public async getLlmProviderModels(providerName: string) {
    return this.request('llm.get_provider_models', { provider_name: providerName });
  }

  public async sendToLlm(providerName: string, messages: any[], model?: string) {
    return this.request('llm.send_message', { 
      provider_name: providerName, 
      messages: messages,
      model: model
    });
  }

  // 会话管理相关方法
  public async createSession(title: string = '新会话', llmProvider?: string, llmModel?: string, mcpServerId?: string) {
    return this.request('sessions.createSession', { 
      title: title,
      llm_provider: llmProvider,
      llm_model: llmModel,
      mcp_server_id: mcpServerId
    });
  }

  public async getAllSessions() {
    return this.request('sessions.listSessions');
  }

  public async getSession(sessionId: string) {
    return this.request('sessions.getSession', { id: sessionId });
  }

  public async updateSessionTitle(sessionId: string, title: string) {
    console.log(`调用 updateSessionTitle: sessionId=${sessionId}, title="${title}"`);
    
    // 确保参数是字符串
    const safeId = String(sessionId);
    const safeTitle = String(title);
    
    const params = { id: safeId, name: safeTitle };
    console.log('发送参数到 sessions.updateSession:', JSON.stringify(params, null, 2));
    
    try {
      const result = await this.request('sessions.updateSession', params);
      console.log('sessions.updateSession 响应:', result);
      return result;
    } catch (error) {
      console.error('调用 sessions.updateSession 失败:', error);
      throw error;
    }
  }

  public async updateSessionLLM(sessionId: string, provider: string, model: string) {
    return this.request('sessions.updateSession', { 
      id: sessionId, 
      llm_provider: provider, 
      llm_model: model 
    });
  }

  public async updateSessionMCPServer(sessionId: string, serverId: string) {
    return this.request('sessions.updateSession', { 
      id: sessionId, 
      mcp_server_id: serverId 
    });
  }

  public async deleteSession(sessionId: string) {
    return this.request('sessions.deleteSession', { id: sessionId });
  }

  public async addMessage(sessionId: string, role: string, content: any) {
    return this.request('sessions.addMessage', { session_id: sessionId, role, content });
  }

  public async getMessages(sessionId: string) {
    return this.request('sessions.getMessages', { session_id: sessionId });
  }

  public async clearMessages(sessionId: string) {
    return this.request('sessions.clearMessages', { session_id: sessionId });
  }

  // 复合操作方法
  public async chatWithTools(
    sessionId: string, 
    message: string, 
    provider: string,
    model: string,
    serverId?: string
  ): Promise<any> {
    console.log('chatWithTools参数:');
    console.log(`- sessionId: '${sessionId}'`);
    console.log(`- message长度: ${message.length}`);
    console.log(`- provider: '${provider}'`);
    console.log(`- model: '${model}'`);
    console.log(`- serverId: ${serverId === undefined ? 'undefined' : `'${serverId}'`}`);
    
    // 构建参数对象，匹配后端chat.with_tools/chat.chat_with_tools方法的参数
    const params: any = {
      session_id: sessionId,
      user_message: message,  // 注意：后端使用user_message，不是message
      provider_name: provider, // 注意：后端使用provider_name，不是provider
      model: model
    };
    
    // 只有当serverId是有效的非空字符串时，才包含它
    if (serverId && typeof serverId === 'string' && serverId.trim() !== '') {
      params.server_id = serverId;
    } else if (serverId === undefined || serverId === '') {
      console.log('未指定serverId，不使用MCP工具');
    } else {
      console.warn('警告: serverId参数无效:', serverId);
    }
    
    console.log('chatWithTools最终参数:', params);
    // 使用正确的方法名称：chat.with_tools
    return this.request('chat.with_tools', params);
  }

  // 添加生成会话标题的方法
  public async generateSessionTitle(
    sessionId: string,
    messages: any[],
    provider: string,
    model: string
  ): Promise<string> {
    console.log(`生成会话标题，sessionId: ${sessionId}`);
    
    try {
      const result = await this.request('sessions.generate_title', {
        session_id: sessionId,
        messages: messages,
        provider_name: provider,
        model: model
      });
      
      if (result && result.title) {
        return result.title;
      }
      return '新会话'; // 默认标题
    } catch (error) {
      console.error('生成会话标题失败:', error);
      return '新会话'; // 出错时的默认标题
    }
  }

  public async setupSamplingCallback(serverId: string, providerName: string) {
    return this.request('mcp.setup_sampling_callback', { 
      server_id: serverId, 
      provider_name: providerName 
    });
  }
}

// 创建并导出默认的JSON-RPC客户端实例
const jsonrpc = new JSONRPCClient();
export default jsonrpc; 