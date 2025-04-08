<template>
  <div class="home-container">
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        <span>MCP 服务状态</span>
        <v-spacer></v-spacer>
        <v-tooltip text="刷新服务状态">
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" icon variant="text" @click="refreshServers">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
        <v-tooltip text="设置">
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" icon variant="text" to="/settings">
              <v-icon>mdi-cog</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12">
            <div v-if="serverStore.loading" class="d-flex justify-center my-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else-if="serverStore.error" class="text-center my-4 text-red">
              {{ serverStore.error }}
            </div>
            <div v-else-if="serverStore.servers.length === 0" class="text-center my-4">
              暂无配置的MCP服务器，请前往<router-link to="/settings">设置页面</router-link>添加。
            </div>
            <div v-else>
              <v-table>
                <thead>
                  <tr>
                    <th>服务名称</th>
                    <th>服务类型</th>
                    <th>状态</th>
                    <th>可用工具</th>
                    <th>资源数</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="server in serverStore.servers" :key="server.id">
                    <td>{{ server.name }}</td>
                    <td>{{ server.type }}</td>
                    <td>
                      <v-chip 
                        size="small" 
                        :color="getStatusColor(server.status)" 
                        :text="getStatusText(server.status)"
                      ></v-chip>
                    </td>
                    <td>{{ server.tools ? server.tools.length : 0 }}</td>
                    <td>{{ server.resources_count || 0 }}</td>
                    <td>
                      <div class="d-flex">
                        <v-tooltip text="查看详情">
                          <template v-slot:activator="{ props }">
                            <v-btn 
                              v-bind="props" 
                              icon 
                              variant="text" 
                              size="small" 
                              @click="openServerDetail(server)"
                            >
                              <v-icon>mdi-information</v-icon>
                            </v-btn>
                          </template>
                        </v-tooltip>
                        <v-tooltip v-if="server.status === 'online'" text="断开连接">
                          <template v-slot:activator="{ props }">
                            <v-btn 
                              v-bind="props" 
                              icon 
                              variant="text" 
                              size="small" 
                              color="red" 
                              @click="disconnectServer(server.id)"
                            >
                              <v-icon>mdi-lan-disconnect</v-icon>
                            </v-btn>
                          </template>
                        </v-tooltip>
                        <v-tooltip v-else text="连接服务器">
                          <template v-slot:activator="{ props }">
                            <v-btn 
                              v-bind="props" 
                              icon 
                              variant="text" 
                              size="small" 
                              color="success" 
                              @click="connectServer(server.id)"
                              :disabled="server.status === 'connecting'"
                            >
                              <v-icon>mdi-lan-connect</v-icon>
                            </v-btn>
                          </template>
                        </v-tooltip>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <div class="text-caption text-grey mt-2" v-if="serverStore.lastCheckedAt">
                最后更新: {{ formatDate(serverStore.lastCheckedAt) }}
              </div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card>
      <v-card-title>
        <span>会话列表</span>
        <v-spacer></v-spacer>
        <v-btn color="primary" prepend-icon="mdi-plus" to="/chat/new">创建新会话</v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12">
            <div v-if="sessionStore.loading" class="d-flex justify-center my-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else-if="sessionStore.error" class="text-center my-4 text-red">
              {{ sessionStore.error }}
            </div>
            <div v-else-if="sessionStore.sessions.length === 0" class="text-center my-4">
              暂无会话记录，点击右上角按钮创建新会话。
            </div>
            <div v-else>
              <v-list lines="two">
                <v-list-item
                  v-for="session in sessionStore.sessions"
                  :key="session.id"
                  :to="`/chat/${session.id}`"
                  color="primary"
                >
                  <template v-slot:prepend>
                    <v-avatar color="grey-lighten-1" size="40">
                      <v-icon>mdi-chat</v-icon>
                    </v-avatar>
                  </template>
                  <v-list-item-title>{{ session.title || '未命名会话' }}</v-list-item-title>
                  <v-list-item-subtitle>
                    <div class="d-flex align-center">
                      <span>{{ session.llmProvider || '-' }} / {{ session.llmModel || '-' }}</span>
                      <v-spacer></v-spacer>
                      <span class="text-caption">{{ formatDate(new Date(session.updatedAt)) }}</span>
                    </div>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 服务器详情对话框 -->
    <v-dialog v-model="serverDetailDialog" max-width="800">
      <v-card>
        <v-card-title>
          <span>服务器详情: {{ selectedServer?.name }}</span>
          <v-spacer></v-spacer>
          <v-btn icon @click="serverDetailDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text v-if="selectedServer">
          <v-row>
            <v-col cols="12" sm="6">
              <v-list-item title="服务器ID">
                <template v-slot:append>
                  <span>{{ selectedServer.id }}</span>
                </template>
              </v-list-item>
              <v-list-item title="服务器类型">
                <template v-slot:append>
                  <span>{{ selectedServer.type }}</span>
                </template>
              </v-list-item>
              <v-list-item title="状态">
                <template v-slot:append>
                  <v-chip 
                    size="small" 
                    :color="getStatusColor(selectedServer.status)" 
                    :text="getStatusText(selectedServer.status)"
                  ></v-chip>
                </template>
              </v-list-item>
              <v-list-item v-if="selectedServer.error" title="错误信息">
                <template v-slot:append>
                  <span class="text-red">{{ selectedServer.error }}</span>
                </template>
              </v-list-item>
            </v-col>
            <v-col cols="12" sm="6">
              <v-list-item v-if="selectedServer.type === 'stdio'" title="命令">
                <template v-slot:append>
                  <span>{{ selectedServer.command }}</span>
                </template>
              </v-list-item>
              <v-list-item v-if="selectedServer.type === 'stdio' && selectedServer.args" title="参数">
                <template v-slot:append>
                  <span>{{ Array.isArray(selectedServer.args) ? selectedServer.args.join(' ') : selectedServer.args }}</span>
                </template>
              </v-list-item>
              <v-list-item v-if="selectedServer.type === 'sse'" title="URL">
                <template v-slot:append>
                  <span>{{ selectedServer.url }}</span>
                </template>
              </v-list-item>
            </v-col>
          </v-row>
          
          <!-- 工具列表 -->
          <v-expansion-panels v-model="expandedPanels" variant="accordion" class="mt-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                工具列表 ({{ selectedServer.tools_list ? selectedServer.tools_list.length : 0 }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="!selectedServer.tools_list || selectedServer.tools_list.length === 0" class="text-center my-2">
                  该服务器未提供工具
                </div>
                <v-list v-else density="compact" class="bg-grey-lighten-4 rounded">
                  <v-list-item
                    v-for="(tool, index) in selectedServer.tools_list"
                    :key="index"
                    :title="tool.name"
                    :subtitle="tool.description || '无描述'"
                    class="rounded mb-1"
                  >
                    <template v-slot:prepend>
                      <v-icon icon="mdi-tools" class="me-2"></v-icon>
                    </template>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
            
            <!-- 资源列表 -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                资源列表 ({{ selectedServer.resources_list ? selectedServer.resources_list.length : 0 }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="!selectedServer.resources_list || selectedServer.resources_list.length === 0" class="text-center my-2">
                  该服务器未提供资源
                </div>
                <v-list v-else density="compact" class="bg-grey-lighten-4 rounded">
                  <v-list-item
                    v-for="(resource, index) in selectedServer.resources_list"
                    :key="index"
                    :title="resource.name"
                    :subtitle="resource.uri || '无URI'"
                    class="rounded mb-1"
                  >
                    <template v-slot:prepend>
                      <v-icon icon="mdi-file-document-outline" class="me-2"></v-icon>
                    </template>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
            
            <!-- Prompt列表 -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                Prompt列表 ({{ selectedServer.prompts_list ? selectedServer.prompts_list.length : 0 }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="!selectedServer.prompts_list || selectedServer.prompts_list.length === 0" class="text-center my-2">
                  该服务器未提供prompt
                </div>
                <v-list v-else density="compact" class="bg-grey-lighten-4 rounded">
                  <v-list-item
                    v-for="(prompt, index) in selectedServer.prompts_list"
                    :key="index"
                    :title="prompt.name"
                    :subtitle="prompt.description || '无描述'"
                    class="rounded mb-1"
                  >
                    <template v-slot:prepend>
                      <v-icon icon="mdi-text-box-outline" class="me-2"></v-icon>
                    </template>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="serverDetailDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useServerStore } from '../stores/servers';
import { useSessionStore } from '../stores/sessions';
import { formatDate } from '../utils/date';
import { useRouter } from 'vue-router';
import jsonrpc from '../api/jsonrpc';

const serverStore = useServerStore();
const sessionStore = useSessionStore();
const router = useRouter();

// 服务器详情对话框
const serverDetailDialog = ref(false);
const selectedServer = ref(null);
const expandedPanels = ref([0, 1, 2]); // 默认展开所有面板

// 初始化页面数据
onMounted(async () => {
  // 加载服务器列表并开始定期检查
  await serverStore.fetchServersWithTools();
  serverStore.startPeriodicCheck(5); // 每5分钟检查一次
  
  // 加载会话列表
  await sessionStore.fetchSessions();
});

// 组件卸载时清理定时器
onUnmounted(() => {
  serverStore.cleanupChecks();
});

// 刷新服务器状态
const refreshServers = async () => {
  await serverStore.fetchServersWithTools();
};

// 连接服务器
const connectServer = async (serverId) => {
  await serverStore.connectServer(serverId);
  // 重新获取服务器状态
  await serverStore.fetchServersWithTools();
};

// 断开服务器连接
const disconnectServer = async (serverId) => {
  await serverStore.disconnectServer(serverId);
  // 重新获取服务器状态
  await serverStore.fetchServersWithTools();
};

// 打开服务器详情
const openServerDetail = async (server) => {
  try {
    // 复制服务器详情
    selectedServer.value = { ...server };
    
    // 获取服务器状态，包括工具和资源列表
    const statusResponse = await jsonrpc.call('mcp.get_servers_status');
    const serverStatus = statusResponse.servers.find(s => s.id === server.id);
    
    if (serverStatus) {
      // 更新工具和资源列表
      selectedServer.value.tools_list = serverStatus.tools_list || [];
      selectedServer.value.resources_list = serverStatus.resources_list || [];
      selectedServer.value.prompts_list = serverStatus.prompts_list || [];
    }
    
    // 打开对话框
    serverDetailDialog.value = true;
  } catch (error) {
    console.error('获取服务器详情失败:', error);
  }
};

// 获取状态颜色
const getStatusColor = (status) => {
  switch (status) {
    case 'online': return 'success';
    case 'offline': return 'grey';
    case 'error': return 'error';
    case 'connecting': return 'warning';
    default: return 'grey';
  }
};

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'online': return '在线';
    case 'offline': return '离线';
    case 'error': return '错误';
    case 'connecting': return '连接中';
    default: return '未知';
  }
};

// 创建新会话
async function createNewSession() {
  try {
    // 生成一个包含时间戳和随机数的唯一会话标题
    const timestamp = new Date().getTime();
    const randomNum = Math.floor(Math.random() * 1000);
    const title = `会话 ${timestamp % 10000}-${randomNum}`;
    
    const newSession = await sessionStore.createSession(title);
    
    if (newSession) {
      router.push(`/chat/${newSession.id}`);
    }
  } catch (error) {
    console.error('创建会话失败', error);
  }
}
</script>

<style scoped>
.home-container {
  padding: 16px;
}
</style> 