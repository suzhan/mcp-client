import axios from 'axios';
import { type SupportedLocales } from '@/types/i18n';

// API基础路径
const API_BASE_URL = '/api/v1/i18n';

/**
 * 获取可用语言列表
 * @returns Promise with available languages and current language
 */
export async function getAvailableLanguages() {
  try {
    const response = await axios.get(`${API_BASE_URL}/languages`);
    return response.data;
  } catch (error) {
    console.error('获取可用语言失败:', error);
    throw error;
  }
}

/**
 * 获取当前语言
 * @returns Promise with current language
 */
export async function getCurrentLanguage() {
  try {
    const response = await axios.get(`${API_BASE_URL}/current`);
    return response.data.language;
  } catch (error) {
    console.error('获取当前语言失败:', error);
    throw error;
  }
}

/**
 * 设置当前语言
 * @param language 语言代码 (e.g., 'en-US', 'zh-CN')
 * @returns Promise with result
 */
export async function setCurrentLanguage(language: SupportedLocales) {
  try {
    const response = await axios.post(`${API_BASE_URL}/set`, { code: language });
    return response.data;
  } catch (error) {
    console.error(`设置语言失败 (${language}):`, error);
    throw error;
  }
}

// 导出服务
export default {
  getAvailableLanguages,
  getCurrentLanguage,
  setCurrentLanguage
}; 