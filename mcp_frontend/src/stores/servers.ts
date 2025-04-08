import { defineStore } from 'pinia';
import { ref } from 'vue';
import jsonrpc from '../api/jsonrpc';

export interface ServerTool {
  name: string;
  description?: string;
  inputSchema?: any;
  outputSchema?: any;
}

export interface MCPServer {
  id: string;
  name: string;
  type: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  status?: 'online' | 'offline' | 'error' | 'connecting';
  error?: string;
  tools?: ServerTool[];
  resources_count?: number;
}

export const useServerStore = defineStore('servers', () => {
  const servers = ref<MCPServer[]>([]);
  const connectedServers = ref<MCPServer[]>([]);
  const loading = ref(false);
  const error = ref('');
  const lastCheckedAt = ref<Date | null>(null);
  const checkInterval = ref<number | null>(null);

  // 获取所有MCP服务器配置
  const fetchServers = async () => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('mcp.get_servers');
      servers.value = Array.isArray(response) ? response : [];
      return servers.value;
    } catch (e) {
      error.value = '加载服务器列表失败';
      console.error('加载服务器列表失败', e);
      return [];
    } finally {
      loading.value = false;
    }
  };

  // 获取所有已连接的服务器
  const fetchConnectedServers = async () => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('mcp.get_connected_servers');
      const connectedIds = response.servers || [];
      
      connectedServers.value = servers.value
        .filter(server => connectedIds.includes(server.id))
        .map(server => ({ ...server, status: 'online' }));
      
      return connectedServers.value;
    } catch (e) {
      error.value = '获取已连接服务器失败';
      console.error('获取已连接服务器失败', e);
      return [];
    } finally {
      loading.value = false;
    }
  };

  // 获取MCP服务器状态及工具信息
  const fetchServersWithTools = async () => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('mcp.get_servers_with_tools');
      if (response && response.servers) {
        // 更新服务器数据
        servers.value = response.servers.map((server: any) => {
          // 服务器状态和错误信息处理
          let serverStatus = server.status || 'offline';
          const serverError = server.error_message || '';
          
          // 创建完整的服务器对象
          return {
            ...server,
            status: serverStatus,
            error_message: serverError,
            tools: server.tools || []
          };
        });
        
        // 更新连接的服务器
        connectedServers.value = servers.value.filter(server => server.status === 'online');
        
        // 更新最后检查时间
        lastCheckedAt.value = new Date();
      }
      return servers.value;
    } catch (e) {
      error.value = '获取服务器状态及工具信息失败';
      console.error('获取服务器状态及工具信息失败', e);
      return [];
    } finally {
      loading.value = false;
    }
  };

  // 连接到服务器
  const connectServer = async (serverId: string) => {
    try {
      // 找到服务器并更新状态
      const server = servers.value.find(s => s.id === serverId);
      if (server) {
        server.status = 'connecting';
      }
      
      const response = await jsonrpc.call('mcp.connect_server', { server_id: serverId });
      
      if (response && response.success) {
        // 更新服务器状态
        if (server) {
          server.status = 'online';
          connectedServers.value.push(server);
        }
        return true;
      } else {
        // 连接失败
        if (server) {
          server.status = 'error';
          server.error = response.message || '连接失败';
        }
        return false;
      }
    } catch (e) {
      error.value = '连接服务器失败';
      console.error('连接服务器失败', e);
      
      // 更新服务器状态为错误
      const server = servers.value.find(s => s.id === serverId);
      if (server) {
        server.status = 'error';
        server.error = e instanceof Error ? e.message : String(e);
      }
      
      return false;
    }
  };

  // 断开服务器连接
  const disconnectServer = async (serverId: string) => {
    try {
      const response = await jsonrpc.call('mcp.disconnect_server', { server_id: serverId });
      
      if (response && response.success) {
        // 更新服务器状态
        const server = servers.value.find(s => s.id === serverId);
        if (server) {
          server.status = 'offline';
        }
        
        // 从已连接服务器列表中移除
        connectedServers.value = connectedServers.value.filter(s => s.id !== serverId);
        
        return true;
      }
      return false;
    } catch (e) {
      error.value = '断开服务器连接失败';
      console.error('断开服务器连接失败', e);
      return false;
    }
  };

  // 测试服务器连接
  const testServerConnection = async (serverId: string) => {
    try {
      // 更新服务器状态为连接中
      const server = servers.value.find(s => s.id === serverId);
      if (server) {
        server.status = 'connecting';
      }
      
      const response = await jsonrpc.call('mcp.test_server_connection', { server_id: serverId });
      
      if (response && response.success) {
        // 更新服务器状态为在线
        if (server) {
          server.status = 'online';
          // 如果有返回工具信息，更新工具列表
          if (response.details && response.details.tools_count !== undefined) {
            server.tools = response.details.tools || [];
          }
        }
        return response;
      } else {
        // 连接测试失败
        if (server) {
          server.status = 'error';
          server.error = response.message || '连接测试失败';
        }
        return response;
      }
    } catch (e) {
      error.value = '测试服务器连接失败';
      console.error('测试服务器连接失败', e);
      
      // 更新服务器状态为错误
      const server = servers.value.find(s => s.id === serverId);
      if (server) {
        server.status = 'error';
        server.error = e instanceof Error ? e.message : String(e);
      }
      
      return {
        success: false,
        message: e instanceof Error ? e.message : String(e)
      };
    }
  };

  // 设置MCP服务器的采样回调
  const setupSamplingCallback = async (serverId: string, providerName: string) => {
    try {
      const response = await jsonrpc.call('mcp.setup_sampling_callback', {
        server_id: serverId,
        provider_name: providerName
      });
      
      return response && response.success;
    } catch (e) {
      error.value = '设置采样回调失败';
      console.error('设置采样回调失败', e);
      return false;
    }
  };

  // 检查服务器是否已连接
  const isServerConnected = (serverId: string) => {
    return connectedServers.value.some(server => server.id === serverId);
  };

  // 启动定期检查服务器状态
  const startPeriodicCheck = (intervalMinutes: number = 15) => {
    // 停止现有的定期检查
    stopPeriodicCheck();
    
    // 立即执行一次检查
    fetchServersWithTools();
    
    // 设置定期检查间隔
    checkInterval.value = window.setInterval(() => {
      fetchServersWithTools();
    }, intervalMinutes * 60 * 1000); // 转换为毫秒
  };

  // 停止定期检查
  const stopPeriodicCheck = () => {
    if (checkInterval.value !== null) {
      window.clearInterval(checkInterval.value);
      checkInterval.value = null;
    }
  };

  // 在组件卸载时停止定期检查
  const cleanupChecks = () => {
    stopPeriodicCheck();
  };

  return {
    servers,
    connectedServers,
    loading,
    error,
    lastCheckedAt,
    fetchServers,
    fetchConnectedServers,
    fetchServersWithTools,
    connectServer,
    disconnectServer,
    testServerConnection,
    setupSamplingCallback,
    isServerConnected,
    startPeriodicCheck,
    stopPeriodicCheck,
    cleanupChecks
  };
}); 