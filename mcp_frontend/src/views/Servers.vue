<template>
  <v-container fluid class="pa-4">
    <h1 class="text-h5 mb-3">{{ $t('servers.title') }}</h1>
    
    <div class="mb-4 rounded-lg overflow-hidden bg-surface">
      <div class="d-flex align-center px-4 py-3">
        <span class="text-subtitle-1 font-weight-medium">{{ $t('servers.serverList') }}</span>
        <v-spacer></v-spacer>
        <v-btn 
          color="primary" 
          prepend-icon="mdi-plus" 
          @click="openServerDialog()"
          density="comfortable"
          variant="tonal"
          class="px-3"
        >
          {{ $t('servers.addServer') }}
        </v-btn>
      </div>
      
      <v-data-table
        :headers="headers"
        :items="servers"
        :loading="loading"
        :items-per-page="10"
        density="comfortable"
        class="elevation-0 border-t"
      >
        <template v-slot:item.status="{ item }">
          <v-chip 
            :color="getStatusColor(item.status)" 
            size="x-small"
            variant="flat"
            class="font-weight-medium"
          >
            {{ getStatusText(item.status) }}
          </v-chip>
        </template>
        
        <template v-slot:item.tools_count="{ item }">
          <div class="d-flex align-center">
            {{ item.tools_count }}
            <v-btn
              v-if="item.tools_count > 0" 
              icon 
              size="x-small" 
              variant="text" 
              class="ms-1"
              @click="showToolsDetails(item)"
            >
              <v-icon size="small">mdi-information-outline</v-icon>
            </v-btn>
          </div>
        </template>
        
        <template v-slot:item.resources_count="{ item }">
          <div class="d-flex align-center">
            {{ item.resources_count }}
            <v-btn
              v-if="item.resources_count > 0" 
              icon 
              size="x-small" 
              variant="text" 
              class="ms-1"
              @click="showResourcesDetails(item)"
            >
              <v-icon size="small">mdi-information-outline</v-icon>
            </v-btn>
          </div>
        </template>
        
        <template v-slot:item.prompts_count="{ item }">
          <div class="d-flex align-center">
            {{ item.prompts_count }}
            <v-btn
              v-if="item.prompts_count > 0" 
              icon 
              size="x-small" 
              variant="text" 
              class="ms-1"
              @click="showPromptsDialog(item)"
            >
              <v-icon size="small">mdi-information-outline</v-icon>
            </v-btn>
          </div>
        </template>
        
        <template v-slot:item.actions="{ item }">
          <div class="d-flex">
            <v-btn 
              icon="mdi-pencil"
              size="small"
              variant="text"
              @click="openServerDialog(item)"
              class="mr-1"
            ></v-btn>
            <v-btn 
              icon="mdi-link"
              size="small"
              variant="text"
              @click="testConnection(item)"
              class="mr-1"
              :loading="item.testing"
            ></v-btn>
            <v-btn 
              v-if="item.resources_count > 0"
              icon="mdi-folder-open-outline"
              size="small"
              variant="text"
              @click="showResourcesDialog(item)"
              class="mr-1"
              color="primary"
            ></v-btn>
            <v-btn 
              v-if="item.prompts_count > 0"
              icon="mdi-text-box-outline"
              size="small"
              variant="text"
              @click="showPromptsDialog(item)"
              class="mr-1"
              color="primary"
            ></v-btn>
            <v-btn 
              icon="mdi-delete"
              size="small"
              variant="text"
              @click="confirmDelete(item)"
              color="error"
            ></v-btn>
          </div>
        </template>
      </v-data-table>
    </div>
    
    <!-- 服务器配置对话框 -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface">
          {{ editMode ? $t('servers.editServer') : $t('servers.addServer') }}
        </v-card-title>
        
        <v-card-text class="px-4 py-3">
          <v-form ref="form" v-model="formValid">
            <v-text-field
              v-model="editedServer.id"
              :label="$t('servers.serverId')"
              required
              :disabled="editMode"
              :rules="[v => !!v || $t('errors.missingRequiredField', { field: $t('servers.serverId') })]"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-text-field>
            
            <v-text-field
              v-model="editedServer.name"
              :label="$t('servers.serverName')"
              required
              :rules="[v => !!v || $t('errors.missingRequiredField', { field: $t('servers.serverName') })]"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-text-field>
            
            <v-select
              v-model="editedServer.type"
              :label="$t('servers.serverType')"
              :items="serverTypes"
              required
              :rules="[v => !!v || $t('errors.missingRequiredField', { field: $t('servers.serverType') })]"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-select>
            
            <div v-if="editedServer.type === 'stdio'">
              <v-text-field
                v-model="editedServer.command"
                :label="$t('servers.command')"
                required
                :rules="[v => editedServer.type !== 'stdio' || !!v || $t('errors.missingRequiredField', { field: $t('servers.command') })]"
                density="comfortable"
                variant="outlined"
                class="mb-2"
              ></v-text-field>
              
              <v-text-field
                v-model="editedServer.args"
                :label="$t('servers.arguments')"
                :hint="$t('servers.argumentsHint')"
                density="comfortable"
                variant="outlined"
                class="mb-2"
              ></v-text-field>
            </div>
            
            <div v-if="editedServer.type === 'sse'">
              <v-text-field
                v-model="editedServer.url"
                :label="$t('servers.serverUrl')"
                required
                :rules="[v => editedServer.type !== 'sse' || !!v || $t('errors.missingRequiredField', { field: $t('servers.serverUrl') })]"
                density="comfortable"
                variant="outlined"
                class="mb-2"
              ></v-text-field>
            </div>
          </v-form>
        </v-card-text>
        
        <v-card-actions class="px-4 py-3 bg-surface border-t">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="dialog = false"
          >
            {{ $t('common.cancel') }}
          </v-btn>
          <v-btn
            color="primary"
            @click="saveServer"
            :disabled="!formValid"
          >
            {{ $t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 删除确认对话框 -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface">
          {{ $t('servers.deleteServer') }}
        </v-card-title>
        <v-card-text class="px-4 py-3">
          {{ $t('servers.deleteConfirm') }}
        </v-card-text>
        <v-card-actions class="px-4 py-3 bg-surface border-t">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="deleteDialog = false"
          >
            {{ $t('common.cancel') }}
          </v-btn>
          <v-btn
            color="error"
            @click="deleteServer"
          >
            {{ $t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 工具详情对话框 -->
    <v-dialog v-model="toolsDialog" max-width="600px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface d-flex">
          {{ $t('servers.toolsTitle') }}
          <v-chip class="ml-2">{{ selectedServer?.name }}</v-chip>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-list density="compact" lines="three">
            <template v-if="toolsList && toolsList.length > 0">
              <v-list-item
                v-for="(tool, index) in toolsList"
                :key="index"
                :subtitle="tool.description"
              >
                <template v-slot:title>
                  <div class="font-weight-medium pb-1">{{ tool.name }}</div>
                </template>
              </v-list-item>
            </template>
            <v-list-item v-else>
              <template v-slot:title>
                {{ $t('servers.noTools') }}
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions class="px-4 py-3 bg-surface border-t">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="toolsDialog = false"
          >
            {{ $t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 资源详情对话框 -->
    <v-dialog v-model="resourcesDialog" max-width="600px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface d-flex">
          {{ $t('servers.resourcesTitle') }}
          <v-chip class="ml-2">{{ selectedServer?.name }}</v-chip>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-list density="compact" lines="two">
            <template v-if="resourcesList && resourcesList.length > 0">
              <v-list-item
                v-for="(resource, index) in resourcesList"
                :key="index"
                :subtitle="resource.uri"
              >
                <template v-slot:title>
                  <div class="font-weight-medium pb-1">{{ resource.name }}</div>
                </template>
              </v-list-item>
            </template>
            <v-list-item v-else>
              <template v-slot:title>
                {{ $t('servers.noResources') }}
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions class="px-4 py-3 bg-surface border-t">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="resourcesDialog = false"
          >
            {{ $t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 提示模板详情对话框 -->
    <v-dialog v-model="promptsDialog" max-width="600px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface d-flex">
          {{ $t('servers.promptsTitle') }}
          <v-chip class="ml-2">{{ selectedServer?.name }}</v-chip>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-list density="compact">
            <template v-if="promptsList && promptsList.length > 0">
              <v-list-item
                v-for="(prompt, index) in promptsList"
                :key="index"
              >
                <template v-slot:title>
                  <div class="font-weight-medium">{{ prompt }}</div>
                </template>
              </v-list-item>
            </template>
            <v-list-item v-else>
              <template v-slot:title>
                {{ $t('servers.noPrompts') }}
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions class="px-4 py-3 bg-surface border-t">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="promptsDialog = false"
          >
            {{ $t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 连接测试结果对话框 -->
    <v-dialog v-model="connectionDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface">
          {{ $t('servers.connectionTest') }}
        </v-card-title>
        <v-card-text class="px-4 py-3">
          <div class="d-flex align-center">
            <v-icon :color="connectionSuccess ? 'success' : 'error'" class="mr-2">
              {{ connectionSuccess ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            <span>{{ connectionMessage }}</span>
          </div>
          
          <div v-if="connectionSuccess && connectionDetails && connectionDetails.tools_count">
            <v-divider class="my-3"></v-divider>
            <div class="text-subtitle-2 mb-2">{{ $t('servers.availableTools') }}</div>
            
            <v-list density="compact" class="bg-surface-variant rounded">
              <v-list-item
                v-for="(tool, index) in connectionDetails.tools" 
                :key="index"
                :subtitle="tool.description"
              >
                <template v-slot:title>
                  <span class="font-weight-medium">{{ tool.name }}</span>
                </template>
              </v-list-item>
            </v-list>
          </div>
        </v-card-text>
        <v-card-actions class="px-4 py-3 bg-surface border-t">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="connectionDialog = false"
          >
            {{ $t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 全局Snackbar -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
    >
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import jsonrpc from '../api/jsonrpc';

const { t } = useI18n();

const serverTypes = [
  { title: t('servers.stdioServer'), value: 'stdio' },
  { title: t('servers.sseServer'), value: 'sse' }
];

// 表格列配置
const headers = computed(() => [
  { title: 'ID', key: 'id', sortable: true },
  { title: t('servers.serverName'), key: 'name', sortable: true },
  { title: t('servers.serverType'), key: 'type', sortable: true },
  { title: t('servers.serverStatus'), key: 'status', sortable: true },
  { title: t('servers.tools'), key: 'tools_count', sortable: true, align: 'center' },
  { title: t('servers.resources'), key: 'resources_count', sortable: true, align: 'center' },
  { title: 'Prompt', key: 'prompts_count', sortable: true, align: 'center' },
  { title: t('servers.actions'), key: 'actions', sortable: false, align: 'end' },
]);

// 服务器列表
const servers = ref([]);
const loading = ref(true);

// 对话框控制
const dialog = ref(false);
const deleteDialog = ref(false);
const toolsDialog = ref(false);
const resourcesDialog = ref(false);
const promptsDialog = ref(false);
const connectionDialog = ref(false);

// 表单控制
const form = ref(null);
const formValid = ref(false);
const editMode = ref(false);
const editedServer = ref({
  id: '',
  name: '',
  type: 'stdio',
  command: '',
  args: '',
  url: ''
});
const defaultServer = {
  id: '',
  name: '',
  type: 'stdio',
  command: '',
  args: '',
  url: ''
};

// 选中的服务器及其工具和资源
const selectedServer = ref(null);
const toolsList = ref([]);
const resourcesList = ref([]);
const promptsList = ref([]);

// 删除操作相关
const serverToDelete = ref(null);

// 连接测试相关
const connectionSuccess = ref(false);
const connectionMessage = ref('');
const connectionDetails = ref(null);

// Snackbar
const snackbar = ref({
  show: false,
  text: '',
  color: 'success'
});

// 显示消息
function showMessage(text, color = 'success') {
  snackbar.value.text = text;
  snackbar.value.color = color;
  snackbar.value.show = true;
}

// 状态颜色
function getStatusColor(status) {
  switch (status) {
    case 'online': return 'success';
    case 'offline': return 'error';
    case 'connecting': return 'warning';
    default: return 'grey';
  }
}

// 获取状态文本翻译
function getStatusText(status) {
  switch (status) {
    case 'online': return t('servers.connected');
    case 'offline': return t('servers.disconnected');
    case 'connecting': return t('servers.connecting');
    default: return status;
  }
}

// 服务器操作
function openServerDialog(server = null) {
  editMode.value = !!server;
  editedServer.value = server ? JSON.parse(JSON.stringify(server)) : JSON.parse(JSON.stringify(defaultServer));
  dialog.value = true;
}

// 获取服务器列表
async function fetchServers() {
  loading.value = true;
  try {
    const response = await jsonrpc.request('mcp.get_servers_status');
    if (response && response.servers) {
      servers.value = response.servers;
    }
  } catch (error) {
    console.error('获取服务器列表失败:', error);
    showMessage(t('errors.connectionFailed'), 'error');
  } finally {
    loading.value = false;
  }
}

// 保存服务器
async function saveServer() {
  if (!formValid.value) return;
  
  const serverData = { ...editedServer.value };
  
  // 处理参数
  if (serverData.args) {
    serverData.args = serverData.args.split(',').map(arg => arg.trim());
  }
  
  try {
    if (editMode.value) {
      // 更新服务器
      await jsonrpc.request('mcp.update_server', {
        server_id: serverData.id,
        ...serverData
      });
      showMessage(t('success.updated', { item: t('servers.serverSingular') }));
    } else {
      // 创建服务器
      await jsonrpc.request('mcp.create_server', serverData);
      showMessage(t('success.created', { item: t('servers.serverSingular') }));
    }
    
    // 刷新列表
    await fetchServers();
    dialog.value = false;
  } catch (error) {
    console.error('保存服务器失败:', error);
    showMessage(t('errors.serverError') + ': ' + error.message, 'error');
  }
}

// 确认删除服务器
function confirmDelete(server) {
  serverToDelete.value = server;
  deleteDialog.value = true;
}

// 删除服务器
async function deleteServer() {
  if (!serverToDelete.value) return;
  
  try {
    await jsonrpc.request('mcp.delete_server', {
      server_id: serverToDelete.value.id
    });
    showMessage(t('success.deleted', { item: t('servers.serverSingular') }));
    await fetchServers();
  } catch (error) {
    console.error('删除服务器失败:', error);
    showMessage(t('errors.serverError') + ': ' + error.message, 'error');
  } finally {
    deleteDialog.value = false;
    serverToDelete.value = null;
  }
}

// 测试服务器连接
async function testConnection(server) {
  if (!server) return;
  
  // 设置测试状态
  server.testing = true;
  
  try {
    const response = await jsonrpc.request('mcp.test_server_connection', {
      server_id: server.id
    });
    
    connectionSuccess.value = response.success;
    connectionMessage.value = response.message || (response.success ? t('servers.testSuccess') : t('servers.testFailed'));
    connectionDetails.value = response.details || null;
    connectionDialog.value = true;
    
    // 如果连接测试成功，刷新服务器状态
    if (response.success) {
      await fetchServers();
    }
  } catch (error) {
    console.error('测试服务器连接失败:', error);
    connectionSuccess.value = false;
    connectionMessage.value = t('errors.connectionFailed') + ': ' + error.message;
    connectionDetails.value = null;
    connectionDialog.value = true;
  } finally {
    server.testing = false;
  }
}

// 显示工具详情
function showToolsDetails(server) {
  selectedServer.value = server;
  toolsList.value = server.tools_list || [];
  toolsDialog.value = true;
}

// 显示资源详情
function showResourcesDetails(server) {
  selectedServer.value = server;
  resourcesList.value = server.resources_list || [];
  resourcesDialog.value = true;
}

// 显示资源对话框
function showResourcesDialog(server) {
  selectedServer.value = server;
  resourcesList.value = server.resources_list || [];
  resourcesDialog.value = true;
}

// 显示提示模板详情
function showPromptsDialog(server) {
  selectedServer.value = server;
  promptsList.value = server.prompts_list || [];
  promptsDialog.value = true;
}

// 在组件挂载时加载服务器列表
onMounted(async () => {
  await fetchServers();
});
</script>

<style scoped>
.border-t {
  border-top: 1px solid rgba(0, 0, 0, 0.12);
}

:deep(.v-data-table-footer) {
  border-top: 1px solid rgba(0, 0, 0, 0.12);
}
</style> 