<template>
  <div class="chat-header">
    <v-container fluid class="py-2 chat-header-container">
      <v-row align="center">
        <v-col cols="auto">
          <v-btn
            icon
            variant="text"
            to="/"
            color="primary"
            class="btn-back"
          >
            <v-icon>mdi-arrow-left</v-icon>
          </v-btn>
        </v-col>

        <v-col>
          <div class="d-flex align-center">
            <v-text-field
              v-model="title"
              variant="underlined"
              density="compact"
              :placeholder="defaultTitle"
              @blur="updateTitle"
              :hide-details="true"
              class="font-weight-bold title-field"
            ></v-text-field>
          </div>
        </v-col>

        <v-col cols="auto">
          <div class="d-flex align-center">
            <!-- 显示连接的MCP服务器 -->
            <v-tooltip
              v-if="mcpServerStatus.length > 0"
              :text="'已连接的MCP服务器: ' + mcpServerStatus.map(s => s.name).join(', ')"
            >
              <template v-slot:activator="{ props }">
                <v-chip
                  v-bind="props"
                  size="small"
                  color="success"
                  class="mr-2 elevation-1 server-chip"
                  prepend-icon="mdi-lan-connect"
                >
                  {{ mcpServerStatus.length }} 个MCP服务
                </v-chip>
              </template>
            </v-tooltip>
            <v-tooltip
              v-else
              text="无可用的MCP服务器连接"
            >
              <template v-slot:activator="{ props }">
                <v-chip
                  v-bind="props"
                  size="small"
                  color="error"
                  class="mr-2 elevation-1 server-chip"
                  prepend-icon="mdi-lan-disconnect"
                >
                  未连接MCP服务
                </v-chip>
              </template>
            </v-tooltip>

            <!-- LLM设置按钮 -->
            <v-dialog v-model="settingsDialog" max-width="500">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon
                  variant="text"
                  color="primary"
                  class="btn-action"
                >
                  <v-icon>mdi-cog</v-icon>
                </v-btn>
              </template>

              <v-card class="settings-dialog">
                <v-card-title class="settings-title">
                  <span>会话设置</span>
                  <v-spacer></v-spacer>
                  <v-btn icon @click="settingsDialog = false" class="close-btn">
                    <v-icon>mdi-close</v-icon>
                  </v-btn>
                </v-card-title>

                <v-card-text>
                  <v-select
                    v-model="selectedProvider"
                    :items="providerOptions"
                    label="LLM供应商"
                    :disabled="providerStore.loading"
                    :loading="providerStore.loading"
                    item-title="name"
                    item-value="id"
                    return-object
                    @update:model-value="updateProviderModels"
                    class="settings-field"
                  ></v-select>

                  <v-select
                    v-model="selectedModel"
                    :items="availableModels"
                    label="模型"
                    :disabled="loadingModels || !selectedProvider"
                    :loading="loadingModels"
                    @update:model-value="updateSessionSettings"
                    class="settings-field"
                  ></v-select>

                  <div class="d-flex align-center mt-4 settings-section">
                    <div class="text-body-1">采样设置</div>
                    <v-spacer></v-spacer>
                    <v-tooltip text="高级参数">
                      <template v-slot:activator="{ props }">
                        <v-btn 
                          v-bind="props" 
                          icon 
                          variant="text" 
                          size="small" 
                          @click="showAdvancedSettings = !showAdvancedSettings"
                          class="btn-toggle"
                        >
                          <v-icon>{{ showAdvancedSettings ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
                        </v-btn>
                      </template>
                    </v-tooltip>
                  </div>

                  <v-slider
                    v-model="temperature"
                    min="0"
                    max="1"
                    step="0.01"
                    label="Temperature"
                    thumb-label
                    @change="updateSessionSettings"
                    class="slider-control"
                  ></v-slider>

                  <v-expand-transition>
                    <div v-if="showAdvancedSettings" class="advanced-settings">
                      <v-slider
                        v-model="topP"
                        min="0"
                        max="1"
                        step="0.01"
                        label="Top P"
                        thumb-label
                        @change="updateSessionSettings"
                        class="slider-control"
                      ></v-slider>

                      <v-slider
                        v-model="maxTokens"
                        min="100"
                        max="4000"
                        step="100"
                        label="最大生成Token数"
                        thumb-label
                        @change="updateSessionSettings"
                        class="slider-control"
                      ></v-slider>
                    </div>
                  </v-expand-transition>
                </v-card-text>

                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn
                    color="primary"
                    variant="text"
                    @click="settingsDialog = false"
                    class="btn-confirm"
                  >
                    完成
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>

            <!-- 其他操作按钮 -->
            <v-btn
              icon
              variant="text"
              color="error"
              @click="confirmClearMessages"
              class="btn-action btn-delete"
            >
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </div>
        </v-col>
      </v-row>
    </v-container>

    <!-- 清空对话确认对话框 -->
    <v-dialog v-model="clearConfirmDialog" max-width="400">
      <v-card>
        <v-card-title>确认清空</v-card-title>
        <v-card-text>确定要清空当前会话的所有消息吗？此操作不可恢复。</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="clearConfirmDialog = false">取消</v-btn>
          <v-btn color="error" variant="text" @click="clearMessages">确认清空</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useSessionStore } from '../stores/sessions';
import { useProviderStore } from '../stores/providers';
import { useServerStore } from '../stores/servers';
import jsonrpc from '../api/jsonrpc';
import { llmProviderApi } from '../api/llmProviders';

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  },
  initialTitle: {
    type: String,
    default: ''
  }
});

