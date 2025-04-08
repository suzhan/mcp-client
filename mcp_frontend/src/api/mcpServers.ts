import jsonrpc from './jsonrpc';

export interface MCPServer {
  id: string;
  name: string;
  type: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  url?: string;
  status?: string;
  error?: string;
}

export interface MCPServerStatus {
  id: string;
  name: string;
  type: string;
  status: string;
  tools_count: number;
  resources_count: number;
  tools_list: Array<{name: string; description: string}>;
  resources_list: Array<{name: string; uri: string}>;
  operations: { name: string; label: string }[];
}

export const mcpServerApi = {
  /**
   * 获取所有MCP服务器
   */
  async getAll(): Promise<MCPServer[]> {
    try {
      return await jsonrpc.getMcpServers();
    } catch (error) {
      console.error('获取MCP服务器列表失败:', error);
      return [];
    }
  },
  
  /**
   * 获取所有MCP服务器状态
   */
  async getStatus(): Promise<MCPServerStatus[]> {
    try {
      const result = await jsonrpc.call('mcp.get_servers_status');
      return result.servers || [];
    } catch (error) {
      console.error('获取MCP服务器状态失败:', error);
      return [];
    }
  },
  
  /**
   * 获取单个MCP服务器
   */
  async getById(serverId: string): Promise<MCPServer | null> {
    try {
      const servers = await this.getAll();
      return servers.find(server => server.id === serverId) || null;
    } catch (error) {
      console.error(`获取MCP服务器 ${serverId} 失败:`, error);
      return null;
    }
  },
  
  /**
   * 创建MCP服务器
   */
  async create(serverData: Omit<MCPServer, 'id'>): Promise<MCPServer> {
    try {
      console.log('API创建服务器，发送数据:', serverData);
      
      // 确保不包含空 id
      const cleanData = {...serverData};
      if ('id' in cleanData && !cleanData.id) {
        delete cleanData.id;
      }
      
      return await jsonrpc.call('mcp.create_server', cleanData);
    } catch (error) {
      console.error('创建MCP服务器失败:', error);
      throw error;
    }
  },
  
  /**
   * 更新MCP服务器
   */
  async update(serverId: string, serverData: Partial<MCPServer>): Promise<MCPServer> {
    try {
      return await jsonrpc.call('mcp.update_server', { 
        server_id: serverId,
        ...serverData
      });
    } catch (error) {
      console.error(`更新MCP服务器 ${serverId} 失败:`, error);
      throw error;
    }
  },
  
  /**
   * 删除MCP服务器
   */
  async delete(serverId: string): Promise<boolean> {
    try {
      return await jsonrpc.call('mcp.delete_server', { server_id: serverId });
    } catch (error) {
      console.error(`删除MCP服务器 ${serverId} 失败:`, error);
      throw error;
    }
  },
  
  /**
   * 测试MCP服务器连接
   */
  async testConnection(serverId: string): Promise<{success: boolean; message?: string}> {
    try {
      return await jsonrpc.call('mcp.test_server_connection', { server_id: serverId });
    } catch (error) {
      console.error(`测试MCP服务器 ${serverId} 连接失败:`, error);
      return { success: false, message: String(error) };
    }
  },
  
  /**
   * 连接到MCP服务器
   */
  async connect(serverId: string): Promise<{success: boolean; message?: string}> {
    try {
      return await jsonrpc.connectToServer(serverId);
    } catch (error) {
      console.error(`连接到MCP服务器 ${serverId} 失败:`, error);
      return { success: false, message: String(error) };
    }
  },
  
  /**
   * 断开MCP服务器连接
   */
  async disconnect(serverId: string): Promise<boolean> {
    try {
      return await jsonrpc.disconnectFromServer(serverId);
    } catch (error) {
      console.error(`断开MCP服务器 ${serverId} 连接失败:`, error);
      throw error;
    }
  },
  
  /**
   * 获取已连接的MCP服务器列表
   */
  async getConnected(): Promise<string[]> {
    try {
      const result = await jsonrpc.getConnectedServers();
      return result.servers || [];
    } catch (error) {
      console.error('获取已连接的MCP服务器列表失败:', error);
      return [];
    }
  },
  
  /**
   * 设置服务器的采样回调
   */
  async setupSamplingCallback(serverId: string, providerName: string): Promise<{success: boolean; message?: string}> {
    try {
      return await jsonrpc.setupSamplingCallback(serverId, providerName);
    } catch (error) {
      console.error(`设置服务器 ${serverId} 的采样回调失败:`, error);
      return { success: false, message: String(error) };
    }
  },
}; 