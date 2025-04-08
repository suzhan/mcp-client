<template>
  <v-app>
    <v-navigation-drawer permanent app width="240">
      <!-- 应用标题和图标 -->
      <v-list-item class="py-1">
        <template v-slot:prepend>
          <v-icon icon="mdi-lan-connect" color="primary" size="default" class="app-logo"></v-icon>
        </template>
        <v-list-item-title class="app-title text-h6">{{ $t('common.appName') }}</v-list-item-title>
      </v-list-item>
      
      <v-divider></v-divider>
      
      <!-- 导航菜单 -->
      <v-list density="compact">
        <v-list-subheader density="compact" class="text-caption">{{ $t('menu.configManagement') }}</v-list-subheader>
        
        <v-list-item to="/servers" value="servers" density="compact" class="menu-item">
          <template v-slot:prepend>
            <v-icon size="small">mdi-server</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ $t('menu.servers') }}</v-list-item-title>
        </v-list-item>
        
        <v-list-item to="/providers" value="providers" density="compact" class="menu-item">
          <template v-slot:prepend>
            <v-icon size="small">mdi-brain</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ $t('menu.providers') }}</v-list-item-title>
        </v-list-item>
        
        <v-divider></v-divider>
        <v-list-subheader density="compact" class="text-caption">{{ $t('menu.sessions') }}</v-list-subheader>
        
        <v-list-item to="/chat/new" value="new-chat" density="compact" class="menu-item">
          <template v-slot:prepend>
            <v-icon size="small">mdi-plus-circle</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ $t('menu.newChat') }}</v-list-item-title>
        </v-list-item>
        
        <!-- 会话历史 - 将由会话存储提供 -->
        <v-list-item 
          v-for="session in recentSessions" 
          :key="session.id" 
          :to="`/chat/${session.id}`"
          :value="session.id"
          density="compact"
          class="menu-item"
        >
          <template v-slot:prepend>
            <v-icon size="small">mdi-chat</v-icon>
          </template>
          <v-list-item-title class="text-body-2 text-truncate">{{ session.title }}</v-list-item-title>
        </v-list-item>
      </v-list>
      
      <!-- 底部工具栏 -->
      <template v-slot:append>
        <div class="d-flex justify-space-between px-3 py-2">
          <language-switcher />
          <div class="text-caption text-medium-emphasis d-flex align-center">
            MCP Client &copy; {{ new Date().getFullYear() }}
          </div>
        </div>
      </template>
    </v-navigation-drawer>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useTheme } from 'vuetify';
import { useSessionStore } from './stores/sessions';
import { useServerStore } from './stores/servers';
import LanguageSwitcher from './components/LanguageSwitcher.vue';

// 主题管理
const theme = useTheme();
const isDarkTheme = ref(false);

const toggleTheme = () => {
  isDarkTheme.value = !isDarkTheme.value;
  theme.global.name.value = isDarkTheme.value ? 'dark' : 'light';
};

// 使用会话存储
const sessionStore = useSessionStore();
const recentSessions = ref(sessionStore.sessions);

// 获取会话数据
onMounted(async () => {
  try {
    await sessionStore.fetchSessions();
    recentSessions.value = sessionStore.sessions;
  } catch (error) {
    console.error('加载会话失败:', error);
  }
});

const serverStore = useServerStore();

// 在应用启动时开始定期检查服务器状态
onMounted(() => {
  // 开始定期检查，每5分钟检查一次
  serverStore.startPeriodicCheck(5);
});

// 在应用关闭时停止检查
onUnmounted(() => {
  serverStore.cleanupChecks();
});
</script>

<style>
.app-logo {
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
}

.app-title {
  font-weight: 600;
  color: var(--primary-color);
  background: linear-gradient(45deg, #1976d2, #42a5f5);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-size: 1.1rem !important;
}

.v-main {
  background-color: var(--background-color);
}

.menu-item {
  min-height: 32px !important;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}
</style> 