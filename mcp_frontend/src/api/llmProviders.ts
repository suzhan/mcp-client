import jsonrpc from './jsonrpc';

export interface LLMProvider {
  id?: string;
  name: string;
  type: string; // 如 'openai', 'openrouter', 'deepseek', 'qwen'
  apiKey: string;
  baseUrl?: string;
  models: string[];
}

export const llmProviderApi = {
  /**
   * 获取所有LLM供应商
   */
  async getAll(): Promise<LLMProvider[]> {
    try {
      return await jsonrpc.getLlmProviders();
    } catch (error) {
      console.error('获取LLM供应商列表失败:', error);
      return [];
    }
  },
  
  /**
   * 获取单个LLM供应商
   */
  async getByName(providerName: string): Promise<LLMProvider | null> {
    try {
      const providers = await this.getAll();
      return providers.find(provider => provider.name === providerName) || null;
    } catch (error) {
      console.error(`获取LLM供应商 ${providerName} 失败:`, error);
      return null;
    }
  },
  
  /**
   * 创建LLM供应商
   */
  async create(providerData: LLMProvider): Promise<LLMProvider> {
    try {
      return await jsonrpc.call('llm.create_provider', providerData);
    } catch (error) {
      console.error('创建LLM供应商失败:', error);
      throw error;
    }
  },
  
  /**
   * 更新LLM供应商
   */
  async update(providerName: string, providerData: Partial<LLMProvider>): Promise<LLMProvider> {
    try {
      return await jsonrpc.call('llm.update_provider', { 
        provider_name: providerName,
        ...providerData
      });
    } catch (error) {
      console.error(`更新LLM供应商 ${providerName} 失败:`, error);
      throw error;
    }
  },
  
  /**
   * 删除LLM供应商
   */
  async delete(providerName: string): Promise<boolean> {
    try {
      return await jsonrpc.call('llm.delete_provider', { provider_name: providerName });
    } catch (error) {
      console.error(`删除LLM供应商 ${providerName} 失败:`, error);
      throw error;
    }
  },
  
  /**
   * 测试LLM供应商连接
   */
  async testConnection(providerName: string): Promise<{success: boolean; message?: string}> {
    try {
      return await jsonrpc.call('llm.test_provider_connection', { provider_name: providerName });
    } catch (error) {
      console.error(`测试LLM供应商 ${providerName} 连接失败:`, error);
      return { success: false, message: String(error) };
    }
  },
  
  /**
   * 发送消息到LLM
   */
  async sendMessage(providerName: string, messages: any[], model?: string): Promise<any> {
    try {
      return await jsonrpc.sendToLlm(providerName, messages, model);
    } catch (error) {
      console.error(`发送消息到LLM供应商 ${providerName} 失败:`, error);
      throw error;
    }
  },
  
  /**
   * 获取供应商支持的模型列表
   */
  async getModels(providerName: string): Promise<string[]> {
    try {
      console.log(`[llmProviderApi.getModels] 正在获取供应商 "${providerName}" 的模型列表`);
      
      // 直接调用API获取模型列表
      const result = await jsonrpc.call('llm.get_provider_models', { provider_name: providerName });
      console.log(`[llmProviderApi.getModels] API返回结果:`, result);
      
      // 如果API返回成功，使用返回的模型列表
      if (result && result.models && Array.isArray(result.models)) {
        console.log(`[llmProviderApi.getModels] 成功获取模型列表: ${result.models.length}个模型`);
        return result.models;
      } else {
        console.warn(`[llmProviderApi.getModels] API未返回有效的模型列表:`, result);
      }
      
      // 如果API调用成功但未返回有效结果，回退到从供应商配置获取
      console.log(`[llmProviderApi.getModels] 回退到从供应商配置获取模型列表`);
      const provider = await this.getByName(providerName);
      if (provider?.models && provider.models.length > 0) {
        console.log(`[llmProviderApi.getModels] 成功从供应商配置获取模型列表: ${provider.models.length}个模型`);
        return provider.models;
      } else {
        console.warn(`[llmProviderApi.getModels] 供应商配置中也没有模型列表`);
        return [];
      }
    } catch (error) {
      console.error(`[llmProviderApi.getModels] 获取LLM供应商 ${providerName} 的模型列表失败:`, error);
      
      // 出错时尝试从供应商配置获取
      try {
        console.log(`[llmProviderApi.getModels] 错误恢复: 尝试从供应商配置获取模型列表`);
        const provider = await this.getByName(providerName);
        if (provider?.models && provider.models.length > 0) {
          console.log(`[llmProviderApi.getModels] 成功从供应商配置获取模型列表: ${provider.models.length}个模型`);
          return provider.models;
        } else {
          console.warn(`[llmProviderApi.getModels] 供应商配置中没有模型列表`);
        }
      } catch (e) {
        console.error(`[llmProviderApi.getModels] 从供应商配置获取模型列表也失败:`, e);
      }
      return [];
    }
  }
}; 