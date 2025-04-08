<template>
  <v-container>
    <h1 class="text-h4 mb-4">{{ $t('settings.title') }}</h1>
    
    <v-card class="mb-4">
      <v-card-title>{{ $t('settings.theme') }}</v-card-title>
      <v-card-text>
        <v-switch
          v-model="darkMode"
          :label="$t('settings.dark')"
          color="primary"
          hide-details
          @change="toggleTheme"
        ></v-switch>
        
        <v-divider class="my-4"></v-divider>
        
        <v-select
          v-model="locale"
          :label="$t('settings.language')"
          :items="availableLanguages"
          item-title="name"
          item-value="code"
          variant="outlined"
          density="comfortable"
          @update:model-value="changeLocale"
        ></v-select>
      </v-card-text>
    </v-card>
    
    <v-card class="mb-4">
      <v-card-title>{{ $t('settings.logging') }}</v-card-title>
      <v-card-text>
        <v-select
          v-model="logLevel"
          label="日志级别"
          :items="logLevels"
          variant="outlined"
          density="comfortable"
        ></v-select>
        
        <v-switch
          v-model="detailedLogs"
          label="显示详细日志"
          color="primary"
          hide-details
          class="mt-4"
        ></v-switch>
      </v-card-text>
    </v-card>
    
    <v-card class="mb-4">
      <v-card-title>{{ $t('settings.advanced') }}</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="apiEndpoint"
          label="API 端点"
          variant="outlined"
          density="comfortable"
          hint="默认: /api/v1/jsonrpc"
          persistent-hint
        ></v-text-field>
        
        <v-text-field
          v-model="apiTimeout"
          label="API 超时 (毫秒)"
          variant="outlined"
          density="comfortable"
          type="number"
          class="mt-4"
        ></v-text-field>
        
        <v-btn 
          color="primary" 
          class="mt-4"
          @click="saveSettings"
        >
          {{ $t('common.save') }}
        </v-btn>
      </v-card-text>
    </v-card>
    
    <v-card class="mb-4">
      <v-card-title>关于</v-card-title>
      <v-card-text>
        <p><strong>{{ $t('common.appName') }}</strong> 版本: 0.1.0</p>
        <p>构建时间: {{ buildDate }}</p>
        <p>基于 Model Context Protocol (MCP)</p>
      </v-card-text>
    </v-card>

    <!-- 加载中的覆盖层 -->
    <v-overlay
      v-model="loading"
      class="align-center justify-center"
    >
      <v-progress-circular
        indeterminate
        size="64"
      ></v-progress-circular>
    </v-overlay>

    <!-- 消息提示 -->
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
import { ref, onMounted } from 'vue';
import { useTheme } from 'vuetify';
import { useI18n } from 'vue-i18n';
import { availableLocales } from '../locales';
import { setLocale } from '../i18n';
import { type SupportedLocales } from '../types/i18n';
import i18nService from '../api/i18nService';

const theme = useTheme();
const { locale: i18nLocale, t } = useI18n();

// 加载状态
const loading = ref(false);

// 消息提示
const snackbar = ref({
  show: false,
  text: '',
  color: 'success'
});

// 显示消息
const showMessage = (text: string, color: 'success' | 'error' | 'info' = 'success') => {
  snackbar.value.text = text;
  snackbar.value.color = color;
  snackbar.value.show = true;
};

// 主题设置
const darkMode = ref(theme.global.name.value === 'dark');
const toggleTheme = () => {
  theme.global.name.value = darkMode.value ? 'dark' : 'light';
};

// 语言设置
const locale = ref(i18nLocale.value);
const availableLanguages = availableLocales;

const changeLocale = async (newLocale: SupportedLocales) => {
  loading.value = true;
  try {
    // 更新前端语言并同步到后端
    await setLocale(newLocale, true);
    
    showMessage(t('settings.restartRequired'));
  } catch (error) {
    console.error('切换语言失败:', error);
    showMessage(t('errors.unknownError'), 'error');
    
    // 回滚UI状态
    locale.value = i18nLocale.value;
  } finally {
    loading.value = false;
  }
};

// 日志设置
const logLevel = ref('info');
const logLevels = [
  { title: '详细 (DEBUG)', value: 'debug' },
  { title: '信息 (INFO)', value: 'info' },
  { title: '警告 (WARN)', value: 'warn' },
  { title: '错误 (ERROR)', value: 'error' }
];
const detailedLogs = ref(false);

// API设置
const apiEndpoint = ref('/api/v1/jsonrpc');
const apiTimeout = ref(30000);

// 关于信息
const buildDate = ref(new Date().toLocaleDateString());

// 保存设置
const saveSettings = async () => {
  loading.value = true;
  
  try {
    // 这里应该将设置保存到本地存储或发送到服务器
    console.log('保存设置:', {
      darkMode: darkMode.value,
      locale: locale.value,
      logLevel: logLevel.value,
      detailedLogs: detailedLogs.value,
      apiEndpoint: apiEndpoint.value,
      apiTimeout: apiTimeout.value
    });
    
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // 显示保存成功提示
    showMessage(t('settings.restartRequired'));
  } catch (error) {
    console.error('保存设置失败:', error);
    showMessage(t('errors.unknownError'), 'error');
  } finally {
    loading.value = false;
  }
};

// 加载设置
onMounted(async () => {
  loading.value = true;
  
  try {
    // 从前端i18n获取当前语言
    locale.value = i18nLocale.value;
  } catch (error) {
    console.error('获取语言设置失败:', error);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
/* 组件特定样式 */
</style> 