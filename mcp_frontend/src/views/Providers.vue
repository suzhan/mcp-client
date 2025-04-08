<template>
  <v-container fluid class="pa-4">
    <h1 class="text-h5 mb-3">{{ $t('providers.title') }}</h1>
    
    <div class="mb-4 rounded-lg overflow-hidden bg-surface">
      <div class="d-flex align-center px-4 py-3">
        <span class="text-subtitle-1 font-weight-medium">{{ $t('providers.providerList') }}</span>
        <v-spacer></v-spacer>
        <v-btn 
          color="primary" 
          prepend-icon="mdi-plus" 
          @click="openProviderDialog()"
          density="comfortable"
          variant="tonal"
          class="px-3"
        >
          {{ $t('providers.addProvider') }}
        </v-btn>
      </div>
      
      <v-data-table
        :headers="headers"
        :items="providers"
        :loading="loading"
        :items-per-page="10"
        density="comfortable"
        class="elevation-0 border-t"
      >
        <template v-slot:item.models="{ item }">
          <div class="model-chips">
            <v-chip 
              v-for="(model, index) in item.models.slice(0, 3)" 
              :key="index" 
              size="x-small" 
              color="info"
              variant="flat"
              class="me-1 font-weight-medium"
            >
              {{ model }}
            </v-chip>
            <v-chip 
              v-if="item.models.length > 3" 
              size="x-small" 
              color="grey-lighten-1"
              variant="flat"
              class="font-weight-medium"
            >
              +{{ item.models.length - 3 }}
            </v-chip>
          </div>
        </template>
        
        <template v-slot:item.actions="{ item }">
          <div class="d-flex gap-1">
            <v-btn icon size="x-small" variant="text" class="action-btn" @click="openProviderDialog(item)">
              <v-icon size="small">mdi-pencil</v-icon>
            </v-btn>
            <v-btn icon size="x-small" variant="text" color="error" class="action-btn" @click="confirmDelete(item)">
              <v-icon size="small">mdi-delete</v-icon>
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </div>
    
    <!-- 供应商配置对话框 -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface">
          {{ editMode ? $t('providers.editProvider') : $t('providers.addProvider') }}
        </v-card-title>
        
        <v-card-text class="px-4 py-3">
          <v-form ref="form" v-model="formValid">
            <v-text-field
              v-model="editedProvider.name"
              :label="$t('providers.providerName')"
              required
              :disabled="editMode"
              :rules="[v => !!v || $t('errors.missingRequiredField')]"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-text-field>
            
            <v-select
              v-model="editedProvider.type"
              :label="$t('providers.providerType')"
              :items="['OpenAI', 'Anthropic', 'OpenRouter', 'DeepSeek', 'Qwen', $t('providers.other')]"
              required
              :rules="[v => !!v || $t('errors.missingRequiredField')]"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-select>
            
            <v-text-field
              v-model="editedProvider.apiKey"
              :label="$t('providers.apiKey')"
              required
              :type="showApiKey ? 'text' : 'password'"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              @click:append-inner="showApiKey = !showApiKey"
              :rules="[v => !!v || $t('errors.missingRequiredField')]"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-text-field>
            
            <v-text-field
              v-model="editedProvider.apiBase"
              :label="$t('providers.apiBaseUrl')"
              placeholder="https://api.example.com"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-text-field>
            
            <v-textarea
              v-model="modelsText"
              :label="$t('providers.modelsList')"
              :hint="$t('providers.modelsHint')"
              auto-grow
              rows="3"
              density="comfortable"
              variant="outlined"
              class="mb-2"
            ></v-textarea>
          </v-form>
        </v-card-text>
        
        <v-card-actions class="px-4 py-3">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="dialog = false" class="text-body-2">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" variant="flat" @click="saveProvider" :disabled="!formValid" class="text-body-2">{{ $t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 删除确认对话框 -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-subtitle-1 px-4 py-3 bg-surface">{{ $t('common.confirm') }}</v-card-title>
        <v-card-text class="px-4 py-3">
          {{ $t('providers.deleteConfirmMessage', { name: deleteProvider?.name }) }}
        </v-card-text>
        <v-card-actions class="px-4 py-3">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="deleteDialog = false" class="text-body-2">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="error" variant="flat" @click="deleteProviderConfirmed" class="text-body-2">{{ $t('common.delete') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import jsonrpc from '../api/jsonrpc';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

// 表格列定义
const headers = computed(() => [
  { title: t('providers.providerName'), key: 'name' },
  { title: t('providers.providerType'), key: 'type' },
  { title: t('providers.supportedModels'), key: 'models' },
  { title: t('common.actions'), key: 'actions', sortable: false }
]);

// 供应商数据
const providers = ref<any[]>([]);
const loading = ref(true);

// 表单相关
const dialog = ref(false);
const editMode = ref(false);
const formValid = ref(false);
const form = ref(null);
const showApiKey = ref(false);
const editedProvider = reactive({
  name: '',
  type: '',
  apiKey: '',
  apiBase: '',
  models: [] as string[]
});

// 模型列表文本框
const modelsText = ref('');
// 处理文本框中的模型列表
const parseModels = (text: string): string[] => {
  return text.split('\n')
    .map(model => model.trim())
    .filter(model => model !== '');
};

// 删除确认
const deleteDialog = ref(false);
const deleteProvider = ref<any>(null);

// 加载供应商列表
const loadProviders = async () => {
  loading.value = true;
  try {
    const response = await jsonrpc.getLlmProviders();
    providers.value = response || [];
  } catch (error) {
    console.error(t('providers.loadError'), error);
    // 显示错误信息
  } finally {
    loading.value = false;
  }
};

// 打开供应商对话框
const openProviderDialog = (provider?: any) => {
  if (provider) {
    // 编辑模式
    editMode.value = true;
    Object.assign(editedProvider, {
      name: provider.name,
      type: provider.type,
      apiKey: provider.apiKey || '',
      apiBase: provider.apiBase || '',
      models: provider.models || []
    });
    modelsText.value = editedProvider.models.join('\n');
  } else {
    // 添加模式
    editMode.value = false;
    Object.assign(editedProvider, {
      name: '',
      type: 'OpenAI',
      apiKey: '',
      apiBase: '',
      models: []
    });
    modelsText.value = '';
  }
  dialog.value = true;
};

// 保存供应商配置
const saveProvider = async () => {
  // 解析模型列表
  editedProvider.models = parseModels(modelsText.value);
  
  // 这里应该调用后端API保存数据
  // 实际项目中应该有一个保存配置的API
  console.log(t('providers.savingConfig'), editedProvider);
  
  // 模拟保存操作
  if (editMode.value) {
    // 更新现有供应商
    const index = providers.value.findIndex(p => p.name === editedProvider.name);
    if (index !== -1) {
      providers.value[index] = { ...editedProvider };
    }
  } else {
    // 添加新供应商
    providers.value.push({ ...editedProvider });
  }
  
  dialog.value = false;
};

// 确认删除供应商
const confirmDelete = (provider: any) => {
  deleteProvider.value = provider;
  deleteDialog.value = true;
};

// 删除供应商
const deleteProviderConfirmed = async () => {
  if (!deleteProvider.value) return;
  
  // 从列表中移除
  providers.value = providers.value.filter(p => p.name !== deleteProvider.value?.name);
  
  // 关闭对话框
  deleteDialog.value = false;
  deleteProvider.value = null;
};

// 页面加载时获取数据
onMounted(() => {
  loadProviders();
});
</script>

<style lang="scss" scoped>
.bg-surface {
  background-color: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.border-t {
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.v-data-table {
  font-size: 0.875rem;
  
  :deep(th) {
    font-size: 0.75rem !important;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.6);
  }
  
  :deep(td) {
    font-size: 0.875rem !important;
  }
}

.action-btn {
  opacity: 0.7;
  transition: opacity 0.2s ease, transform 0.2s ease;
  
  &:hover {
    opacity: 1;
    transform: translateY(-1px);
  }
}

.v-chip {
  font-size: 0.75rem !important;
}

.model-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-width: 100%;
}
</style> 