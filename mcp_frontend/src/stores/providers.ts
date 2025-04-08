import { defineStore } from 'pinia';
import { ref } from 'vue';
import jsonrpc from '../api/jsonrpc';

export interface LLMProvider {
  id?: string;
  name: string;
  type: string; // 如 'openai', 'openrouter', 'deepseek', 'qwen'
  apiKey: string;
  baseUrl?: string;
  models: string[];
  status?: 'available' | 'unavailable' | 'testing' | 'error' | 'connected';
  error?: string;
}

export const useProviderStore = defineStore('providers', () => {
  const providers = ref<LLMProvider[]>([]);
  const loading = ref(false);
  const error = ref('');

  // 获取所有供应商
  const fetchProviders = async () => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('llm.get_providers', {});
      providers.value = response || [];
      return providers.value;
    } catch (e) {
      error.value = '加载供应商列表失败';
      console.error('加载供应商列表失败', e);
      return [];
    } finally {
      loading.value = false;
    }
  };

  // 创建新供应商
  const createProvider = async (providerData: Omit<LLMProvider, 'id'>) => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('llm.create_provider', providerData);
      const newProvider = response;
      providers.value.push(newProvider);
      return newProvider;
    } catch (e) {
      error.value = '创建供应商失败';
      console.error('创建供应商失败', e);
      throw e;
    } finally {
      loading.value = false;
    }
  };

  // 更新供应商
  const updateProvider = async (providerName: string, providerData: Partial<LLMProvider>) => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('llm.update_provider', { 
        provider_name: providerName,
        ...providerData
      });
      
      const updatedProvider = response;
      const index = providers.value.findIndex(p => p.name === providerName);
      
      if (index !== -1) {
        providers.value[index] = { ...providers.value[index], ...updatedProvider };
      }
      
      return updatedProvider;
    } catch (e) {
      error.value = '更新供应商失败';
      console.error('更新供应商失败', e);
      throw e;
    } finally {
      loading.value = false;
    }
  };

  // 删除供应商
  const deleteProvider = async (providerName: string) => {
    loading.value = true;
    error.value = '';
    
    try {
      const response = await jsonrpc.call('llm.delete_provider', { provider_name: providerName });
      
      if (response.success) {
        providers.value = providers.value.filter(p => p.name !== providerName);
      }
      
      return response.success;
    } catch (e) {
      error.value = '删除供应商失败';
      console.error('删除供应商失败', e);
      throw e;
    } finally {
      loading.value = false;
    }
  };

  // 测试供应商连接
  const testConnection = async (providerName: string) => {
    loading.value = true;
    error.value = '';
    
    try {
      const provider = providers.value.find(p => p.name === providerName);
      if (provider) {
        // 更新状态为测试中
        provider.status = 'testing';
      }
      
      const response = await jsonrpc.call('llm.test_provider_connection', { provider_name: providerName });
      
      if (provider) {
        // 更新状态为可用或错误
        provider.status = response.success ? 'available' : 'error';
        provider.error = response.success ? undefined : response.message;
      }
      
      return response;
    } catch (e) {
      error.value = '测试供应商连接失败';
      console.error('测试供应商连接失败', e);
      
      const provider = providers.value.find(p => p.name === providerName);
      if (provider) {
        provider.status = 'error';
        provider.error = e instanceof Error ? e.message : String(e);
      }
      
      return { success: false, message: String(e) };
    } finally {
      loading.value = false;
    }
  };

  // 获取供应商模型列表
  const getProviderModels = async (providerName: string) => {
    loading.value = true;
    error.value = '';
    
    console.log(`开始获取供应商 "${providerName}" 的模型列表`);
    
    try {
      // 使用API调用获取模型列表
      console.log(`调用API llm.get_provider_models，参数: { provider_name: "${providerName}" }`);
      const response = await jsonrpc.call('llm.get_provider_models', { provider_name: providerName });
      
      console.log(`API响应:`, response);
      
      // 如果有模型详情，同时存储起来以便将来使用
      if (response.model_details && Array.isArray(response.model_details)) {
        console.log(`获取到详细模型信息: ${response.model_details.length}个模型`);
        // 可以在这里存储模型详情信息以供将来使用
        // 比如将模型详情存储到状态中
      }
      
      // 更新供应商的模型列表
      const provider = providers.value.find(p => p.name === providerName);
      if (provider && response.models && Array.isArray(response.models)) {
        console.log(`更新供应商"${providerName}"的模型列表:`, response.models);
        provider.models = response.models;
      } else if (!provider) {
        console.warn(`未找到名为"${providerName}"的供应商`);
      } else if (!response.models || !Array.isArray(response.models)) {
        console.warn(`API未返回有效的模型列表:`, response.models);
      }
      
      return response.models || [];
    } catch (e) {
      error.value = '获取供应商模型列表失败';
      console.error(`获取供应商"${providerName}"模型列表失败:`, e);
      
      // 如果API调用失败，返回供应商配置中的模型列表作为后备
      const provider = providers.value.find(p => p.name === providerName);
      if (provider) {
        console.log(`使用供应商"${providerName}"配置中的模型列表作为后备:`, provider.models);
        return provider?.models || [];
      } else {
        console.warn(`未找到名为"${providerName}"的供应商，无法获取后备模型列表`);
        return [];
      }
    } finally {
      loading.value = false;
    }
  };

  // 发送消息到供应商
  const sendMessage = async (providerName: string, messages: any[], model?: string) => {
    loading.value = true;
    error.value = '';
    
    try {
      return await jsonrpc.call('llm.send_message', { 
        provider_name: providerName, 
        messages,
        model
      });
    } catch (e) {
      error.value = '发送消息失败';
      console.error('发送消息失败', e);
      throw e;
    } finally {
      loading.value = false;
    }
  };

  return {
    providers,
    loading,
    error,
    fetchProviders,
    createProvider,
    updateProvider,
    deleteProvider,
    testConnection,
    getProviderModels,
    sendMessage
  };
}); 