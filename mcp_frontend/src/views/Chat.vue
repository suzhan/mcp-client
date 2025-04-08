<template>
  <v-container fluid class="chat-container d-flex flex-column pa-0">
    <!-- 聊天头部 (精简版，无边框) -->
    <div class="mb-3 py-2 px-3 borderless-header">
      <!-- 聊天标题 -->
      <div class="d-flex align-center">
        <div class="title-container me-auto">
          <template v-if="isEditingTitle">
            <input 
              v-model="editedTitle" 
              class="title-input"
              @keyup.enter="saveTitle"
              @keyup.esc="cancelEditTitle"
              @blur="saveTitle"
              ref="titleInput"
              :placeholder="$t('chat.enterSessionTitle')"
            />
          </template>
          <template v-else>
            <!-- 使用key强制在titleKey变化时重新渲染标题 -->
            <div :key="titleUpdateKey">
              <h1 @click="startEditingTitle" class="chat-title" :data-title="sessionStore.currentSession?.title || $t('chat.newChat')">
                {{ sessionStore.currentSession?.title || $t('chat.newChat') }}
              </h1>
            </div>
            <div class="title-actions">
              <v-icon @click="startEditingTitle" icon="mdi-pencil" size="small" color="grey" class="me-1"></v-icon>
              <v-icon v-if="sessionStore.messages.length > 2" @click="autoGenerateTitle" icon="mdi-magic-staff" size="small" color="primary" :title="$t('chat.autoGenerateTitle')"></v-icon>
            </div>
          </template>
        </div>

        <!-- 自动重命名开关 -->
        <div class="auto-rename-switch" style="display: none;">
          <label class="switch-label">
            <input type="checkbox" v-model="autoRenameAfterFirstResponse">
            <span class="switch-text" :title="$t('chat.autoRenameTip')">{{ $t('chat.autoRename') }}</span>
          </label>
        </div>

        <!-- 精简的设置区域 -->
        <div class="d-flex align-center gap-1">
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn 
                density="compact"
                variant="text"
                v-bind="props"
                class="text-caption"
                :class="{'text-primary font-weight-bold': selectedProvider, 'text-medium-emphasis': !selectedProvider}"
              >
                <span v-if="selectedProvider">{{ selectedProvider.name }}</span>
                <span v-else class="text-error font-weight-bold">{{ $t('chat.selectLLM') }}</span>
                <v-icon size="small" class="ms-1">mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list density="compact" class="py-0">
              <v-list-item
                v-for="provider in providerStore.providers"
                :key="provider.id"
                :value="provider.name"
                :selected="selectedProvider && selectedProvider.name === provider.name"
                :class="{'bg-primary-lighten-5': selectedProvider && selectedProvider.name === provider.name}"
                @click="() => {
                  selectedProvider = provider;
                  updateProviderModels(provider);
                }"
              >
                <v-list-item-title>{{ provider.name }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <v-divider vertical></v-divider>

          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn 
                density="compact"
                variant="text"
                v-bind="props"
                :disabled="!selectedProvider || availableModels.length === 0"
                class="text-caption"
                :class="{'text-primary font-weight-bold': selectedModel, 'text-medium-emphasis': !selectedModel}"
              >
                <span v-if="selectedModel">{{ selectedModel }}</span>
                <span v-else class="text-error font-weight-bold">{{ $t('chat.selectModel') }}</span>
                <v-icon size="small" class="ms-1">mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list density="compact" class="py-0">
              <v-list-item
                v-for="model in availableModels"
                :key="model"
                :value="model"
                :selected="selectedModel === model"
                :class="{'bg-primary-lighten-5': selectedModel === model}"
                @click="selectedModel = model"
              >
                <v-list-item-title>{{ model }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </div>
      
      <!-- MCP服务器标签显示 -->
      <div class="d-flex flex-column py-1" v-if="serverStore.servers.length > 0">
        <div class="d-flex flex-wrap align-center">
          <span class="text-caption text-medium-emphasis me-2">{{ $t('chat.mcpServers') }}:</span>
          <div class="server-chips-container">
            <v-chip
              v-for="server in serverStore.servers"
              :key="server.id"
              size="small"
              :color="serverStore.isServerConnected(server.id) ? 'success' : 'error'"
              :class="[selectedMCPServer && selectedMCPServer.id === server.id ? 'selected-server' : '']"
              @click="toggleMCPServer(server)"
              class="server-chip ma-1"
              variant="text"
              label
            >
              <span class="server-name">{{ server.name }}</span>
              <span v-if="getServerTools(server.id).length > 0" class="server-tools-list ms-1">
                <v-tooltip activator="parent" location="bottom">
                  <div class="pa-1">
                    <div class="text-caption mb-1 font-weight-medium">{{ $t('chat.tools') }}:</div>
                    <div v-for="tool in getServerTools(server.id)" :key="tool.name" class="text-caption pb-1">
                      {{ tool.name }}
                    </div>
                  </div>
                </v-tooltip>
                ({{ getServerTools(server.id).length }})
              </span>
              <span v-if="getServerResources(server.id).length > 0" class="server-resources-list ms-1">
                <v-tooltip activator="parent" location="bottom">
                  <div class="pa-1">
                    <div class="text-caption mb-1 font-weight-medium">{{ $t('chat.resources') }}:</div>
                    <div v-for="resource in getServerResources(server.id)" :key="resource.name" class="text-caption pb-1">
                      {{ resource.name }}
                    </div>
                  </div>
                </v-tooltip>
                [{{ getServerResources(server.id).length }}]
              </span>
              <span v-if="getServerPrompts(server.id).length > 0" class="server-prompts-list ms-1">
                <v-tooltip activator="parent" location="bottom">
                  <div class="pa-1">
                    <div class="text-caption mb-1 font-weight-medium">{{ $t('chat.prompts') }}:</div>
                    <div v-for="prompt in getServerPrompts(server.id)" :key="prompt.name" class="text-caption pb-1">
                      {{ prompt.name }}
                    </div>
                  </div>
                </v-tooltip>
                {{ getServerPrompts(server.id).length }}
              </span>
              <v-icon size="x-small" class="ms-1">
                {{ serverStore.isServerConnected(server.id) ? 'mdi-check-circle' : 'mdi-alert-circle' }}
              </v-icon>
            </v-chip>
          </div>
        </div>
      </div>
    </div>

    <!-- 消息显示区域 (无边框) -->
    <div class="flex-grow-1 message-area overflow-auto">
      <div 
        v-if="!sessionStore.messages.length" 
        class="d-flex flex-column justify-center align-center pa-4 empty-message"
        style="height: 100%"
      >
        <v-icon size="48" class="mb-4 text-primary-lighten-1">mdi-message-text-outline</v-icon>
        <p class="text-h6 text-center">{{ $t('chat.startNewConversation') }}</p>
        <p class="text-subtitle-1 text-center text-medium-emphasis">
          {{ $t('chat.selectProviderAndSend') }}
        </p>
      </div>
      
      <div v-else class="pa-2">
        <div class="d-flex flex-column gap-2">
          <div 
            v-for="message in sessionStore.messages" 
            :key="message.id"
            :class="['chat-message', `${message.role}-message`]"
          >
            <div class="d-flex">
              <div class="flex-grow-1">
                <div class="d-flex align-center mb-1">
                  <span class="role-name">{{ getRoleName(message.role) }}</span>
                </div>
                
                <div class="message-content">
                  <div v-if="typeof message.content === 'string'" v-html="formatMessageContent(message.content)" class="markdown-body"></div>
                  <div v-else-if="typeof message.content === 'object' && message.content.text" v-html="formatMessageContent(message.content.text)" class="markdown-body"></div>
                  <div v-else-if="typeof message.content === 'object'" v-html="formatMessageContent(JSON.stringify(message.content, null, 2))" class="markdown-body"></div>
                  <div v-else v-html="formatMessageContent(String(message.content))" class="markdown-body"></div>
                </div>

                <!-- 工具调用显示 -->
                <div v-if="message.toolCalls && message.toolCalls.length > 0" class="tool-calls mt-1">
                  <div
                    v-for="(toolCall, index) in message.toolCalls"
                    :key="toolCall.id || index"
                    class="tool-call-item mb-1"
                  >
                    <div class="d-flex align-center">
                      <v-icon size="x-small" class="mr-1">mdi-tools</v-icon>
                      <span class="text-caption font-weight-medium">调用: {{ toolCall.name }}</span>
                    </div>
                    <pre class="text-caption mt-1 tool-call-args">{{ formatToolCallArguments(toolCall.arguments) }}</pre>
                  </div>
                </div>

                <!-- 工具结果显示 -->
                <div v-if="message.toolResults && message.toolResults.length > 0" class="tool-results mt-1">
                  <div
                    v-for="(toolResult, index) in message.toolResults"
                    :key="index"
                    class="tool-result-item mb-1"
                    :class="toolResult.error ? 'tool-error' : 'tool-success'"
                  >
                    <div class="d-flex align-center">
                      <v-icon size="x-small" class="mr-1">
                        {{ toolResult.error ? 'mdi-alert-circle' : 'mdi-check-circle' }}
                      </v-icon>
                      <span class="text-caption font-weight-medium">
                        {{ toolResult.error ? '执行失败' : '执行结果' }}
                      </span>
                    </div>
                    <pre class="text-caption mt-1 tool-result-content">{{ toolResult.content }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="sessionStore.loading" class="d-flex justify-center align-center pa-4">
        <v-progress-circular indeterminate color="primary"></v-progress-circular>
      </div>
    </div>

    <!-- 消息输入区域 - 固定在底部 (无边框) -->
    <div class="message-input-container">
      <div class="pa-2 input-area">
        <div class="input-wrapper elevation-1">
          <v-textarea
            v-model="userInput"
            variant="plain"
            hide-details
            rows="1"
            auto-grow
            max-rows="4"
            :placeholder="$t('chat.enterMessage')"
            class="message-input ml-2"
            @keydown.ctrl.enter.prevent="sendMessage"
            @keydown.enter.exact.prevent="handleEnterKey"
          ></v-textarea>
          
          <v-btn 
            color="primary" 
            :disabled="!userInput.trim() || sessionStore.isLoadingResponse"
            :loading="sessionStore.isLoadingResponse"
            @click="sendMessage"
            class="send-button"
            elevation="0"
            icon
          >
            <v-icon>mdi-send</v-icon>
          </v-btn>
        </div>
      </div>
    </div>

    <!-- 加载动画 - 中央显示 -->
    <div v-if="isLoadingResponse && !isSessionTimedOut" class="thinking-overlay">
      <div class="thinking-container">
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <p>{{ $t('chat.aiThinking') }}</p>
      </div>
    </div>

    <!-- 会话超时提示 -->
    <div v-if="isSessionTimedOut" class="session-timeout-alert">
      <i class="fas fa-exclamation-circle"></i>
      <span>{{ $t('chat.sessionTimedOut') }}</span>
      <button @click="resetSession" class="reset-session-btn">{{ $t('chat.resetSession') }}</button>
    </div>
  </v-container>
</template>

<script setup lang="ts">
import mdHighlight from 'markdown-it-highlightjs';
import jsonrpc from '../api/jsonrpc';
import { useI18n } from 'vue-i18n';
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '../stores/sessions';
import { useProviderStore } from '../stores/providers';
import { useServerStore } from '../stores/servers';
import MarkdownIt from 'markdown-it';
import { format } from 'date-fns';

const { t } = useI18n();
const sessionStore = useSessionStore();
const providerStore = useProviderStore();
const serverStore = useServerStore();
const route = useRoute();
const router = useRouter();

const userInput = ref('');
const isEditingTitle = ref(false);
const editedTitle = ref('');
const selectedProvider = ref(null);
const selectedModel = ref('');
const availableModels = ref<string[]>([]);
const isConnectingServers = ref(false);
const loadingModels = ref(false);
const errorMessage = ref('');
const loading = ref(true);
const titleUpdateKey = ref(Date.now());
const autoRenameAfterFirstResponse = ref(false);
const isSessionTimedOut = computed(() => sessionStore.isSessionTimedOut);
const responseError = computed(() => sessionStore.responseError);
const isLoadingResponse = computed(() => sessionStore.isLoadingResponse);
const isLoadingMessages = computed(() => sessionStore.isLoadingMessages);
const messagesError = computed(() => sessionStore.messagesError);
const messages = computed(() => sessionStore.messages);
const selectedMCPServer = ref(null);
const polling = ref<number | null>(null);
const pollingInterval = 3000; // 3秒轮询一次
const titleInput = ref<HTMLInputElement | null>(null);

// 服务器工具列表
const serverTools = ref<any[]>([]);
// 所有服务器的工具列表
const allServerTools = ref<any[]>([]);
// 所有服务器的资源列表
const allServerResources = ref<any[]>([]);
// 所有服务器的prompt列表
const allServerPrompts = ref<any[]>([]);

const md = new MarkdownIt({
  linkify: true,
  typographer: true,
  breaks: true,
  html: false
}).use(mdHighlight);

// 当前会话ID
const sessionId = computed(() => route.params.id as string);

// 当前会话标题 - 添加依赖确保刷新
const currentTitle = computed(() => {
  // 添加依赖：整个currentSession对象，包括其所有属性
  const session = sessionStore.currentSession;
  // 显式访问session.title确保此计算属性依赖于title
  const title = session?.title;
  // 记录每次标题计算
  console.log('计算currentTitle:', title);
  return title || t('chat.newChat');
});

// 手动强制刷新标题
const forceRefreshTitle = async () => {
  console.log('强制刷新标题');
  if (sessionStore.currentSession) {
    // 获取当前标题
    const currentTitle = sessionStore.currentSession.title;
    console.log(`当前标题: "${currentTitle}"`);
    
    // 强制UI更新
    titleUpdateKey.value = Date.now();
    
    // 直接更新DOM
    try {
      const titleElement = document.querySelector('.chat-title');
      if (titleElement) {
        titleElement.textContent = currentTitle;
        console.log('DOM标题已更新');
      }
    } catch (e) {
      console.error('DOM更新失败:', e);
    }
    
    await nextTick();
  }
};

// 监听会话标题变化
watch(() => sessionStore.currentSession?.title, (newTitle) => {
  console.log('会话标题已更新:', newTitle);
});

// 生命周期钩子
onMounted(async () => {
  loading.value = true;
  
  try {
    console.log("聊天页面挂载，开始初始化...");
    
    // 先加载LLM提供商
    await providerStore.fetchProviders();
    console.log(`加载了 ${providerStore.providers.length} 个LLM提供商`);
    
    // 先确保MCP服务器连接
    await ensureMCPServerConnections();
    
    // 根据路由参数判断是否需要加载现有会话
    if (sessionId.value) {
      console.log(`发现会话ID参数: ${sessionId.value}，加载现有会话`);
      await loadSession(sessionId.value);
      
      // 显式同步一次，确保UI状态与会话状态一致
      if (sessionStore.currentSession) {
        console.log("检查会话LLM设置与UI状态是否同步");
        
        // 如果会话有LLM设置但UI没有选择，则同步到UI
        if (sessionStore.currentSession.llmProvider && (!selectedProvider.value || selectedProvider.value.name !== sessionStore.currentSession.llmProvider)) {
          const providerObj = providerStore.providers.find(
            p => p.name === sessionStore.currentSession?.llmProvider
          );
          
          if (providerObj) {
            console.log(`同步会话LLM提供商 ${sessionStore.currentSession.llmProvider} 到UI`);
            selectedProvider.value = providerObj;
            await updateProviderModels(providerObj);
            
            if (sessionStore.currentSession.llmModel) {
              console.log(`同步会话LLM模型 ${sessionStore.currentSession.llmModel} 到UI`);
              selectedModel.value = sessionStore.currentSession.llmModel;
            }
          }
        }
      }
    } else {
      console.log("没有会话ID参数，设置默认LLM选项");
      // 对于新会话页面，设置默认的提供商和模型
      if (providerStore.providers.length > 0) {
        selectedProvider.value = providerStore.providers[0];
        console.log(`设置默认提供商: ${selectedProvider.value.name}`);
        await updateProviderModels(selectedProvider.value);
      } else {
        console.log("没有可用的LLM提供商");
      }
    }

    // 获取所有服务器工具
    await fetchAllServerTools();
    
    // 获取所有服务器资源
    await fetchAllServerResources();
    
    // 获取所有服务器Prompts
    await fetchAllServerPrompts();
    
    // 记录最终状态
    console.log("初始化完成. 当前状态:", {
      会话ID: sessionStore.currentSession?.id || '无',
      会话LLM供应商: sessionStore.currentSession?.llmProvider || '未设置',
      会话LLM模型: sessionStore.currentSession?.llmModel || '未设置',
      界面供应商: selectedProvider.value ? selectedProvider.value.name : '未选择',
      界面模型: selectedModel.value || '未选择',
      服务器数量: serverStore.servers.length,
      已连接服务器: serverStore.connectedServers.length
    });

    // 启动消息轮询
    startMessagePolling();
  } catch (error) {
    console.error('初始化聊天页面失败', error);
    errorMessage.value = '加载会话数据失败: ' + (error instanceof Error ? error.message : '未知错误');
  } finally {
    loading.value = false;
  }
});

// 监听路由变化，处理/chat/new路径
watch(() => route.path, async (newPath) => {
  console.log('路由路径变化:', newPath);
  if (newPath === '/chat/new') {
    console.log('检测到新会话路由，正在创建新会话...');
    await createNewChat();
  }
}, { immediate: true });

// 切换MCP服务器选择
function toggleMCPServer(server) {
  if (!serverStore.isServerConnected(server.id)) {
    console.log(`服务器 ${server.id} 未连接，不执行任何操作`);
    return; // 如果服务器未连接，不执行任何操作
  }
  
  console.log(`切换服务器选择: ${server.id} (${server.name})`);
  console.log('当前选中服务器:', selectedMCPServer.value ? `${selectedMCPServer.value.id} (${selectedMCPServer.value.name})` : '无');
  
  // 如果当前已选择该服务器，则取消选择
  if (selectedMCPServer.value && selectedMCPServer.value.id === server.id) {
    console.log(`取消选择服务器: ${server.id}`);
    selectedMCPServer.value = null; // 如果已选中，则取消选择
  } else {
    console.log(`选择服务器: ${server.id} (${server.name})`);
    // 确保保存完整的服务器对象，而不仅仅是ID
    selectedMCPServer.value = {...server}; // 深拷贝服务器对象
  }
  
  // 更新工具选中状态
  updateSelectedTools();
  
  console.log('更新后选中的服务器:', selectedMCPServer.value ? `${selectedMCPServer.value.id} (${selectedMCPServer.value.name})` : '无');
  
  // 更新会话的MCP服务器设置 (如果当前有会话)
  if (sessionStore.currentSession) {
    // 获取当前选择的服务器ID（可能为null）
    const serverId = selectedMCPServer.value ? selectedMCPServer.value.id : undefined;
    console.log(`更新会话 ${sessionStore.currentSession.id} 的MCP服务器设置为: ${serverId || '无'}`);
    
    // 调用会话存储的更新方法
    sessionStore.updateSessionMCPServer(sessionStore.currentSession.id, serverId)
      .then(success => {
        if (success) {
          console.log('会话MCP服务器设置更新成功');
        } else {
          console.error('会话MCP服务器设置更新失败');
          errorMessage.value = '更新会话MCP服务器设置失败';
        }
      })
      .catch(err => {
        console.error('更新会话MCP服务器设置时发生错误:', err);
        errorMessage.value = '更新会话MCP服务器设置失败: ' + err.message;
      });
  } else {
    console.log('当前没有活跃会话，不更新会话设置');
  }
}

// 获取服务器工具列表
function getServerTools(serverId) {
  if (!serverId || !allServerTools.value) {
    return [];
  }
  
  // 添加调试日志
  console.log(`获取服务器 ${serverId} 的工具`);
  
  const tools = allServerTools.value.filter(tool => tool && tool.serverId === serverId);
  console.log(`找到 ${tools.length} 个工具`);
  
  return tools;
}

// 获取服务器工具列表
async function fetchServerTools(serverId) {
  try {
    console.log('获取服务器工具列表:', serverId);
    const response = await jsonrpc.listTools(serverId);
    console.log('服务器工具列表原始响应:', response);
    
    // 格式化工具名称，把中划线替换为下划线
    const formatToolName = (name) => {
      return name ? name.replace(/-/g, '_') : name;
    };
    
    // 处理响应格式：后端可能返回数组或者{tools:[...]}对象
    if (response && Array.isArray(response)) {
      // 后端直接返回数组
      console.log('工具列表是数组格式:', response.length);
      return response.map(tool => ({
        ...tool,
        name: formatToolName(tool.name)
      }));
    } else if (response && typeof response === 'object') {
      if (response.tools && Array.isArray(response.tools)) {
        // 后端返回{tools:[...]}格式
        console.log('工具列表在tools属性中:', response.tools.length);
        return response.tools.map(tool => ({
          ...tool,
          name: formatToolName(tool.name)
        }));
      } else {
        // 尝试将对象转换为工具数组
        console.log('尝试将对象转换为工具:', response);
        // 检查是否至少有name属性，表示这是单个工具
        if (response.name) {
          return [{
            ...response,
            name: formatToolName(response.name)
          }];
        }
      }
    }
    
    console.warn('未能识别的工具列表格式:', response);
    return [];
  } catch (error) {
    console.error('获取服务器工具列表失败:', error);
    return [];
  }
}

// 获取所有服务器的工具
async function fetchAllServerTools() {
  try {
    console.log('获取所有连接服务器的工具列表');
    const connectedServers = serverStore.connectedServers;
    console.log('已连接的服务器:', connectedServers);
    
    const toolsPromises = connectedServers.map(async (server) => {
      console.log(`正在获取服务器 ${server.id} (${server.name}) 的工具...`);
      try {
        const tools = await fetchServerTools(server.id);
        console.log(`服务器 ${server.id} 的工具:`, tools);
        return tools.map(tool => ({
          ...tool,
          serverId: server.id,
          serverName: server.name,
          selected: selectedMCPServer.value && selectedMCPServer.value.id === server.id
        }));
      } catch (error) {
        console.error(`获取服务器 ${server.id} 工具列表失败:`, error);
        return [];
      }
    });
    
    const allTools = await Promise.all(toolsPromises);
    const flattenedTools = allTools.flat();
    console.log('所有服务器工具列表 (扁平化):', flattenedTools);
    allServerTools.value = flattenedTools;
  } catch (error) {
    console.error('获取所有服务器工具列表失败:', error);
    allServerTools.value = [];
  }
}

// 更新工具选中状态
function updateSelectedTools() {
  allServerTools.value = allServerTools.value.map(tool => ({
    ...tool,
    selected: selectedMCPServer.value && selectedMCPServer.value.id === tool.serverId
  }));
}

// 清除轮询
onUnmounted(() => {
  if (polling.value !== null) {
    clearInterval(polling.value);
    polling.value = null;
  }
});

// 添加轮询相关方法
function startMessagePolling() {
  if (polling.value === null) {
    console.log('启动消息轮询');
    // 立即执行一次
    pollMessages();
    // 设置定时器
    polling.value = window.setInterval(pollMessages, pollingInterval);
  }
}

function stopMessagePolling() {
  if (polling.value !== null) {
    console.log('停止消息轮询');
    window.clearInterval(polling.value);
    polling.value = null;
  }
}

async function pollMessages() {
  // 只有当存在会话ID且不在加载状态时才轮询
  if (sessionId.value && !sessionStore.isLoadingMessages && !sessionStore.isLoadingResponse) {
    try {
      // 记录原始标题值，防止被轮询覆盖
      const originalTitle = sessionStore.currentSession?.title || '';
      console.log(`轮询消息更新...（当前标题: ${originalTitle}）`);
      
      // 仅获取消息，不刷新整个会话
      await sessionStore.fetchMessages(sessionId.value);
      
      // 确保标题没有被轮询覆盖
      if (sessionStore.currentSession && originalTitle && originalTitle !== '新会话' && originalTitle !== sessionStore.currentSession.title) {
        console.log(`检测到标题被重置（从 "${originalTitle}" 到 "${sessionStore.currentSession.title}"），恢复原始标题...`);
        await sessionStore.updateSessionTitle(sessionStore.currentSession.id, originalTitle);
      }
    } catch (error) {
      console.error('轮询消息失败:', error);
    }
  }
}

// 在监听路由变化的部分，更新轮询以对应新会话
watch(() => route.params.id, async (newId) => {
  if (newId && typeof newId === 'string') {
    // 停止现有轮询
    stopMessagePolling();
    // 加载新会话
    await loadSession(newId);
    // 重新开始轮询
    startMessagePolling();
  }
});

// 监听服务器连接状态变化，更新工具列表
watch(() => serverStore.connectedServers, async () => {
  await fetchAllServerTools();
  updateSelectedTools();
}, { deep: true });

// 连接所有服务器
async function connectAllServers() {
  if (isConnectingServers.value) return;
  
  isConnectingServers.value = true;
  try {
    for (const server of serverStore.servers) {
      if (!serverStore.connectedServers.some(s => s.id === server.id)) {
        await serverStore.connectServer(server.id);
      }
    }
  } catch (error) {
    console.error('连接服务器失败', error);
  } finally {
    isConnectingServers.value = false;
  }
}

// 同步UI和会话的LLM设置
async function syncLLMSettings() {
  console.log("同步LLM设置...");
  
  if (!sessionStore.currentSession) {
    console.log("没有活跃会话，无需同步");
    return;
  }
  
  // 记录当前状态
  console.log("同步前状态:", {
    会话LLM供应商: sessionStore.currentSession.llmProvider || '未设置',
    会话LLM模型: sessionStore.currentSession.llmModel || '未设置',
    UI供应商: selectedProvider.value ? selectedProvider.value.name : '未选择',
    UI模型: selectedModel.value || '未选择'
  });
  
  try {
    // 情况1: UI有选择，但会话没有或不一致
    if (selectedProvider.value && selectedProvider.value.name && selectedModel.value) {
      if (!sessionStore.currentSession.llmProvider || 
          !sessionStore.currentSession.llmModel ||
          sessionStore.currentSession.llmProvider !== selectedProvider.value.name ||
          sessionStore.currentSession.llmModel !== selectedModel.value) {
        
        console.log("情况1: 从UI同步到会话");
        
        // 更新会话设置
        await sessionStore.updateSessionLLM(
          sessionStore.currentSession.id,
          String(selectedProvider.value.name),
          String(selectedModel.value)
        );
        
        // 刷新会话
        await sessionStore.fetchSession(sessionStore.currentSession.id);
      }
    }
    // 情况2: 会话有设置，但UI没有选择或不一致
    else if (sessionStore.currentSession.llmProvider && sessionStore.currentSession.llmModel) {
      if (!selectedProvider.value || 
          !selectedModel.value ||
          selectedProvider.value.name !== sessionStore.currentSession.llmProvider) {
        
        console.log("情况2: 从会话同步到UI");
        
        // 查找供应商
        const providerObj = providerStore.providers.find(
          p => p.name === sessionStore.currentSession?.llmProvider
        );
        
        if (providerObj) {
          // 更新UI
          selectedProvider.value = providerObj;
          await updateProviderModels(providerObj);
          selectedModel.value = sessionStore.currentSession.llmModel;
        } else {
          console.error(`找不到提供商: ${sessionStore.currentSession.llmProvider}`);
        }
      }
    }
    
    // 记录同步后状态
    console.log("同步后状态:", {
      会话LLM供应商: sessionStore.currentSession.llmProvider || '未设置',
      会话LLM模型: sessionStore.currentSession.llmModel || '未设置',
      UI供应商: selectedProvider.value ? selectedProvider.value.name : '未选择',
      UI模型: selectedModel.value || '未选择'
    });
  } catch (error) {
    console.error("同步LLM设置失败:", error);
    throw error;
  }
}

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim()) return;
  
  errorMessage.value = '';
  
  try {
    console.log('准备发送消息:');
    
    // 如果没有当前会话，自动创建一个
    if (!sessionStore.currentSession) {
      console.log('没有当前会话，创建新会话');
      await createNewChat();
      
      // 如果创建后仍然没有会话，则无法发送
      if (!sessionStore.currentSession) {
        throw new Error('创建会话失败，无法发送消息');
      }
    }
    
    console.log('当前会话:', sessionStore.currentSession);
    console.log('提供商和模型:', selectedProvider.value, selectedModel.value);
    
    // 检查LLM提供商和模型是否已选择并有效
    if (!selectedProvider.value || !selectedProvider.value.name) {
      errorMessage.value = '请先选择LLM提供商后再发送消息';
      console.error('发送失败: 未选择LLM提供商或无效的提供商', selectedProvider.value);
      return;
    }
    
    if (!selectedModel.value) {
      errorMessage.value = '请先选择LLM模型后再发送消息';
      console.error('发送失败: 未选择LLM模型或无效的模型', selectedModel.value);
      return;
    }
    
    // 确保会话中的LLM设置与当前选择的一致
    if (sessionStore.currentSession) {
      const providerName = selectedProvider.value.name;
      
      if (sessionStore.currentSession.llmProvider !== providerName || 
          sessionStore.currentSession.llmModel !== selectedModel.value) {
        console.log('当前会话的LLM设置与选择不一致，正在更新...');
        console.log(`更新前: provider=${sessionStore.currentSession.llmProvider}, model=${sessionStore.currentSession.llmModel}`);
        console.log(`更新后: provider=${providerName}, model=${selectedModel.value}`);
        
        await sessionStore.updateSessionLLM(
          sessionStore.currentSession.id, 
          providerName, 
          selectedModel.value
        );
        
        // 确认更新成功
        console.log(`更新后的会话LLM设置: provider=${sessionStore.currentSession.llmProvider}, model=${sessionStore.currentSession.llmModel}`);
      }
    }
    
    // 确保MCP服务器设置正确
    if (sessionStore.currentSession) {
      const serverIdInSession = sessionStore.currentSession.mcpServerId;
      const selectedServerId = selectedMCPServer.value?.id;
      
      console.log('MCP服务器检查:');
      console.log(`- 会话中的serverId: ${serverIdInSession}`);
      console.log(`- 当前选择的serverId: ${selectedServerId}`);
      
      // 如果不一致，更新会话的MCP服务器设置
      if (serverIdInSession !== selectedServerId) {
        console.log('MCP服务器设置不一致，正在同步...');
        await sessionStore.updateSessionMCPServer(
          sessionStore.currentSession.id, 
          selectedServerId
        );
      }
    }
    
    const message = userInput.value;
    userInput.value = '';
    await sessionStore.sendMessage(message);
  } catch (error) {
    console.error('发送消息失败:', error);
    errorMessage.value = error instanceof Error ? error.message : '发送消息失败';
  }
};

// 加载现有会话
async function loadSession(id: string) {
  if (!id) return;
  console.log("加载会话:", id);
  
  try {
    // 加载会话详情
    await sessionStore.fetchSession(id);
    console.log("会话加载成功:", sessionStore.currentSession);
    
    // 清除任何潜在的错误状态
    errorMessage.value = '';
    sessionStore.clearError();
    
    // 设置选中的供应商和模型
    if (sessionStore.currentSession?.llmProvider) {
      const providerObj = providerStore.providers.find(
        p => p.name === sessionStore.currentSession?.llmProvider
      );
      if (providerObj) {
        selectedProvider.value = providerObj;
        await updateProviderModels(providerObj);
        selectedModel.value = sessionStore.currentSession?.llmModel || '';
      }
    }
    
    // 设置选中的MCP服务器
    if (sessionStore.currentSession?.mcpServerId) {
      const serverId = sessionStore.currentSession.mcpServerId;
      console.log(`会话有MCP服务器设置: ${serverId}`);
      
      const serverObj = serverStore.servers.find(s => s.id === serverId);
      if (serverObj) {
        console.log(`找到服务器对象: ${serverObj.id} (${serverObj.name})`);
        
        // 确保服务器已连接
        if (!serverStore.isServerConnected(serverId)) {
          console.log(`服务器 ${serverId} 未连接，尝试连接`);
          await serverStore.connectServer(serverId);
        }
        
        // 深拷贝服务器对象以避免引用问题
        selectedMCPServer.value = {...serverObj};
        console.log(`已设置selectedMCPServer: ${selectedMCPServer.value.id} (${selectedMCPServer.value.name})`);
        
        // 获取服务器工具列表
        await fetchServerTools(serverId);
      } else {
        console.log(`无法找到服务器对象: ${serverId}，可用服务器:`, serverStore.servers);
      }
    } else {
      console.log("会话没有MCP服务器设置");
      selectedMCPServer.value = null;
      serverTools.value = [];
    }
    
    // 确保处于活跃状态
    sessionStore.resetSessionTimeout();
    
    // 加载所有服务器的工具列表
    await fetchAllServerTools();
    updateSelectedTools();
    
  } catch (error) {
    console.error("加载会话失败:", error);
    errorMessage.value = '加载会话失败';
  }
}

// 创建新聊天
const createNewChat = async () => {
  try {
    errorMessage.value = '';
    console.log('创建新会话');
    
    // 清除当前会话和消息
    sessionStore.currentSession = null;
    sessionStore.messages.value = [];
    sessionStore.clearError();
    
    // 获取当前提供商和模型信息
    let providerName = null;
    let modelName = null;
    
    if (selectedProvider.value && selectedProvider.value.name) {
      providerName = selectedProvider.value.name;
    }
    
    if (selectedModel.value) {
      modelName = selectedModel.value;
    }
    
    console.log(`使用以下设置创建新会话: provider=${providerName || '未设置'}, model=${modelName || '未设置'}`);
    
    // 创建新会话，如果有选择提供商和模型，则提供这些参数
    const newSession = await sessionStore.createSession(
      '新会话',
      providerName || undefined,
      modelName || undefined,
      selectedMCPServer.value?.id
    );
    
    console.log('创建的新会话:', newSession);
    
    if (newSession && newSession.id) {
      // 使用router导航到新会话
      await router.push({ 
        name: 'chat', 
        params: { 
          id: newSession.id
        }
      });
      
      console.log('已导航到新会话页面');
    } else {
      console.error('创建会话失败，返回数据:', newSession);
      errorMessage.value = '创建新会话失败';
    }
  } catch (error) {
    console.error('创建新会话失败:', error);
    errorMessage.value = error instanceof Error ? error.message : '创建新会话失败';
  }
};

// 加载可用模型
const loadAvailableModels = async () => {
  availableModels.value = [];
  
  if (!selectedProvider.value || !selectedProvider.value.name) {
    console.log('没有选择提供商，无法加载模型');
    return;
  }
  
  const providerName = selectedProvider.value.name;
  
  try {
    console.log(`正在为提供商 ${providerName} 加载模型列表...`);
    loadingModels.value = true;
    
    const response = await jsonrpc.getProviderModels(providerName);
    
    if (response && response.models) {
      console.log(`获取到 ${response.models.length} 个模型:`, response.models);
      availableModels.value = response.models;
      
      // 如果已设置过模型且该模型存在于列表中，则保持选择
      if (selectedModel.value && availableModels.value.includes(selectedModel.value)) {
        console.log(`保持当前选择的模型: ${selectedModel.value}`);
      } 
      // 如果当前会话有模型且在列表中，则选择它
      else if (sessionStore.currentSession?.llmModel && 
               availableModels.value.includes(sessionStore.currentSession.llmModel)) {
        selectedModel.value = sessionStore.currentSession.llmModel;
        console.log(`从会话中恢复模型选择: ${selectedModel.value}`);
      } 
      // 如果有模型但不在列表中，选择第一个
      else if (availableModels.value.length > 0) {
        selectedModel.value = availableModels.value[0];
        console.log(`自动选择第一个模型: ${selectedModel.value}`);
      } else {
        selectedModel.value = null;
        console.log('没有可用的模型');
      }
    } else {
      console.error('获取模型列表失败，返回值无效:', response);
      errorMessage.value = '获取模型列表失败，请检查提供商配置';
      availableModels.value = [];
      selectedModel.value = null;
    }
  } catch (error) {
    console.error('加载模型列表失败:', error);
    errorMessage.value = error instanceof Error ? error.message : '加载模型列表失败';
    availableModels.value = [];
    selectedModel.value = null;
  } finally {
    loadingModels.value = false;
  }
};

// 提供商变更处理
const handleProviderChange = async (provider) => {
  console.log('提供商变更:', provider);
  errorMessage.value = '';
  
  // 如果选择了undefined或null，重置选择
  if (!provider) {
    console.log('重置提供商选择');
    selectedProvider.value = null;
    selectedModel.value = null;
    availableModels.value = [];
    return;
  }
  
  try {
    // 设置选中的提供商
    selectedProvider.value = provider;
    const providerName = provider.name;
    console.log(`选择了提供商: ${providerName}`);
    
    // 加载该提供商的模型
    await loadAvailableModels();
    
    // 如果有当前会话，更新会话的LLM设置
    if (sessionStore.currentSession) {
      // 如果提供商变了，需要更新会话
      if (sessionStore.currentSession.llmProvider !== providerName) {
        console.log(`更新会话提供商从 ${sessionStore.currentSession.llmProvider} 到 ${providerName}`);
        
        // 选择第一个可用模型
        const modelToUse = selectedModel.value || (availableModels.value.length > 0 ? availableModels.value[0] : null);
        
        if (modelToUse) {
          console.log(`更新会话模型为: ${modelToUse}`);
          await sessionStore.updateSessionLLM(
            sessionStore.currentSession.id,
            providerName,
            modelToUse
          );
          
          // 确认更新成功并设置本地状态
          selectedModel.value = modelToUse;
          console.log('会话LLM设置已更新');
        } else {
          console.error('无法更新会话LLM设置：没有可用的模型');
          errorMessage.value = '无法选择模型，当前提供商没有可用模型';
        }
      }
    }
  } catch (error) {
    console.error('提供商变更处理失败:', error);
    errorMessage.value = error instanceof Error ? error.message : '提供商变更处理失败';
  }
};

// 开始编辑标题
function startEditingTitle() {
  if (sessionStore.currentSession) {
    isEditingTitle.value = true;
    editedTitle.value = sessionStore.currentSession.title || t('chat.newChat');
    nextTick(() => {
      titleInput.value?.focus();
    });
  }
}

// 取消编辑标题
function cancelEditTitle() {
  isEditingTitle.value = false;
  editedTitle.value = sessionStore.currentSession?.title || t('chat.newChat');
}

// 保存标题
async function saveTitle() {
  if (isEditingTitle.value) {
    isEditingTitle.value = false;
    const newTitle = editedTitle.value.trim();
    
    if (newTitle && newTitle !== (sessionStore.currentSession?.title || '新会话')) {
      if (sessionStore.currentSession) {
        console.log(`保存新标题: "${newTitle}"`);
        
        try {
          // 先手动更新DOM
          const titleElement = document.querySelector('.chat-title');
          if (titleElement) {
            titleElement.textContent = newTitle;
            console.log('已直接更新DOM标题为:', newTitle);
          }
          
          // 更新反应式状态
          titleUpdateKey.value = Date.now();
          
          console.log('调用sessionStore.updateSessionTitle，sessionId:', sessionStore.currentSession.id);
          // 调用store方法更新标题
          const success = await sessionStore.updateSessionTitle(
            sessionStore.currentSession.id,
            newTitle
          );
          
          console.log('标题更新API调用结果:', success ? '成功' : '失败');
          
          if (!success) {
            console.warn('标题更新API调用失败，将尝试刷新会话获取最新状态');
            await sessionStore.refreshCurrentSession();
          } else {
            // 无论API调用成功与否，确保本地标题已经更新
            if (sessionStore.currentSession) {
              // 我们在sessionStore中已经更新了状态，这里只是二次确认
              const currentTitle = sessionStore.currentSession.title;
              if (currentTitle !== newTitle) {
                console.log(`检测到标题不一致，强制更新（当前:${currentTitle}，预期:${newTitle}）`);
                // 强制设置会话标题
                sessionStore.currentSession = {
                  ...sessionStore.currentSession,
                  title: newTitle
                };
                
                // 再次强制更新UI
                titleUpdateKey.value = Date.now();
              }
            }
          }
        } catch (error) {
          console.error('更新标题时发生错误:', error);
          
          // 即使发生错误，也要确保本地UI已更新
          if (sessionStore.currentSession) {
            sessionStore.currentSession.title = newTitle;
            titleUpdateKey.value = Date.now();
            
            // 尝试重新加载会话
            setTimeout(() => {
              sessionStore.refreshCurrentSession().catch(e => 
                console.error('刷新会话失败:', e)
              );
            }, 500);
          }
        }
      }
    } else {
      console.log('标题未变更，保持不变');
    }
  }
}

// 使用AI自动生成标题
async function autoGenerateTitle() {
  if (!sessionStore.currentSession) {
    console.error('无法生成标题：当前没有活跃会话');
    errorMessage.value = '无法生成标题：当前没有活跃会话';
    return;
  }
  
  if (sessionStore.messages.length < 2) {
    console.error('对话长度不足，无法生成标题');
    errorMessage.value = '对话长度不足，无法生成标题';
    return;
  }
  
  try {
    loading.value = true;
    errorMessage.value = '';
    console.log('开始手动生成标题...');
    
    // 显示临时加载状态
    const originalTitle = sessionStore.currentSession?.title || '';
    await nextTick();
    
    // 添加重试机制
    let retryCount = 0;
    const maxRetries = 2;
    let success = false;
    
    while (retryCount <= maxRetries && !success) {
      try {
        // 调用会话存储的生成标题方法
        success = await sessionStore.generateSessionTitle(sessionStore.currentSession.id);
        
        if (success) {
          console.log('标题生成成功！');
          // 确保UI更新 - 强制刷新标题
          await forceRefreshTitle();
          break;
        } else if (retryCount < maxRetries) {
          retryCount++;
          console.log(`标题生成失败，尝试重试 (${retryCount}/${maxRetries})...`);
          await new Promise(resolve => setTimeout(resolve, 500));
        } else {
          console.error('多次尝试后生成标题失败');
          errorMessage.value = '生成标题失败，请稍后再试';
        }
      } catch (err) {
        console.error(`第 ${retryCount + 1} 次尝试生成标题出错:`, err);
        if (retryCount < maxRetries) {
          retryCount++;
          await new Promise(resolve => setTimeout(resolve, 500));
        } else {
          throw err;
        }
      }
    }
  } catch (error) {
    console.error('生成标题时发生错误', error);
    errorMessage.value = '生成标题失败：' + (error instanceof Error ? error.message : '未知错误');
  } finally {
    loading.value = false;
  }
}

// 获取角色名称
function getRoleName(role: string): string {
  switch (role) {
    case 'user': return '用户';
    case 'assistant': return '助手';
    case 'system': return '系统';
    case 'tool': return '工具';
    case 'function': return '函数';
    default: return role || '未知';
  }
}

// 格式化时间戳
function formatTimestamp(timestamp: number | string | null) {
  if (!timestamp) {
    // 如果没有时间戳，返回当前时间
    return format(new Date(), 'yyyy-MM-dd HH:mm:ss');
  }
  
  try {
    // 检查是否是1970年的时间戳（表示无效时间）
    const date = new Date(typeof timestamp === 'number' ? timestamp : parseInt(timestamp as string));
    if (date.getFullYear() === 1970) {
      // 如果是1970年的时间戳，返回当前时间
      return format(new Date(), 'yyyy-MM-dd HH:mm:ss');
    }
    
    // 正常格式化时间戳
    return format(date, 'yyyy-MM-dd HH:mm:ss');
  } catch (e) {
    console.error('格式化时间戳失败:', e, timestamp);
    // 出错时返回当前时间
    return format(new Date(), 'yyyy-MM-dd HH:mm:ss');
  }
}

// 获取服务器状态颜色
function getServerStatusColor(server: any): string {
  if (!server) return 'grey';
  
  switch (server.status) {
    case 'connected': return 'success';
    case 'disconnected': return 'grey';
    case 'error': return 'error';
    default: return 'grey';
  }
}

// 更新LLM供应商的可用模型
async function updateProviderModels(provider: any) {
  if (!provider) {
    availableModels.value = [];
    selectedModel.value = '';
    return;
  }
  
  try {
    loadingModels.value = true;
    
    // 解析provider名称，确保它是有效的字符串
    const providerName = typeof provider === 'string' ? provider : (provider.name || '');
    if (!providerName || providerName === 'undefined' || providerName === 'null') {
      console.error(`无效的提供商名称: ${providerName}`);
      throw new Error(`无效的提供商名称: ${providerName}`);
    }
    
    console.log(`更新提供商模型: ${providerName}`);
    
    // 获取供应商模型列表
    let modelList: string[] = [];
    
    // 如果provider是对象，直接使用models属性
    if (typeof provider === 'object' && provider.models && Array.isArray(provider.models)) {
      modelList = provider.models.filter(m => m && typeof m === 'string');
    } else {
      // 否则通过API获取模型
      modelList = await providerStore.getProviderModels(providerName);
    }
    
    // 确保模型列表是有效的
    if (!modelList || !Array.isArray(modelList) || modelList.length === 0) {
      console.error(`无法获取提供商 ${providerName} 的模型列表`);
      availableModels.value = [];
      selectedModel.value = '';
      throw new Error(`无法获取提供商 ${providerName} 的模型列表`);
    }
    
    console.log(`获取到 ${modelList.length} 个模型:`, modelList);
    
    // 设置可用模型列表
    availableModels.value = modelList;
    
    // 选择第一个有效模型
    const firstValidModel = modelList.find(m => m && m !== 'undefined' && m !== 'null');
    if (firstValidModel) {
      selectedModel.value = firstValidModel;
    } else {
      console.error('没有有效的模型可供选择');
      selectedModel.value = '';
      throw new Error('没有有效的模型可供选择');
    }
    
    // 如果当前会话存在，更新会话的LLM设置
    if (sessionStore.currentSession) {
      try {
        // 保存当前会话的MCP服务器设置
        const currentMcpServerId = sessionStore.currentSession.mcpServerId;
        
        await sessionStore.updateSession({
          ...sessionStore.currentSession,
          llmProvider: providerName,
          llmModel: selectedModel.value,
          // 保持MCP服务器ID不变
          mcpServerId: currentMcpServerId
        });
        
        console.log(`已更新会话LLM设置为: ${providerName}/${selectedModel.value}, MCP服务器ID保持为: ${currentMcpServerId || '无'}`);
      } catch (error) {
        console.error('更新会话LLM设置失败', error);
        throw error;
      }
    }
  } catch (error) {
    console.error('更新供应商模型失败', error);
    errorMessage.value = `更新供应商模型失败: ${error.message || '未知错误'}`;
    availableModels.value = [];
    selectedModel.value = '';
    throw error;
  } finally {
    loadingModels.value = false;
  }
}

// 格式化消息内容
const formatMessageContent = (content) => {
  if (!content) return '';
  
  // 添加日志帮助调试
  console.log('格式化消息内容:', typeof content, content?.length || 0);
  
  // 尝试判断content是否是JSON字符串，如果是则格式化显示
  try {
    if (typeof content === 'string' && (content.startsWith('{') || content.startsWith('['))) {
      const parsedJson = JSON.parse(content);
      // 如果成功解析为JSON，返回格式化的JSON
      return `<pre class="language-json">${JSON.stringify(parsedJson, null, 2)}</pre>`;
    }
  } catch (e) {
    // 解析失败，非JSON字符串，继续按照Markdown处理
    console.log('非JSON字符串，按Markdown处理');
  }
  
  // 处理markdown内容
  const rendered = md.render(String(content));
  console.log('Markdown渲染结果长度:', rendered.length);
  return rendered;
};

// 确保MCP服务器连接初始化
async function ensureMCPServerConnections() {
  try {
    console.log("确保MCP服务器连接...");
    
    // 加载服务器列表
    await serverStore.fetchServers();
    
    // 获取当前已连接的服务器
    await serverStore.fetchConnectedServers();
    
    // 如果有服务器但没有连接，自动连接第一个
    if (serverStore.servers.length > 0 && serverStore.connectedServers.length === 0) {
      console.log("没有已连接的服务器，尝试连接第一个");
      const firstServer = serverStore.servers[0];
      await serverStore.connectServer(firstServer.id);
    }
    
    // 加载所有已连接服务器的工具列表
    await fetchAllServerTools();
    
    console.log(`当前已连接的服务器: ${serverStore.connectedServers.length}个`);
  } catch (error) {
    console.error("初始化MCP服务器连接失败:", error);
    errorMessage.value = '初始化服务器连接失败';
  }
}

// 重置会话
const resetSession = async () => {
  try {
    sessionStore.resetSessionTimeout();
    // 重新加载当前会话的消息
    if (sessionStore.currentSession?.id) {
      await sessionStore.fetchMessages(sessionStore.currentSession.id);
    }
  } catch (error) {
    console.error('重置会话失败', error);
  }
};

// 关闭错误提示
const dismissError = () => {
  sessionStore.clearError();
};

// 格式化工具调用参数
function formatToolCallArguments(args: string | null) {
  if (!args) return '';
  
  try {
    const parsedJson = JSON.parse(args);
    return JSON.stringify(parsedJson, null, 2);
  } catch (e) {
    return args;
  }
}

// 处理回车键 - 直接发送消息
const handleEnterKey = (event) => {
  // 如果文本不为空，则发送消息
  if (userInput.value.trim()) {
    sendMessage();
  }
};

// 获取服务器资源列表
function getServerResources(serverId) {
  if (!serverId || !allServerResources.value) {
    return [];
  }
  
  console.log(`获取服务器 ${serverId} 的资源`);
  
  const resources = allServerResources.value.filter(resource => resource && resource.serverId === serverId);
  console.log(`找到 ${resources.length} 个资源`);
  
  return resources;
}

// 获取服务器资源列表
async function fetchServerResources(serverId) {
  try {
    console.log('获取服务器资源列表:', serverId);
    const response = await jsonrpc.listResources(serverId);
    console.log('服务器资源列表原始响应:', response);
    
    // 处理响应格式
    if (response && Array.isArray(response)) {
      // 直接返回数组
      console.log('资源列表是数组格式:', response.length);
      return response;
    } else if (response && typeof response === 'object') {
      if (response.resources && Array.isArray(response.resources)) {
        // 返回{resources:[...]}格式
        console.log('资源列表在resources属性中:', response.resources.length);
        return response.resources;
      } else {
        // 尝试将对象转换为资源数组
        console.log('尝试将对象转换为资源:', response);
        // 检查是否至少有name属性，表示这是单个资源
        if (response.name) {
          return [response];
        }
      }
    }
    
    console.warn('未能识别的资源列表格式:', response);
    return [];
  } catch (error) {
    console.error('获取服务器资源列表失败:', error);
    return [];
  }
}

// 获取所有服务器的资源
async function fetchAllServerResources() {
  try {
    console.log('获取所有连接服务器的资源列表');
    const connectedServers = serverStore.connectedServers;
    console.log('已连接的服务器:', connectedServers);
    
    const resourcesPromises = connectedServers.map(async (server) => {
      console.log(`正在获取服务器 ${server.id} (${server.name}) 的资源...`);
      try {
        const resources = await fetchServerResources(server.id);
        console.log(`服务器 ${server.id} 的资源:`, resources);
        return resources.map(resource => ({
          ...resource,
          serverId: server.id,
          serverName: server.name
        }));
      } catch (error) {
        console.error(`获取服务器 ${server.id} 资源列表失败:`, error);
        return [];
      }
    });
    
    const allResources = await Promise.all(resourcesPromises);
    const flattenedResources = allResources.flat();
    console.log('所有服务器资源列表 (扁平化):', flattenedResources);
    allServerResources.value = flattenedResources;
  } catch (error) {
    console.error('获取所有服务器资源列表失败:', error);
    allServerResources.value = [];
  }
}

// 获取服务器Prompt列表
function getServerPrompts(serverId) {
  if (!serverId || !allServerPrompts.value) {
    return [];
  }
  
  console.log(`获取服务器 ${serverId} 的prompts`);
  
  const prompts = allServerPrompts.value.filter(prompt => prompt && prompt.serverId === serverId);
  console.log(`找到 ${prompts.length} 个prompts`);
  
  return prompts;
}

// 获取服务器Prompt列表
async function fetchServerPrompts(serverId) {
  try {
    console.log('获取服务器Prompt列表:', serverId);
    const response = await jsonrpc.call('mcp.list_prompts', { server_id: serverId });
    console.log('服务器Prompt列表原始响应:', response);
    
    // 处理响应格式
    if (response && Array.isArray(response)) {
      // 直接返回数组
      console.log('Prompt列表是数组格式:', response.length);
      return response;
    } else if (response && typeof response === 'object') {
      if (response.prompts && Array.isArray(response.prompts)) {
        // 返回{prompts:[...]}格式
        console.log('Prompt列表在prompts属性中:', response.prompts.length);
        return response.prompts;
      } else {
        // 尝试将对象转换为Prompt数组
        console.log('尝试将对象转换为Prompt:', response);
        // 检查是否至少有name属性，表示这是单个Prompt
        if (response.name) {
          return [response];
        }
      }
    }
    
    console.warn('未能识别的Prompt列表格式:', response);
    return [];
  } catch (error) {
    console.error('获取服务器Prompt列表失败:', error);
    return [];
  }
}

// 获取所有服务器的Prompts
async function fetchAllServerPrompts() {
  try {
    console.log('获取所有连接服务器的Prompt列表');
    const connectedServers = serverStore.connectedServers;
    console.log('已连接的服务器:', connectedServers);
    
    const promptsPromises = connectedServers.map(async (server) => {
      console.log(`正在获取服务器 ${server.id} (${server.name}) 的Prompts...`);
      try {
        const prompts = await fetchServerPrompts(server.id);
        console.log(`服务器 ${server.id} 的Prompts:`, prompts);
        return prompts.map(prompt => ({
          ...prompt,
          serverId: server.id,
          serverName: server.name
        }));
      } catch (error) {
        console.error(`获取服务器 ${server.id} Prompt列表失败:`, error);
        return [];
      }
    });
    
    const allPrompts = await Promise.all(promptsPromises);
    const flattenedPrompts = allPrompts.flat();
    console.log('所有服务器Prompt列表 (扁平化):', flattenedPrompts);
    allServerPrompts.value = flattenedPrompts;
  } catch (error) {
    console.error('获取所有服务器Prompt列表失败:', error);
    allServerPrompts.value = [];
  }
}

// 模型变更处理
const handleModelChange = async (model) => {
  console.log('模型变更:', model);
  errorMessage.value = '';
  
  if (!model) {
    console.log('重置模型选择');
    selectedModel.value = null;
    return;
  }
  
  try {
    selectedModel.value = model;
    console.log(`选择了模型: ${model}`);
    
    // 如果有当前会话，更新会话的模型设置
    if (sessionStore.currentSession && selectedProvider.value) {
      const providerName = selectedProvider.value.name;
      
      // 如果模型变了，需要更新会话
      if (sessionStore.currentSession.llmModel !== model) {
        console.log(`更新会话模型从 ${sessionStore.currentSession.llmModel} 到 ${model}`);
        
        await sessionStore.updateSessionLLM(
          sessionStore.currentSession.id,
          providerName,
          model
        );
        
        console.log('会话模型设置已更新');
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模型变更处理失败';
  }
};
</script>

<style lang="scss">
.chat-container {
  height: calc(100vh - 64px);
  padding: 16px;
  background-color: #f8f9fa;
  position: relative;
}

.borderless-header {
  background-color: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border-radius: 8px;
}

.title-container {
  display: flex;
  align-items: center;
}

.chat-title {
  font-size: 1.2rem;
  margin-right: 8px;
  cursor: pointer;
  font-weight: 500;
}

.title-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.title-container:hover .title-actions {
  opacity: 1;
}

.title-input {
  font-size: 1.2rem;
  border: none;
  border-bottom: 1px solid #1976d2;
  outline: none;
  background: transparent;
  padding: 4px 8px;
  width: 250px;
}

.server-chips-container {
  display: flex;
  flex-wrap: wrap;
  max-width: 100%;
  overflow-x: auto;
  padding: 2px 0;
}

.server-chip {
  font-size: 13px !important;
  min-height: 28px !important;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0 12px !important;
  display: inline-flex !important;
  align-items: center !important;
  
  &.selected-server {
    box-shadow: 0 0 0 1px currentColor;
    font-weight: 500;
  }
}

.server-name {
  font-weight: 500;
  display: inline;
  white-space: nowrap;
}

.server-tools-list, .server-resources-list, .server-prompts-list {
  font-size: 0.75rem;
  opacity: 0.8;
  color: inherit;
}

.server-resources-list {
  font-style: italic;
}

.server-prompts-list {
  font-weight: 500;
}

.message-area {
  background-color: transparent;
  margin-bottom: 56px; /* 减小为底部输入框留出的空间 */
  position: relative; /* 添加相对定位 */
  flex-grow: 1;
  overflow-y: auto;
  z-index: 5; /* 确保消息区域的z-index高于思考动画 */
}

.message-input-container {
  position: fixed;
  bottom: 10px;
  left: 256px; /* 240px侧边栏宽度 + 16px左边距 */
  right: 16px;
  z-index: 10;
}

.input-area {
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 20px; /* 减小圆角 */
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.3s ease;
  
  &:hover {
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.07);
  }
}

.input-wrapper {
  display: flex;
  align-items: center;
  padding: 4px;
  border-radius: 12px;
  background-color: rgb(var(--v-theme-surface));
  transition: all 0.2s ease;
  
  &:focus-within {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
  }
}

.message-input {
  flex-grow: 1;
  
  ::v-deep(.v-field__field) {
    padding-top: 4px !important;
  }
}

.send-button {
  margin-right: 4px;
  transition: transform 0.2s ease;
  
  &:hover:not(:disabled) {
    transform: scale(1.1);
  }
}

.chat-message {
  margin-bottom: 12px;
  max-width: 85%;
  border-radius: 12px;
  padding: 10px 14px;
  word-break: break-word;
  transition: transform 0.1s ease;
  position: relative; /* 添加相对定位 */
  z-index: 10; /* 确保消息的z-index高于背景元素 */
  
  pre {
    margin: 0;
    padding: 8px;
    border-radius: 4px;
    background-color: rgba(0, 0, 0, 0.05);
    font-size: 0.9em;
    overflow-x: auto;
  }
  
  code {
    font-family: 'Fira Code', monospace;
    font-size: 0.9em;
    background-color: rgba(0, 0, 0, 0.05);
    padding: 2px 4px;
    border-radius: 4px;
  }
}

.user-message {
  background-color: #ffffff;
  color: #000000;
  align-self: flex-end;
  margin-left: auto;
  border-bottom-right-radius: 4px;
  font-size: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.assistant-message {
  background-color: #f5f5f5;
  color: #000000;
  align-self: flex-start;
  margin-right: auto;
  border-bottom-left-radius: 4px;
  font-size: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.system-message, .tool-message {
  background-color: rgba(0, 0, 0, 0.03);
  align-self: flex-start;
  margin-right: auto;
  border-left: 2px solid rgb(var(--v-theme-secondary));
  font-size: 13px;
  opacity: 0.9;
}

.message-content {
  padding: 4px 0;
  line-height: 1.4;
  font-size: 0.9rem;
  word-break: break-all;
  overflow-wrap: break-word;
}

.tool-calls {
  margin-top: 8px;
}

.tool-call-item {
  background-color: rgba(25, 118, 210, 0.05);
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 8px;
  font-size: 13px;
  border-left: 2px solid #1976d2;
}

.tool-call-args, .tool-result-content {
  background-color: rgba(255, 255, 255, 0.9);
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 8px;
  font-family: 'Fira Code', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: break-word;
}

.tool-result-item {
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 8px;
  font-size: 13px;
}

.tool-success {
  background-color: rgba(76, 175, 80, 0.05);
  border-left: 2px solid #4caf50;
}

.tool-error {
  background-color: rgba(244, 67, 54, 0.05);
  border-left: 2px solid #f44336;
}

.empty-message {
  opacity: 0.7;
}

.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  font-size: 0.9rem;
  word-break: break-all;
  overflow-wrap: break-word;
}

.markdown-body p {
  margin: 0.5em 0;
}

.markdown-body h1, .markdown-body h2, .markdown-body h3, 
.markdown-body h4, .markdown-body h5, .markdown-body h6 {
  margin-top: 0.8em;
  margin-bottom: 0.5em;
  font-size: 1.1em;
  line-height: 1.3;
}

.markdown-body h1 { font-size: 1.3em; }
.markdown-body h2 { font-size: 1.2em; }
.markdown-body h3 { font-size: 1.1em; }
.markdown-body h4, .markdown-body h5, .markdown-body h6 { font-size: 1em; }

.markdown-body pre {
  background-color: rgba(245, 247, 250, 0.6);
  border-radius: 6px;
  padding: 8px;
  overflow-x: auto;
  border: none;
  margin: 0.5em 0;
  font-size: 0.85em;
  white-space: pre-wrap;
  word-break: break-all;
}

.markdown-body code {
  font-family: 'Fira Code', monospace, 'Courier New', Courier;
  font-size: 0.85em;
  padding: 1px 3px;
  border-radius: 3px;
  background-color: rgba(0, 0, 0, 0.03);
}

.markdown-body pre code {
  padding: 0;
  background-color: transparent;
  word-break: break-all;
  overflow-wrap: break-word;
}

.markdown-body blockquote {
  border-left: 3px solid #e0e0e0;
  padding-left: 16px;
  margin-left: 0;
  color: #616161;
}

.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}

.markdown-body table th,
.markdown-body table td {
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 8px;
  text-align: left;
}

.markdown-body table th {
  background-color: rgba(0, 0, 0, 0.02);
}

.markdown-body img {
  max-width: 100%;
  border-radius: 4px;
}

.tool-chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  max-width: 100%;
  overflow-x: auto;
  max-height: 60px;
  overflow-y: auto;
  padding: 2px;
}

.tool-chip {
  cursor: help;
  transition: all 0.2s ease;
  min-height: 22px !important;
  font-size: 10px !important;
}

.tool-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.time-stamp {
  font-size: 0.7rem;
  opacity: 0.7;
}

.session-timeout-alert, .loading-response {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 100;
  max-width: 400px;
  padding: 10px;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  gap: 10px;
}

.thinking-overlay {
  position: absolute;
  top: 50px;
  left: 0;
  right: 0;
  bottom: 56px;
  background-color: rgba(255, 255, 255, 0);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2;
  pointer-events: none;
}

.thinking-container {
  background-color: rgba(255, 255, 255, 0.8); /* 降低背景不透明度 */
  padding: 16px 28px;
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 16px;
  animation: pulse 2s infinite ease-in-out, slideUp 0.5s ease forwards;
  pointer-events: auto;
}

@keyframes pulse {
  0% { box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15); }
  50% { box-shadow: 0 8px 32px rgba(25, 118, 210, 0.25); }
  100% { box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15); }
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background-color: #f0f7ff;
  border-radius: 50%;
  position: relative;
  box-shadow: 0 0 0 rgba(25, 118, 210, 0.4);
  animation: ripple 2s infinite;

  span {
    display: block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #1976d2;
    position: absolute;
    animation: typing 1.5s infinite ease-in-out;

    &:nth-child(1) {
      left: 12px;
      animation-delay: 0s;
    }

    &:nth-child(2) {
      left: 20px;
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      left: 28px;
      animation-delay: 0.4s;
    }
  }
}