const sessionStore = useSessionStore();
const providerStore = useProviderStore();
const serverStore = useServerStore();

const title = ref(props.initialTitle || '');
const defaultTitle = computed(() => props.sessionId ? '未命名会话' : '新会话');
const settingsDialog = ref(false);
const clearConfirmDialog = ref(false);
const showAdvancedSettings = ref(false);

// LLM设置
const selectedProvider = ref(null);
const selectedModel = ref('');
const availableModels = ref<string[]>([]);
const loadingModels = ref(false);
const temperature = ref(0.7);
const topP = ref(0.9);
const maxTokens = ref(2000);

// MCP服务器状态
const mcpServerStatus = computed(() => {
  // 确保只返回成功连接的服务器
  return serverStore.connectedServers.filter(server => server.status === 'online');
});

// 供应商选项
const providerOptions = computed(() => {
  return providerStore.providers;
});

// 初始化
onMounted(async () => {
  console.log("ChatHeader组件加载...");
  
  // 获取服务器状态
  await serverStore.fetchServersWithTools();
  console.log("已加载服务器状态:", serverStore.connectedServers);
  
  // 获取LLM供应商列表
  await providerStore.fetchProviders();
  console.log("已加载LLM供应商:", providerStore.providers);
  
  // 如果是现有会话，加载会话设置
  if (props.sessionId) {
    console.log(`加载会话设置: sessionId=${props.sessionId}`);
    await loadSessionSettings();
  } else {
    console.log("新会话，设置默认供应商");
    // 新会话默认选择第一个供应商
    if (providerOptions.value.length > 0) {
      selectedProvider.value = providerOptions.value[0];
      console.log("默认选择供应商:", selectedProvider.value);
      await updateProviderModels(selectedProvider.value);
    } else {
      console.warn("无可用供应商");
    }
  }
});

// 监听会话ID变化
watch(() => props.sessionId, (newId) => {
  if (newId) {
    loadSessionSettings();
  }
});

// 加载会话设置
async function loadSessionSettings() {
  try {
    if (!props.sessionId) return;
    
    console.log(`开始加载会话设置: sessionId=${props.sessionId}`);
    const session = await sessionStore.fetchSession(props.sessionId);
    console.log("获取到会话信息:", session);
    
    title.value = session.title || '';
    
    // 设置LLM供应商和模型
    if (session.llmProvider) {
      console.log(`会话指定的供应商ID: ${session.llmProvider}`);
      const provider = providerOptions.value.find(p => p.id === session.llmProvider || p.name === session.llmProvider);
      
      if (provider) {
        console.log("找到对应的供应商:", provider);
        selectedProvider.value = provider;
        
        console.log("更新供应商模型列表...");
        await updateProviderModels(provider);
        
        // 设置模型
        if (session.llmModel) {
          console.log(`会话指定的模型: ${session.llmModel}`);
          // 验证模型是否在可用列表中
          if (availableModels.value.includes(session.llmModel)) {
            selectedModel.value = session.llmModel;
            console.log(`已设置模型: ${selectedModel.value}`);
          } else {
            console.warn(`指定的模型 ${session.llmModel} 不在可用列表中, 使用第一个可用模型`);
            selectedModel.value = availableModels.value[0] || '';
          }
        } else {
          console.warn("会话未指定模型，使用第一个可用模型");
          selectedModel.value = availableModels.value[0] || '';
        }
      } else {
        console.warn(`未找到ID为 ${session.llmProvider} 的供应商`);
        // 选择第一个可用供应商
        if (providerOptions.value.length > 0) {
          selectedProvider.value = providerOptions.value[0];
          await updateProviderModels(selectedProvider.value);
        }
      }
    } else {
      console.warn("会话未指定供应商，使用第一个可用供应商");
      // 选择第一个可用供应商
      if (providerOptions.value.length > 0) {
        selectedProvider.value = providerOptions.value[0];
        await updateProviderModels(selectedProvider.value);
      }
    }
    
    // 设置采样参数
    if (session.settings) {
      temperature.value = session.settings.temperature !== undefined ? session.settings.temperature : 0.7;
      topP.value = session.settings.topP !== undefined ? session.settings.topP : 0.9;
      maxTokens.value = session.settings.maxTokens !== undefined ? session.settings.maxTokens : 2000;
      console.log("已设置采样参数:", { temperature: temperature.value, topP: topP.value, maxTokens: maxTokens.value });
    }
  } catch (error) {
    console.error('加载会话设置失败', error);
  }
}

