import { defineStore } from 'pinia';
import { ref } from 'vue';
import jsonrpc from '../api/jsonrpc';

export interface Message {
  id: string;
  role: string;
  content: any;
  timestamp: number;
  toolCalls?: any[];
}

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  llmProvider?: string;
  llmModel?: string;
  mcpServerId?: string;
  messageCount?: number;
}

export const useSessionStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([]);
  const currentSession = ref<Session | null>(null);
  const messages = ref<Message[]>([]);
  const loading = ref(false);
  const sending = ref(false); // 单独跟踪消息发送状态
  const error = ref('');
  const isLoadingMessages = ref(false);
  const messagesError = ref<string | null>(null);
  const isLoadingResponse = ref(false);
  const responseError = ref<string | null>(null);
  const sessionInactiveTimeout = ref<number>(5 * 60 * 1000); // 5分钟超时
  const sessionLastActivityTime = ref<number>(Date.now());
  const isSessionTimedOut = ref<boolean>(false);
  const sessionTimeoutTimer = ref<number | null>(null);

  // 清除所有错误信息
  const clearError = () => {
    error.value = '';
    messagesError.value = null;
    responseError.value = null;
  };

  // 更新会话活动时间
  const updateLastActivityTime = () => {
    sessionLastActivityTime.value = Date.now();
    isSessionTimedOut.value = false;
    
    // 重置超时计时器
    if (sessionTimeoutTimer.value !== null) {
      clearTimeout(sessionTimeoutTimer.value);
    }
    
    // 设置新的超时计时器
    sessionTimeoutTimer.value = window.setTimeout(() => {
      isSessionTimedOut.value = true;
    }, sessionInactiveTimeout.value);
  };

  // 检查会话是否超时
  const checkSessionTimeout = (): boolean => {
    if (!currentSession.value) return false;
    
    const currentTime = Date.now();
    const elapsedTime = currentTime - sessionLastActivityTime.value;
    
    if (elapsedTime > sessionInactiveTimeout.value) {
      isSessionTimedOut.value = true;
      return true;
    }
    
    return false;
  };

  // 重置会话超时状态
  const resetSessionTimeout = () => {
    isSessionTimedOut.value = false;
    updateLastActivityTime();
  };

  // 获取所有会话
  const fetchSessions = async () => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('sessions.listSessions', {});
      sessions.value = (response || []).map(convertApiSessionToSession);
      return sessions.value;
    } catch (e) {
      error.value = '加载会话列表失败';
      console.error('加载会话列表失败', e);
      return [];
    } finally {
      loading.value = false;
    }
  };

  // 创建新会话
  const createSession = async (title: string = '新会话', llmProvider?: string, llmModel?: string, mcpServerId?: string) => {
    loading.value = true;
    error.value = '';
    
    try {
      // 确保所有参数都是简单值
      const safeTitle = String(title || '新会话');
      const safeProvider = llmProvider ? String(llmProvider) : undefined;
      const safeModel = llmModel ? String(llmModel) : undefined;
      const safeServerId = mcpServerId ? String(mcpServerId) : undefined;
      
      console.log("调用创建会话API:", { 
        title: safeTitle, 
        llm_provider: safeProvider, 
        llm_model: safeModel, 
        mcp_server_id: safeServerId 
      });
      
      const response = await jsonrpc.call('sessions.createSession', {
        title: safeTitle,
        llm_provider: safeProvider,
        llm_model: safeModel,
        mcp_server_id: safeServerId
      });
      
      console.log("创建会话响应:", response);
      
      if (!response) {
        console.error("创建会话返回空响应");
        error.value = '创建会话失败: 服务器返回空响应';
        return null;
      }
      
      // 统一处理后端返回格式
      // 处理格式: {session: {...}} 或直接 {...} 
      const sessionData = response.session || response;
      
      if (!sessionData || !sessionData.id) {
        console.error("创建会话返回无效数据", response);
        error.value = '创建会话失败: 服务器返回无效数据';
        return null;
      }
      
      console.log("提取的会话数据:", sessionData);
      
      const newSession = convertApiSessionToSession(sessionData);
      
      console.log("处理后的会话对象:", newSession);
      
      // 添加到会话列表并设置为当前会话
      sessions.value.unshift(newSession);
      currentSession.value = newSession;
      messages.value = [];
      
      // 更新最后活动时间
      updateLastActivityTime();
      
      return newSession;
    } catch (e) {
      error.value = '创建会话失败';
      console.error('创建会话失败', e);
      throw e;
    } finally {
      loading.value = false;
    }
  };

  // 获取会话详情
  const fetchSession = async (sessionId: string) => {
    loading.value = true;
    error.value = '';
    
    try {
      console.log(`获取会话详情: ${sessionId}`);
      const response = await jsonrpc.call('sessions.getSession', { id: sessionId });
      console.log('会话详情响应:', response);
      
      if (response) {
        // 处理不同格式的响应
        // 1. 如果响应是 {session: {...}} 格式
        // 2. 如果响应直接是会话对象
        const sessionData = response.session || response;
        
        if (!sessionData || !sessionData.id) {
          console.error("获取会话返回无效数据", response);
          error.value = '会话不存在或数据无效';
          return null;
        }
        
        const session = convertApiSessionToSession(sessionData);
        console.log('处理后的会话对象:', session);
        
        // 设置当前会话
        currentSession.value = session;
        
        // 检查会话是否有效
        if (!currentSession.value || !currentSession.value.id) {
          console.error('设置currentSession失败', currentSession.value);
          error.value = '会话设置失败';
          return null;
        }
        
        // 如果返回的会话包含消息，也更新消息列表
        if (sessionData.messages && sessionData.messages.length > 0) {
          messages.value = sessionData.messages.map(convertApiMessageToMessage);
        } else {
          // 否则单独获取消息
          await fetchMessages(sessionId);
        }
        
        return session;
      }
      
      error.value = '会话不存在';
      return null;
    } catch (e) {
      error.value = '获取会话详情失败';
      console.error('获取会话详情失败', e);
      return null;
    } finally {
      loading.value = false;
    }
  };

  // 更新会话标题
  const updateSessionTitle = async (sessionId: string, title: string) => {
    console.log(`更新会话 ${sessionId} 标题为: "${title}"`);
    try {
      // 直接强制更新前端状态，即使后端可能失败
      if (currentSession.value && currentSession.value.id === sessionId) {
        // 创建新对象以触发响应式更新
        const updatedSession = { ...currentSession.value, title };
        currentSession.value = updatedSession;
        
        // 同时更新会话列表中的对应会话
        const index = sessions.value.findIndex(s => s.id === sessionId);
        if (index !== -1) {
          sessions.value[index] = { ...sessions.value[index], title };
        }
        
        console.log('前端状态已更新，当前标题:', currentSession.value.title);
        
        // 尝试直接通过DOM更新标题元素（备用方案）
        try {
          const titleElement = document.querySelector('.chat-title');
          if (titleElement) {
            titleElement.textContent = title;
            console.log('通过DOM直接更新了标题元素');
          }
        } catch (domError) {
          console.error('DOM更新失败:', domError);
        }
      }
      
      // 调用后端API更新标题
      console.log('调用后端API更新标题，参数:', { sessionId, title });
      const response = await jsonrpc.updateSessionTitle(sessionId, title);
      console.log('updateSessionTitle 原始响应:', JSON.stringify(response, null, 2));
      
      // 检查响应是否成功
      if (response && response.session) {
        console.log('后端返回会话数据:', response.session);
        
        // 更新会话数据 - 使用后端返回的最新数据
        const updatedSession = convertApiSessionToSession(response.session);
        
        // 只有当标题真的不同时才更新
        if (currentSession.value && 
            currentSession.value.id === sessionId && 
            currentSession.value.title !== updatedSession.title) {
          console.log(`使用后端返回的标题更新前端状态: "${updatedSession.title}"`);
          currentSession.value = updatedSession;
          
          // 同时更新会话列表
          const index = sessions.value.findIndex(s => s.id === sessionId);
          if (index !== -1) {
            sessions.value[index] = updatedSession;
          }
        }
        
        return true;
      } else {
        console.warn('后端未返回有效的会话数据，但前端状态已更新');
        // 即使后端可能失败，我们已经更新了前端状态
        return true;
      }
    } catch (error) {
      console.error('更新会话标题出错:', error);
      // 尝试再次刷新会话数据
      try {
        await refreshCurrentSession();
      } catch (refreshError) {
        console.error('刷新会话失败:', refreshError);
      }
      return false;
    }
  };

  // 自动生成会话标题
  const generateSessionTitle = async (sessionId: string): Promise<boolean> => {
    try {
      console.log(`为会话 ${sessionId} 生成标题...`);
      // 确保当前会话已加载
      if (!currentSession.value || currentSession.value.id !== sessionId) {
        console.log('当前会话未加载，正在加载会话...');
        const session = await fetchSession(sessionId);
        if (!session) {
          console.error('无法加载会话，生成标题失败');
          return false;
        }
      }

      // 确保有足够的消息用于生成标题
      if (messages.value.length < 2) {
        console.error('消息不足，无法生成有意义的标题');
        return false;
      }

      const provider = currentSession.value?.llmProvider;
      const model = currentSession.value?.llmModel;

      if (!provider || !model) {
        console.error('无法获取当前LLM提供商或模型：', { provider, model });
        return false;
      }

      console.log(`使用 ${provider}/${model} 生成标题`);
      
      // 获取最多10条消息用于生成标题，并格式化为后端期望的格式
      const messagesToUse = messages.value.slice(0, Math.min(10, messages.value.length)).map(msg => ({
        role: msg.role,
        content: typeof msg.content === 'string' 
          ? msg.content 
          : (msg.content?.text || JSON.stringify(msg.content))
      }));
      
      console.log('准备传递给后端的格式化消息:', JSON.stringify(messagesToUse, null, 2));
      
      // 调用API生成标题
      const generatedTitle = await jsonrpc.generateSessionTitle(
        sessionId,
        messagesToUse,
        provider,
        model
      );

      if (!generatedTitle) {
        console.error('生成的标题为空');
        return false;
      }

      console.log(`生成的标题: "${generatedTitle}"`);
      
      // 更新会话标题
      const success = await updateSessionTitle(sessionId, generatedTitle);
      if (success) {
        console.log(`会话标题已更新为: "${generatedTitle}"`);
        
        // 确保会话刷新
        const refreshSuccess = await refreshCurrentSession();
        console.log(`会话刷新 ${refreshSuccess ? '成功' : '失败'}`);
        
        return true;
      } else {
        console.error('更新会话标题失败');
        // 尝试直接刷新会话，可能标题已在后端更新
        await refreshCurrentSession();
        return false;
      }
    } catch (error: any) {
      console.error('生成标题时出错:', error);
      // 不要在catch块中给全局error赋值，使用单独的变量或message
      console.error('无法生成会话标题: ' + (error.message || '未知错误'));
      return false;
    }
  };

  // 更新会话LLM配置
  const updateSessionLLM = async (sessionId: string, provider: string, model: string) => {
    // 确保provider和model是有效的字符串
    const safeProvider = provider && typeof provider === 'string' ? provider : '';
    const safeModel = model && typeof model === 'string' ? model : '';
    
    if (!safeProvider || !safeModel) {
      console.error('无效的LLM配置', { provider, model });
      return false;
    }
    
    console.log(`更新会话 ${sessionId} LLM设置:`, { provider: safeProvider, model: safeModel });
    
    try {
      // 直接使用jsonrpc.updateSessionLLM方法
      const response = await jsonrpc.updateSessionLLM(sessionId, safeProvider, safeModel);
      console.log('updateSessionLLM 响应:', response);
      
      // 检查response是否存在且success为true，并且包含session数据
      if (response && response.success && response.session) { 
        // 更新会话信息
        const updatedSession = convertApiSessionToSession(response.session);
        
        const index = sessions.value.findIndex(s => s.id === sessionId);
        if (index !== -1) {
          // 更新会话列表中的会话
          sessions.value[index] = updatedSession;
        }
        
        if (currentSession.value && currentSession.value.id === sessionId) {
          // 更新当前活动会话
          currentSession.value = updatedSession;
          console.log('LLM设置更新成功:', currentSession.value.llmProvider, currentSession.value.llmModel);
        }
        
        return true;
      } else {
        console.error('更新会话LLM设置失败: 后端未返回有效数据', response);
        return false;
      }
    } catch (error) {
      console.error('更新会话LLM设置出错:', error);
      return false;
    }
  };

  // 更新会话MCP服务器
  const updateSessionMCPServer = async (sessionId: string, serverId: string | undefined) => {
    // serverId可以是undefined，表示不使用MCP服务器
    const safeServerId = serverId ? String(serverId) : '';
    console.log(`更新会话 ${sessionId} MCP服务器为:`, safeServerId || '无');
    
    try {
      // 直接使用jsonrpc.updateSessionMCPServer方法
      const response = await jsonrpc.updateSessionMCPServer(sessionId, safeServerId);
      console.log('updateSessionMCPServer 响应:', response);
      
      // 检查response是否存在且success为true，并且包含session数据
      if (response && response.success && response.session) { 
        // 更新会话信息
        const updatedSession = convertApiSessionToSession(response.session);
        
        const index = sessions.value.findIndex(s => s.id === sessionId);
        if (index !== -1) {
          // 更新会话列表中的会话
          sessions.value[index] = updatedSession;
        }
        
        if (currentSession.value && currentSession.value.id === sessionId) {
          // 更新当前活动会话
          currentSession.value = updatedSession;
          console.log('MCP服务器设置更新成功:', currentSession.value.mcpServerId);
        }
        
        return true;
      } else {
        console.error('更新会话MCP服务器设置失败: 后端未返回有效数据', response);
        return false;
      }
    } catch (error) {
      console.error('更新会话MCP服务器设置出错:', error);
      return false;
    }
  };

  // 删除会话
  const deleteSession = async (sessionId: string) => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('sessions.delete', { session_id: sessionId });
      
      if (response.success) {
        sessions.value = sessions.value.filter(s => s.id !== sessionId);
        
        if (currentSession.value && currentSession.value.id === sessionId) {
          currentSession.value = null;
          messages.value = [];
        }
        
        return true;
      }
      
      return false;
    } catch (e) {
      error.value = '删除会话失败';
      console.error('删除会话失败', e);
      return false;
    } finally {
      loading.value = false;
    }
  };

  // 获取会话消息
  const fetchMessages = async (sessionId: string): Promise<void> => {
    if (isLoadingMessages.value) return;
    
    isLoadingMessages.value = true;
    messagesError.value = null;
    
    try {
      // 更新会话活动时间
      updateLastActivityTime();
      
      const response = await jsonrpc.call('sessions.getMessages', { session_id: sessionId });
      
      if (response && response.messages) {
        // 将API消息转换为前端消息对象
        const newMessages = response.messages.map(convertApiMessageToMessage);
        
        // 智能对比，仅在消息有变化时更新
        if (JSON.stringify(newMessages) !== JSON.stringify(messages.value)) {
          console.log('检测到消息变化，更新UI');
          // 如果消息数量增加，滚动到底部
          const shouldScroll = newMessages.length > messages.value.length;
          
          // 更新消息列表
          messages.value = newMessages;
          
          // 如果消息数量增加，在下一个渲染周期滚动到底部
          if (shouldScroll) {
            setTimeout(() => {
              const container = document.querySelector('.message-container');
              if (container) {
                container.scrollTop = container.scrollHeight;
              }
            }, 100);
          }
        }
      } else {
        // 如果没有返回消息，也要确保消息列表为空
        if (messages.value.length > 0) {
          messages.value = [];
        }
      }
    } catch (e) {
      console.error('获取会话消息失败', e);
      messagesError.value = e instanceof Error ? e.message : '获取消息失败';
    } finally {
      isLoadingMessages.value = false;
    }
  };

  // 生成唯一消息ID
  function generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // 发送消息
  const sendMessage = async (content: string) => {
    // 首先检查是否正在处理上一条消息
    if (isLoadingResponse.value) {
      console.log('正在处理上一条消息，忽略新的发送请求');
      throw new Error('当前正在处理上一条消息，请等待响应完成后再发送');
    }
    
    // 检查会话是否存在
    if (!currentSession.value || !currentSession.value.id) {
      console.error('无法发送消息：当前没有活跃会话', currentSession.value);
      throw new Error('无法发送消息：当前没有活跃会话');
    }
    
    // 预检查LLM提供商，避免后续错误
    if (!currentSession.value.llmProvider || 
        currentSession.value.llmProvider === 'undefined' || 
        currentSession.value.llmProvider === 'null') {
      throw new Error('请先在界面顶部选择有效的LLM提供商后再发送消息');
    }
    
    // 预检查LLM模型，避免后续错误
    if (!currentSession.value.llmModel || 
        currentSession.value.llmModel === 'undefined' || 
        currentSession.value.llmModel === 'null') {
      throw new Error('请先在界面顶部选择有效的LLM模型后再发送消息');
    }
    
    const sessionId = currentSession.value.id;
    const messageId = generateMessageId();
    sending.value = true;
    isLoadingResponse.value = true;
    responseError.value = null;
    
    // 检查这是否是第一条消息
    const isFirstMessage = messages.value.length === 0 || 
      (messages.value.length === 1 && messages.value[0].role === 'user');
    
    try {
      // 更新会话活动时间
      updateLastActivityTime();
      
      // 添加临时用户消息，立即显示在UI上
      messages.value.push({
        id: messageId,
        role: 'user',
        content: content,
        timestamp: Date.now()
      });
      
      // 自动滚动到底部
      setTimeout(() => {
        const container = document.querySelector('.message-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }, 100);
      
      // 使用MCP工具进行对话
      let response;
      
      // 确保所有参数都是字符串
      const sessionIdStr = String(sessionId);
      const contentStr = String(content);
      
      // 确保提供商名称是有效的非空字符串
      if (!currentSession.value.llmProvider) {
        throw new Error('LLM提供商不能为空，请确保选择了有效的LLM提供商');
      }
      const llmProviderStr = String(currentSession.value.llmProvider);
      if (llmProviderStr === 'undefined' || llmProviderStr === 'null') {
        throw new Error(`无效的LLM提供商: ${llmProviderStr}`);
      }
      
      // 确保模型名称是有效的非空字符串
      if (!currentSession.value.llmModel) {
        throw new Error('LLM模型不能为空，请确保选择了有效的LLM模型');
      }
      const llmModelStr = String(currentSession.value.llmModel);
      if (llmModelStr === 'undefined' || llmModelStr === 'null') {
        throw new Error(`无效的LLM模型: ${llmModelStr}`);
      }
      
      console.log('发送消息的参数检查:');
      console.log(`- sessionId: ${sessionIdStr} (${typeof sessionIdStr})`);
      console.log(`- content长度: ${contentStr.length} (${typeof contentStr})`);
      console.log(`- llmProvider: ${llmProviderStr} (${typeof llmProviderStr})`);
      console.log(`- llmModel: ${llmModelStr} (${typeof llmModelStr})`);
      
      // 判断是否使用MCP工具 - 确保mcpServerId不为undefined或空值
      if (currentSession.value.mcpServerId && String(currentSession.value.mcpServerId).trim() !== '') {
        const mcpServerIdStr = String(currentSession.value.mcpServerId);
        console.log(`- mcpServerId: ${mcpServerIdStr} (${typeof mcpServerIdStr})`);
        
        // 不应该传递"undefined"字符串，确保这里的值是有效的
        if (mcpServerIdStr === "undefined" || mcpServerIdStr === "null") {
          console.log('警告: mcpServerId是"undefined"或"null"字符串，将发送不使用MCP服务器的请求');
          response = await jsonrpc.chatWithTools(
            sessionIdStr,    // 会话ID
            contentStr,      // 用户消息内容
            llmProviderStr,  // LLM提供商
            llmModelStr      // 模型参数
          );
        } else {
          console.log(`发送消息使用MCP服务器: ${mcpServerIdStr}`);
          response = await jsonrpc.chatWithTools(
            sessionIdStr,    // 会话ID
            contentStr,      // 用户消息内容
            llmProviderStr,  // LLM提供商
            llmModelStr,     // 模型参数
            mcpServerIdStr   // 服务器ID参数
          );
        }
      } else {
        console.log('发送消息不使用MCP服务器');
        response = await jsonrpc.chatWithTools(
          sessionIdStr,    // 会话ID
          contentStr,      // 用户消息内容
          llmProviderStr,  // LLM提供商
          llmModelStr      // 模型参数
        );
      }
      
      // 刷新消息列表以获取完整会话
      await fetchMessages(sessionId);
      
      return response;
    } catch (e) {
      console.error('发送消息失败', e);
      responseError.value = e instanceof Error ? e.message : '发送消息失败';
      
      // 刷新消息列表，以防止UI和后端不同步
      try {
        await fetchMessages(sessionId);
      } catch (fetchError) {
        console.error('刷新消息列表失败', fetchError);
      }
      
      throw e;
    } finally {
      sending.value = false;
      isLoadingResponse.value = false;
    }
  };

  // 清空会话消息
  const clearMessages = async (sessionId: string) => {
    try {
      // 更新会话活动时间
      updateLastActivityTime();
      
      const response = await jsonrpc.call('sessions.clearMessages', { session_id: sessionId });
      
      if (response.success) {
        // 清空内存中的消息
        messages.value = [];
        return true;
      }
      
      return false;
    } catch (e) {
      console.error('清空会话消息失败', e);
      throw e;
    }
  };

  // 更新会话的通用方法
  const updateSession = async (sessionId: string, updateData: Partial<Session>) => {
    loading.value = true;
    error.value = '';
    
    let response: any = null; // 声明response变量以便在catch块外部访问
    try {
      console.log(`准备更新会话 ${sessionId}:`, updateData);
      
      // 确保所有参数类型正确，并转换成后端需要的格式
      const params: Record<string, any> = { id: sessionId };
      
      if ('title' in updateData && updateData.title !== undefined) {
        // 后端需要 'name' 字段
        params.name = String(updateData.title); 
      }
      
      if ('llmProvider' in updateData && updateData.llmProvider !== undefined) {
        params.llm_provider = String(updateData.llmProvider);
      }
      
      if ('llmModel' in updateData && updateData.llmModel !== undefined) {
        params.llm_model = String(updateData.llmModel);
      }
      
      if ('mcpServerId' in updateData) {
        params.mcp_server_id = updateData.mcpServerId !== undefined ? 
          String(updateData.mcpServerId) : '';
      }
      
      console.log('发送更新参数到 sessions.updateSession:', params);
      response = await jsonrpc.call('sessions.updateSession', params);
      console.log('sessions.updateSession 后端响应:', response); // 记录后端响应
      
      // 检查response是否存在且success为true，并且包含session数据
      if (response && response.success && response.session) { 
        // 使用后端返回的完整会话数据来更新前端状态
        const updatedSession = convertApiSessionToSession(response.session);
        console.log('使用后端返回的数据更新会话:', updatedSession);

        const index = sessions.value.findIndex(s => s.id === sessionId);
        if (index !== -1) {
          // 更新会话列表中的会话
          sessions.value[index] = updatedSession;
        }
        
        if (currentSession.value && currentSession.value.id === sessionId) {
          // 更新当前活动会话
          currentSession.value = updatedSession;
          // 在状态更新后立刻打印 title，确认其值
          console.log('确认更新后的 currentSession.value.title:', currentSession.value?.title);
        }
        
        return true;
      } else {
        // 如果后端没有返回 success: true 或缺少session数据
        console.error('更新会话失败: 后端未返回成功标志或有效会话数据。响应:', response);
        error.value = '更新会话信息失败: 服务器未确认成功或数据无效';
        return false; // 明确返回false
      }
      
    } catch (e) {
      error.value = '更新会话信息失败';
      console.error('更新会话信息失败 - 捕获到错误:', e);
      console.error('失败时的后端响应 (如果可用):', response); // 记录失败时的响应
      return false;
    } finally {
      loading.value = false;
    }
  };

  // 辅助函数：将后端API会话对象转换为前端Session对象
  const convertApiSessionToSession = (apiSession: any): Session => {
    return {
      id: apiSession.id,
      // 后端返回的是 name，前端需要 title
      title: apiSession.name || '新会话', 
      createdAt: apiSession.created_at ? new Date(apiSession.created_at).getTime() : Date.now(),
      updatedAt: apiSession.updated_at ? new Date(apiSession.updated_at).getTime() : Date.now(),
      llmProvider: apiSession.llm_provider,
      llmModel: apiSession.llm_model,
      mcpServerId: apiSession.mcp_server_id,
      messageCount: apiSession.message_count
    };
  };
  
  // 辅助函数：将后端API消息转换为前端Message对象
  const convertApiMessageToMessage = (apiMessage: any): Message => {
    return {
      id: apiMessage.id,
      role: apiMessage.role,
      content: apiMessage.content, 
      timestamp: new Date(apiMessage.timestamp).getTime(),
      toolCalls: apiMessage.toolCalls || apiMessage.tool_calls // 兼容不同命名
    };
  };

  // 刷新当前会话
  const refreshCurrentSession = async () => {
    if (currentSession.value) {
      try {
        console.log(`刷新会话 ${currentSession.value.id}...`);
        await fetchSession(currentSession.value.id);
        console.log('会话刷新成功，更新后的标题:', currentSession.value.title);
        return true;
      } catch (error) {
        console.error('刷新会话失败:', error);
        return false;
      }
    }
    return false;
  };

  // 重置会话错误状态
  function resetSessionErrorState() {
    responseError.value = '';
    messagesError.value = '';
    isLoadingResponse.value = false;
    isLoadingMessages.value = false;
  }

  return {
    sessions,
    currentSession,
    messages,
    loading,
    sending,
    error,
    isLoadingMessages,
    messagesError,
    isLoadingResponse,
    responseError,
    sessionInactiveTimeout,
    sessionLastActivityTime,
    isSessionTimedOut,
    sessionTimeoutTimer,
    fetchSessions,
    createSession,
    fetchSession,
    updateSessionTitle,
    updateSessionLLM,
    updateSessionMCPServer,
    updateSession,
    deleteSession,
    fetchMessages,
    sendMessage,
    clearMessages,
    clearError,
    updateLastActivityTime,
    checkSessionTimeout,
    resetSessionTimeout,
    generateSessionTitle,
    refreshCurrentSession,
    resetSessionErrorState
  };
}); 