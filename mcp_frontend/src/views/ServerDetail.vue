<template>
  <v-container>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">服务器详情</h1>
      <v-spacer></v-spacer>
      <v-btn to="/servers" prepend-icon="mdi-arrow-left" color="primary">
        返回服务器列表
      </v-btn>
    </div>
    
    <!-- 服务器基本信息 -->
    <v-card class="mb-4">
      <v-card-title>基本信息</v-card-title>
      <v-card-text v-if="loading">
        <v-skeleton-loader type="article"></v-skeleton-loader>
      </v-card-text>
      <v-card-text v-else>
        <v-row>
          <v-col cols="12" md="6">
            <p><strong>服务器ID:</strong> {{ server.id }}</p>
            <p><strong>名称:</strong> {{ server.name }}</p>
            <p><strong>连接类型:</strong> {{ server.type }}</p>
          </v-col>
          <v-col cols="12" md="6">
            <p><strong>状态:</strong> 
              <v-chip :color="getStatusColor(server.status)" size="small">
                {{ server.status }}
              </v-chip>
            </p>
            <p v-if="server.type === 'stdio'"><strong>命令:</strong> {{ server.command }}</p>
            <p v-if="server.type === 'sse'"><strong>URL:</strong> {{ server.url }}</p>
            <div class="mt-2">
              <v-btn 
                :color="server.status === '已连接' ? 'error' : 'success'" 
                size="small" 
                class="mr-2"
                @click="toggleConnection"
                :loading="connecting"
              >
                {{ server.status === '已连接' ? '断开连接' : '连接' }}
              </v-btn>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
    
    <!-- 工具列表 -->
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        可用工具
        <v-spacer></v-spacer>
        <v-btn 
          size="small" 
          color="primary" 
          @click="loadTools" 
          :disabled="!isConnected || loadingTools"
          :loading="loadingTools"
        >
          刷新
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div v-if="!isConnected" class="text-center pa-4">
          <p>请先连接到服务器以查看可用工具</p>
        </div>
        <div v-else-if="loadingTools" class="text-center pa-4">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
          <p class="mt-2">加载工具列表...</p>
        </div>
        <v-alert v-else-if="tools.length === 0" type="info" variant="tonal">
          此服务器没有提供工具
        </v-alert>
        <v-expansion-panels v-else>
          <v-expansion-panel
            v-for="tool in tools"
            :key="tool.name"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-tools</v-icon>
                <span>{{ tool.name }}</span>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p v-if="tool.description"><strong>描述:</strong> {{ tool.description }}</p>
              <div class="mt-2">
                <strong>输入参数:</strong>
                <v-card variant="outlined" class="mt-1">
                  <pre>{{ formatJson(tool.inputSchema) }}</pre>
                </v-card>
              </div>
              <v-btn color="primary" size="small" class="mt-2" @click="showToolDialog(tool)">
                测试工具
              </v-btn>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
    
    <!-- 资源列表 -->
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        可用资源
        <v-spacer></v-spacer>
        <v-btn 
          size="small" 
          color="primary" 
          @click="loadResources" 
          :disabled="!isConnected || loadingResources"
          :loading="loadingResources"
        >
          刷新
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div v-if="!isConnected" class="text-center pa-4">
          <p>请先连接到服务器以查看可用资源</p>
        </div>
        <div v-else-if="loadingResources" class="text-center pa-4">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
          <p class="mt-2">加载资源列表...</p>
        </div>
        <v-alert v-else-if="resources.length === 0 && resourceTemplates.length === 0" type="info" variant="tonal">
          此服务器没有提供资源
        </v-alert>
        <div v-else>
          <h3 class="text-subtitle-1 mb-2" v-if="resources.length > 0">资源列表</h3>
          <v-list v-if="resources.length > 0">
            <v-list-item
              v-for="resource in resources"
              :key="resource.uri"
              @click="viewResource(resource)"
            >
              <template v-slot:prepend>
                <v-icon>mdi-file-document-outline</v-icon>
              </template>
              <v-list-item-title>{{ resource.name || resource.uri }}</v-list-item-title>
            </v-list-item>
          </v-list>
          
          <h3 class="text-subtitle-1 my-2" v-if="resourceTemplates.length > 0">资源模板</h3>
          <v-list v-if="resourceTemplates.length > 0">
            <v-list-item
              v-for="template in resourceTemplates"
              :key="template.uriTemplate"
            >
              <template v-slot:prepend>
                <v-icon>mdi-file-cabinet</v-icon>
              </template>
              <v-list-item-title>{{ template.name || template.uriTemplate }}</v-list-item-title>
              <v-list-item-subtitle>{{ template.uriTemplate }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>
    </v-card>
    
    <!-- 提示模板列表 -->
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        提示模板
        <v-spacer></v-spacer>
        <v-btn 
          size="small" 
          color="primary" 
          @click="loadPrompts" 
          :disabled="!isConnected || loadingPrompts"
          :loading="loadingPrompts"
        >
          刷新
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div v-if="!isConnected" class="text-center pa-4">
          <p>请先连接到服务器以查看可用提示模板</p>
        </div>
        <div v-else-if="loadingPrompts" class="text-center pa-4">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
          <p class="mt-2">加载提示模板列表...</p>
        </div>
        <v-alert v-else-if="prompts.length === 0" type="info" variant="tonal">
          此服务器没有提供提示模板
        </v-alert>
        <v-expansion-panels v-else>
          <v-expansion-panel
            v-for="prompt in prompts"
            :key="prompt.name"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-text-box-outline</v-icon>
                <span>{{ prompt.name }}</span>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p v-if="prompt.description"><strong>描述:</strong> {{ prompt.description }}</p>
              <div class="mt-2" v-if="prompt.arguments && prompt.arguments.length > 0">
                <strong>参数:</strong>
                <v-list density="compact">
                  <v-list-item v-for="arg in prompt.arguments" :key="arg.name">
                    <v-list-item-title>{{ arg.name }}</v-list-item-title>
                    <v-list-item-subtitle>{{ arg.description || '无描述' }}</v-list-item-subtitle>
                    <template v-slot:append>
                      <v-chip size="x-small" color="primary" v-if="arg.required">必填</v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </div>
              <v-btn color="primary" size="small" class="mt-2" @click="showPromptDialog(prompt)">
                查看提示
              </v-btn>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
    
    <!-- 工具测试对话框 -->
    <v-dialog v-model="toolDialog" max-width="800px">
      <v-card>
        <v-card-title>测试工具: {{ selectedTool?.name }}</v-card-title>
        <v-card-text>
          <p v-if="selectedTool?.description">{{ selectedTool.description }}</p>
          
          <v-form ref="toolForm" v-model="toolFormValid">
            <div class="tool-params my-4">
              <h3 class="text-subtitle-1 mb-2">参数:</h3>
              <v-text-field
                v-model="toolParams"
                label="参数 (JSON格式)"
                variant="outlined"
                type="text"
                hint="示例: { &quot;param1&quot;: &quot;value1&quot; }"
                persistent-hint
              ></v-text-field>
            </div>
          </v-form>
          
          <v-divider class="my-3"></v-divider>
          
          <div v-if="toolResult">
            <h3 class="text-subtitle-1 mb-2">结果:</h3>
            <v-alert
              :type="toolResultError ? 'error' : 'success'"
              variant="tonal"
              class="mb-2"
            >
              {{ toolResultError ? '工具执行失败' : '工具执行成功' }}
            </v-alert>
            <v-card variant="outlined">
              <pre>{{ formatJson(toolResult) }}</pre>
            </v-card>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" @click="toolDialog = false">关闭</v-btn>
          <v-btn 
            color="primary" 
            @click="executeSelectedTool" 
            :loading="executingTool"
            :disabled="!toolFormValid || executingTool"
          >
            执行
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 资源查看对话框 -->
    <v-dialog v-model="resourceDialog" max-width="800px">
      <v-card>
        <v-card-title>资源: {{ selectedResource?.name || selectedResource?.uri }}</v-card-title>
        <v-card-text>
          <div v-if="loadingResource" class="text-center pa-4">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
            <p class="mt-2">加载资源内容...</p>
          </div>
          <div v-else-if="resourceError" class="text-center pa-4">
            <v-alert type="error" variant="tonal">
              {{ resourceError }}
            </v-alert>
          </div>
          <div v-else-if="resourceContent.length > 0">
            <v-tabs v-model="resourceTab">
              <v-tab value="content">内容</v-tab>
              <v-tab value="info">信息</v-tab>
            </v-tabs>
            <v-window v-model="resourceTab">
              <v-window-item value="content">
                <div v-for="(content, index) in resourceContent" :key="index">
                  <div v-if="content.text" class="pa-2">
                    <pre class="resource-content">{{ content.text }}</pre>
                  </div>
                  <div v-else-if="content.blob" class="pa-2">
                    <p>二进制内容 (Base64编码)</p>
                    <v-textarea
                      :model-value="content.blob.substring(0, 200) + '...'"
                      rows="5"
                      readonly
                      variant="outlined"
                    ></v-textarea>
                  </div>
                </div>
              </v-window-item>
              <v-window-item value="info">
                <div class="pa-2">
                  <p><strong>URI:</strong> {{ selectedResource?.uri }}</p>
                  <p v-if="resourceContent[0]?.mimeType"><strong>MIME类型:</strong> {{ resourceContent[0]?.mimeType }}</p>
                </div>
              </v-window-item>
            </v-window>
          </div>
          <div v-else class="text-center pa-4">
            <v-alert type="info" variant="tonal">
              资源内容为空
            </v-alert>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="resourceDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 提示模板查看对话框 -->
    <v-dialog v-model="promptDialog" max-width="800px">
      <v-card>
        <v-card-title>提示模板: {{ selectedPrompt?.name }}</v-card-title>
        <v-card-text>
          <p v-if="selectedPrompt?.description">{{ selectedPrompt.description }}</p>
          
          <v-form ref="promptForm" v-model="promptFormValid" class="my-4">
            <h3 class="text-subtitle-1 mb-2" v-if="selectedPrompt?.arguments && selectedPrompt.arguments.length > 0">
              参数:
            </h3>
            <div v-for="arg in selectedPrompt?.arguments" :key="arg.name">
              <v-text-field
                v-model="promptArguments[arg.name]"
                :label="arg.name"
                :hint="arg.description"
                persistent-hint
                variant="outlined"
                :rules="arg.required ? [v => !!v || '此参数为必填项'] : []"
              ></v-text-field>
            </div>
          </v-form>
          
          <v-divider class="my-3"></v-divider>
          
          <div v-if="promptResult">
            <h3 class="text-subtitle-1 mb-2">提示内容:</h3>
            <v-card variant="outlined" class="pa-3">
              <div v-for="(message, index) in promptResult.messages" :key="index" class="mb-3">
                <strong>{{ message.role }}:</strong>
                <div class="pa-2 mt-1" style="background-color: rgba(0,0,0,0.05); border-radius: 4px;">
                  {{ getMessage(message) }}
                </div>
              </div>
            </v-card>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" @click="promptDialog = false">关闭</v-btn>
          <v-btn 
            color="primary" 
            @click="loadPromptContent" 
            :loading="loadingPromptContent"
            :disabled="!promptFormValid || loadingPromptContent"
          >
            获取提示内容
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
import jsonrpc from '../api/jsonrpc';

const props = defineProps<{
  serverId: string
}>();

// 服务器信息状态
const loading = ref(true);
const server = ref<any>({ id: props.serverId });
const connecting = ref(false);

// 工具、资源和提示模板状态
const tools = ref<any[]>([]);
const resources = ref<any[]>([]);
const resourceTemplates = ref<any[]>([]);
const prompts = ref<any[]>([]);
const loadingTools = ref(false);
const loadingResources = ref(false);
const loadingPrompts = ref(false);

// 计算属性
const isConnected = computed(() => server.value.status === '已连接');

// 工具测试对话框
const toolDialog = ref(false);
const selectedTool = ref<any>(null);
const toolParams = ref('{}');
const toolFormValid = ref(true);
const toolResult = ref<any>(null);
const toolResultError = ref(false);
const executingTool = ref(false);

// 资源查看对话框
const resourceDialog = ref(false);
const selectedResource = ref<any>(null);
const resourceContent = ref<any[]>([]);
const resourceTab = ref('content');
const loadingResource = ref(false);
const resourceError = ref('');

// 提示模板对话框
const promptDialog = ref(false);
const selectedPrompt = ref<any>(null);
const promptArguments = reactive<Record<string, any>>({});
const promptFormValid = ref(true);
const promptResult = ref<any>(null);
const loadingPromptContent = ref(false);

// 获取服务器详情
const loadServerDetails = async () => {
  loading.value = true;
  try {
    const servers = await jsonrpc.getMcpServers();
    const serverDetail = servers.find((s: any) => s.id === props.serverId);
    
    if (serverDetail) {
      server.value = {
        ...serverDetail,
        status: '未连接',
        args: Array.isArray(serverDetail.args) ? serverDetail.args.join(',') : serverDetail.args || ''
      };
      
      // 检查连接状态
      const connectedServers = await jsonrpc.getConnectedServers();
      if (connectedServers.servers && connectedServers.servers.includes(props.serverId)) {
        server.value.status = '已连接';
        // 加载相关数据
        await Promise.all([
          loadTools(),
          loadResources(),
          loadPrompts()
        ]);
      }
    }
  } catch (error) {
    console.error('加载服务器详情失败:', error);
  } finally {
    loading.value = false;
  }
};

// 连接或断开连接
const toggleConnection = async () => {
  connecting.value = true;
  try {
    if (server.value.status === '已连接') {
      // 断开连接
      await jsonrpc.disconnectFromServer(props.serverId);
      server.value.status = '未连接';
      // 清空相关数据
      tools.value = [];
      resources.value = [];
      resourceTemplates.value = [];
      prompts.value = [];
    } else {
      // 连接
      const result = await jsonrpc.connectToServer(props.serverId);
      if (result.success) {
        server.value.status = '已连接';
        // 加载相关数据
        await Promise.all([
          loadTools(),
          loadResources(),
          loadPrompts()
        ]);
      } else {
        server.value.status = '连接失败';
      }
    }
  } catch (error) {
    console.error('切换连接状态失败:', error);
    server.value.status = '连接错误';
  } finally {
    connecting.value = false;
  }
};

// 加载工具列表
const loadTools = async () => {
  if (!isConnected.value) return;
  
  loadingTools.value = true;
  try {
    const result = await jsonrpc.listTools(props.serverId);
    tools.value = result.tools || [];
  } catch (error) {
    console.error('加载工具列表失败:', error);
    tools.value = [];
  } finally {
    loadingTools.value = false;
  }
};

// 加载资源列表
const loadResources = async () => {
  if (!isConnected.value) return;
  
  loadingResources.value = true;
  try {
    const result = await jsonrpc.listResources(props.serverId);
    resources.value = result.resources || [];
    resourceTemplates.value = result.resourceTemplates || [];
  } catch (error) {
    console.error('加载资源列表失败:', error);
    resources.value = [];
    resourceTemplates.value = [];
  } finally {
    loadingResources.value = false;
  }
};

// 加载提示模板列表
const loadPrompts = async () => {
  if (!isConnected.value) return;
  
  loadingPrompts.value = true;
  try {
    const result = await jsonrpc.listPrompts(props.serverId);
    prompts.value = result.prompts || [];
  } catch (error) {
    console.error('加载提示模板列表失败:', error);
    prompts.value = [];
  } finally {
    loadingPrompts.value = false;
  }
};

// 显示工具测试对话框
const showToolDialog = (tool: any) => {
  selectedTool.value = tool;
  toolParams.value = '{}';
  toolResult.value = null;
  toolResultError.value = false;
  toolDialog.value = true;
};

// 执行选中的工具
const executeSelectedTool = async () => {
  if (!selectedTool.value || executingTool.value) return;
  
  executingTool.value = true;
  try {
    let params = {};
    try {
      params = JSON.parse(toolParams.value);
    } catch (e) {
      alert('参数格式不正确，请输入有效的JSON');
      return;
    }
    
    const result = await jsonrpc.callTool(props.serverId, selectedTool.value.name, params);
    toolResult.value = result;
    toolResultError.value = result.isError || false;
  } catch (error) {
    console.error('执行工具失败:', error);
    toolResult.value = { error: String(error) };
    toolResultError.value = true;
  } finally {
    executingTool.value = false;
  }
};

// 查看资源内容
const viewResource = async (resource: any) => {
  selectedResource.value = resource;
  resourceContent.value = [];
  resourceError.value = '';
  resourceTab.value = 'content';
  resourceDialog.value = true;
  
  loadingResource.value = true;
  try {
    const result = await jsonrpc.readResource(props.serverId, resource.uri);
    resourceContent.value = result.contents || [];
  } catch (error) {
    console.error('读取资源内容失败:', error);
    resourceError.value = String(error);
  } finally {
    loadingResource.value = false;
  }
};

// 显示提示模板对话框
const showPromptDialog = (prompt: any) => {
  selectedPrompt.value = prompt;
  Object.keys(promptArguments).forEach(key => delete promptArguments[key]);
  promptResult.value = null;
  promptDialog.value = true;
};

// 加载提示模板内容
const loadPromptContent = async () => {
  if (!selectedPrompt.value || loadingPromptContent.value) return;
  
  loadingPromptContent.value = true;
  try {
    const result = await jsonrpc.getPrompt(props.serverId, selectedPrompt.value.name, promptArguments);
    promptResult.value = result;
  } catch (error) {
    console.error('获取提示内容失败:', error);
    alert(`获取提示内容失败: ${error}`);
  } finally {
    loadingPromptContent.value = false;
  }
};

// 工具函数
const formatJson = (obj: any): string => {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return String(obj);
  }
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case '已连接': return 'success';
    case '连接失败': return 'error';
    case '连接错误': return 'error';
    default: return 'grey';
  }
};

const getMessage = (message: any): string => {
  if (typeof message.content === 'string') {
    return message.content;
  } else if (message.content?.text) {
    return message.content.text;
  }
  return JSON.stringify(message.content);
};

// 页面加载时获取数据
onMounted(() => {
  loadServerDetails();
});
</script>

<style scoped>
.resource-content {
  white-space: pre-wrap;
  max-height: 500px;
  overflow-y: auto;
  font-family: monospace;
}

pre {
  white-space: pre-wrap;
  overflow-x: auto;
  background-color: rgba(0, 0, 0, 0.03);
  padding: 8px;
  border-radius: 4px;
  font-family: monospace;
}
</style> 