// 更新标题
async function updateTitle() {
  if (!props.sessionId) return;
  
  try {
    await sessionStore.updateSession(props.sessionId, {
      title: title.value || defaultTitle.value
    });
  } catch (error) {
    console.error('更新标题失败', error);
  }
}

// 更新供应商对应的模型列表
async function updateProviderModels(provider) {
  if (!provider) {
    availableModels.value = [];
    selectedModel.value = '';
    return;
  }
  
  loadingModels.value = true;
  
  try {
    // 确保正确提取供应商名称，优先使用name属性
    const providerName = typeof provider === 'string' 
      ? provider 
      : provider.name || provider.id;
    
    console.log('获取模型列表，供应商信息:', {
      provider,
      providerName,
      type: typeof provider
    });
    
    // 直接调用API获取模型列表
    const result = await jsonrpc.call('llm.get_provider_models', { provider_name: providerName });
    console.log('API直接返回结果:', result);
    
    if (result && result.models && Array.isArray(result.models)) {
      availableModels.value = result.models;
      
      // 如果没有选择模型或当前选择的模型不在可用列表中，选择第一个
      if (!selectedModel.value || !availableModels.value.includes(selectedModel.value)) {
        selectedModel.value = availableModels.value[0] || '';
      }
      
      console.log('已设置模型列表:', availableModels.value, '已选择模型:', selectedModel.value);
    } 
    // 如果API没有返回模型列表，但provider对象有models属性，使用它
    else if (provider.models && provider.models.length > 0) {
      availableModels.value = provider.models;
      
      if (!selectedModel.value || !availableModels.value.includes(selectedModel.value)) {
        selectedModel.value = availableModels.value[0] || '';
      }
      
      console.log('使用提供商自带模型列表:', availableModels.value, '已选择模型:', selectedModel.value);
    }
    else {
      // 没有可用模型
      availableModels.value = [];
      selectedModel.value = '';
      console.log('无可用模型');
    }
    
    // 如果是现有会话，更新会话设置
    if (props.sessionId) {
      updateSessionSettings();
    }
  } catch (error) {
    console.error('获取模型列表失败', error);
    
    // 如果失败但provider对象有models属性，使用它
    if (provider.models && provider.models.length > 0) {
      availableModels.value = provider.models;
      
      if (!selectedModel.value || !availableModels.value.includes(selectedModel.value)) {
        selectedModel.value = availableModels.value[0] || '';
      }
      console.log('错误后使用提供商自带模型列表:', availableModels.value, '已选择模型:', selectedModel.value);
    } else {
      availableModels.value = [];
      selectedModel.value = '';
      console.log('错误且无可用模型');
    }
  } finally {
    loadingModels.value = false;
  }
}

// 更新会话设置
async function updateSessionSettings() {
  if (!props.sessionId) return;
  
  try {
    await sessionStore.updateSession(props.sessionId, {
      llmProvider: selectedProvider.value?.id || '',
      llmModel: selectedModel.value,
      settings: {
        temperature: temperature.value,
        topP: topP.value,
        maxTokens: maxTokens.value
      }
    });
  } catch (error) {
    console.error('更新会话设置失败', error);
  }
}

// 确认清空消息
function confirmClearMessages() {
  clearConfirmDialog.value = true;
}

// 清空消息
async function clearMessages() {
  if (!props.sessionId) return;
  
  try {
    await sessionStore.clearMessages(props.sessionId);
    clearConfirmDialog.value = false;
  } catch (error) {
    console.error('清空消息失败', error);
  }
}
</script>

<style>
.chat-header-container {
  background-color: rgba(255, 255, 255, 0.95);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 10px 10px 0 0;
}

.btn-back {
  transition: transform 0.2s ease;
}

.btn-back:hover {
  transform: translateX(-2px);
}

.title-field {
  font-size: 1.2rem;
  font-weight: 500;
  color: #333;
  transition: all 0.2s ease;
}

.title-field:focus-within {
  color: #1976d2;
}

.server-chip {
  transition: all 0.2s ease;
  font-weight: 500;
}

.server-chip:hover {
  transform: scale(1.05);
}

.btn-action {
  transition: all 0.2s ease;
  margin: 0 4px;
}

.btn-action:hover {
  transform: scale(1.1);
}

.btn-delete:hover {
  background-color: rgba(244, 67, 54, 0.1);
}

.settings-dialog {
  border-radius: 12px;
  overflow: hidden;
}

.settings-title {
  background-color: #f5f7fa;
  padding: 16px;
  font-weight: 500;
}

.settings-field {
  margin-bottom: 16px;
}

.settings-section {
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding-top: 12px;
  margin-top: 8px;
  font-weight: 500;
}

.btn-toggle {
  opacity: 0.7;
}

.btn-toggle:hover {
  opacity: 1;
}

.slider-control {
  padding-top: 12px;
}

.advanced-settings {
  background-color: rgba(0, 0, 0, 0.02);
  padding: 12px;
  border-radius: 8px;
  margin-top: 12px;
}

.btn-confirm {
  font-weight: 500;
}

.close-btn {
  transition: all 0.2s ease;
}

.close-btn:hover {
  transform: rotate(90deg);
}
</style> 