@keyframes ripple {
  0% {
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.3);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(25, 118, 210, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0);
  }
}

.thinking-container p {
  font-size: 1rem;
  font-weight: 500;
  color: #333;
  margin: 0;
}

@keyframes typing {
  0% {
    transform: translateY(0px);
    opacity: 0.2;
  }
  50% {
    transform: translateY(-10px);
    opacity: 1;
  }
  100% {
    transform: translateY(0px);
    opacity: 0.2;
  }
}

.reset-session-btn {
  background-color: #007bff;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 14px;

  &:hover {
    background-color: #0056b3;
  }
}

.disabled {
  opacity: 0.7;
  cursor: not-allowed;
  
  textarea, button {
    cursor: not-allowed;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.role-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

/* 自动重命名开关样式 */
.auto-rename-switch {
  display: flex;
  align-items: center;
  margin-left: 15px;
  font-size: 0.85rem;
}

.switch-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.switch-label input {
  margin-right: 5px;
}

.switch-text {
  color: #666;
}

/* LLM提供商和模型选择器 */
.provider-model-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}

/* LLM提供商选择器 */
.provider-selector {
  flex: 1;
  min-width: 200px;
}

/* 模型选择器 */
.model-selector {
  flex: 1;
  min-width: 200px;
}

/* 加载状态 */
.loading-providers {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 错误信息 */
.error-message {
  color: #f44336;
  font-size: 0.8rem;
  margin-top: 4px;
}
</style>
